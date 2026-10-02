"""One fixed first-action update-direction transplant at seed 2002:373."""

from __future__ import annotations

import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

from project_b.experiments import TinyLaneSession
from scripts.a8_1_first_action_reward_attribution import OUT as A81_OUT
from scripts.cue_300ms_necessity_diagnostic import probe_with_readout_trace
from scripts.cue_300ms_saturation_contrast_diagnostic import first_note
from scripts.cue_300ms_threshold_cohort_diagnostic import assert_same_state_except_weights, weights
from scripts.exploration_map_diagnostic import load_long_rows, load_rows
from scripts.long_continuation import atomic_json, event_record, sha
from scripts.successive_update_interference_diagnostic import (
    LONG_PROTOCOL, ORIGINAL_LEDGER, make_config, timing_summary,
)


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/a8_2_first_action_local_direction.json"
A5 = ROOT / "docs/figures/cue_300ms_necessity"
OUT = ROOT / "docs/figures/a8_2_first_action_local_direction"
BRANCHES = ("no_update", "historical_real_full", "first_action_candidate_5_percent",
            "first_action_candidate_full")


def norm(values: list[float]) -> dict:
    return {"l1_mv": sum(abs(x) for x in values),
            "l2_mv": math.sqrt(sum(x*x for x in values)),
            "max_abs_mv": max((abs(x) for x in values), default=0.0)}


def main() -> None:
    spec = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert spec["seed"] == 2002 and spec["one_based_outcome"] == 373
    assert spec["small_fraction_of_raw_candidate"] == 0.05
    assert tuple(spec["branches"]) == BRANCHES
    a81 = json.loads((A81_OUT / "result.json").read_text(encoding="utf-8"))
    first_record = a81["selected"]["373"]
    assert first_record["first_down"]["time_us"] == spec["first_down_time_us"]
    assert first_record["first_down"]["disposition"] == "null_press"
    assert first_record["diagnostic_first_action_rpe"] == spec["diagnostic_first_action_rpe"]
    a5 = json.loads((A5 / "result.json").read_text(encoding="utf-8"))
    assert a5["seed"] == 2002 and a5["one_based_outcome"] == 373
    assert sha(A5 / "result.json") == json.loads((A5 / "status.json").read_text())["result_sha256"]
    long_rows = load_long_rows()
    source = long_rows[2002]
    config = make_config(2002, load_rows(ORIGINAL_LEDGER), long_rows,
                         json.loads(LONG_PROTOCOL.read_text(encoding="utf-8")))
    session = TinyLaneSession(config)
    OUT.mkdir(parents=True, exist_ok=True)
    atomic_json(OUT / "status.json", {"status": "running", "protocol_sha256": sha(PROTOCOL)})
    session.run_until(spec["first_down_time_us"])
    assert session.resolved_count == 372
    assert [event_record(session,i) for i in range(372)] == source["training_events"][:372]
    note_downs = [r for r in session.game.result().actions
                  if r.action.kind.value == "down" and
                  config.explicit_note_times_us[372]-500_000 <= r.action.time_us
                  <= config.explicit_note_times_us[372]+session.game.windows.expiry_offset_us]
    assert len(note_downs) == 1
    assert note_downs[0].action.time_us == spec["first_down_time_us"]
    assert note_downs[0].disposition.value == "null_press"
    first_bytes = session.checkpoint_bytes()
    (OUT / "first_down_checkpoint.pkl").write_bytes(first_bytes)
    slots = session.layout.plastic_slots
    assert len(slots) == 480
    first_e = [session.plasticity.eligibility_at(slot,spec["first_down_time_us"])
               for slot in slots]
    first_w = weights(session)
    eta = session.plasticity.parameters.eta
    candidate_raw = [eta*e*spec["diagnostic_first_action_rpe"] for e in first_e]
    real_apply = session.simulator.apply_dopamine
    captured = {}

    def intercept(dopamine: float):
        assert session.resolved_count == 372
        del session.simulator.apply_dopamine
        try:
            captured["pre_bytes"] = session.checkpoint_bytes()
            captured["dopamine"] = dopamine
            changes = real_apply(dopamine)
        finally:
            session.simulator.apply_dopamine = intercept
        return changes

    session.simulator.apply_dopamine = intercept
    while session.resolved_count < 373:
        session.step()
    del session.simulator.apply_dopamine
    assert event_record(session,372) == source["training_events"][372]
    assert captured["dopamine"] == first_record["actual_rpe"]
    saved_pre = TinyLaneSession.from_trusted_checkpoint_bytes(
        (A5 / "pre_update_checkpoint.pkl").read_bytes())
    replay_pre = TinyLaneSession.from_trusted_checkpoint_bytes(captured["pre_bytes"])
    assert weights(saved_pre) == weights(replay_pre) == first_w
    assert_same_state_except_weights(saved_pre,replay_pre)
    no_bytes = (A5 / "no_update_checkpoint.pkl").read_bytes()
    full_bytes = (A5 / "real_full_checkpoint.pkl").read_bytes()
    no = TinyLaneSession.from_trusted_checkpoint_bytes(no_bytes)
    full = TinyLaneSession.from_trusted_checkpoint_bytes(full_bytes)
    assert weights(no) == first_w
    assert_same_state_except_weights(no,full)
    lo,hi = no.plasticity.parameters.w_min_mv,no.plasticity.parameters.w_max_mv
    sessions = {"no_update":no,"historical_real_full":full}
    geometry = {}
    for name,fraction in (("first_action_candidate_5_percent",0.05),
                          ("first_action_candidate_full",1.0)):
        clone = TinyLaneSession.from_trusted_checkpoint_bytes(no_bytes)
        proposed = [w+fraction*d for w,d in zip(first_w,candidate_raw)]
        after = [min(hi,max(lo,w)) for w in proposed]
        for slot,value in zip(slots,after):
            clone.plasticity._weights[slot] = value
        assert_same_state_except_weights(no,clone)
        sessions[name] = clone
        applied = [a-w for a,w in zip(after,first_w)]
        geometry[name] = {"fraction":fraction,"raw_delta_mv":[fraction*d for d in candidate_raw],
                          "weights_after_mv":after,"applied_delta_mv":applied,
                          "raw_norm":norm([fraction*d for d in candidate_raw]),
                          "applied_norm":norm(applied),
                          "proposed_below_min_edges":sum(v<lo for v in proposed),
                          "proposed_above_max_edges":sum(v>hi for v in proposed),
                          "lower_bound_edges_after":sum(w==lo for w in after),
                          "upper_bound_edges_after":sum(w==hi for w in after)}
    reference = a5["branches"]["no_update"]["probe"]
    note_times = tuple(reference["checkpoint_time_us"]+x
                       for x in reference["relative_note_offsets_us"])
    gains = tuple(reference["cue_gains"])
    branches = {}
    for name in BRANCHES:
        data = sessions[name].checkpoint_bytes()
        (OUT / f"{name}_checkpoint.pkl").write_bytes(data)
        probe,trace = probe_with_readout_trace(data,note_times,gains)
        if name == "no_update":
            assert probe == a5["branches"]["no_update"]["probe"]
        if name == "historical_real_full":
            assert probe == a5["branches"]["real_full"]["probe"]
        first = first_note(probe,trace)
        branches[name] = {"checkpoint_sha256":hashlib.sha256(data).hexdigest(),
                          "weights_after_mv":weights(sessions[name]),
                          "probe":probe,"readout_trace":trace,
                          "first_note":first,"timing":timing_summary(probe)}
        print(json.dumps({"branch":name,"first_crossing_us":first["first_on_threshold_rise_us"],
                          "first_down_us":first["first_down_us"],
                          "good_plus":probe["metrics"]["good_or_better_count"],
                          "utility":probe["metrics"]["mean_utility"]}),flush=True)
    no_t = branches["no_update"]["first_note"]["first_on_threshold_rise_us"]
    small_t = branches["first_action_candidate_5_percent"]["first_note"]["first_on_threshold_rise_us"]
    full_t = branches["first_action_candidate_full"]["first_note"]["first_on_threshold_rise_us"]
    small_useful = small_t is not None and branches["first_action_candidate_5_percent"]["first_note"]["first_down_us"] is not None and small_t >= no_t+1000
    if small_t is None or branches["first_action_candidate_5_percent"]["first_note"]["first_down_us"] is None or small_t < no_t:
        classification = "DIRECTION_NOT_SUPPORTED"
    elif small_t == no_t:
        classification = "INCONCLUSIVE_NO_CROSSING_MOVEMENT"
    elif small_useful and (full_t is None or full_t <= no_t):
        classification = "SMALL_DIRECTION_USEFUL_FULL_MAGNITUDE_HARMS_OR_SILENCES"
    else:
        classification = "SMALL_DIRECTION_USEFUL_FULL_NOT_SHOWN_HARMFUL"
    result = {
        "status":"complete","study_id":spec["study_id"],
        "protocol_sha256":sha(PROTOCOL),"a5_result_sha256":sha(A5/"result.json"),
        "a81_result_sha256":sha(A81_OUT/"result.json"),
        "source_sha256":{
            str(p.relative_to(ROOT)):sha(p) for p in (
                ROOT/"src/project_b/experiments/tiny_brain.py",
                ROOT/"src/project_b/plasticity/eligibility.py",
                ROOT/"scripts/a8_2_first_action_local_direction.py")},
        "seed":2002,"one_based_outcome":373,
        "first_down_time_us":spec["first_down_time_us"],
        "first_down_checkpoint_sha256":sha(OUT/"first_down_checkpoint.pkl"),
        "first_down_eligibility":first_e,"first_down_weights_mv":first_w,
        "first_action_diagnostic_rpe":spec["diagnostic_first_action_rpe"],
        "eta":eta,"candidate_raw_delta_mv":candidate_raw,
        "exact_training_events_replayed":373,
        "saved_pre_state_fieldwise_equal":True,
        "branches":branches,"candidate_geometry":geometry,
        "classification":classification,
        "completed_utc":datetime.now(timezone.utc).isoformat(),
    }
    atomic_json(OUT/"result.json",result)
    atomic_json(OUT/"status.json",{"status":"complete",
                                    "protocol_sha256":sha(PROTOCOL),
                                    "result_sha256":sha(OUT/"result.json")})
    print(json.dumps({"classification":classification}),flush=True)


if __name__ == "__main__":
    main()
