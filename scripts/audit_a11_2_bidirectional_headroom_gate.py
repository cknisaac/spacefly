"""Independent checkpoint, LIF, readout, action and no-learning audit for A11.2."""

from __future__ import annotations

import hashlib
import json
import math
from collections import deque
from pathlib import Path

from project_b.experiments import TinyLaneSession
from project_b.neurons.lif import advance_lif
from project_b.osu import GameEnvironment, KeyAction, KeyActionKind, TapNote
from scripts.cue_300ms_threshold_cohort_diagnostic import assert_same_state_except_weights, weights
from scripts.long_continuation import event_record

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/a11_2_bidirectional_headroom_gate.json"
A11 = ROOT / "docs/figures/a11_signed_perturbation_information_gate"
OUT = ROOT / "docs/figures/a11_2_bidirectional_headroom_gate"
BRANCHES = ("no_pulse_reference", "locked_signed", "locked_signed_inverse")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def next_voltage(session: TinyLaneSession, neuron: int) -> tuple[float, float, list]:
    sim = session.simulator
    p = sim.parameters[neuron]
    start = sim.current_time_us
    end = start + session.config.dt_us
    arrivals = sorted((time, post, pre, slot, sequence, weight)
                      for time, post, pre, slot, sequence, weight in sim._queue
                      if post == neuron and time <= end)
    v = sim.voltage_mv[neuron]
    syn = sim.synaptic_drive_mv[neuron]
    refractory_end = sim.refractory_until_us[neuron]
    at = start
    for time, _, _, _, _, weight in arrivals + [(end, neuron, -1, -1, -1, 0.0)]:
        assert start < time <= end
        if at < refractory_end:
            clamp = min(time, refractory_end)
            if clamp > at:
                syn *= math.exp(-(clamp - at) / p.tau_syn_us)
                v = p.v_reset_mv
                at = clamp
        if at < time:
            v, syn = advance_lif(v, syn, 0.0, time - at, p)
            at = time
        syn += weight
    coefficient = 1.0 - math.exp(-max(0, end - max(start, refractory_end)) / p.tau_m_us)
    return v, coefficient, [[time, weight, pre, slot, sequence]
                            for time, _, pre, slot, sequence, weight in arrivals]


def main() -> None:
    spec = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    result = json.loads((OUT / "result.json").read_text(encoding="utf-8"))
    status = json.loads((OUT / "status.json").read_text(encoding="utf-8"))
    a11 = json.loads((A11 / "result.json").read_text(encoding="utf-8"))
    a11_audit = json.loads((A11 / "audit.json").read_text(encoding="utf-8"))
    assert spec["stage"] == result["stage"] == "A11.2"
    assert result["status"] == status["status"] == "complete"
    assert result["protocol_sha256"] == status["protocol_sha256"] == sha(PROTOCOL)
    assert status["result_sha256"] == sha(OUT / "result.json")
    assert result["a11_result_sha256"] == sha(A11 / "result.json")
    assert result["a11_audit_sha256"] == sha(A11 / "audit.json")
    assert a11_audit["status"] == "passed"
    assert all(sha(ROOT / path) == digest for path, digest in result["source_sha256"].items())
    parent_path = A11 / "no_pulse_post_pulse_checkpoint.pkl"
    assert result["a11_parent_checkpoint_sha256"] == sha(parent_path)
    parent = TinyLaneSession.from_trusted_checkpoint_bytes(parent_path.read_bytes())
    target = spec["state"]["pre_intervention_time_us"]
    parent.run_until(target)
    pre_path = OUT / "pre_intervention_checkpoint.pkl"
    assert result["pre_intervention_checkpoint_sha256"] == sha(pre_path)
    pre = TinyLaneSession.from_trusted_checkpoint_bytes(pre_path.read_bytes())
    assert_same_state_except_weights(parent, pre)
    assert weights(parent) == weights(pre) == result["initial_plastic_weights_mv"]
    assert pre.simulator.current_time_us == target == 371380000
    assert pre.resolved_count == 372
    assert len(pre.readout._spike_times) == result["pre_intervention_readout_count"] == 5
    assert pre.readout.on_threshold == 10 and not pre.readout.key_down
    assert pre.config.exploration_probability == 0.0 and not pre.config.plasticity_enabled
    assert list(pre.layout.motor) == result["motor_ids"]
    signs = {int(j): value for j, value in a11["locked_motor_signs"].items()}
    assert {str(j): value for j, value in signs.items()} == result["locked_motor_signs"]
    analytic = result["analytic_next_tick"]
    assert analytic["time_us"] == target and analytic["next_tick_us"] == target + 1000
    retained = sum(time > target + 1000 - pre.readout.window_us
                   for time in pre.readout._spike_times)
    assert analytic["retained_prior_window_spikes"] == retained
    predicted = {name: [] for name in BRANCHES}
    for neuron in pre.layout.motor:
        cell = analytic["cells"][str(neuron)]
        v, alpha, arrivals = next_voltage(pre, neuron)
        assert math.isclose(v, cell["voltage_no_drive_pre_reset_mv"], rel_tol=0, abs_tol=1e-12)
        assert math.isclose(alpha, cell["external_drive_coefficient"], rel_tol=0, abs_tol=1e-12)
        assert arrivals == cell["arrival_events"]
        if alpha:
            assert math.isclose((pre.simulator.parameters[neuron].v_threshold_mv - v) / alpha,
                                cell["critical_external_drive_mv"], rel_tol=0, abs_tol=1e-10)
        else:
            assert cell["critical_external_drive_mv"] is None
        eligible = target + 1000 >= pre.simulator.refractory_until_us[neuron]
        threshold = pre.simulator.parameters[neuron].v_threshold_mv
        drive = {"no_pulse_reference": 0.0, "locked_signed": 20.0 * signs[neuron],
                 "locked_signed_inverse": -20.0 * signs[neuron]}
        for name in BRANCHES:
            fires = eligible and v + alpha * drive[name] >= threshold
            assert fires == cell["predicted_spike"][name]
            if fires:
                predicted[name].append(neuron)
    for name in BRANCHES:
        count = retained + len(predicted[name])
        assert analytic["predicted_readout_counts"][name] == count
        assert analytic["predicted_next_tick_crosses"][name] == (count >= 10)
    rises_by_name = {}
    total_actions = total_motor_spikes = 0
    for name in BRANCHES:
        record = result["branches"][name]
        branch = TinyLaneSession.from_trusted_checkpoint_bytes(pre_path.read_bytes())
        old_actions = len(branch.game.result().actions)
        old_decisions = len(branch.decisions)
        old_pulses = len(branch.exploration_pulses)
        before_predictor = branch.reward.predictor.expected_utility
        old_set = branch.simulator.set_external_drive_mv
        applied = {}

        def intercept(drive):
            assert all(drive[j] == 0.0 for j in pre.layout.motor)
            changed = list(drive)
            for j in pre.layout.motor:
                changed[j] = (0.0 if name == "no_pulse_reference" else
                              20.0 * signs[j] * (1 if name == "locked_signed" else -1))
            applied["original"] = [drive[j] for j in pre.layout.motor]
            applied["modified"] = [changed[j] for j in pre.layout.motor]
            old_set(changed)

        branch.simulator.set_external_drive_mv = intercept
        try:
            branch.step()
        finally:
            del branch.simulator.set_external_drive_mv
        assert applied["original"] == record["original_motor_drive_mv"]
        assert applied["modified"] == record["applied_motor_drive_mv"]
        assert [j for j in pre.layout.motor if branch.simulator.spiked_this_tick[j]] == predicted[name]
        assert predicted[name] == record["first_tick_motor_spikes"]
        assert len(branch.readout._spike_times) == analytic["predicted_readout_counts"][name]
        assert sha(OUT / f"{name}_post_intervention_checkpoint.pkl") == record[
            "post_intervention_checkpoint_sha256"]
        saved = TinyLaneSession.from_trusted_checkpoint_bytes(
            (OUT / f"{name}_post_intervention_checkpoint.pkl").read_bytes())
        assert_same_state_except_weights(branch, saved)
        assert weights(branch) == weights(saved) == weights(pre)
        spikes = []
        ticks = []

        def collect():
            time = branch.simulator.current_time_us
            batch = [j for j in pre.layout.motor if branch.simulator.spiked_this_tick[j]]
            spikes.extend((time, j) for j in batch)
            ticks.append({"time_us": time, "count": len(branch.readout._spike_times),
                          "key_down": branch.readout.key_down, "motor_spikes": batch})

        collect()
        while branch.resolved_count < 373:
            branch.step()
            collect()
        assert [list(row) for row in spikes] == record["spike_events"]
        assert ticks == record["readout_ticks"]
        history = deque(pre.readout._spike_times)
        on_before = len(history) >= pre.readout.on_threshold
        rises = []
        for row in ticks:
            time = row["time_us"]
            history.extend([time] * len(row["motor_spikes"]))
            while history and history[0] <= time - pre.readout.window_us:
                history.popleft()
            assert len(history) == row["count"]
            on = row["count"] >= pre.readout.on_threshold
            if on and not on_before:
                rises.append(time)
            on_before = on
        assert rises == record["threshold_rises_us"]
        assert (rises[0] if rises else None) == record["first_threshold_rise_us"]
        rises_by_name[name] = rises[0] if rises else None
        actions = [{"time_us": a.action.time_us, "kind": a.action.kind.value,
                    "disposition": a.disposition.value, "note_id": a.note_id}
                   for a in branch.game.result().actions[old_actions:]]
        assert actions == record["actions"]
        decisions = [{"time_us": d.time_us, "kind": d.action.kind.value,
                      "spike_count_in_window": d.spike_count_in_window}
                     for d in branch.decisions[old_decisions:]]
        assert decisions == record["decisions"]
        first = next((a for a in actions if a["kind"] == "down"), None)
        assert ({k: value for k, value in first.items() if k != "kind"} if first else None) == record["first_action"]
        isolated = GameEnvironment((TapNote("lane1-372", 0, pre.note_times_us[372]),))
        isolated.current_time_us = target
        isolated._key_down[0] = pre.game._key_down[0]
        for action in actions:
            isolated.advance_to(action["time_us"])
            replayed = isolated.apply_action(KeyAction(action["time_us"], 0,
                                                       KeyActionKind(action["kind"])))
            assert replayed.disposition.value == action["disposition"]
            assert replayed.note_id == action["note_id"]
        isolated.advance_to(branch.simulator.current_time_us)
        judged = isolated.result().judgements
        assert len(judged) == 1
        assert judged[0].judgement.name == record["resolved_event"]["judgement"]
        assert judged[0].hit_error_us == record["resolved_event"]["hit_error_us"]
        assert event_record(branch, 372) == record["resolved_event"]
        if name == "no_pulse_reference":
            saved_parent = a11["branches"]["no_pulse"]
            assert actions == [a for a in saved_parent["actions"] if a["time_us"] > target]
            assert record["resolved_event"] == saved_parent["resolved_training_event_with_learning_frozen"]
        assert record["predictor_before"] == before_predictor
        assert record["predictor_after_resolution"] == branch.reward.predictor.expected_utility
        assert weights(branch) == weights(pre)
        assert record["weight_change_count"] == 0
        assert record["new_exploration_pulse_count"] == 0
        assert len(branch.exploration_pulses) == old_pulses
        assert all(not feedback.weight_changes for feedback in branch.feedback[372:373])
        total_actions += len(actions)
        total_motor_spikes += len(spikes)
    t0 = rises_by_name["no_pulse_reference"]
    assert t0 == spec["state"]["expected_no_pulse_first_crossing_us"]
    ts = [rises_by_name[name] for name in BRANCHES[1:]]
    actions_present = all(result["branches"][name]["first_action"] is not None for name in BRANCHES)
    if actions_present and all(t is not None for t in ts) and (
        (ts[0] < t0 < ts[1]) or (ts[1] < t0 < ts[0])):
        classification = "PASS_LOCAL_BIDIRECTIONAL"
    elif actions_present and all(t is not None for t in ts) and sum(t != t0 for t in ts) == 1:
        classification = "ONE_SIDED"
    else:
        classification = "INCONCLUSIVE"
    assert classification == result["classification"]
    assert {name: rises_by_name[name] - t0 if rises_by_name[name] is not None else None
            for name in BRANCHES[1:]} == result["first_rise_delta_vs_no_pulse_us"]
    receipt = {"status": "passed", "stage": "A11.2", "classification": classification,
               "parent_checkpoint_verified": True, "analytic_cells_checked": len(pre.layout.motor),
               "branches_replayed": len(BRANCHES), "actions_replayed": total_actions,
               "motor_spikes_recounted": total_motor_spikes,
               "first_rises_us": rises_by_name, "protocol_sha256": sha(PROTOCOL),
               "result_sha256": sha(OUT / "result.json")}
    (OUT / "audit.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
