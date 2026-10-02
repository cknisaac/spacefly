"""Audit pinned A2 ledgers under the predeclared A3 first-action contract."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from enum import Enum
from pathlib import Path

from project_b.mvp_c1.feedback import NoteWindow
from project_b.mvp_c1.first_action_audit import (
    WINDOW_US, compare_owner_outcomes, game_events_from_mvp_ledger,
    reconstruct_first_actions)
from project_b.mvp_c1.task_session import MvpTaskSession
from project_b.osu.types import KeyAction, KeyActionKind


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "configs/a3_first_action_audit_inputs.json"
CONTRACT = ROOT / "configs/a3_first_action_metric_contract.json"
OUT = ROOT / "docs/figures/a3_first_action"


def _plain(value):
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _save(path: Path, value) -> str:
    payload = (json.dumps(_plain(value), sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False) + "\n").encode()
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError(f"A3 existing evidence differs: {path.name}")
    else:
        path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def main() -> None:
    config = json.loads(INPUT.read_text(encoding="utf-8"))
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if (config["contract_id"] != contract["contract_id"] or
            config["success_window_us_inclusive"] != WINDOW_US or
            contract["success_window_us_inclusive"] != WINDOW_US):
        raise ValueError("A3 input and metric contract differ")
    a2 = json.loads((ROOT / "docs/figures/a2_mvp_coupled/receipt.json")
                    .read_text(encoding="utf-8"))
    b2 = json.loads((ROOT / "configs/b2_candidate1_design.json")
                    .read_text(encoding="utf-8"))
    visible_lead_us = b2["renderer"]["visible_lead_us"]
    OUT.mkdir(parents=True, exist_ok=True)
    case_receipts = []
    for case in config["cases"]:
        if case["case_id"] == "A2-untrained-replay":
            expected_hash = a2["coupled_replay"]["uninterrupted_ledger_sha256"]
            checkpoint = json.loads((ROOT / "docs/figures/a2_mvp_coupled/"
                                     "committed_cut_139000/state.json")
                                    .read_text(encoding="utf-8"))
            expected_notes = checkpoint["task"]["identity"]["notes"]
        elif case["case_id"] == "A2-controlled-policy-frozen-fresh":
            expected_hash = a2["fresh_frozen"]["ledger_sha256"]
            expected_notes = [
                {"note_id": item["note_id"], "hit_us": item["note_time_us"],
                 "visible_from_us": item["note_time_us"] - visible_lead_us}
                for item in a2["fresh_frozen"]["judgements"]]
            if [n["note_id"] for n in expected_notes] != a2["fresh_frozen"]["fresh_note_ids"]:
                raise ValueError("A2 frozen note IDs and judgements differ")
        else:
            raise ValueError("unrecognized predeclared A3 case")
        if (case["raw_ledger_sha256"] != expected_hash or
                case["notes"] != expected_notes):
            raise ValueError("A3 schedule or ledger differs from A2 pinned evidence")
        path = ROOT / case["raw_ledger"]
        if _sha(path) != case["raw_ledger_sha256"]:
            raise ValueError("A2 raw ledger differs from predeclared input")
        notes = tuple(NoteWindow(**item) for item in case["notes"])
        ledger = json.loads(path.read_text(encoding="utf-8"))
        raw_events = game_events_from_mvp_ledger(ledger)
        audit = reconstruct_first_actions(notes, raw_events, case["audit_end_us"])
        owner = MvpTaskSession(notes, teaching_enabled=case["teaching_enabled"])
        for event in raw_events:
            if event["kind"] == "action":
                raw = event["record"]["action"]
                owner.apply_action(KeyAction(raw["time_us"], raw["lane"],
                                             KeyActionKind(raw["kind"])))
        owner.advance_to(case["audit_end_us"])
        if _plain(owner.game.state()["events"]) != raw_events:
            raise AssertionError("independent game replay differs from A2 raw game events")
        owner.first_action.finish(case["audit_end_us"])
        compare_owner_outcomes(audit, owner.first_action.outcomes)
        stem = case["case_id"]
        rows_sha = _save(OUT / f"{stem}_per_note.json", [asdict(x) for x in audit.rows])
        summary_sha = _save(OUT / f"{stem}_summary.json", audit.summary)
        case_receipts.append({
            "case_id": stem, "raw_ledger_sha256": case["raw_ledger_sha256"],
            "raw_game_events": len(raw_events), "notes": len(audit.rows),
            "game_replay_exact": True, "first_action_owner_agreement": True,
            "per_note_sha256": rows_sha, "summary_sha256": summary_sha,
            "primary_success_count": audit.summary["first_down_success_count"],
            "primary_denominator": audit.summary["eligible_note_denominator"],
            "missing_action_count": audit.summary["missing_action_count"],
            "secondary_positive_judgement_notes": audit.summary[
                "secondary_positive_judgement_notes"],
        })
    receipt = {"stage_id": "A3", "status": "PASS infrastructure",
               "metric_contract_sha256": _sha(CONTRACT),
               "predeclared_inputs_sha256": _sha(INPUT),
               "cases": case_receipts,
               "scope": "raw A2 action/judgement audit; no neural run, training or B3"}
    _save(OUT / "receipt_v2.json", receipt)
    print(json.dumps(case_receipts, sort_keys=True))


if __name__ == "__main__":
    main()
