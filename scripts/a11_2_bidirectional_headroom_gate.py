"""One locked signed motor pulse test with an analytic next-tick range audit."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from project_b.experiments import TinyLaneSession
from project_b.neurons.lif import advance_lif
from scripts.cue_300ms_threshold_cohort_diagnostic import assert_same_state_except_weights, weights
from scripts.long_continuation import atomic_json, event_record, sha

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/a11_2_bidirectional_headroom_gate.json"
A11 = ROOT / "docs/figures/a11_signed_perturbation_information_gate"
OUT = ROOT / "docs/figures/a11_2_bidirectional_headroom_gate"
BRANCHES = ("no_pulse_reference", "locked_signed", "locked_signed_inverse")


def byte_sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def analytic_motor_next_tick(session: TinyLaneSession, signs: dict[int, int]) -> dict:
    """Predict a single tick directly from saved cell state, queued arrivals and LIF."""
    sim = session.simulator
    t = sim.current_time_us
    tick = t + session.config.dt_us
    motor = session.layout.motor
    arrivals = {j: [] for j in motor}
    for time_us, post, pre, slot, sequence, weight_mv in sorted(sim._queue):
        if time_us <= tick and post in arrivals:
            assert time_us > t
            arrivals[post].append((time_us, weight_mv, pre, slot, sequence))
    retained = sum(x > tick - session.readout.window_us for x in session.readout._spike_times)
    cells = {}
    for j in motor:
        p = sim.parameters[j]
        v = sim.voltage_mv[j]
        syn = sim.synaptic_drive_mv[j]
        refractory = sim.refractory_until_us[j]
        cursor = t
        for at, weight_mv, _, _, _ in arrivals[j]:
            if cursor < min(at, refractory):
                until = min(at, refractory)
                syn *= math.exp(-(until - cursor) / p.tau_syn_us)
                v = p.v_reset_mv
                cursor = until
            if cursor < at:
                v, syn = advance_lif(v, syn, 0.0, at - cursor, p)
                cursor = at
            syn += weight_mv
        if cursor < min(tick, refractory):
            until = min(tick, refractory)
            syn *= math.exp(-(until - cursor) / p.tau_syn_us)
            v = p.v_reset_mv
            cursor = until
        if cursor < tick:
            v, syn = advance_lif(v, syn, 0.0, tick - cursor, p)
        active_us = max(0, tick - max(t, refractory))
        alpha = -math.expm1(-active_us / p.tau_m_us)
        eligible = tick >= refractory
        critical_drive = ((p.v_threshold_mv - v) / alpha if alpha > 0 else None)
        predicted = {
            "no_pulse_reference": eligible and v >= p.v_threshold_mv,
            "locked_signed": eligible and v + alpha * (20.0 * signs[j]) >= p.v_threshold_mv,
            "locked_signed_inverse": eligible and v - alpha * (20.0 * signs[j]) >= p.v_threshold_mv,
        }
        cells[str(j)] = {
            "voltage_start_mv": sim.voltage_mv[j],
            "synaptic_start_mv": sim.synaptic_drive_mv[j],
            "refractory_until_us": refractory,
            "arrival_events": arrivals[j],
            "voltage_no_drive_pre_reset_mv": v,
            "synaptic_end_mv": syn,
            "external_drive_coefficient": alpha,
            "critical_external_drive_mv": critical_drive,
            "predicted_spike": predicted,
        }
    counts = {name: retained + sum(c["predicted_spike"][name] for c in cells.values())
              for name in BRANCHES}
    return {"time_us": t, "next_tick_us": tick,
            "retained_prior_window_spikes": retained,
            "predicted_readout_counts": counts,
            "predicted_next_tick_crosses": {name: count >= session.readout.on_threshold
                                            for name, count in counts.items()},
            "cells": cells}


def main() -> None:
    spec = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert spec["stage"] == "A11.2"
    assert spec["intervention"]["branches"] == list(BRANCHES)
    parent_result = json.loads((A11 / "result.json").read_text(encoding="utf-8"))
    parent_audit = json.loads((A11 / "audit.json").read_text(encoding="utf-8"))
    assert parent_audit["status"] == "passed"
    assert parent_audit["result_sha256"] == sha(A11 / "result.json")
    parent_path = A11 / "no_pulse_post_pulse_checkpoint.pkl"
    assert sha(parent_path) == parent_result["branches"]["no_pulse"]["post_pulse_checkpoint_sha256"]
    parent = TinyLaneSession.from_trusted_checkpoint_bytes(parent_path.read_bytes())
    target_t = spec["state"]["pre_intervention_time_us"]
    parent.run_until(target_t)
    assert parent.simulator.current_time_us == target_t
    assert parent.resolved_count == 372
    assert len(parent.readout._spike_times) == spec["state"]["expected_readout_count"] == 5
    assert parent.readout.on_threshold == spec["state"]["fixed_on_threshold"] == 10
    assert parent.readout.key_down is spec["state"]["expected_key_down"] is False
    assert parent.config.exploration_probability == 0.0
    assert not parent.config.plasticity_enabled
    assert len(parent.layout.motor) == 32
    signs = {int(j): value for j, value in parent_result["locked_motor_signs"].items()}
    assert set(signs) == set(parent.layout.motor)
    assert sum(v > 0 for v in signs.values()) == 22
    assert sum(v < 0 for v in signs.values()) == 10
    pre = parent.checkpoint_bytes()
    analytic = analytic_motor_next_tick(parent, signs)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "pre_intervention_checkpoint.pkl").write_bytes(pre)
    atomic_json(OUT / "status.json", {"status": "running", "protocol_sha256": sha(PROTOCOL)})
    initial_weights = weights(parent)
    motor = parent.layout.motor
    records = {}
    for name in BRANCHES:
        clone = TinyLaneSession.from_trusted_checkpoint_bytes(pre)
        assert weights(clone) == initial_weights
        n_actions = len(clone.game.result().actions)
        n_decisions = len(clone.decisions)
        n_pulses = len(clone.exploration_pulses)
        predictor_before = clone.reward.predictor.expected_utility
        original_set = clone.simulator.set_external_drive_mv
        drive_record = {}

        def injected_drive(drive):
            assert all(drive[j] == 0.0 for j in motor)
            changed = list(drive)
            for j in motor:
                changed[j] = (0.0 if name == "no_pulse_reference" else
                              20.0 * signs[j] * (1 if name == "locked_signed" else -1))
            assert changed[:motor[0]] == list(drive[:motor[0]])
            assert changed[motor[-1] + 1:] == list(drive[motor[-1] + 1:])
            drive_record["original_motor_mv"] = [drive[j] for j in motor]
            drive_record["applied_motor_mv"] = [changed[j] for j in motor]
            original_set(changed)

        clone.simulator.set_external_drive_mv = injected_drive
        try:
            clone.step()
        finally:
            del clone.simulator.set_external_drive_mv
        assert drive_record
        assert len(clone.exploration_pulses) == n_pulses
        post_tick = clone.checkpoint_bytes()
        (OUT / f"{name}_post_intervention_checkpoint.pkl").write_bytes(post_tick)
        if name == "no_pulse_reference":
            reference = TinyLaneSession.from_trusted_checkpoint_bytes(pre)
            reference.step()
            assert_same_state_except_weights(clone, reference)
            assert weights(clone) == weights(reference)
        first_tick_spikes = [j for j in motor if clone.simulator.spiked_this_tick[j]]
        predicted = [j for j in motor if analytic["cells"][str(j)]["predicted_spike"][name]]
        assert first_tick_spikes == predicted, (name, first_tick_spikes, predicted)
        assert len(clone.readout._spike_times) == analytic["predicted_readout_counts"][name]
        spike_events = []
        readout_ticks = []
        rises = []
        on_before = len(parent.readout._spike_times) >= parent.readout.on_threshold
        first_action = None

        def capture() -> None:
            nonlocal on_before, first_action
            t = clone.simulator.current_time_us
            batch = [j for j in motor if clone.simulator.spiked_this_tick[j]]
            spike_events.extend((t, j) for j in batch)
            count = len(clone.readout._spike_times)
            now_on = count >= clone.readout.on_threshold
            readout_ticks.append({"time_us": t, "count": count,
                                  "key_down": clone.readout.key_down,
                                  "motor_spikes": batch})
            if now_on and not on_before:
                rises.append(t)
            on_before = now_on
            if first_action is None:
                first = next((a for a in clone.game.result().actions[n_actions:]
                              if a.action.kind.value == "down"), None)
                if first is not None:
                    first_action = {"time_us": first.action.time_us,
                                    "disposition": first.disposition.value,
                                    "note_id": first.note_id}

        capture()
        while clone.resolved_count < 373:
            clone.step()
            capture()
        assert weights(clone) == initial_weights
        assert len(clone.exploration_pulses) == n_pulses
        assert all(not feedback.weight_changes for feedback in clone.feedback[372:373])
        actions = [{"time_us": a.action.time_us, "kind": a.action.kind.value,
                    "disposition": a.disposition.value, "note_id": a.note_id}
                   for a in clone.game.result().actions[n_actions:]]
        score = event_record(clone, 372)
        if name == "no_pulse_reference":
            saved = parent_result["branches"]["no_pulse"]
            assert actions == [a for a in saved["actions"] if a["time_us"] > target_t]
            assert score == saved["resolved_training_event_with_learning_frozen"]
            assert rises[0] == spec["state"]["expected_no_pulse_first_crossing_us"]
        records[name] = {
            "post_intervention_checkpoint_sha256": byte_sha(post_tick),
            "original_motor_drive_mv": drive_record["original_motor_mv"],
            "applied_motor_drive_mv": drive_record["applied_motor_mv"],
            "first_tick_motor_spikes": first_tick_spikes,
            "spike_events": spike_events,
            "readout_ticks": readout_ticks,
            "threshold_rises_us": rises,
            "first_threshold_rise_us": rises[0] if rises else None,
            "first_action": first_action,
            "actions": actions,
            "decisions": [{"time_us": d.time_us, "kind": d.action.kind.value,
                           "spike_count_in_window": d.spike_count_in_window}
                          for d in clone.decisions[n_decisions:]],
            "resolved_event": score,
            "predictor_before": predictor_before,
            "predictor_after_resolution": clone.reward.predictor.expected_utility,
            "weight_change_count": sum(len(f.weight_changes) for f in clone.feedback[372:373]),
            "new_exploration_pulse_count": len(clone.exploration_pulses) - n_pulses,
        }
        print(json.dumps({"branch": name, "first_rise_us": records[name]["first_threshold_rise_us"],
                          "first_action": first_action, "first_tick_count":
                          records[name]["readout_ticks"][0]["count"]}), flush=True)
    t0 = records["no_pulse_reference"]["first_threshold_rise_us"]
    ts = [records[name]["first_threshold_rise_us"] for name in BRANCHES[1:]]
    actions_present = all(records[name]["first_action"] is not None for name in BRANCHES)
    opposite = actions_present and all(t is not None for t in ts) and (
        (ts[0] < t0 < ts[1]) or (ts[1] < t0 < ts[0]))
    if opposite:
        classification = "PASS_LOCAL_BIDIRECTIONAL"
    elif actions_present and all(t is not None for t in ts) and (
        (ts[0] < t0 and ts[1] == t0) or (ts[1] < t0 and ts[0] == t0)
        or (ts[0] > t0 and ts[1] == t0) or (ts[1] > t0 and ts[0] == t0)):
        classification = "ONE_SIDED"
    else:
        classification = "INCONCLUSIVE"
    result = {
        "status": "complete", "stage": "A11.2", "study_id": spec["study_id"],
        "protocol_sha256": sha(PROTOCOL),
        "a11_result_sha256": sha(A11 / "result.json"),
        "a11_audit_sha256": sha(A11 / "audit.json"),
        "a11_parent_checkpoint_sha256": sha(parent_path),
        "pre_intervention_checkpoint_sha256": byte_sha(pre),
        "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in (
            ROOT / "src/project_b/experiments/tiny_brain.py",
            ROOT / "src/project_b/neurons/lif.py",
            ROOT / "src/project_b/simulation/spiking.py",
            ROOT / "src/project_b/motor/fixed_readout.py",
            ROOT / "scripts/a11_2_bidirectional_headroom_gate.py")},
        "pre_intervention_time_us": target_t,
        "pre_intervention_readout_count": len(parent.readout._spike_times),
        "initial_plastic_weights_mv": initial_weights,
        "motor_ids": list(motor),
        "locked_motor_signs": signs,
        "analytic_next_tick": analytic,
        "branches": records,
        "first_rise_delta_vs_no_pulse_us": {name: records[name]["first_threshold_rise_us"] - t0
                                             if records[name]["first_threshold_rise_us"] is not None else None
                                             for name in BRANCHES[1:]},
        "classification": classification,
        "completed_utc": datetime.now(timezone.utc).isoformat(),
    }
    atomic_json(OUT / "result.json", result)
    atomic_json(OUT / "status.json", {"status": "complete", "protocol_sha256": sha(PROTOCOL),
                                      "result_sha256": sha(OUT / "result.json")})
    print(json.dumps({"classification": classification, "deltas_us":
                      result["first_rise_delta_vs_no_pulse_us"]}), flush=True)


if __name__ == "__main__":
    main()
