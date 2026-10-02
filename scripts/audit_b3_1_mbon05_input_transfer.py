"""Audit the saved B3.1 matched pair and its selective target trace."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from project_b.checkpoint.codec import _canonical, _decode, _encode
from project_b.mvp_c1.feedback import NoteWindow
from project_b.mvp_c1.first_action_audit import (
    game_events_from_mvp_ledger, reconstruct_first_actions)


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/figures/b3_1_mbon05_input_transfer"


def read(path: Path):
    return _decode(json.loads(path.read_text(encoding="utf-8")))


def main() -> None:
    protocol_path = ROOT / "configs/b3_1_mbon05_input_transfer.json"
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    receipt = read(OUT / "receipt.json")
    if (receipt["protocol_sha256"] != hashlib.sha256(protocol_path.read_bytes()).hexdigest()
            or receipt["status"] != "FAIL" or not receipt["matched_start"] or
            not receipt["baseline_b3_ledger_reproduced"] or
            not receipt["selective_balance_verified"] or
            not receipt["one_target_intervention_and_frozen_weights"]):
        raise AssertionError("B3.1 receipt or gate identity differs")
    if hashlib.sha256((OUT / "parent_cut_1000/state.json").read_bytes()).hexdigest() != \
            receipt["parent_checkpoint_sha256"]:
        raise AssertionError("B3.1 parent checkpoint differs")
    b3_rows = read(ROOT / "docs/figures/b3_controllability_v2/arm_results.json")
    b3_baseline = next(r for r in b3_rows if (r["seed"], r["level"], r["arm"]) ==
                       (31001, "nominal", "weight_1.0"))
    notes = (NoteWindow(**protocol["note"]),)
    parsed = {}
    for row in receipt["arms"]:
        arm = row["arm"]
        if arm not in protocol["arms"] or row["start_state_sha256"] != \
                receipt["parent_state_sha256"]:
            raise AssertionError("B3.1 arm did not start at the parent cut")
        files = {"ledger": OUT / f"{arm}_ledger.json",
                 "selective_trace": OUT / f"{arm}_selective_trace.json",
                 "source_arrivals": OUT / f"{arm}_mbon05_source_arrivals.json",
                 "first_action_audit": OUT / f"{arm}_first_action.json"}
        for key, path in files.items():
            if hashlib.sha256(path.read_bytes()).hexdigest() != row[f"{key}_sha256"]:
                raise AssertionError(f"B3.1 {arm} {key} digest differs")
        ledger = read(files["ledger"])
        trace = read(files["selective_trace"])
        arrivals = read(files["source_arrivals"])
        audit = reconstruct_first_actions(notes, game_events_from_mvp_ledger(ledger),
                                          protocol["end_us"])
        if _canonical(_encode(audit.as_dict())) != files["first_action_audit"].read_bytes():
            raise AssertionError("B3.1 independent first action differs")
        if arrivals != [event for event in ledger if event[0] ==
                        "output_chemical_arrival" and event[2] == 10495]:
            raise AssertionError("B3.1 source-tagged arrival extraction differs")
        raw_spikes = [event[1] for event in ledger if event[0] == "spike" and
                      event[2] == 10495 and 100_000 <= event[1] <= 900_000]
        if raw_spikes != row["cue_mbon05_spike_times_us"] or raw_spikes:
            raise AssertionError("B3.1 MBON05 spike endpoint differs")
        if (not trace or len(trace) != row["selective_trace_ticks"] or
                any(b["time_us"] <= a["time_us"] for a, b in zip(trace, trace[1:])) or
                max(t["mbon05_voltage_before_arrivals_and_threshold"] for t in trace
                    if t["time_us"] >= 100_000) != row["max_cue_mbon05_voltage"] or
                row["max_cue_mbon05_voltage"] >= 1.0 or
                not math.isfinite(row["max_abs_interval_balance_error"]) or
                row["max_abs_interval_balance_error"] > 1e-12):
            raise AssertionError("B3.1 trace, threshold or balance differs")
        parsed[arm] = {"row": row, "ledger": ledger, "trace": trace,
                       "arrivals": arrivals}
    if set(parsed) != set(protocol["arms"]):
        raise AssertionError("B3.1 arm coverage differs")
    baseline = parsed["baseline"]
    off = parsed["apl_to_mbon05_off"]
    if (baseline["row"]["ledger_sha256"] != b3_baseline["ledger_sha256"] or
            baseline["ledger"] != off["ledger"] or
            baseline["arrivals"] != off["arrivals"] or
            baseline["row"]["apl_current_integral"] >= 0 or
            off["row"]["apl_current_integral"] != 0 or
            baseline["row"]["first_down_us"] != off["row"]["first_down_us"]):
        raise AssertionError("B3.1 baseline reproduction or one-target effect differs")
    for a, b in zip(baseline["trace"], off["trace"]):
        for key in ("time_us", "mbon05_external_current", "mbon05_synaptic_state",
                    "apl_graded_state", "mbon05_refractory_until_us"):
            if a[key] != b[key]:
                raise AssertionError(f"B3.1 non-target trace diverged: {key}")
        if b["declared_apl_current"] != 0 or a["declared_apl_current"] > 0:
            raise AssertionError("B3.1 APL output was not disabled at target")
    result = {"stage_id": "MVP-B3.1", "status": "PASS_RAW_AUDIT_OF_FAILED_GATE",
              "matched_parent_state_sha256": receipt["parent_state_sha256"],
              "B3_baseline_reproduced": True,
              "raw_event_ledgers_identical": True,
              "target_arrivals_identical": True,
              "non_target_trace_inputs_identical": True,
              "baseline_peak_voltage": baseline["row"]["max_cue_mbon05_voltage"],
              "apl_off_peak_voltage": off["row"]["max_cue_mbon05_voltage"],
              "threshold": 1.0,
              "baseline_apl_current_integral": baseline["row"]["apl_current_integral"],
              "apl_off_current_integral": off["row"]["apl_current_integral"]}
    target = OUT / "independent_audit.json"
    if target.exists():
        raise FileExistsError("B3.1 audit exists")
    target.write_bytes(_canonical(_encode(result)))
    print(json.dumps({"status": result["status"],
                      "baseline_peak": result["baseline_peak_voltage"],
                      "apl_off_peak": result["apl_off_peak_voltage"]}, sort_keys=True))


if __name__ == "__main__":
    main()
