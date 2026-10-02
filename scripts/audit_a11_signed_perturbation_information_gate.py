"""Independent A11 checkpoint, intervention, readout and action-tag audit."""

from __future__ import annotations

import hashlib
import json
import math
from collections import deque
from dataclasses import replace
from pathlib import Path

from project_b.experiments import TinyLaneSession
from project_b.osu import GameEnvironment, KeyAction, KeyActionKind, TapNote
from scripts.cue_300ms_threshold_cohort_diagnostic import assert_same_state_except_weights, weights
from scripts.exploration_map_diagnostic import load_long_rows
from scripts.long_continuation import event_record

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/a11_signed_perturbation_information_gate.json"
OUT = ROOT / "docs/figures/a11_signed_perturbation_information_gate"
A82_FIRST = ROOT / "docs/figures/a8_2_first_action_local_direction/first_down_checkpoint.pkl"
BRANCHES = ("no_pulse", "historical_shared_positive", "locked_signed", "locked_signed_inverse")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expected_sign(j: int) -> int:
    bit = hashlib.sha256(f"A11|2002|373|371324000|{j}".encode("ascii")).digest()[0] & 1
    return 1 if bit else -1


def main() -> None:
    spec = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    result = json.loads((OUT/"result.json").read_text(encoding="utf-8"))
    status = json.loads((OUT/"status.json").read_text(encoding="utf-8"))
    assert result["status"] == status["status"] == "complete"
    assert result["stage"] == spec["stage"] == "A11"
    assert spec["intervention"]["branches"] == list(BRANCHES)
    assert result["protocol_sha256"] == status["protocol_sha256"] == sha(PROTOCOL)
    assert status["result_sha256"] == sha(OUT/"result.json")
    assert result["a82_first_down_checkpoint_sha256"] == sha(A82_FIRST)
    assert all(sha(ROOT/path) == h for path,h in result["source_sha256"].items())
    pre_path = OUT/"pre_pulse_checkpoint.pkl"
    assert result["pre_pulse_checkpoint_sha256"] == sha(pre_path)
    pre_bytes = pre_path.read_bytes()
    pre = TinyLaneSession.from_trusted_checkpoint_bytes(pre_bytes)
    t0 = spec["state"]["pre_pulse_simulator_time_us"]
    assert pre.simulator.current_time_us == t0 == result["pulse_start_us"]
    assert pre.resolved_count == 372
    assert [event_record(pre,i) for i in range(372)] == load_long_rows()[2002]["training_events"][:372]
    motor = pre.layout.motor
    slots = pre.layout.plastic_slots
    assert len(motor) == 32 and len(slots) == 480
    assert list(motor) == result["motor_ids"]
    assert list(slots) == result["selected_edge_slots"]
    signs = {j:expected_sign(j) for j in motor}
    assert {str(j):v for j,v in signs.items()} == result["locked_motor_signs"]
    tau_pre = pre.plasticity.parameters.tau_pre_us
    tau_e = pre.plasticity.parameters.tau_eligibility_us
    pre_trace = [pre.plasticity._pre[pre.layout.graph.pre_indices[slot]][0] *
                 math.exp(-(t0-pre.plasticity._pre[pre.layout.graph.pre_indices[slot]][1])/tau_pre)
                 for slot in slots]
    assert pre_trace == result["pre_trace_at_pulse"]
    branch_rises = {}
    branch_action_tags = {}
    total_actions = total_motor_spikes = 0
    for name in BRANCHES:
        stored = result["branches"][name]
        branch = TinyLaneSession.from_trusted_checkpoint_bytes(pre_bytes)
        branch.config = replace(branch.config, plasticity_enabled=False)
        old_weights = weights(branch)
        old_rng = branch.rng.getstate()
        old_pulses = len(branch.exploration_pulses)
        old_decisions = len(branch.decisions)
        old_actions = len(branch.game.result().actions)
        original_drive = branch.simulator.set_external_drive_mv
        seen_drive = []
        expected_motor_drive = {j: 0.0 if name == "no_pulse" else 20.0 if name == "historical_shared_positive"
                                else 20.0*signs[j] if name == "locked_signed" else -20.0*signs[j]
                                for j in motor}

        def intercept(drive):
            assert all(drive[j] == 20.0 for j in motor)
            modified = list(drive)
            for j in motor:
                modified[j] = expected_motor_drive[j]
            seen_drive.extend(modified[j] for j in motor)
            original_drive(modified)

        branch.simulator.set_external_drive_mv = intercept
        try:
            branch.step()
        finally:
            del branch.simulator.set_external_drive_mv
        assert len(branch.exploration_pulses) == old_pulses+1
        assert branch.exploration_pulses[-1] == t0
        assert seen_drive == stored["intervention"]["applied_motor_drive_mv"]
        assert stored["intervention"]["original_motor_drive_mv"] == [20.0]*32
        if name == "historical_shared_positive":
            historical = TinyLaneSession.from_trusted_checkpoint_bytes(A82_FIRST.read_bytes())
            historical.config = replace(historical.config,plasticity_enabled=False)
            assert_same_state_except_weights(branch,historical)
            assert weights(branch) == weights(historical)
        branch.config = replace(branch.config,exploration_probability=0.0)
        checkpoint_path = OUT/f"{name}_post_pulse_checkpoint.pkl"
        assert sha(checkpoint_path) == stored["post_pulse_checkpoint_sha256"]
        saved = TinyLaneSession.from_trusted_checkpoint_bytes(checkpoint_path.read_bytes())
        assert_same_state_except_weights(branch,saved)
        assert weights(branch) == weights(saved)
        motor_spikes = []
        counts_by_tick = []

        def collect():
            t = branch.simulator.current_time_us
            batch = [j for j in motor if branch.simulator.spiked_this_tick[j]]
            motor_spikes.extend((t,j) for j in batch)
            counts_by_tick.append((t,len(branch.readout._spike_times),branch.readout.key_down,batch))

        collect()
        while branch.resolved_count < 373:
            branch.step()
            collect()
        assert weights(branch) == old_weights
        assert branch.rng.getstate() != old_rng
        assert branch.exploration_pulses[old_pulses:] == [t0]
        assert all(not x.weight_changes for x in branch.feedback[372:373])
        assert [list(x) for x in motor_spikes] == stored["spike_events"]
        assert [{"time_us":t,"count":c,"key_down":key,"motor_spikes":b}
                for t,c,key,b in counts_by_tick] == stored["readout_ticks"]
        first_count = stored["initial_readout_count"]
        on = first_count >= branch.readout.on_threshold
        rises = []
        # Independently rebuild the 20-ms motor population window from the
        # saved initial readout timestamps and recorded motor cell spikes.
        history = deque(TinyLaneSession.from_trusted_checkpoint_bytes(pre_bytes).readout._spike_times)
        for t,c,key,batch in counts_by_tick:
            history.extend([t]*len(batch))
            while history and history[0] <= t-branch.readout.window_us:
                history.popleft()
            assert len(history) == c
            now = c >= branch.readout.on_threshold
            if now and not on:
                rises.append(t)
            on = now
        assert rises == stored["threshold_rises_us"]
        assert (rises[0] if rises else None) == stored["first_threshold_rise_us"]
        decisions = [{"time_us":d.time_us,"kind":d.action.kind.value,
                      "spike_count_in_window":d.spike_count_in_window}
                     for d in branch.decisions[old_decisions:]]
        assert decisions == stored["decisions"]
        actions = [{"time_us":a.action.time_us,"kind":a.action.kind.value,
                    "disposition":a.disposition.value,"note_id":a.note_id}
                   for a in branch.game.result().actions[old_actions:]]
        assert actions == stored["actions"]
        first = next((a for a in actions if a["kind"]=="down"),None)
        assert ({k:v for k,v in first.items() if k != "kind"} if first is not None else None) == stored["first_action"]
        isolated = GameEnvironment((TapNote("lane1-372",0,pre.note_times_us[372]),))
        isolated.current_time_us = t0
        isolated._key_down[0] = pre.game._key_down[0]
        for a in actions:
            isolated.advance_to(a["time_us"])
            rec = isolated.apply_action(KeyAction(a["time_us"],0,KeyActionKind(a["kind"])))
            assert rec.disposition.value == a["disposition"]
            assert rec.note_id == a["note_id"]
        isolated.advance_to(branch.simulator.current_time_us)
        judged = isolated.result().judgements
        assert len(judged) == 1
        assert judged[0].judgement.name == stored["resolved_training_event_with_learning_frozen"]["judgement"]
        assert judged[0].hit_error_us == stored["resolved_training_event_with_learning_frozen"]["hit_error_us"]
        per_motor_sign = {j: 0 if name=="no_pulse" else 1 if name=="historical_shared_positive"
                          else signs[j] if name=="locked_signed" else -signs[j] for j in motor}
        assert {str(j):v for j,v in per_motor_sign.items()} == stored["motor_signs"]
        pulse_tags = [pre_trace[i]*per_motor_sign[pre.layout.graph.post_indices[slot]]
                      for i,slot in enumerate(slots)]
        assert pulse_tags == stored["pulse_tags"]
        action_tags = ([v*math.exp(-(first["time_us"]-t0)/tau_e) for v in pulse_tags]
                       if first is not None else None)
        assert action_tags == stored["first_action_tags"]
        branch_rises[name] = rises[0] if rises else None
        branch_action_tags[name] = action_tags
        total_actions += len(actions)
        total_motor_spikes += len(motor_spikes)
    t_end = t0+20_000
    counts = {name:{j:sum(t<=t_end and cell==j for t,cell in result["branches"][name]["spike_events"])
                    for j in motor} for name in BRANCHES}
    assert {name:{str(j):v for j,v in d.items()} for name,d in counts.items()} == result["motor_spike_counts_first_20ms"]
    dot = sum(signs[j]*(counts["locked_signed"][j]-counts["locked_signed_inverse"][j]) for j in motor)
    assert dot == result["signed_response_dot"]
    signed_tags = [branch_action_tags[name] for name in ("locked_signed","locked_signed_inverse")]
    both_signs = all(v is not None and any(x>0 for x in v) and any(x<0 for x in v)
                     for v in signed_tags)
    assert both_signs == result["signed_action_tags_both_signs"]
    rise1,rise2 = branch_rises["locked_signed"],branch_rises["locked_signed_inverse"]
    assert (rise1-rise2 if rise1 is not None and rise2 is not None else None) == result["signed_first_rise_delta_us"]
    both_actions = all(result["branches"][name]["first_action"] is not None
                       for name in ("locked_signed","locked_signed_inverse"))
    assert both_actions == result["signed_branches_have_first_action"]
    if not both_signs or dot <= 0:
        classification = "FAIL"
    elif not both_actions or rise1 is None or rise2 is None or rise1==rise2:
        classification = "INCONCLUSIVE"
    else:
        classification = "PASS"
    assert classification == result["classification"]
    receipt = {"status":"passed","stage":"A11", "classification":classification,
               "historical_events_verified":372,"branches_replayed":4,
               "actions_replayed":total_actions,"motor_spikes_recounted":total_motor_spikes,
               "signed_response_dot":dot,
               "signed_first_rise_delta_us":result["signed_first_rise_delta_us"],
               "protocol_sha256":sha(PROTOCOL),"result_sha256":sha(OUT/"result.json")}
    (OUT/"audit.json").write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(receipt,indent=2))


if __name__ == "__main__":
    main()
