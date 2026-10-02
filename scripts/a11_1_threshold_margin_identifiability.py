"""One locked A11.1 threshold-margin pulse comparison; no synaptic learning."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from project_b.experiments import TinyLaneSession
from scripts.cue_300ms_threshold_cohort_diagnostic import assert_same_state_except_weights, weights
from scripts.long_continuation import atomic_json, event_record, sha

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/a11_1_threshold_margin_identifiability.json"
A11 = ROOT / "docs/figures/a11_signed_perturbation_information_gate"
OUT = ROOT / "docs/figures/a11_1_threshold_margin_identifiability"
BRANCHES = ("no_pulse_reference", "shared_positive_control", "locked_signed", "locked_signed_inverse")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    spec = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert spec["stage"] == "A11.1"
    assert spec["intervention"]["branches"] == list(BRANCHES)
    parent_result = json.loads((A11/"result.json").read_text(encoding="utf-8"))
    parent_audit = json.loads((A11/"audit.json").read_text(encoding="utf-8"))
    assert parent_result["classification"] == "INCONCLUSIVE"
    assert parent_audit["status"] == "passed"
    assert sha(A11/"result.json") == parent_audit["result_sha256"]
    parent_path = A11/"no_pulse_post_pulse_checkpoint.pkl"
    assert sha(parent_path) == parent_result["branches"]["no_pulse"]["post_pulse_checkpoint_sha256"]
    baseline = TinyLaneSession.from_trusted_checkpoint_bytes(parent_path.read_bytes())
    target_t = spec["state"]["pre_intervention_time_us"]
    baseline.run_until(target_t)
    assert baseline.simulator.current_time_us == target_t
    assert baseline.resolved_count == 372
    assert len(baseline.readout._spike_times) == spec["state"]["pre_intervention_readout_count"] == 5
    assert baseline.readout.on_threshold == spec["state"]["fixed_on_threshold"] == 10
    assert baseline.readout.key_down is spec["state"]["key_down"] is False
    assert baseline.config.plasticity_enabled is False
    assert baseline.config.exploration_probability == 0.0
    pre = baseline.checkpoint_bytes()
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"pre_intervention_checkpoint.pkl").write_bytes(pre)
    atomic_json(OUT/"status.json",{"status":"running","protocol_sha256":sha(PROTOCOL)})
    motor = baseline.layout.motor
    slots = baseline.layout.plastic_slots
    assert len(motor) == 32 and len(slots) == 480
    signs = {int(j):v for j,v in parent_result["locked_motor_signs"].items()}
    assert set(signs) == set(motor)
    assert sum(v>0 for v in signs.values()) == 22
    assert sum(v<0 for v in signs.values()) == 10
    tau_pre = baseline.plasticity.parameters.tau_pre_us
    tau_e = baseline.plasticity.parameters.tau_eligibility_us
    pre_trace = [baseline.plasticity._decayed(
        baseline.plasticity._pre[baseline.layout.graph.pre_indices[slot]],target_t,tau_pre)
        for slot in slots]
    initial_weights = weights(baseline)
    records = {}
    for name in BRANCHES:
        clone = TinyLaneSession.from_trusted_checkpoint_bytes(pre)
        assert weights(clone) == initial_weights
        n_actions = len(clone.game.result().actions)
        n_decisions = len(clone.decisions)
        n_pulses = len(clone.exploration_pulses)
        predictor_before = clone.reward.predictor.expected_utility
        original_set = clone.simulator.set_external_drive_mv
        captured_drive = {}
        branch_signs = {j:(0 if name == "no_pulse_reference" else
                           1 if name == "shared_positive_control" else
                           signs[j] if name == "locked_signed" else -signs[j])
                        for j in motor}

        def injected_drive(drive):
            assert all(drive[j] == 0.0 for j in motor)
            changed = list(drive)
            for j in motor:
                changed[j] = 20.0*branch_signs[j]
            assert changed[:motor[0]] == list(drive[:motor[0]])
            assert changed[motor[-1]+1:] == list(drive[motor[-1]+1:])
            captured_drive["original_motor_mv"] = [drive[j] for j in motor]
            captured_drive["applied_motor_mv"] = [changed[j] for j in motor]
            original_set(changed)

        clone.simulator.set_external_drive_mv = injected_drive
        try:
            clone.step()
        finally:
            del clone.simulator.set_external_drive_mv
        assert captured_drive
        assert len(clone.exploration_pulses) == n_pulses
        post_tick = clone.checkpoint_bytes()
        (OUT/f"{name}_post_intervention_checkpoint.pkl").write_bytes(post_tick)
        if name == "no_pulse_reference":
            reference = TinyLaneSession.from_trusted_checkpoint_bytes(pre)
            reference.step()
            assert_same_state_except_weights(clone,reference)
            assert weights(clone) == weights(reference)
        spike_events = []
        readout_ticks = []
        rises = []
        on_before = 5 >= clone.readout.on_threshold
        first_action = None

        def capture() -> None:
            nonlocal on_before,first_action
            t = clone.simulator.current_time_us
            batch = [j for j in motor if clone.simulator.spiked_this_tick[j]]
            spike_events.extend((t,j) for j in batch)
            count = len(clone.readout._spike_times)
            now_on = count >= clone.readout.on_threshold
            readout_ticks.append({"time_us":t,"count":count,
                                  "key_down":clone.readout.key_down,
                                  "motor_spikes":batch})
            if now_on and not on_before:
                rises.append(t)
            on_before = now_on
            if first_action is None:
                first = next((a for a in clone.game.result().actions[n_actions:]
                              if a.action.kind.value == "down"),None)
                if first is not None:
                    first_action = {"time_us":first.action.time_us,
                                    "disposition":first.disposition.value,
                                    "note_id":first.note_id}

        capture()
        while clone.resolved_count < 373:
            clone.step()
            capture()
        assert weights(clone) == initial_weights
        assert len(clone.exploration_pulses) == n_pulses
        assert all(not f.weight_changes for f in clone.feedback[372:373])
        score = event_record(clone,372)
        actions = [{"time_us":a.action.time_us,"kind":a.action.kind.value,
                    "disposition":a.disposition.value,"note_id":a.note_id}
                   for a in clone.game.result().actions[n_actions:]]
        decisions = [{"time_us":d.time_us,"kind":d.action.kind.value,
                      "spike_count_in_window":d.spike_count_in_window}
                     for d in clone.decisions[n_decisions:]]
        if name == "no_pulse_reference":
            parent = parent_result["branches"]["no_pulse"]
            assert actions == [x for x in parent["actions"] if x["time_us"] > target_t]
            assert score == parent["resolved_training_event_with_learning_frozen"]
            assert rises[0] == spec["state"]["historical_no_pulse_first_crossing_us"]
        pulse_tags = [pre_trace[i]*branch_signs[baseline.layout.graph.post_indices[slot]]
                      for i,slot in enumerate(slots)]
        action_tags = ([v*math.exp(-(first_action["time_us"]-target_t)/tau_e) for v in pulse_tags]
                       if first_action is not None else None)
        records[name] = {
            "post_intervention_checkpoint_sha256":digest(post_tick),
            "original_motor_drive_mv":captured_drive["original_motor_mv"],
            "applied_motor_drive_mv":captured_drive["applied_motor_mv"],
            "motor_signs":branch_signs,
            "spike_events":spike_events,
            "readout_ticks":readout_ticks,
            "threshold_rises_us":rises,
            "first_threshold_rise_us":rises[0] if rises else None,
            "first_action":first_action,
            "actions":actions,"decisions":decisions,
            "resolved_event":score,
            "pulse_tags":pulse_tags,"first_action_tags":action_tags,
            "positive_action_tags":sum(v>0 for v in action_tags) if action_tags is not None else None,
            "negative_action_tags":sum(v<0 for v in action_tags) if action_tags is not None else None,
            "predictor_before":predictor_before,
            "predictor_after_resolution":clone.reward.predictor.expected_utility,
            "weight_change_count":sum(len(f.weight_changes) for f in clone.feedback[372:373]),
        }
        print(json.dumps({"branch":name,"first_rise_us":rises[0] if rises else None,
                          "first_action":first_action,
                          "positive_tags":records[name]["positive_action_tags"],
                          "negative_tags":records[name]["negative_action_tags"]}),flush=True)
    t_end = target_t+20_000
    counts = {name:{j:sum(t<=t_end and cell==j for t,cell in rec["spike_events"])
                    for j in motor} for name,rec in records.items()}
    response_dot = sum(signs[j]*(counts["locked_signed"][j]-counts["locked_signed_inverse"][j])
                       for j in motor)
    signed,inverse = records["locked_signed"],records["locked_signed_inverse"]
    both_tags = all(r["positive_action_tags"] and r["negative_action_tags"] for r in (signed,inverse))
    t1,t2 = signed["first_threshold_rise_us"],inverse["first_threshold_rise_us"]
    both_actions = signed["first_action"] is not None and inverse["first_action"] is not None
    if not both_tags or response_dot <= 0:
        classification = "FAIL"
    elif not both_actions or t1 is None or t2 is None or t1 == t2:
        classification = "INCONCLUSIVE"
    else:
        assert abs(t1-t2) >= 1000
        classification = "PASS"
    result = {"status":"complete","study_id":spec["study_id"],"stage":"A11.1",
              "protocol_sha256":sha(PROTOCOL),
              "a11_result_sha256":sha(A11/"result.json"),
              "a11_audit_sha256":sha(A11/"audit.json"),
              "a11_parent_checkpoint_sha256":sha(parent_path),
              "source_sha256":{str(p.relative_to(ROOT)):sha(p) for p in (
                  ROOT/"src/project_b/experiments/tiny_brain.py",
                  ROOT/"src/project_b/plasticity/eligibility.py",
                  ROOT/"src/project_b/motor/fixed_readout.py",
                  ROOT/"scripts/a11_1_threshold_margin_identifiability.py")},
              "pre_intervention_checkpoint_sha256":digest(pre),
              "pre_intervention_time_us":target_t,
              "pre_intervention_readout_count":5,
              "fixed_on_threshold":10,
              "initial_plastic_weights_mv":initial_weights,
              "selected_edge_slots":list(slots),
              "motor_ids":list(motor),
              "locked_motor_signs":signs,
              "pre_trace_at_intervention":pre_trace,
              "branches":records,
              "motor_spike_counts_first_20ms":counts,
              "signed_response_dot":response_dot,
              "signed_action_tags_both_signs":bool(both_tags),
              "signed_branches_have_first_action":bool(both_actions),
              "signed_first_rise_delta_us":t1-t2 if t1 is not None and t2 is not None else None,
              "classification":classification,
              "completed_utc":datetime.now(timezone.utc).isoformat()}
    atomic_json(OUT/"result.json",result)
    atomic_json(OUT/"status.json",{"status":"complete","protocol_sha256":sha(PROTOCOL),
                                    "result_sha256":sha(OUT/"result.json")})
    print(json.dumps({"classification":classification,
                      "signed_response_dot":response_dot,
                      "signed_first_rise_delta_us":result["signed_first_rise_delta_us"]}),flush=True)


if __name__ == "__main__":
    main()
