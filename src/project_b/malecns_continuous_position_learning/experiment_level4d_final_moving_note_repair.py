"""Final Level 4D run with MBON-valid output and note-local eligibility window."""

from __future__ import annotations

import json
from pathlib import Path

from project_b.malecns_continuous_position_learning.encoder import population_drive
from project_b.malecns_continuous_position_learning.experiment_level3b_dan_ensemble import (
    CONFIG_DEFAULT as LEVEL3B_CONFIG,
    _dan_coverage,
    _load_inputs as _load_level3b_inputs,
)
from project_b.malecns_continuous_position_learning.experiment_level4_moving_note import _sha256
from project_b.malecns_continuous_position_learning.experiment_level4c_moving_note_learning import (
    _inputs as _level4c_inputs,
)
from project_b.malecns_minimal_internal_learning.ltd import LocalLTD
from project_b.malecns_continuous_position_learning.probe import _lif
from project_b.simulation import SpikingSimulator
from project_b.synapses import SparseGraph, Synapse


CONFIG_DEFAULT = "configs/malecns_level4d_final_moving_note_repair.json"
RESULT_DEFAULT = "runs/malecns_level4d_final_moving_note_repair/result.json"
LEVEL4C_CONFIG = "configs/malecns_level4c_moving_note_learning.json"
LEVEL4C_RESULT = "runs/malecns_level4c_moving_note_learning/result.json"
LEVEL4B_READOUT_CONFIG = "configs/malecns_level4_moving_note_500ms_readout_validity_v1.json"


def _inputs(root: Path, config_path: str):
    root = Path(root)
    stage = json.loads((root / config_path).read_text(encoding="utf-8"))
    if _sha256(root / LEVEL4C_CONFIG) != stage["parent_level4c_config_sha256"]:
        raise ValueError("Level 4C config changed after the final repair was frozen")
    if _sha256(root / LEVEL4C_RESULT) != stage["parent_level4c_result_sha256"]:
        raise ValueError("Level 4C result changed after the final repair was frozen")
    if _sha256(root / LEVEL4B_READOUT_CONFIG) != stage["parent_level4b_readout_config_sha256"]:
        raise ValueError("Level 4B readout config changed after the final repair was frozen")
    old_result = json.loads((root / LEVEL4C_RESULT).read_text(encoding="utf-8"))
    if old_result.get("status") != "FAIL":
        raise ValueError("Level 4D must preserve the recorded Level 4C FAIL as its parent")
    _, l3, parent, audit, threshold = _level4c_inputs(root, LEVEL4C_CONFIG)
    l3_loaded, parent_loaded, audit_loaded, _, threshold_loaded = _load_level3b_inputs(root, LEVEL3B_CONFIG)
    if (l3 != l3_loaded or parent != parent_loaded or audit != audit_loaded or
            threshold != threshold_loaded):
        raise ValueError("Level 4D parent resolution disagrees with the frozen Level 3B inputs")
    protocol = stage["protocol"]
    if stage["dan_source_ids"] != l3["dan_source_ids"]:
        raise ValueError("Level 4D changed the frozen DAN ensemble")
    fixed = {
        "traversal_duration_us": 500_000,
        "dt_us": parent["overlay"]["lif"]["dt_us"],
        "position_bin_width": 0.05,
        "kc_count": 32,
        "encoder_sigma": parent["encoder"]["sigma"],
        "peak_drive_mv_equivalent": parent["encoder"]["peak_drive_mv"],
        "eta": parent["training"]["ltd"]["eta"],
        "eligibility_tau_us": parent["training"]["ltd"]["tau_us"],
        "weight_floor_fraction_of_immutable_original": parent["training"]["ltd"]["minimum_fraction"],
        "action_threshold_mv": threshold,
    }
    for key, value in fixed.items():
        if protocol[key] != value:
            raise ValueError(f"Level 4D changed frozen setting {key}")
    if protocol["training_duration"]["blocks"] != parent["training"]["blocks"]:
        raise ValueError("Level 4D changed the inherited block duration")
    if protocol["training_duration"]["presentations"] != len(parent["training"]["sequence"]):
        raise ValueError("Level 4D changed the inherited presentation count")
    if protocol["training_duration"]["trial_spacing_us"] != parent["training"]["trial_spacing_us"]:
        raise ValueError("Level 4D changed inherited schedule spacing")
    if protocol["eligibility_locality_repair"]["window_us"] != 50_000:
        raise ValueError("Level 4D eligibility window differs from its frozen protocol")
    if protocol["action_output_validity_repair"]["threshold_mv"] != threshold:
        raise ValueError("Level 4D changed the inherited action threshold")
    return stage, l3, parent, audit, threshold


def _position_at(time_us: int, duration_us: int) -> float:
    return 1.0 - max(0, time_us) / duration_us


def _readout_from_timecourse(timecourse: list[dict], first_valid_time: int | None,
                             grid: list[float], bin_width: float,
                             threshold: float) -> tuple[list[dict], dict | None]:
    position_map = []
    half_bin = bin_width / 2.0
    for position in grid:
        samples = [row for row in timecourse
                   if abs(row["position"] - position) <= half_bin + 1e-12]
        valid = [row for row in samples if first_valid_time is not None
                 and row["time_us"] >= first_valid_time]
        if not valid:
            position_map.append({
                "position": position,
                "sample_count": len(samples),
                "valid_sample_count": 0,
                "mbon05_max_voltage_mv": None,
                "action": None,
                "state": "disabled_until_mbon05_response",
                "readout_time_us": None,
            })
            continue
        maximum = max(row["mbon05_voltage_mv"] for row in valid)
        action = maximum <= threshold
        position_map.append({
            "position": position,
            "sample_count": len(samples),
            "valid_sample_count": len(valid),
            "mbon05_max_voltage_mv": maximum,
            "action": action,
            "state": "action" if action else "no_action",
            # The frozen maximum-voltage readout is available at bin completion.
            "readout_time_us": max(row["time_us"] for row in valid),
        })
    action_rows = [row for row in position_map if row["action"] is True]
    first_row = min(action_rows, key=lambda row: row["readout_time_us"]) if action_rows else None
    first_action = None if first_row is None else {
        "time_us": first_row["readout_time_us"],
        "position": first_row["position"],
        "position_bin": [first_row["position"] - half_bin,
                         first_row["position"] + half_bin],
        "mbon05_max_voltage_mv": first_row["mbon05_max_voltage_mv"],
    }
    return position_map, first_action


def _simulate_note(parent: dict, weights: list[float], duration_us: int,
                   bin_width: float, threshold: float) -> dict:
    cells = parent["circuit"]["selected_kcs"]
    n_kc = len(cells)
    dt = parent["overlay"]["lif"]["dt_us"]
    graph = SparseGraph(n_kc + 1, [
        Synapse(i, n_kc, weights[i], parent["overlay"]["synaptic_delay_us"])
        for i in range(n_kc)
    ])
    initial_drive = list(population_drive(
        1.0, cells, sigma=parent["encoder"]["sigma"],
        peak_drive_mv=parent["encoder"]["peak_drive_mv"])) + [0.0]
    sim = SpikingSimulator([_lif(parent)] * (n_kc + 1), graph, initial_drive,
                           dt_us=dt, record_neurons=[n_kc], record_spikes=True)
    for tick in range(dt, duration_us + dt, dt):
        sim.run_until(tick)
        if tick < duration_us:
            position = _position_at(tick, duration_us)
            sim.set_external_drive_mv(list(population_drive(
                position, cells, sigma=parent["encoder"]["sigma"],
                peak_drive_mv=parent["encoder"]["peak_drive_mv"])) + [0.0])
    snapshot = sim.snapshot()
    kc_spikes = []
    counts = {str(int(cell["source_id"])): 0 for cell in cells}
    for spike in snapshot.spikes:
        if spike.neuron_index >= n_kc:
            continue
        source_id = int(cells[spike.neuron_index]["source_id"])
        counts[str(source_id)] += 1
        kc_spikes.append({
            "time_us": spike.time_us,
            "position": _position_at(max(0, spike.time_us - dt), duration_us),
            "kc_source_id": source_id,
            "kc_index": spike.neuron_index,
        })
    first_kc_spike = min((row["time_us"] for row in kc_spikes), default=None)
    voltage_rows = sorted((row.time_us, row.voltage_before_reset_mv)
                          for row in snapshot.voltage_trace if row.neuron_index == n_kc)
    raw_timecourse = [{
        "time_us": time_us,
        "position": _position_at(max(0, time_us - dt), duration_us),
        "mbon05_voltage_mv": voltage,
        "raw_threshold_action": voltage <= threshold,
    } for time_us, voltage in voltage_rows if time_us > 0]
    # Sensory validity begins on a measured nonzero postsynaptic MBON response;
    # the raw KC spike is retained as evidence but cannot open the output gate.
    first_valid = next((row["time_us"] for row in raw_timecourse
                        if row["mbon05_voltage_mv"] > 0.0), None)
    position_map, first_action = _readout_from_timecourse(
        raw_timecourse, first_valid, parent["evaluation"]["position_grid"],
        bin_width, threshold)
    for row in raw_timecourse:
        row["output_enabled"] = first_valid is not None and row["time_us"] >= first_valid
        row["action"] = None if not row["output_enabled"] else row["raw_threshold_action"]
    return {
        "trajectory_duration_us": duration_us,
        "total_kc_spikes": len(kc_spikes),
        "spiking_kc_source_ids": sorted(int(source_id) for source_id, count in counts.items() if count),
        "kc_spike_counts_by_source_id": {source_id: count for source_id, count in counts.items() if count},
        "kc_spikes_over_time": kc_spikes,
        "first_kc_spike_time_us": first_kc_spike,
        "first_mbon05_valid_time_us": first_valid,
        "mbon05_peak_voltage_mv": max((row["mbon05_voltage_mv"] for row in raw_timecourse), default=0.0),
        "mbon05_timecourse": raw_timecourse,
        "first_action": first_action,
        "position_to_action_map": position_map,
        "action_positions": [row["position"] for row in position_map if row["action"] is True],
        "disabled_positions": [row["position"] for row in position_map if row["action"] is None],
        "no_action_before_mbon05_validity": all(
            row["action"] is None and not row["output_enabled"]
            for row in raw_timecourse
            if first_valid is None or row["time_us"] < first_valid),
        "validity_opens_only_after_mbon_response": (
            first_valid is not None and
            next(row for row in raw_timecourse if row["time_us"] == first_valid)
                ["mbon05_voltage_mv"] > 0.0),
    }


def _stimulate_dans(parent: dict, stage: dict, onset_us: int) -> dict[int, list[int]]:
    stimulation = stage["protocol"]["dan_stimulation"]
    result = {}
    for dan_id in stage["dan_source_ids"]:
        sim = SpikingSimulator([_lif(parent)], SparseGraph(1, []), [0.0],
            dt_us=parent["overlay"]["lif"]["dt_us"], record_neurons=[0], record_spikes=True)
        sim.run_until(onset_us)
        sim.set_external_drive_mv([stimulation["pulse_amplitude_mv_equivalent"]])
        sim.run_until(onset_us + stimulation["pulse_duration_us"])
        result[int(dan_id)] = [spike.time_us for spike in sim.snapshot().spikes]
    return result


def _trigger_position(arm: str, position_class: str, stage: dict) -> float | None:
    if arm in ("target_teaching", "matched_dan_on_plasticity_off_control"):
        return (stage["protocol"]["dan_stimulation"]["trigger_positions"]["target"]
                if position_class == "target_region" else None)
    if arm == "wrong_region_teaching":
        return (stage["protocol"]["dan_stimulation"]["trigger_positions"]["wrong"]
                if position_class == "wrong_region_distractor" else None)
    raise ValueError(f"unknown Level 4D arm {arm}")


def _train_arm(parent: dict, stage: dict, audit: dict, threshold: float, *, arm: str) -> dict:
    cells = parent["circuit"]["selected_kcs"]
    ids = [int(cell["source_id"]) for cell in cells]
    initial = [cell["plastic_contact_rows"] / parent["circuit"]["plastic_contact_count"]
               for cell in cells]
    weights = list(initial)
    coverage = _dan_coverage(audit)
    slot_by_id = {source_id: index for index, source_id in enumerate(ids)}
    protocol = stage["protocol"]
    duration = protocol["traversal_duration_us"]
    bin_width = protocol["position_bin_width"]
    spacing = protocol["training_duration"]["trial_spacing_us"]
    window_us = protocol["eligibility_locality_repair"]["window_us"]
    ltd = parent["training"]["ltd"]
    plasticity_on = arm != "matched_dan_on_plasticity_off_control"
    trials, weight_history, block_summaries = [], [], []
    for scheduled in parent["training"]["sequence"]:
        note_offset = (scheduled["presentation"] - 1) * spacing
        weights_before = list(weights)
        note = _simulate_note(parent, weights, duration, bin_width, threshold)
        trigger = _trigger_position(arm, scheduled["position_class"], stage)
        dan_spikes = {int(dan_id): [] for dan_id in stage["dan_source_ids"]}
        pulse_onset = None
        dan_gate_time = None
        if trigger is not None:
            pulse_onset = round((1.0 - trigger) * duration)
            if pulse_onset % parent["overlay"]["lif"]["dt_us"]:
                raise ValueError("DAN teaching position misses the frozen integration grid")
            dan_spikes = _stimulate_dans(parent, stage, pulse_onset)
            dan_gate_time = min((times[0] for times in dan_spikes.values() if times), default=None)
        active_dans = [dan_id for dan_id, times in dan_spikes.items() if times]
        active_kcs = set().union(*(coverage[dan_id] for dan_id in active_dans)) if active_dans else set()
        active_slots = (tuple(sorted(slot_by_id[kc] for kc in active_kcs))
                        if plasticity_on else ())
        rule = LocalLTD(list(weights), original_weights=initial,
                        plastic_slots=active_slots, tau_us=ltd["tau_us"],
                        eta=ltd["eta"], minimum_fraction=ltd["minimum_fraction"])
        window_start = (max(0, dan_gate_time - window_us)
                        if dan_gate_time is not None else None)
        credited_spikes = [spike for spike in note["kc_spikes_over_time"]
                           if dan_gate_time is not None and
                           window_start <= spike["time_us"] <= dan_gate_time]
        for spike in credited_spikes:
            rule.observe_kc_spike(spike["kc_index"], note_offset + spike["time_us"])
        commit_time = (note_offset + dan_gate_time if dan_gate_time is not None
                       else note_offset + duration)
        changes = rule.teacher_pulse(commit_time, teacher=bool(active_slots))
        weights = list(rule.weights)
        changed = [dict(change,
                        source_id=ids[change["edge_index"]],
                        active_connected_dan_source_ids=[dan_id for dan_id in active_dans
                            if ids[change["edge_index"]] in coverage[dan_id]],
                        note_presentation=scheduled["presentation"],
                        scheduled_class=scheduled["position_class"],
                        credited_kc_source_ids=[row["kc_source_id"] for row in credited_spikes])
                   for change in changes]
        floor_ids = [ids[index] for index, (weight, original) in
                     enumerate(zip(weights, initial))
                     if weight <= original * ltd["minimum_fraction"] + 1e-15]
        trial = {
            "presentation": scheduled["presentation"],
            "block": scheduled["block"],
            "scheduled_class_for_teacher_timing_only": scheduled["position_class"],
            "trigger_position": trigger,
            "dan_pulse_onset_us_relative_to_note": pulse_onset,
            "dan_spike_times_us_relative_to_note": {str(key): value for key, value in dan_spikes.items()},
            "active_dan_source_ids": active_dans,
            "dan_gate_time_us_relative_to_note": dan_gate_time,
            "eligibility_window_start_us_relative_to_note": window_start,
            "eligibility_window_us": window_us,
            "kc_spikes_credited_to_eligibility": credited_spikes,
            "kc_spikes_excluded_as_too_early": sum(
                dan_gate_time is not None and spike["time_us"] < window_start
                for spike in note["kc_spikes_over_time"]),
            "dan_gate_kc_source_ids": [ids[index] for index in active_slots],
            "positive_eligibility_kc_source_ids_at_gate": [
                ids[index] for index in active_slots
                if dan_gate_time is not None and rule.eligibility_at(index, commit_time) > 0.0],
            "first_action_during_training_note": note["first_action"],
            "no_action_before_mbon05_validity": note["no_action_before_mbon05_validity"],
            "validity_opens_only_after_mbon_response": note["validity_opens_only_after_mbon_response"],
            "kc_spikes_over_time": note["kc_spikes_over_time"],
            "weight_changes": changed,
            "weights_before": weights_before,
            "weights_after": list(weights),
            "weights_at_original_floor_source_ids": floor_ids,
            "presentation_local_eligibility_reset": True,
            "teacher_class_is_not_sensory_input": True,
        }
        trials.append(trial)
        weight_history.append({
            "presentation": scheduled["presentation"], "block": scheduled["block"],
            "weights": list(weights), "weight_changes": changed,
            "weights_at_original_floor_source_ids": floor_ids,
        })
        if scheduled["presentation"] % 10 == 0:
            block_summaries.append({
                "block": scheduled["block"], "presentations_completed": scheduled["presentation"],
                "weights": list(weights), "weights_at_original_floor_source_ids": floor_ids,
            })
    return {
        "arm": arm,
        "training_presentations": len(trials),
        "blocks_completed": len(block_summaries),
        "scheduled_dan_pulse_count": sum(row["trigger_position"] is not None for row in trials),
        "active_dan_event_count": sum(bool(row["active_dan_source_ids"]) for row in trials),
        "total_weight_changes": sum(len(row["weight_changes"]) for row in trials),
        "initial_weights": initial,
        "final_weights": list(weights),
        "weights_at_original_floor_final_source_ids": [ids[index] for index, (weight, original)
            in enumerate(zip(weights, initial))
            if weight <= original * ltd["minimum_fraction"] + 1e-15],
        "trials": trials,
        "evolving_weights": weight_history,
        "block_weight_summaries": block_summaries,
    }


def _action_in_region(evaluation: dict, core: list[float]) -> bool:
    action = evaluation["first_action"]
    return action is not None and core[0] <= action["position"] <= core[1]


def run_level4d(root: Path, config_path: str = CONFIG_DEFAULT) -> dict:
    root = Path(root)
    stage, level3b, parent, audit, threshold = _inputs(root, config_path)
    protocol = stage["protocol"]
    initial = [cell["plastic_contact_rows"] / parent["circuit"]["plastic_contact_count"]
               for cell in parent["circuit"]["selected_kcs"]]
    baseline = _simulate_note(parent, initial, protocol["traversal_duration_us"],
                              protocol["position_bin_width"], threshold)
    arms = {}
    for name in ("target_teaching", "wrong_region_teaching",
                 "matched_dan_on_plasticity_off_control"):
        trained = _train_arm(parent, stage, audit, threshold, arm=name)
        evaluation = _simulate_note(parent, trained["final_weights"],
            protocol["traversal_duration_us"], protocol["position_bin_width"], threshold)
        arms[name] = {**trained, "post_training_evaluation": {
            "dan_stimulation": "OFF", "plasticity": "OFF",
            "weights_retained": list(trained["final_weights"]), **evaluation}}

    all_trials = [trial for arm in arms.values() for trial in arm["trials"]]
    updates = [change for trial in all_trials for change in trial["weight_changes"]]
    coverage = _dan_coverage(audit)
    floor_fraction = parent["training"]["ltd"]["minimum_fraction"]
    floors_ok = all(
        all(weight + 1e-15 >= original * floor_fraction
            for weight, original in zip(history["weights"], arm["initial_weights"]))
        for arm in arms.values() for history in arm["evolving_weights"])
    local_updates_ok = all(
        change["eligibility"] > 0.0 and change["active_connected_dan_source_ids"] and
        any(change["source_id"] in coverage[dan_id]
            for dan_id in change["active_connected_dan_source_ids"])
        for change in updates)
    window_updates_ok = all(
        trial["eligibility_window_us"] == protocol["eligibility_locality_repair"]["window_us"] and
        all(trial["eligibility_window_start_us_relative_to_note"] <= spike["time_us"] <=
            trial["dan_gate_time_us_relative_to_note"]
            for spike in trial["kc_spikes_credited_to_eligibility"])
        for trial in all_trials if trial["trigger_position"] is not None)
    baseline_no_action = baseline["first_action"] is None
    target = arms["target_teaching"]
    wrong = arms["wrong_region_teaching"]
    control = arms["matched_dan_on_plasticity_off_control"]
    target_core = protocol["action_cores"]["target"]
    wrong_core = protocol["action_cores"]["wrong"]
    criteria = {
        "naive_baseline_has_no_first_action": baseline_no_action,
        "target_first_action_in_core": _action_in_region(target["post_training_evaluation"], target_core),
        "wrong_first_action_in_core": _action_in_region(wrong["post_training_evaluation"], wrong_core),
        "plasticity_off_weights_unchanged_and_no_action": (
            control["initial_weights"] == control["final_weights"] and
            control["post_training_evaluation"]["first_action"] is None),
        "target_and_wrong_actions_persist_dan_plasticity_off": (
            _action_in_region(target["post_training_evaluation"], target_core) and
            _action_in_region(wrong["post_training_evaluation"], wrong_core)),
        "output_validity_waits_for_mbon05_response": (
            baseline["validity_opens_only_after_mbon_response"] and all(
                trial["validity_opens_only_after_mbon_response"]
                for trial in all_trials) and
            all(arm["post_training_evaluation"]["validity_opens_only_after_mbon_response"]
                for arm in arms.values())),
        "no_action_before_mbon05_output_validity": (
            baseline["no_action_before_mbon05_validity"] and all(
                trial["no_action_before_mbon05_validity"] for trial in all_trials) and
            all(arm["post_training_evaluation"]["no_action_before_mbon05_validity"]
                for arm in arms.values())),
        "all_weight_updates_within_frozen_eligibility_window": window_updates_ok,
        "all_weight_updates_have_local_eligibility_and_anatomical_dan_gate": local_updates_ok,
        "immutable_original_weight_floor_respected_throughout": floors_ok,
        "all_predeclared_blocks_and_presentations_completed": all(
            arm["blocks_completed"] == protocol["training_duration"]["blocks"] and
            arm["training_presentations"] == protocol["training_duration"]["presentations"]
            for arm in arms.values()),
        "all_scheduled_dan_events_activate_all_three_dans": all(
            arm["scheduled_dan_pulse_count"] == 600 and arm["active_dan_event_count"] == 600 and
            all(len(trial["active_dan_source_ids"]) == 3 for trial in arm["trials"]
                if trial["trigger_position"] is not None)
            for arm in arms.values()),
    }
    return {
        "experiment_id": stage["experiment_id"],
        "stage": "level4d_final_moving_note_repair",
        "config": config_path,
        "config_sha256": _sha256(root / config_path),
        "parent_level4c_config_sha256": stage["parent_level4c_config_sha256"],
        "parent_level4c_result_sha256": stage["parent_level4c_result_sha256"],
        "fixed_settings": {
            "duration_us": protocol["traversal_duration_us"],
            "kc_count": protocol["kc_count"], "mbon": protocol["mbon_source"],
            "dan_source_ids": stage["dan_source_ids"],
            "encoder_sigma": protocol["encoder_sigma"],
            "threshold_mv": threshold,
            "eta": parent["training"]["ltd"]["eta"],
            "original_weight_floor_fraction": floor_fraction,
        },
        "action_validity_repair": protocol["action_output_validity_repair"],
        "eligibility_locality_repair": protocol["eligibility_locality_repair"],
        "training_duration": protocol["training_duration"],
        "learning_runs": 3,
        "baseline_naive_evaluation": baseline,
        "arms": arms,
        "final_first_actions": {
            name: arm["post_training_evaluation"]["first_action"]
            for name, arm in arms.items()},
        "criteria": criteria,
        "status": "PASS" if all(criteria.values()) else "FAIL",
        "decision": ("The final Level 4D run passed its frozen criteria. Level 4 is complete."
                     if all(criteria.values()) else
                     "The final Level 4D run completed under the frozen protocol but failed one or more criteria. Level 4 is complete; no tuning or follow-up search was run."),
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--config", default=CONFIG_DEFAULT)
    parser.add_argument("--output", type=Path, default=Path(RESULT_DEFAULT))
    args = parser.parse_args()
    result = run_level4d(args.root, args.config)
    output = args.output if args.output.is_absolute() else args.root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"], "criteria": result["criteria"],
        "first_actions": result["final_first_actions"],
        "weight_changes": {key: arm["total_weight_changes"] for key, arm in result["arms"].items()},
        "floor_hits": {key: len(arm["weights_at_original_floor_final_source_ids"])
                       for key, arm in result["arms"].items()},
    }, indent=2))
