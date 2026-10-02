"""Independent arithmetic, state, historical-reference and frozen-probe audit."""

from __future__ import annotations

import json
import math
from collections import deque
from pathlib import Path

from project_b.experiments import TinyLaneSession
from scripts.audit_cue_300ms_threshold_cohort_diagnostic import (
    assert_same_nonweight_state, check_probe, sha, weights,
)
from scripts.a10_signed_first_action_credit_gate import reference
from scripts.exploration_map_diagnostic import load_long_rows, load_rows
from scripts.long_continuation import event_record
from scripts.successive_update_interference_diagnostic import LONG_PROTOCOL, ORIGINAL_LEDGER, make_config

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/a10_signed_first_action_credit_gate.json"
OUT = ROOT / "docs/figures/a10_signed_first_action_credit_gate"
A81 = ROOT / "docs/figures/a8_1_first_action_reward_attribution/result.json"
BRANCHES = ("no_update", "historical_legacy_update", "locked_a10_update")


def main() -> None:
    spec = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    result = json.loads((OUT / "result.json").read_text(encoding="utf-8"))
    status = json.loads((OUT / "status.json").read_text(encoding="utf-8"))
    a81 = json.loads(A81.read_text(encoding="utf-8"))
    assert spec["one_based_outcomes"] == [372, 373, 377]
    assert spec["branches"] == list(BRANCHES)
    assert result["status"] == status["status"] == "complete"
    assert result["protocol_sha256"] == status["protocol_sha256"] == sha(PROTOCOL)
    assert result["a81_result_sha256"] == sha(A81)
    assert status["result_sha256"] == sha(OUT / "result.json")
    assert all(sha(ROOT / path) == digest for path, digest in result["source_sha256"].items())
    assert result["exact_historical_training_events_replayed"] == 377
    total_events = total_downs = total_rises = 0
    cases = {}
    long_rows = load_long_rows()
    source = long_rows[2002]
    replay = TinyLaneSession(make_config(2002, load_rows(ORIGINAL_LEDGER), long_rows,
                                          json.loads(LONG_PROTOCOL.read_text(encoding="utf-8"))))
    action_times = {a81["selected"][str(k)]["first_down"]["time_us"]: k
                    for k in spec["one_based_outcomes"]}
    recent: deque[tuple[int,int]] = deque()
    replay_matches = 0
    while replay.resolved_count < 377:
        replay.step()
        t = replay.simulator.current_time_us
        recent.extend((t,j) for j in replay.layout.motor if replay.simulator.spiked_this_tick[j])
        while recent and recent[0][0] <= t - replay.readout.window_us:
            recent.popleft()
        if t in action_times:
            outcome = action_times[t]
            row = result["cases"][str(outcome)]["action_record"]
            assert replay.resolved_count == outcome-1
            assert replay.game.result().actions[-1].action.time_us == t
            assert replay.game.result().actions[-1].disposition.value == "null_press"
            assert row["motor_spike_events_in_window"] == [list(x) for x in recent]
            assert row["eligibility_at_first_down"] == [replay.plasticity.eligibility_at(slot,t)
                                                        for slot in replay.layout.plastic_slots]
            assert row["expected_utility_at_first_down"] == replay.reward.predictor.expected_utility
            replay_matches += 1
    assert replay_matches == 3
    assert [event_record(replay,i) for i in range(377)] == source["training_events"][:377]
    for outcome in spec["one_based_outcomes"]:
        item = result["cases"][str(outcome)]
        action = item["action_record"]
        first = a81["selected"][str(outcome)]
        assert action["first_down_time_us"] == first["first_down"]["time_us"]
        assert action["first_down_disposition"] == first["first_down"]["disposition"] == "null_press"
        assert action["first_action_utility"] == -1
        assert action["expected_utility_at_first_down"] == first["expected_utility_before"]
        assert action["first_action_rpe"] == first["diagnostic_first_action_rpe"]
        events = [tuple(x) for x in action["motor_spike_events_in_window"]]
        assert all(action["first_down_time_us"]-action["window_us"] < t <= action["first_down_time_us"]
                   for t, _ in events)
        no_ref, full_ref, geo, no_source, full_source = reference(outcome)
        no_path = OUT / f"{outcome}_no_update_checkpoint.pkl"
        full_path = OUT / f"{outcome}_historical_legacy_update_checkpoint.pkl"
        a10_path = OUT / f"{outcome}_locked_a10_update_checkpoint.pkl"
        assert no_path.read_bytes() == no_source
        assert full_path.read_bytes() == full_source
        no = TinyLaneSession.from_trusted_checkpoint_bytes(no_source)
        full = TinyLaneSession.from_trusted_checkpoint_bytes(full_source)
        candidate = TinyLaneSession.from_trusted_checkpoint_bytes(a10_path.read_bytes())
        for x in (full, candidate):
            assert_same_nonweight_state(no, x)
        motor = no.layout.motor
        assert set(map(int, action["motor_spike_counts"])) == set(motor)
        counts = {j: sum(cell == j for _, cell in events) for j in motor}
        assert {str(j): counts[j] for j in motor} == action["motor_spike_counts"]
        assert sum(counts.values()) >= no.readout.on_threshold
        mean_count = sum(counts.values()) / len(motor)
        assert action["mean_motor_spike_count"] == mean_count
        assert action["on_threshold"] == no.readout.on_threshold
        assert action["edge_slots"] == list(no.layout.plastic_slots)
        assert len(action["edge_slots"]) == 480
        e = action["eligibility_at_first_down"]
        z = [e_i*(counts[no.layout.graph.post_indices[slot]]-mean_count)/no.readout.on_threshold
             for slot,e_i in zip(no.layout.plastic_slots,e)]
        assert z == action["signed_action_eligibility"]
        # A zero vector is a genuine A-C3 failure in a synchronous motor state,
        # not an audit failure. Preserve it in the receipt.
        eta = no.plasticity.parameters.eta
        raw = [eta*v*action["first_action_rpe"] for v in z]
        assert raw == action["raw_proposed_update_mv"]
        before = weights(no)
        assert before == geo["weights_before_mv"]
        lo, hi = no.plasticity.parameters.w_min_mv, no.plasticity.parameters.w_max_mv
        proposed = [w+d for w,d in zip(before,raw)]
        after = [min(hi,max(lo,v)) for v in proposed]
        applied = [a-b for a,b in zip(after,before)]
        geom = item["candidate_geometry"]
        assert geom["weights_before_mv"] == before
        assert geom["weights_after_mv"] == after == weights(candidate)
        assert geom["raw_update_mv"] == raw
        assert geom["applied_update_mv"] == applied
        assert geom["positive_signed_edges"] == sum(v>0 for v in z)
        assert geom["negative_signed_edges"] == sum(v<0 for v in z)
        assert geom["proposed_lower_clips"] == sum(v<lo for v in proposed)
        assert geom["proposed_upper_clips"] == sum(v>hi for v in proposed)
        for key, vector in (("raw_norm",raw),("applied_norm",applied)):
            assert math.isclose(geom[key]["l1_mv"],sum(abs(v) for v in vector),abs_tol=1e-9)
            assert math.isclose(geom[key]["l2_mv"],math.sqrt(sum(v*v for v in vector)),abs_tol=1e-9)
            assert geom[key]["nonzero"] == sum(v!=0 for v in vector)
        legacy_expected = [min(hi,max(lo,w+d)) for w,d in zip(before,geo["raw_proposed_update_mv"])]
        assert weights(full) == legacy_expected
        note_times = tuple(no_ref["checkpoint_time_us"]+x for x in no_ref["relative_note_offsets_us"])
        gains = tuple(no_ref["cue_gains"])
        for branch,path,reference_probe in (("no_update",no_path,no_ref),
                                            ("historical_legacy_update",full_path,full_ref),
                                            ("locked_a10_update",a10_path,None)):
            row = item["branches"][branch]
            assert row["checkpoint_sha256"] == sha(path)
            assert row["probe"] == reference_probe if reference_probe is not None else True
            n,a,r = check_probe(row,path.read_bytes(),note_times,gains)
            total_events += n
            total_downs += a
            total_rises += r
        no_t = item["branches"]["no_update"]["first_note"]["first_on_threshold_rise_us"]
        a10_t = item["branches"]["locked_a10_update"]["first_note"]["first_on_threshold_rise_us"]
        delta = a10_t-no_t if no_t is not None and a10_t is not None else None
        assert delta == item["candidate_minus_no_crossing_us"]
        cases[str(outcome)] = {"first_crossing_delta_us": delta,
                               "classification": item["classification"],
                               "signed_credit_available": any(v>0 for v in z) and any(v<0 for v in z),
                               "signed_positive_edges": sum(v>0 for v in z),
                               "signed_negative_edges": sum(v<0 for v in z)}
    contract_c3 = "FAIL" if any(not x["signed_credit_available"] for x in cases.values()) else "PASS"
    receipt = {"status":"passed", "stage":"A10", "cases":cases,
               "action_trace_replay_matches":replay_matches,
               "historical_training_events_replayed":377,
               "contract_c3":contract_c3,
               "a10_stage_result":"FAIL" if contract_c3 == "FAIL" else result["classification"],
               "branches":9, "frozen_notes_replayed":total_events,
               "down_actions_replayed":total_downs,
               "motor_on_rises_recomputed":total_rises,
               "protocol_sha256":sha(PROTOCOL), "result_sha256":sha(OUT/"result.json")}
    (OUT/"audit.json").write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(receipt,indent=2))


if __name__ == "__main__":
    main()
