"""Independent replay and threshold/action audit of the one A11.1 checkpoint."""

from __future__ import annotations

import hashlib
import json
import math
from collections import deque
from pathlib import Path

from project_b.experiments import TinyLaneSession
from project_b.osu import GameEnvironment, KeyAction, KeyActionKind, TapNote
from scripts.cue_300ms_threshold_cohort_diagnostic import assert_same_state_except_weights, weights
from scripts.long_continuation import event_record

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT/"configs/a11_1_threshold_margin_identifiability.json"
A11 = ROOT/"docs/figures/a11_signed_perturbation_information_gate"
OUT = ROOT/"docs/figures/a11_1_threshold_margin_identifiability"
BRANCHES = ("no_pulse_reference","shared_positive_control","locked_signed","locked_signed_inverse")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    spec = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    result = json.loads((OUT/"result.json").read_text(encoding="utf-8"))
    status = json.loads((OUT/"status.json").read_text(encoding="utf-8"))
    a11 = json.loads((A11/"result.json").read_text(encoding="utf-8"))
    a11_audit = json.loads((A11/"audit.json").read_text(encoding="utf-8"))
    assert spec["stage"] == result["stage"] == "A11.1"
    assert spec["intervention"]["branches"] == list(BRANCHES)
    assert result["status"] == status["status"] == "complete"
    assert result["protocol_sha256"] == status["protocol_sha256"] == sha(PROTOCOL)
    assert status["result_sha256"] == sha(OUT/"result.json")
    assert result["a11_result_sha256"] == sha(A11/"result.json")
    assert result["a11_audit_sha256"] == sha(A11/"audit.json")
    assert a11_audit["status"] == "passed"
    assert all(sha(ROOT/name) == h for name,h in result["source_sha256"].items())
    parent_path = A11/"no_pulse_post_pulse_checkpoint.pkl"
    assert result["a11_parent_checkpoint_sha256"] == sha(parent_path)
    parent = TinyLaneSession.from_trusted_checkpoint_bytes(parent_path.read_bytes())
    target_t = spec["state"]["pre_intervention_time_us"]
    parent.run_until(target_t)
    pre_path = OUT/"pre_intervention_checkpoint.pkl"
    assert result["pre_intervention_checkpoint_sha256"] == sha(pre_path)
    pre = TinyLaneSession.from_trusted_checkpoint_bytes(pre_path.read_bytes())
    assert_same_state_except_weights(parent,pre)
    assert weights(parent) == weights(pre) == result["initial_plastic_weights_mv"]
    assert pre.simulator.current_time_us == target_t == 371390000
    assert pre.resolved_count == 372
    assert len(pre.readout._spike_times) == result["pre_intervention_readout_count"] == 5
    assert pre.readout.on_threshold == result["fixed_on_threshold"] == 10
    assert not pre.readout.key_down
    assert not pre.config.plasticity_enabled and pre.config.exploration_probability == 0.0
    motor, slots = pre.layout.motor, pre.layout.plastic_slots
    assert list(motor) == result["motor_ids"] and list(slots) == result["selected_edge_slots"]
    signs = {int(j):v for j,v in a11["locked_motor_signs"].items()}
    assert {str(j):v for j,v in signs.items()} == result["locked_motor_signs"]
    tau_pre = pre.plasticity.parameters.tau_pre_us
    tau_e = pre.plasticity.parameters.tau_eligibility_us
    pre_trace = [pre.plasticity._pre[pre.layout.graph.pre_indices[slot]][0] *
                 math.exp(-(target_t-pre.plasticity._pre[pre.layout.graph.pre_indices[slot]][1])/tau_pre)
                 for slot in slots]
    assert pre_trace == result["pre_trace_at_intervention"]
    all_rises = {}
    total_actions = total_spikes = 0
    for name in BRANCHES:
        record = result["branches"][name]
        branch = TinyLaneSession.from_trusted_checkpoint_bytes(pre_path.read_bytes())
        old_action_len = len(branch.game.result().actions)
        old_decision_len = len(branch.decisions)
        old_pulse_len = len(branch.exploration_pulses)
        before_predictor = branch.reward.predictor.expected_utility
        applied = {j:0.0 if name=="no_pulse_reference" else
                   20.0 if name=="shared_positive_control" else
                   20.0*signs[j] if name=="locked_signed" else -20.0*signs[j]
                   for j in motor}
        old_set = branch.simulator.set_external_drive_mv
        observed_drive = []

        def intercept(drive):
            assert all(drive[j] == 0.0 for j in motor)
            changed = list(drive)
            for j in motor:
                changed[j] = applied[j]
            observed_drive.extend(changed[j] for j in motor)
            old_set(changed)

        branch.simulator.set_external_drive_mv = intercept
        try:
            branch.step()
        finally:
            del branch.simulator.set_external_drive_mv
        assert observed_drive == record["applied_motor_drive_mv"]
        assert record["original_motor_drive_mv"] == [0.0]*32
        assert len(branch.exploration_pulses) == old_pulse_len
        checkpoint_path = OUT/f"{name}_post_intervention_checkpoint.pkl"
        assert record["post_intervention_checkpoint_sha256"] == sha(checkpoint_path)
        saved = TinyLaneSession.from_trusted_checkpoint_bytes(checkpoint_path.read_bytes())
        assert_same_state_except_weights(branch,saved)
        assert weights(branch) == weights(saved)
        spike_events = []
        ticks = []

        def collect():
            t = branch.simulator.current_time_us
            batch = [j for j in motor if branch.simulator.spiked_this_tick[j]]
            spike_events.extend((t,j) for j in batch)
            ticks.append((t,len(branch.readout._spike_times),branch.readout.key_down,batch))

        collect()
        while branch.resolved_count < 373:
            branch.step()
            collect()
        assert weights(branch) == weights(pre)
        assert len(branch.exploration_pulses) == old_pulse_len
        assert all(not f.weight_changes for f in branch.feedback[372:373])
        assert record["predictor_before"] == before_predictor
        assert record["predictor_after_resolution"] == branch.reward.predictor.expected_utility
        assert [list(x) for x in spike_events] == record["spike_events"]
        assert [{"time_us":t,"count":c,"key_down":key,"motor_spikes":batch}
                for t,c,key,batch in ticks] == record["readout_ticks"]
        history = deque(pre.readout._spike_times)
        before_on = len(history) >= pre.readout.on_threshold
        rises = []
        for t,c,key,batch in ticks:
            history.extend([t]*len(batch))
            while history and history[0] <= t-pre.readout.window_us:
                history.popleft()
            assert len(history) == c
            now_on = c >= pre.readout.on_threshold
            if now_on and not before_on:
                rises.append(t)
            before_on = now_on
        assert rises == record["threshold_rises_us"]
        assert (rises[0] if rises else None) == record["first_threshold_rise_us"]
        all_rises[name] = rises[0] if rises else None
        actions = [{"time_us":a.action.time_us,"kind":a.action.kind.value,
                    "disposition":a.disposition.value,"note_id":a.note_id}
                   for a in branch.game.result().actions[old_action_len:]]
        assert actions == record["actions"]
        decisions = [{"time_us":d.time_us,"kind":d.action.kind.value,
                      "spike_count_in_window":d.spike_count_in_window}
                     for d in branch.decisions[old_decision_len:]]
        assert decisions == record["decisions"]
        first = next((a for a in actions if a["kind"]=="down"),None)
        assert ({k:v for k,v in first.items() if k!="kind"} if first else None) == record["first_action"]
        isolated = GameEnvironment((TapNote("lane1-372",0,pre.note_times_us[372]),))
        isolated.current_time_us = target_t
        isolated._key_down[0] = pre.game._key_down[0]
        for action in actions:
            isolated.advance_to(action["time_us"])
            replayed = isolated.apply_action(KeyAction(action["time_us"],0,KeyActionKind(action["kind"])))
            assert replayed.disposition.value == action["disposition"]
            assert replayed.note_id == action["note_id"]
        isolated.advance_to(branch.simulator.current_time_us)
        judged = isolated.result().judgements
        assert len(judged) == 1
        assert judged[0].judgement.name == record["resolved_event"]["judgement"]
        assert judged[0].hit_error_us == record["resolved_event"]["hit_error_us"]
        assert event_record(branch,372) == record["resolved_event"]
        branch_sign = {j:0 if name=="no_pulse_reference" else
                       1 if name=="shared_positive_control" else
                       signs[j] if name=="locked_signed" else -signs[j]
                       for j in motor}
        assert {str(j):v for j,v in branch_sign.items()} == record["motor_signs"]
        tags = [pre_trace[i]*branch_sign[pre.layout.graph.post_indices[slot]]
                for i,slot in enumerate(slots)]
        assert tags == record["pulse_tags"]
        action_tags = ([v*math.exp(-(first["time_us"]-target_t)/tau_e) for v in tags]
                       if first is not None else None)
        assert action_tags == record["first_action_tags"]
        assert record["positive_action_tags"] == (sum(x>0 for x in action_tags) if action_tags else None)
        assert record["negative_action_tags"] == (sum(x<0 for x in action_tags) if action_tags else None)
        total_actions += len(actions)
        total_spikes += len(spike_events)
    t_end = target_t+20000
    counts = {name:{j:sum(t<=t_end and cell==j for t,cell in result["branches"][name]["spike_events"])
                    for j in motor} for name in BRANCHES}
    assert {name:{str(j):v for j,v in vals.items()} for name,vals in counts.items()} == result["motor_spike_counts_first_20ms"]
    dot = sum(signs[j]*(counts["locked_signed"][j]-counts["locked_signed_inverse"][j]) for j in motor)
    assert dot == result["signed_response_dot"]
    signed,inverse = result["branches"]["locked_signed"],result["branches"]["locked_signed_inverse"]
    both_tags = all(r["positive_action_tags"] and r["negative_action_tags"] for r in (signed,inverse))
    assert bool(both_tags) == result["signed_action_tags_both_signs"]
    both_actions = signed["first_action"] is not None and inverse["first_action"] is not None
    assert bool(both_actions) == result["signed_branches_have_first_action"]
    t1,t2 = all_rises["locked_signed"],all_rises["locked_signed_inverse"]
    assert (t1-t2 if t1 is not None and t2 is not None else None) == result["signed_first_rise_delta_us"]
    classification = ("FAIL" if not both_tags or dot<=0 else
                      "INCONCLUSIVE" if not both_actions or t1 is None or t2 is None or t1==t2 else "PASS")
    assert classification == result["classification"]
    receipt = {"status":"passed","stage":"A11.1","classification":classification,
               "parent_checkpoint_verified":True,"pre_intervention_readout_count":5,
               "branches_replayed":4,"actions_replayed":total_actions,
               "motor_spikes_recounted":total_spikes,
               "first_rises_us":all_rises,
               "signed_response_dot":dot,
               "protocol_sha256":sha(PROTOCOL),"result_sha256":sha(OUT/"result.json")}
    (OUT/"audit.json").write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(receipt,indent=2))


if __name__ == "__main__":
    main()
