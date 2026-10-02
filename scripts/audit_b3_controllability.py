"""Independently audit saved B3 raw ledgers without rerunning the neural model."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from project_b.checkpoint.codec import _canonical, _decode, _encode
from project_b.mvp_c1.feedback import NoteWindow
from project_b.mvp_c1.first_action_audit import (
    game_events_from_mvp_ledger, reconstruct_first_actions)


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/figures/b3_controllability_v2"


def read(path: Path):
    return _decode(json.loads(path.read_text(encoding="utf-8")))


def main() -> None:
    protocol_path = ROOT / "configs/b3_controllability_protocol.json"
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    receipt = read(OUT / "receipt.json")
    arms = read(OUT / "arm_results.json")
    pairings = read(OUT / "pairing_records.json")
    notes = (NoteWindow(**protocol["note"]),)
    anatomy = json.loads((ROOT / "docs/figures/b1_mvp_pathway_rule_selection/selected_anatomy.json")
                         .read_text(encoding="utf-8"))
    kc_ids = set(anatomy["kc_source_ids"])
    expected = {(seed, level, arm)
                for seed in protocol["seeds"]
                for level in ["nominal", "low", "high"]
                for arm in (["weight_0.5", "weight_1.0", "weight_1.5"] +
                            (protocol["nominal_single_mechanism_controls"]
                             if level == "nominal" else []))}
    if (len(arms) != 39 or {(r["seed"], r["level"], r["arm"]) for r in arms} != expected
            or receipt["protocol_sha256"] != hashlib.sha256(protocol_path.read_bytes()).hexdigest()):
        raise AssertionError("B3 arm/protocol coverage differs")
    details = []
    for row in arms:
        stem = f"seed_{row['seed']}_{row['level']}_{row['arm']}"
        ledger_path = OUT / f"{stem}_ledger.json"
        audit_path = OUT / f"{stem}_first_action.json"
        if (hashlib.sha256(ledger_path.read_bytes()).hexdigest() != row["ledger_sha256"] or
                hashlib.sha256(audit_path.read_bytes()).hexdigest() != row["first_action_audit_sha256"]):
            raise AssertionError(f"B3 raw artifact hash differs: {stem}")
        ledger = read(ledger_path)
        audit = reconstruct_first_actions(notes, game_events_from_mvp_ledger(ledger),
                                          protocol["end_us"])
        if (_canonical(_encode(audit.as_dict())) != audit_path.read_bytes() or
                audit.rows[0].first_down_us != row["first_down_us"]):
            raise AssertionError(f"B3 A3 first-action reconstruction differs: {stem}")
        spikes = {source: sum(event[0] == "spike" and event[2] == source
                              for event in ledger)
                  for source in (10495, 11145, 10713)}
        cue_dn = sum(event[0] == "spike" and event[2] == 10713 and
                     notes[0].visible_from_us <= event[1] <= notes[0].hit_us
                     for event in ledger)
        if cue_dn != row["cue_dn_spike_count"] or any(e[0] == "pam_pulse" for e in ledger):
            raise AssertionError(f"B3 spike or teaching record differs: {stem}")
        kc_to_mbon05_cue = sum(e[7] for e in ledger
                               if e[0] == "output_chemical_arrival" and e[2] == 10495
                               and notes[0].visible_from_us <= e[1] <= notes[0].hit_us)
        kc_spikes = sum(e[0] == "spike" and e[2] in kc_ids for e in ledger)
        details.append({"seed": row["seed"], "level": row["level"], "arm": row["arm"],
                        "mbon05_spikes": spikes[10495], "mbon20_spikes": spikes[11145],
                        "dnp42_spikes": spikes[10713],
                        "kc_to_mbon05_cue_arrival_sum": kc_to_mbon05_cue,
                        "first_down_us": row["first_down_us"],
                        "first_action_category": audit.rows[0].category,
                        "background_only_no_kc": (kc_spikes == 0 if row["arm"] ==
                                                  "background_only" else None)})
    by_key = {(r["seed"], r["level"], r["arm"]): r for r in details}
    for seed in protocol["seeds"]:
        low, mid, high = (by_key[seed, "nominal", f"weight_{x:.1f}"]
                          for x in protocol["selected_weight_factors"])
        if not (low["kc_to_mbon05_cue_arrival_sum"] <
                mid["kc_to_mbon05_cue_arrival_sum"] <
                high["kc_to_mbon05_cue_arrival_sum"]):
            raise AssertionError("selected-weight intervention did not reach MBON05")
        baseline_start = next(r["start_state_sha256"] for r in arms if
                              (r["seed"], r["level"], r["arm"]) ==
                              (seed, "nominal", "weight_1.0"))
        for arm in protocol["nominal_single_mechanism_controls"]:
            matched = next(r["start_state_sha256"] for r in arms if
                           (r["seed"], r["level"], r["arm"]) == (seed, "nominal", arm))
            if matched != baseline_start:
                raise AssertionError("single-mechanism arm changed initial state")
        if not by_key[seed, "nominal", "background_only"]["background_only_no_kc"]:
            raise AssertionError("background-only arm still had KC spikes")
    if (any(r["mbon05_spikes"] for r in details) or
            len(pairings) != 6 or not all(p["correct_and_confined"] for p in pairings) or
            receipt["status"] != "FAIL"):
        raise AssertionError("B3 raw events do not support the reported failed gate")
    audit = {"stage_id": "MVP-B3", "status": "PASS_RAW_AUDIT_OF_FAILED_GATE",
             "raw_arms_checked": len(details), "all_mbon05_silent": True,
             "all_nominal_controls_matched_start": True,
             "selected_weight_intervention_reached_mbon05": True,
             "background_only_no_kc_spikes": True,
             "all_pairing_checks_signed_and_confined": True,
             "arm_details": details}
    target = OUT / "independent_audit.json"
    if target.exists():
        raise FileExistsError("B3 independent audit already exists")
    target.write_bytes(_canonical(_encode(audit)))
    print(json.dumps({"status": audit["status"], "arms": len(details),
                      "all_mbon05_silent": True}, sort_keys=True))


if __name__ == "__main__":
    main()
