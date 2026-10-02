"""Locked A10 diagnostic vector transplant; never edits the production learner."""

from __future__ import annotations

import json
import math
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from project_b.experiments import TinyLaneSession
from scripts.cue_300ms_necessity_diagnostic import probe_with_readout_trace
from scripts.cue_300ms_saturation_contrast_diagnostic import first_note
from scripts.cue_300ms_threshold_cohort_diagnostic import assert_same_state_except_weights, weights
from scripts.exploration_map_diagnostic import load_long_rows, load_rows
from scripts.long_continuation import atomic_json, event_record, sha
from scripts.successive_update_interference_diagnostic import (
    LONG_PROTOCOL, ORIGINAL_LEDGER, make_config,
)

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/a10_signed_first_action_credit_gate.json"
OUT = ROOT / "docs/figures/a10_signed_first_action_credit_gate"
A81 = ROOT / "docs/figures/a8_1_first_action_reward_attribution/result.json"
A5 = ROOT / "docs/figures/cue_300ms_necessity"
SAT = ROOT / "docs/figures/cue_300ms_saturation_contrast"
BRANCHES = ("no_update", "historical_legacy_update", "locked_a10_update")


def norm(vector: list[float]) -> dict:
    return {"l1_mv": sum(abs(x) for x in vector),
            "l2_mv": math.sqrt(sum(x*x for x in vector)),
            "nonzero": sum(x != 0 for x in vector)}


def reference(outcome: int) -> tuple[dict, dict, dict, bytes, bytes]:
    """Return previously saved no/full probes and exact no/full checkpoints."""
    if outcome == 373:
        result = json.loads((A5 / "result.json").read_text(encoding="utf-8"))
        no, full = (A5 / "no_update_checkpoint.pkl").read_bytes(), (A5 / "real_full_checkpoint.pkl").read_bytes()
        return result["branches"]["no_update"]["probe"], result["branches"]["real_full"]["probe"], result["pre_update_geometry"], no, full
    result = json.loads((SAT / "result.json").read_text(encoding="utf-8"))["cases"][str(outcome)]
    no = (SAT / f"{outcome}_no_update_checkpoint.pkl").read_bytes()
    full = (SAT / f"{outcome}_real_full_checkpoint.pkl").read_bytes()
    return result["branches"]["no_update"]["probe"], result["branches"]["real_full"]["probe"], result["pre_update_geometry"], no, full


def main() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert protocol["one_based_outcomes"] == [372, 373, 377]
    assert protocol["branches"] == list(BRANCHES)
    a81 = json.loads(A81.read_text(encoding="utf-8"))
    long_rows = load_long_rows()
    source = long_rows[2002]
    session = TinyLaneSession(make_config(2002, load_rows(ORIGINAL_LEDGER),
                                          long_rows, json.loads(LONG_PROTOCOL.read_text(encoding="utf-8"))))
    OUT.mkdir(parents=True, exist_ok=True)
    atomic_json(OUT / "status.json", {"status": "running", "protocol_sha256": sha(PROTOCOL)})
    motor = session.layout.motor
    window_us = session.readout.window_us
    recent: deque[tuple[int, int]] = deque()
    captures = {}
    target_times = {a81["selected"][str(k)]["first_down"]["time_us"]: k for k in protocol["one_based_outcomes"]}
    while session.resolved_count < 377:
        session.step()
        time_us = session.simulator.current_time_us
        for j in motor:
            if session.simulator.spiked_this_tick[j]:
                recent.append((time_us, j))
        while recent and recent[0][0] <= time_us - window_us:
            recent.popleft()
        if time_us not in target_times:
            continue
        outcome = target_times[time_us]
        source_action = a81["selected"][str(outcome)]["first_down"]
        action = session.game.result().actions[-1]
        assert action.action.time_us == time_us == source_action["time_us"]
        assert action.disposition.value == source_action["disposition"] == "null_press"
        assert session.resolved_count == outcome - 1
        assert [event_record(session, i) for i in range(outcome-1)] == source["training_events"][:outcome-1]
        counts = {j: sum(cell == j for _, cell in recent) for j in motor}
        assert sum(counts.values()) == session.readout.on_threshold or sum(counts.values()) > session.readout.on_threshold
        assert sum(counts.values()) == source_action["spike_count_in_window"] if "spike_count_in_window" in source_action else sum(counts.values()) == session.decisions[-1].spike_count_in_window
        slots = session.layout.plastic_slots
        e = [session.plasticity.eligibility_at(slot, time_us) for slot in slots]
        expected = session.reward.predictor.expected_utility
        rpe = -1.0 - expected
        assert rpe == a81["selected"][str(outcome)]["diagnostic_first_action_rpe"]
        mean_count = sum(counts.values()) / len(motor)
        z = [e_i * (counts[session.layout.graph.post_indices[slot]] - mean_count)
             / session.readout.on_threshold for slot, e_i in zip(slots, e)]
        raw = [session.plasticity.parameters.eta * value * rpe for value in z]
        captures[outcome] = {"first_down_time_us": time_us,
                             "first_down_disposition": action.disposition.value,
                             "first_action_utility": -1.0,
                             "expected_utility_at_first_down": expected,
                             "first_action_rpe": rpe,
                             "window_us": window_us,
                             "motor_spike_events_in_window": list(recent),
                             "motor_spike_counts": counts,
                             "mean_motor_spike_count": mean_count,
                             "on_threshold": session.readout.on_threshold,
                             "edge_slots": list(slots), "eligibility_at_first_down": e,
                             "signed_action_eligibility": z,
                             "raw_proposed_update_mv": raw,
                             "action_checkpoint_sha256": sha_bytes(session.checkpoint_bytes())}
    assert set(captures) == {372, 373, 377}
    assert [event_record(session, i) for i in range(377)] == source["training_events"][:377]
    results = {}
    for outcome in protocol["one_based_outcomes"]:
        action = captures[outcome]
        no_ref, full_ref, geo, no_data, full_data = reference(outcome)
        no = TinyLaneSession.from_trusted_checkpoint_bytes(no_data)
        full = TinyLaneSession.from_trusted_checkpoint_bytes(full_data)
        assert_same_state_except_weights(no, full)
        before = weights(no)
        assert before == geo["weights_before_mv"]
        assert action["edge_slots"] == list(no.layout.plastic_slots)
        assert no.plasticity.parameters.eta == geo["eta"]
        lo, hi = no.plasticity.parameters.w_min_mv, no.plasticity.parameters.w_max_mv
        proposed = [w+d for w,d in zip(before, action["raw_proposed_update_mv"])]
        after = [min(hi, max(lo, w)) for w in proposed]
        candidate = TinyLaneSession.from_trusted_checkpoint_bytes(no_data)
        for slot, value in zip(action["edge_slots"], after):
            candidate.plasticity._weights[slot] = value
        assert_same_state_except_weights(no, candidate)
        applied = [a-b for a,b in zip(after, before)]
        times = tuple(no_ref["checkpoint_time_us"] + offset for offset in no_ref["relative_note_offsets_us"])
        gains = tuple(no_ref["cue_gains"])
        records = {}
        for name, state, data, previous in (("no_update", no, no_data, no_ref),
                                            ("historical_legacy_update", full, full_data, full_ref),
                                            ("locked_a10_update", candidate, candidate.checkpoint_bytes(), None)):
            probe, trace = probe_with_readout_trace(data, times, gains)
            if previous is not None:
                assert probe == previous
            first = first_note(probe, trace)
            records[name] = {"checkpoint_sha256": sha_bytes(data),
                             "weights_after_mv": weights(state),
                             "probe": probe, "readout_trace": trace, "first_note": first}
            (OUT / f"{outcome}_{name}_checkpoint.pkl").write_bytes(data)
            print(json.dumps({"outcome": outcome, "branch": name,
                              "first_crossing_us": first["first_on_threshold_rise_us"],
                              "first_down_us": first["first_down_us"],
                              "good_plus": probe["metrics"]["good_or_better_count"],
                              "utility": probe["metrics"]["mean_utility"]}), flush=True)
        no_first = records["no_update"]["first_note"]
        a10_first = records["locked_a10_update"]["first_note"]
        no_t, a10_t = no_first["first_on_threshold_rise_us"], a10_first["first_on_threshold_rise_us"]
        delta = a10_t - no_t if no_t is not None and a10_t is not None else None
        silence = a10_first["first_down_us"] is None
        no_count = sum(a["time_us"] <= times[0]+no.game.windows.expiry_offset_us for a in records["no_update"]["probe"]["down_actions"])
        candidate_count = sum(a["time_us"] <= times[0]+no.game.windows.expiry_offset_us for a in records["locked_a10_update"]["probe"]["down_actions"])
        if silence or delta is None or delta <= -1000:
            classification = "FAIL"
        elif delta >= protocol["prediction"]["meaningful_delay_us"] and candidate_count == no_count:
            classification = "PASS"
        else:
            classification = "INCONCLUSIVE"
        results[str(outcome)] = {"action_record": action,
                                 "legacy_geometry": geo,
                                 "candidate_geometry": {
                                     "weights_before_mv": before, "weights_after_mv": after,
                                     "raw_update_mv": action["raw_proposed_update_mv"],
                                     "applied_update_mv": applied,
                                     "raw_norm": norm(action["raw_proposed_update_mv"]),
                                     "applied_norm": norm(applied),
                                     "positive_signed_edges": sum(x>0 for x in action["signed_action_eligibility"]),
                                     "negative_signed_edges": sum(x<0 for x in action["signed_action_eligibility"]),
                                     "proposed_lower_clips": sum(x<lo for x in proposed),
                                     "proposed_upper_clips": sum(x>hi for x in proposed),
                                     "at_lower_after": sum(x==lo for x in after),
                                     "at_upper_after": sum(x==hi for x in after)},
                                 "branches": records, "candidate_minus_no_crossing_us": delta,
                                 "no_first_note_down_count": no_count,
                                 "candidate_first_note_down_count": candidate_count,
                                 "classification": classification}
    statuses = [r["classification"] for r in results.values()]
    overall = "FAIL" if "FAIL" in statuses else "PASS" if all(x == "PASS" for x in statuses) else "INCONCLUSIVE"
    result = {"status": "complete", "study_id": protocol["study_id"],
              "protocol_sha256": sha(PROTOCOL), "a81_result_sha256": sha(A81),
              "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in (
                  ROOT/"src/project_b/experiments/tiny_brain.py",
                  ROOT/"src/project_b/plasticity/eligibility.py",
                  ROOT/"src/project_b/motor/fixed_readout.py",
                  ROOT/"scripts/a10_signed_first_action_credit_gate.py")},
              "exact_historical_training_events_replayed": 377,
              "cases": results, "classification": overall,
              "completed_utc": datetime.now(timezone.utc).isoformat()}
    atomic_json(OUT / "result.json", result)
    atomic_json(OUT / "status.json", {"status": "complete", "protocol_sha256": sha(PROTOCOL),
                                      "result_sha256": sha(OUT / "result.json")})
    print(json.dumps({"classification": overall, "case_statuses": dict(zip(results, statuses))}), flush=True)


def sha_bytes(data: bytes) -> str:
    import hashlib
    return hashlib.sha256(data).hexdigest()


if __name__ == "__main__":
    main()
