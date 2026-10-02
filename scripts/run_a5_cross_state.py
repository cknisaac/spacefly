"""A5 outcome-blind fixture capture, exact replay, and common frozen panel."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from project_b.checkpoint.codec import _canonical, _encode
from project_b.checkpoint.frozen import FrozenPolicySnapshot
from project_b.mvp_c1.cross_state import select_checkpoints
from project_b.mvp_c1.feedback import NoteWindow
from project_b.mvp_c1.runtime import MvpSession
from project_b.mvp_c1.source import load_mvp_circuit


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/a5_cross_state_contract.json"
OUT = ROOT / "docs/figures/a5_cross_state"


def digest(value) -> str:
    return hashlib.sha256(_canonical(_encode(value))).hexdigest()


def save_json(path: Path, value) -> str:
    if path.exists():
        raise FileExistsError(f"preserve prior A5 artifact: {path}")
    payload = _canonical(_encode(value))
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def declared() -> tuple[dict, tuple, tuple[NoteWindow, ...]]:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    fixture = contract["fixture"]
    runs = tuple((item["run_id"], item["seed"]) for item in fixture["runs"])
    selected = select_checkpoints(contract, horizon_us=fixture["horizon_us"], runs=runs)
    notes = tuple(NoteWindow(**item) for item in fixture["notes"])
    return contract, selected, notes


def capture() -> dict:
    contract, selected, notes = declared()
    if OUT.exists():
        raise FileExistsError("A5 fixture directory already exists; preserve prior run")
    OUT.mkdir(parents=True)
    contract_sha = hashlib.sha256(CONTRACT.read_bytes()).hexdigest()
    schedule = {
        "schema": contract["selection"]["schema"],
        "contract_sha256": contract_sha,
        "horizon_us": contract["fixture"]["horizon_us"],
        "selections": [asdict(item) for item in selected],
        "note_schedule_sha256": digest([asdict(note) for note in notes]),
    }
    schedule_sha = save_json(OUT / "selection_manifest.json", schedule)
    circuit = load_mvp_circuit(ROOT)
    rows = []
    for run_id, seed in ((r["run_id"], r["seed"]) for r in contract["fixture"]["runs"]):
        original = MvpSession(circuit, ROOT, notes, seed=seed)
        run_selections = [item for item in selected if item.run_id == run_id]
        for item in run_selections:
            original.run_until(item.checkpoint_us)
            checkpoint_name = f"{item.run_id}_{item.phase}_checkpoint"
            checkpoint_sha = original.save(OUT / checkpoint_name)
            rows.append({
                **asdict(item), "status": "CAPTURED",
                "checkpoint_path": checkpoint_name,
                "checkpoint_state_sha256": checkpoint_sha,
                "identity_sha256": digest(original.identity),
                "identity": original.identity,
                "source_sha256": original.identity["source_connections_sha256"],
                "config_sha256": original.identity["resolved_config_sha256"],
                "interface_sha256": digest({key: original.identity[key] for key in (
                    "renderer_and_note_schedule_sha256", "ruleset_and_metric_sha256",
                    "B2_design_sha256", "B2_runtime_mask_sha256")}),
                "source_state_spike_total": int(original.spike_counts.sum()),
            })
        original.run_until(contract["fixture"]["horizon_us"])
        final_state_sha = digest(original.state())
        final_ledger_sha = hashlib.sha256(original.ledger_bytes()).hexdigest()
        for row in (item for item in rows if item["run_id"] == run_id):
            restored = MvpSession(circuit, ROOT, notes, seed=seed)
            restored.load(OUT / row["checkpoint_path"])
            if digest(restored.state()) != row["checkpoint_state_sha256"]:
                raise AssertionError("restored cut state differs")
            restored.run_until(contract["fixture"]["horizon_us"])
            if (digest(restored.state()) != final_state_sha or
                    hashlib.sha256(restored.ledger_bytes()).hexdigest() != final_ledger_sha):
                raise AssertionError("cross-state continuation differs")
            row.update(status="PASS", continuation_end_us=restored.time_us,
                       continuation_state_sha256=final_state_sha,
                       continuation_ledger_sha256=final_ledger_sha)
    if len(rows) != len(selected) or any(row["status"] != "PASS" for row in rows):
        raise AssertionError("A5.2 selection coverage or replay failed")
    receipt = {"stage": "A5.2", "status": "PASS", "scope": contract["scope"],
               "contract_sha256": contract_sha, "selection_manifest_sha256": schedule_sha,
               "rows": rows}
    save_json(OUT / "capture_receipt.json", receipt)
    return receipt


def _weight_saturation(session: MvpSession) -> bool:
    rule = session.rule
    for slot, weight in rule._plastic_by_slot.items():
        initial = rule._initial_by_slot[slot]
        if (weight <= initial * rule.parameters.minimum_weight_factor or
                weight >= initial * rule.parameters.maximum_weight_factor):
            return True
    return False


def _frozen_arm(circuit, policy: FrozenPolicySnapshot, notes, *, seed: int,
                end_us: int, ledger_path: Path) -> dict:
    session = MvpSession(circuit, ROOT, notes, seed=seed, frozen_policy=policy)
    initial_weights = session.rule.state()["selected_plastic_weights_by_kc_source_id"]
    if (session.time_us != 0 or int(session.spike_counts.sum()) != 0 or
            session.rule.enabled or session.task.teaching_enabled):
        raise AssertionError("panel frozen arm is not fresh and disabled")
    session.run_until(end_us)
    if (session.rule.state()["selected_plastic_weights_by_kc_source_id"] != initial_weights or
            session.task.feedback.pulse_records or
            any(row[0] == "pam_delivery" for row in session.ledger)):
        raise AssertionError("frozen panel changed weights or delivered teaching")
    ledger_sha = save_json(ledger_path, session.ledger)
    return {"status": "PASS", "ledger_sha256": ledger_sha,
            "event_counts": dict(Counter(row[0] for row in session.ledger)),
            "spike_total": int(session.spike_counts.sum()),
            "motor_events": sum(row[0] == "motor" for row in session.ledger),
            "first_action_outcomes": [asdict(x) for x in session.task.first_action.outcomes],
            "pending_event_counts": {"chemical": len(session.chemical_queue),
                                     "apl": len(session.apl_queue),
                                     "sensory": len(session.encoder._queue)},
            "selected_weight_state_sha256": digest(initial_weights),
            "weights_unchanged": True, "teaching_disabled": True}


def panel() -> dict:
    contract, selected, training_notes = declared()
    capture_receipt = json.loads((OUT / "capture_receipt.json").read_text(encoding="utf-8"))
    if (capture_receipt["contract_sha256"] != hashlib.sha256(CONTRACT.read_bytes()).hexdigest() or
            len(capture_receipt["rows"]) != len(selected) or
            [(r["run_id"], r["phase"], r["checkpoint_us"]) for r in capture_receipt["rows"]] !=
            [(x.run_id, x.phase, x.checkpoint_us) for x in selected]):
        raise ValueError("capture receipt does not match predeclared selection")
    circuit = load_mvp_circuit(ROOT)
    panel_config = contract["panel"]
    panel_notes = tuple(NoteWindow(**item) for item in panel_config["notes"])
    initial = MvpSession(circuit, ROOT, training_notes, seed=contract["fixture"]["runs"][0]["seed"])
    initial_policy = FrozenPolicySnapshot.capture(initial.rule)
    initial_policy_sha = save_json(OUT / "initial_selected_policy.json", asdict(initial_policy))
    panel_rows = []
    for item, captured in zip(selected, capture_receipt["rows"], strict=True):
        row = {"run_id": item.run_id, "phase": item.phase,
               "checkpoint_us": item.checkpoint_us, "selection_reason": item.reason,
               "panel_schema": panel_config["schema"], "panel_config_sha256": digest(panel_config),
               "source_state_spike_total": captured["source_state_spike_total"]}
        try:
            source = MvpSession(circuit, ROOT, training_notes, seed=item.seed)
            source.load(OUT / captured["checkpoint_path"])
            policy = FrozenPolicySnapshot.capture(source.rule)
            row["captured_policy_sha256"] = save_json(
                OUT / f"{item.run_id}_{item.phase}_selected_policy.json", asdict(policy))
            row["activity_flags"] = {"silent": int(source.spike_counts.sum()) == 0,
                                     "saturated": _weight_saturation(source)}
            row["arms"] = {}
            for arm, arm_policy in (("captured_selected_policy", policy),
                                    ("initial_selected_policy", initial_policy)):
                row["arms"][arm] = _frozen_arm(
                    circuit, arm_policy, panel_notes, seed=panel_config["seed"],
                    end_us=panel_config["end_us"],
                    ledger_path=OUT / f"{item.run_id}_{item.phase}_{arm}_ledger.json")
            row["status"] = "PASS"
        except Exception as exc:
            row["status"] = "FAIL"
            row["error"] = f"{type(exc).__name__}: {exc}"
        panel_rows.append(row)
    complete = (len(panel_rows) == len(selected) and
                all(row["status"] == "PASS" and
                    set(row.get("arms", {})) == set(panel_config["arms"])
                    for row in panel_rows))
    receipt = {"stage": "A5.3", "status": "PASS" if complete else "FAIL",
               "scope": contract["scope"], "initial_policy_sha256": initial_policy_sha,
               "panel_config_sha256": digest(panel_config), "rows": panel_rows}
    save_json(OUT / "panel_receipt.json", receipt)
    if not complete:
        raise AssertionError("A5.3 panel has failed or missing state rows")
    save_json(OUT / "receipt.json", {"stage": "A5", "status": "PASS",
                                     "A5.1": "PASS", "A5.2": "PASS", "A5.3": "PASS",
                                     "capture_receipt_sha256": hashlib.sha256(
                                         (OUT / "capture_receipt.json").read_bytes()).hexdigest(),
                                     "panel_receipt_sha256": hashlib.sha256(
                                         (OUT / "panel_receipt.json").read_bytes()).hexdigest()})
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("capture", "panel"))
    args = parser.parse_args()
    receipt = capture() if args.phase == "capture" else panel()
    print(json.dumps({"stage": receipt["stage"], "status": receipt["status"],
                      "states": len(receipt["rows"])}, sort_keys=True))


if __name__ == "__main__":
    main()
