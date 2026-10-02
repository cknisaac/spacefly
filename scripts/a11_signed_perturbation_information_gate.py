"""A11 one-state signed motor perturbation information test; no learning."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from project_b.experiments import TinyLaneSession
from scripts.cue_300ms_threshold_cohort_diagnostic import assert_same_state_except_weights, weights
from scripts.exploration_map_diagnostic import load_long_rows, load_rows
from scripts.long_continuation import atomic_json, event_record, sha
from scripts.successive_update_interference_diagnostic import LONG_PROTOCOL, ORIGINAL_LEDGER, make_config

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/a11_signed_perturbation_information_gate.json"
OUT = ROOT / "docs/figures/a11_signed_perturbation_information_gate"
A82_FIRST = ROOT / "docs/figures/a8_2_first_action_local_direction/first_down_checkpoint.pkl"
BRANCHES = ("no_pulse", "historical_shared_positive", "locked_signed", "locked_signed_inverse")


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def locked_sign(motor_id: int) -> int:
    payload = f"A11|2002|373|371324000|{motor_id}".encode("ascii")
    return 1 if hashlib.sha256(payload).digest()[0] & 1 else -1


def main() -> None:
    spec = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert spec["intervention"]["branches"] == list(BRANCHES)
    assert spec["state"]["pre_pulse_simulator_time_us"] == 371_324_000
    long_rows = load_long_rows()
    source = long_rows[2002]
    session = TinyLaneSession(make_config(2002, load_rows(ORIGINAL_LEDGER),
                                          long_rows, json.loads(LONG_PROTOCOL.read_text(encoding="utf-8"))))
    session.run_until(spec["state"]["pre_pulse_simulator_time_us"])
    assert session.resolved_count == 372
    assert [event_record(session,i) for i in range(372)] == source["training_events"][:372]
    assert session.simulator.current_time_us == 371_324_000
    assert session.note_times_us[372] == 371_700_000
    pre = session.checkpoint_bytes()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "pre_pulse_checkpoint.pkl").write_bytes(pre)
    atomic_json(OUT / "status.json", {"status":"running", "protocol_sha256":sha(PROTOCOL)})
    slots = session.layout.plastic_slots
    motor = session.layout.motor
    assert len(slots) == 480 and len(motor) == 32
    signs = {j: locked_sign(j) for j in motor}
    tau_pre = session.plasticity.parameters.tau_pre_us
    tau_e = session.plasticity.parameters.tau_eligibility_us
    pulse_t = session.simulator.current_time_us
    pre_trace = [session.plasticity._decayed(
        session.plasticity._pre[session.layout.graph.pre_indices[slot]], pulse_t, tau_pre)
        for slot in slots]
    assert all(value >= 0 and math.isfinite(value) for value in pre_trace)
    records = {}
    for name in BRANCHES:
        clone = TinyLaneSession.from_trusted_checkpoint_bytes(pre)
        clone.config = replace(clone.config, plasticity_enabled=False)
        assert clone.simulator.current_time_us == pulse_t
        assert weights(clone) == weights(session)
        start_decisions = len(clone.decisions)
        start_actions = len(clone.game.result().actions)
        start_pulses = len(clone.exploration_pulses)
        initial_count = len(clone.readout._spike_times)
        initial_key_down = clone.readout.key_down
        original_set = clone.simulator.set_external_drive_mv
        intervention = {}

        def replace_drive(drive):
            assert len(drive) == clone.config.neuron_count
            assert all(drive[j] == 20.0 for j in motor)
            modified = list(drive)
            for j in motor:
                sign = (0 if name == "no_pulse" else 1 if name == "historical_shared_positive"
                        else signs[j] if name == "locked_signed" else -signs[j])
                modified[j] = 20.0 * sign
            intervention["original_motor_drive_mv"] = [drive[j] for j in motor]
            intervention["applied_motor_drive_mv"] = [modified[j] for j in motor]
            assert modified[:motor[0]] == list(drive[:motor[0]])
            assert modified[motor[-1]+1:] == list(drive[motor[-1]+1:])
            original_set(modified)

        clone.simulator.set_external_drive_mv = replace_drive
        try:
            clone.step()
        finally:
            del clone.simulator.set_external_drive_mv
        assert len(clone.exploration_pulses) == start_pulses+1
        assert clone.exploration_pulses[-1] == pulse_t
        assert intervention
        if name == "historical_shared_positive":
            historical = TinyLaneSession.from_trusted_checkpoint_bytes(A82_FIRST.read_bytes())
            historical.config = replace(historical.config, plasticity_enabled=False)
            assert_same_state_except_weights(clone, historical)
            assert weights(clone) == weights(historical)
            assert clone.simulator.current_time_us == spec["state"]["historical_first_down_us"]
        clone.config = replace(clone.config, exploration_probability=0.0)
        post_tick = clone.checkpoint_bytes()
        (OUT / f"{name}_post_pulse_checkpoint.pkl").write_bytes(post_tick)
        spike_events = []
        readout_ticks = []
        threshold_rises = []
        previous_on = initial_count >= clone.readout.on_threshold
        first_action = None

        def collect_tick() -> None:
            nonlocal previous_on, first_action
            t = clone.simulator.current_time_us
            batch = [j for j in motor if clone.simulator.spiked_this_tick[j]]
            spike_events.extend((t,j) for j in batch)
            count = len(clone.readout._spike_times)
            now_on = count >= clone.readout.on_threshold
            readout_ticks.append({"time_us":t, "count":count,
                                  "key_down":clone.readout.key_down,
                                  "motor_spikes":batch})
            if now_on and not previous_on:
                threshold_rises.append(t)
            previous_on = now_on
            if first_action is None:
                new_actions = clone.game.result().actions[start_actions:]
                for action in new_actions:
                    if action.action.kind.value == "down":
                        first_action = {"time_us":action.action.time_us,
                                        "disposition":action.disposition.value,
                                        "note_id":action.note_id}
                        break

        collect_tick()
        while clone.resolved_count < 373:
            clone.step()
            collect_tick()
        assert all(not delivery.weight_changes for delivery in clone.feedback[372:373])
        assert weights(clone) == weights(session)
        assert not any(t > pulse_t for t in clone.exploration_pulses[start_pulses:])
        score = event_record(clone,372)
        decisions = [{"time_us":d.time_us, "kind":d.action.kind.value,
                      "spike_count_in_window":d.spike_count_in_window}
                     for d in clone.decisions[start_decisions:]]
        actions = [{"time_us":a.action.time_us, "kind":a.action.kind.value,
                    "disposition":a.disposition.value, "note_id":a.note_id}
                   for a in clone.game.result().actions[start_actions:]]
        factor = (math.exp(-(first_action["time_us"]-pulse_t)/tau_e)
                  if first_action is not None else None)
        branch_signs = {j: (0 if name == "no_pulse" else 1 if name == "historical_shared_positive"
                            else signs[j] if name == "locked_signed" else -signs[j])
                        for j in motor}
        pulse_tags = [pre_trace[i]*branch_signs[session.layout.graph.post_indices[slot]]
                      for i,slot in enumerate(slots)]
        action_tags = [x*factor for x in pulse_tags] if factor is not None else None
        if action_tags is not None:
            assert all(math.isfinite(x) for x in action_tags)
        records[name] = {
            "post_pulse_checkpoint_sha256":digest_bytes(post_tick),
            "intervention":intervention,
            "motor_signs":branch_signs,
            "initial_readout_count":initial_count,
            "initial_key_down":initial_key_down,
            "spike_events":spike_events,
            "readout_ticks":readout_ticks,
            "threshold_rises_us":threshold_rises,
            "first_threshold_rise_us":threshold_rises[0] if threshold_rises else None,
            "first_action":first_action,
            "decisions":decisions,
            "actions":actions,
            "resolved_training_event_with_learning_frozen":score,
            "pulse_tags":pulse_tags,
            "first_action_tags":action_tags,
            "positive_action_tags":sum(x>0 for x in action_tags) if action_tags is not None else None,
            "negative_action_tags":sum(x<0 for x in action_tags) if action_tags is not None else None,
            "weight_change_count":sum(len(f.weight_changes) for f in clone.feedback[372:373]),
            "exploration_pulse_count_after_intervention":len(clone.exploration_pulses)-start_pulses,
        }
        print(json.dumps({"branch":name,
                          "first_rise_us":records[name]["first_threshold_rise_us"],
                          "first_action":first_action,
                          "positive_tags":records[name]["positive_action_tags"],
                          "negative_tags":records[name]["negative_action_tags"]}),flush=True)
    t_end = pulse_t + 20_000
    counts = {name:{j:sum(t<=t_end and cell==j for t,cell in record["spike_events"])
                    for j in motor} for name,record in records.items()}
    response_dot = sum(signs[j]*(counts["locked_signed"][j]-counts["locked_signed_inverse"][j])
                       for j in motor)
    signed = records["locked_signed"]
    inverse = records["locked_signed_inverse"]
    tags_both = all(r["positive_action_tags"] and r["negative_action_tags"]
                    for r in (signed,inverse))
    rises = (signed["first_threshold_rise_us"],inverse["first_threshold_rise_us"])
    both_actions = signed["first_action"] is not None and inverse["first_action"] is not None
    if not tags_both or response_dot <= 0:
        classification = "FAIL"
    elif not both_actions or any(t is None for t in rises) or rises[0] == rises[1]:
        classification = "INCONCLUSIVE"
    else:
        assert abs(rises[0]-rises[1]) >= session.config.dt_us
        classification = "PASS"
    result = {"status":"complete", "stage":"A11", "study_id":spec["study_id"],
              "protocol_sha256":sha(PROTOCOL),
              "source_sha256":{str(p.relative_to(ROOT)):sha(p) for p in (
                  ROOT/"src/project_b/experiments/tiny_brain.py",
                  ROOT/"src/project_b/plasticity/eligibility.py",
                  ROOT/"src/project_b/motor/fixed_readout.py",
                  ROOT/"scripts/a11_signed_perturbation_information_gate.py")},
              "a82_first_down_checkpoint_sha256":sha(A82_FIRST),
              "pre_pulse_checkpoint_sha256":digest_bytes(pre),
              "exact_historical_events_before_pulse":372,
              "pulse_start_us":pulse_t,
              "motor_ids":list(motor), "selected_edge_slots":list(slots),
              "pre_trace_at_pulse":pre_trace,
              "locked_motor_signs":signs,
              "branches":records,
              "motor_spike_counts_first_20ms":counts,
              "signed_response_dot":response_dot,
              "signed_action_tags_both_signs":bool(tags_both),
              "signed_branches_have_first_action":bool(both_actions),
              "signed_first_rise_delta_us":(rises[0]-rises[1] if all(t is not None for t in rises) else None),
              "classification":classification,
              "completed_utc":datetime.now(timezone.utc).isoformat()}
    atomic_json(OUT / "result.json",result)
    atomic_json(OUT / "status.json",{"status":"complete","protocol_sha256":sha(PROTOCOL),
                                     "result_sha256":sha(OUT/"result.json")})
    print(json.dumps({"classification":classification,
                      "signed_response_dot":response_dot,
                      "signed_first_rise_delta_us":result["signed_first_rise_delta_us"]}),flush=True)


if __name__ == "__main__":
    main()
