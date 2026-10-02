"""Level 4C moving-note learning with frozen Level 4B output validity."""

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
from project_b.malecns_minimal_internal_learning.ltd import LocalLTD
from project_b.malecns_continuous_position_learning.probe import _lif
from project_b.simulation import SpikingSimulator
from project_b.synapses import SparseGraph, Synapse


CONFIG_DEFAULT = "configs/malecns_level4c_moving_note_learning.json"
RESULT_DEFAULT = "runs/malecns_level4c_moving_note_learning/result.json"
LEVEL4B_CONFIG = "configs/malecns_level4b_moving_output_admission_repair.json"
LEVEL4B_RESULT = "runs/malecns_level4b_moving_output_admission_repair/result.json"
LEVEL4B_READOUT_CONFIG = "configs/malecns_level4_moving_note_500ms_readout_validity_v1.json"


def _inputs(root: Path, config_path: str):
    root = Path(root)
    stage = json.loads((root / config_path).read_text(encoding="utf-8"))
    if _sha256(root / LEVEL4B_READOUT_CONFIG) != stage["parent_level4_readout_config_sha256"]:
        raise ValueError("frozen Level 4B readout config changed after Level 4C freeze")
    if _sha256(root / LEVEL4B_CONFIG) != stage["parent_level4b_config_sha256"]:
        raise ValueError("Level 4B protocol config changed after Level 4C freeze")
    if _sha256(root / LEVEL4B_RESULT) != stage["parent_level4b_result_sha256"]:
        raise ValueError("Level 4B PASS receipt changed after Level 4C freeze")
    if _sha256(root / stage["parent_speed_config"]) != stage["parent_speed_config_sha256"]:
        raise ValueError("admitted 500-ms speed config changed after Level 4C freeze")
    if _sha256(root / LEVEL3B_CONFIG) != stage["parent_level3b_config_sha256"]:
        raise ValueError("Level 3B config changed after Level 4C freeze")
    if _sha256(root / stage["parent_level3b_result"]) != stage["parent_level3b_result_sha256"]:
        raise ValueError("Level 3B result changed after Level 4C freeze")
    if _sha256(root / stage["anatomy_audit"]) != stage["anatomy_audit_sha256"]:
        raise ValueError("frozen Level 3B anatomy audit changed after Level 4C freeze")

    level3b, parent, audit, _, threshold = _load_level3b_inputs(root, LEVEL3B_CONFIG)
    frozen_readout = json.loads((root / LEVEL4B_READOUT_CONFIG).read_text(encoding="utf-8"))
    b_protocol = json.loads((root / LEVEL4B_CONFIG).read_text(encoding="utf-8"))["protocol"]
    protocol = stage["protocol"]
    expected_ids = level3b["dan_source_ids"]
    if stage["dan_source_ids"] != expected_ids or expected_ids != [87177, 107285, 55210]:
        raise ValueError("Level 4C changed the frozen anatomy-selected DAN ensemble")
    fixed = {
        "traversal_duration_us": 500_000,
        "dt_us": parent["overlay"]["lif"]["dt_us"],
        "kc_count": len(parent["circuit"]["selected_kcs"]),
        "encoder_sigma": parent["encoder"]["sigma"],
        "eta": parent["training"]["ltd"]["eta"],
        "eligibility_tau_us": parent["training"]["ltd"]["tau_us"],
        "weight_floor_fraction_of_immutable_original": parent["training"]["ltd"]["minimum_fraction"],
        "action_threshold_mv": threshold,
        "peak_drive_mv_equivalent": parent["encoder"]["peak_drive_mv"],
    }
    for key, value in fixed.items():
        if protocol[key] != value:
            raise ValueError(f"Level 4C changed frozen Level 4B/Level 3B setting {key}")
    if protocol["training_duration"]["blocks"] != parent["training"]["blocks"]:
        raise ValueError("Level 4C training blocks differ from the inherited fixed duration")
    if protocol["training_duration"]["presentations"] != len(parent["training"]["sequence"]):
        raise ValueError("Level 4C presentation count differs from the frozen schedule")
    if protocol["training_duration"]["trial_spacing_us"] != parent["training"]["trial_spacing_us"]:
        raise ValueError("Level 4C changed the inherited presentation schedule spacing")
    if len(parent["training"]["sequence"]) != 1200 or any(
            sum(row["position_class"] == label for row in parent["training"]["sequence"]) != 600
            for label in ("target_region", "wrong_region_distractor")):
        raise ValueError("Level 4C requires the frozen 600 target / 600 wrong 1200-note schedule")
    if protocol["action_threshold_mv"] != frozen_readout["readout_validity"]["threshold_mv"]:
        raise ValueError("Level 4C changed the frozen Level 4B threshold")
    if b_protocol["duration_us"] != protocol["traversal_duration_us"]:
        raise ValueError("Level 4C changed the Level 4B admitted traversal duration")
    b_result = json.loads((root / LEVEL4B_RESULT).read_text(encoding="utf-8"))
    if b_result.get("status") != "PASS":
        raise ValueError("Level 4C requires the frozen Level 4B admission PASS")
    return stage, level3b, parent, audit, threshold


def _position_at(time_us: int, duration_us: int) -> float:
    return 1.0 - max(0, time_us) / duration_us


def _simulate_note(parent: dict, weights: list[float], duration_us: int,
                   bin_width: float, threshold: float) -> dict:
    cells = parent["circuit"]["selected_kcs"]
    n_kc = len(cells)
    dt = parent["overlay"]["lif"]["dt_us"]
    if duration_us <= 0 or duration_us % dt:
        raise ValueError("note duration must align with the frozen integration step")
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
    timecourse = []
    for time_us, voltage in voltage_rows:
        if time_us <= 0:
            continue
        position = _position_at(max(0, time_us - dt), duration_us)
        enabled = first_kc_spike is not None and time_us >= first_kc_spike
        action = bool(enabled and voltage <= threshold)
        timecourse.append({
            "time_us": time_us,
            "position": position,
            "mbon05_voltage_mv": voltage,
            "output_enabled": enabled,
            "action": action if enabled else None,
        })
    first_action_row = next((row for row in timecourse if row["action"] is True), None)
    first_action = None if first_action_row is None else {
        "time_us": first_action_row["time_us"],
        "position": first_action_row["position"],
        "mbon05_voltage_mv": first_action_row["mbon05_voltage_mv"],
    }

    grid = parent["evaluation"]["position_grid"]
    half_bin = bin_width / 2.0
    position_map = []
    for position in grid:
        rows = [row for row in timecourse
                if abs(row["position"] - position) <= half_bin + 1e-12]
        valid = [row for row in rows if row["output_enabled"]]
        if not valid:
            position_map.append({
                "position": position, "sample_count": len(rows),
                "enabled_sample_count": 0, "mbon05_max_voltage_mv": None,
                "mbon05_min_voltage_mv": None, "action_sample_count": 0,
                "action": None, "state": "disabled_before_first_kc_spike",
            })
            continue
        actions = sum(row["action"] is True for row in valid)
        position_map.append({
            "position": position,
            "sample_count": len(rows),
            "enabled_sample_count": len(valid),
            "mbon05_max_voltage_mv": max(row["mbon05_voltage_mv"] for row in valid),
            "mbon05_min_voltage_mv": min(row["mbon05_voltage_mv"] for row in valid),
            "action_sample_count": actions,
            "action": actions > 0,
            "state": "action" if actions else "no_action",
        })
    return {
        "trajectory_duration_us": duration_us,
        "total_kc_spikes": len(kc_spikes),
        "spiking_kc_source_ids": sorted(int(source_id) for source_id, count in counts.items() if count),
        "kc_spike_counts_by_source_id": {source_id: count for source_id, count in counts.items() if count},
        "kc_spikes_over_time": kc_spikes,
        "first_kc_spike_time_us": first_kc_spike,
        "mbon05_peak_voltage_mv": max((row["mbon05_voltage_mv"] for row in timecourse), default=0.0),
        "mbon05_timecourse": timecourse,
        "first_action": first_action,
        "position_to_action_map": position_map,
        "action_positions": [row["position"] for row in position_map if row["action"] is True],
        "disabled_positions": [row["position"] for row in position_map if row["action"] is None],
        "no_action_before_first_kc_spike": all(
            row["action"] is None and not row["output_enabled"]
            for row in timecourse
            if first_kc_spike is None or row["time_us"] < first_kc_spike),
    }


def _stimulate_dans(parent: dict, stage: dict, onset_us: int) -> dict[int, list[int]]:
    result = {}
    stimulation = stage["protocol"]["dan_stimulation"]
    for dan_id in stage["dan_source_ids"]:
        sim = SpikingSimulator([_lif(parent)], SparseGraph(1, []), [0.0],
            dt_us=parent["overlay"]["lif"]["dt_us"], record_neurons=[0], record_spikes=True)
        sim.run_until(onset_us)
        sim.set_external_drive_mv([stimulation["pulse_amplitude_mv_equivalent"]])
        sim.run_until(onset_us + stimulation["pulse_duration_us"])
        result[int(dan_id)] = [spike.time_us for spike in sim.snapshot().spikes]
    return result


def _scheduled_trigger(arm: str, position_class: str, stage: dict) -> float | None:
    if arm in ("target_teaching", "matched_dan_on_plasticity_off_control"):
        return (stage["protocol"]["teaching_positions"]["target"]
                if position_class == "target_region" else None)
    if arm == "wrong_region_teaching":
        return (stage["protocol"]["teaching_positions"]["wrong"]
                if position_class == "wrong_region_distractor" else None)
    raise ValueError(f"unknown Level 4C arm: {arm}")


def _train_arm(parent: dict, stage: dict, audit: dict, threshold: float,
               *, arm: str) -> dict:
    cells = parent["circuit"]["selected_kcs"]
    ids = [int(cell["source_id"]) for cell in cells]
    initial = [cell["plastic_contact_rows"] / parent["circuit"]["plastic_contact_count"]
               for cell in cells]
    weights = list(initial)
    coverage = _dan_coverage(audit)
    slot_by_id = {source_id: index for index, source_id in enumerate(ids)}
    duration = stage["protocol"]["traversal_duration_us"]
    spacing = stage["protocol"]["training_duration"]["trial_spacing_us"]
    dt = parent["overlay"]["lif"]["dt_us"]
    ltd = parent["training"]["ltd"]
    plasticity_enabled = arm != "matched_dan_on_plasticity_off_control"
    trials = []
    weight_history = []
    block_summaries = []
    schedule = parent["training"]["sequence"]
    for scheduled in schedule:
        note_offset = (scheduled["presentation"] - 1) * spacing
        weights_before = list(weights)
        note = _simulate_note(parent, weights, duration,
                              stage["protocol"]["position_bin_width"], threshold)
        trigger = _scheduled_trigger(arm, scheduled["position_class"], stage)
        dan_spikes: dict[int, list[int]] = {dan_id: [] for dan_id in stage["dan_source_ids"]}
        pulse_onset_us = None
        dan_gate_time_us = None
        if trigger is not None:
            pulse_onset_us = round((1.0 - trigger) * duration)
            if pulse_onset_us % dt:
                raise ValueError("teaching position does not align to the frozen time grid")
            dan_spikes = _stimulate_dans(parent, stage, pulse_onset_us)
            first_spikes = [times[0] for times in dan_spikes.values() if times]
            dan_gate_time_us = min(first_spikes, default=None)
        active_dans = [dan_id for dan_id, times in dan_spikes.items() if times]
        active_kcs = set().union(*(coverage[dan_id] for dan_id in active_dans)) if active_dans else set()
        active_slots = (tuple(sorted(slot_by_id[kc] for kc in active_kcs))
                        if plasticity_enabled else ())
        rule = LocalLTD(list(weights), original_weights=initial,
                        plastic_slots=active_slots, tau_us=ltd["tau_us"],
                        eta=ltd["eta"], minimum_fraction=ltd["minimum_fraction"])
        eligible_spikes = [row for row in note["kc_spikes_over_time"]
                           if dan_gate_time_us is not None and row["time_us"] <= dan_gate_time_us]
        for spike in eligible_spikes:
            rule.observe_kc_spike(spike["kc_index"], note_offset + spike["time_us"])
        if dan_gate_time_us is None:
            commit_time = note_offset + duration
        else:
            commit_time = note_offset + dan_gate_time_us
        changes = rule.teacher_pulse(commit_time, teacher=bool(active_slots))
        weights = list(rule.weights)
        changes_with_ids = [dict(change, source_id=ids[change["edge_index"]],
                                 active_connected_dan_source_ids=[dan_id for dan_id in active_dans
                                     if ids[change["edge_index"]] in coverage[dan_id]],
                                 note_presentation=scheduled["presentation"],
                                 scheduled_class=scheduled["position_class"])
                            for change in changes]
        floor_ids = [ids[index] for index, (weight, original) in
                     enumerate(zip(weights, initial))
                     if weight <= original * ltd["minimum_fraction"] + 1e-15]
        row = {
            "presentation": scheduled["presentation"],
            "block": scheduled["block"],
            "scheduled_class_for_teaching_timing_only": scheduled["position_class"],
            "trigger_position": trigger,
            "dan_pulse_onset_us_relative_to_note": pulse_onset_us,
            "dan_spike_times_us_relative_to_note": {str(key): value for key, value in dan_spikes.items()},
            "active_dan_source_ids": active_dans,
            "dan_gate_time_us_relative_to_note": dan_gate_time_us,
            "dan_gate_kc_source_ids": [ids[index] for index in active_slots],
            "positive_eligibility_kc_source_ids_at_gate": [
                ids[index] for index in active_slots
                if dan_gate_time_us is not None and
                rule.eligibility_at(index, commit_time) > 0.0],
            "kc_spike_count_before_dan_gate": len(eligible_spikes),
            "first_action_during_training_note": note["first_action"],
            "no_action_before_first_kc_spike": note["no_action_before_first_kc_spike"],
            "kc_spikes_over_time": note["kc_spikes_over_time"],
            "weight_changes": changes_with_ids,
            "weights_before": weights_before,
            "weights_after": list(weights),
            "weights_at_original_floor_source_ids": floor_ids,
            "presentation_local_eligibility_reset": True,
            "teacher_class_is_not_sensory_input": True,
        }
        trials.append(row)
        weight_history.append({
            "presentation": scheduled["presentation"],
            "block": scheduled["block"],
            "weights": list(weights),
            "weight_changes": changes_with_ids,
            "weights_at_original_floor_source_ids": floor_ids,
        })
        if scheduled["presentation"] % 10 == 0:
            block_summaries.append({
                "block": scheduled["block"],
                "presentations_completed": scheduled["presentation"],
                "weights": list(weights),
                "weights_at_original_floor_source_ids": floor_ids,
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


def _first_action_in_core(evaluation: dict, core: list[float]) -> bool:
    action = evaluation["first_action"]
    return action is not None and core[0] <= action["position"] <= core[1]


def run_level4c(root: Path, config_path: str = CONFIG_DEFAULT) -> dict:
    root = Path(root)
    stage, level3b, parent, audit, threshold = _inputs(root, config_path)
    baseline_weights = [cell["plastic_contact_rows"] / parent["circuit"]["plastic_contact_count"]
                        for cell in parent["circuit"]["selected_kcs"]]
    duration = stage["protocol"]["traversal_duration_us"]
    bin_width = stage["protocol"]["position_bin_width"]
    baseline = _simulate_note(parent, baseline_weights, duration, bin_width, threshold)

    arms = {}
    for arm_name in ("target_teaching", "wrong_region_teaching",
                     "matched_dan_on_plasticity_off_control"):
        learned = _train_arm(parent, stage, audit, threshold, arm=arm_name)
        evaluation = _simulate_note(parent, learned["final_weights"], duration, bin_width, threshold)
        arms[arm_name] = {**learned, "post_training_evaluation": {
            "dan_stimulation": "OFF",
            "plasticity": "OFF",
            "weights_retained": list(learned["final_weights"]),
            **evaluation,
        }}

    schedule_count = len(parent["training"]["sequence"])
    target_core = stage["protocol"]["teaching_positions"]["target_core"]
    wrong_core = stage["protocol"]["teaching_positions"]["wrong_core"]
    all_training_notes_valid = all(
        trial["no_action_before_first_kc_spike"]
        for arm in arms.values() for trial in arm["trials"])
    all_updates = [change for arm in arms.values() for trial in arm["trials"]
                   for change in trial["weight_changes"]]
    coverage = _dan_coverage(audit)
    update_gating = all(
        change["eligibility"] > 0.0 and
        bool(change["active_connected_dan_source_ids"]) and
        any(change["source_id"] in coverage[dan_id]
            for dan_id in change["active_connected_dan_source_ids"])
        for change in all_updates)
    floors_respected = all(
        all(weight + 1e-15 >= original * parent["training"]["ltd"]["minimum_fraction"]
            for weight, original in zip(history["weights"], arm["initial_weights"]))
        for arm in arms.values() for history in arm["evolving_weights"])
    control = arms["matched_dan_on_plasticity_off_control"]
    target = arms["target_teaching"]
    wrong = arms["wrong_region_teaching"]
    criteria = {
        "naive_baseline_no_first_action": baseline["first_action"] is None,
        "target_first_action_in_target_region": _first_action_in_core(
            target["post_training_evaluation"], target_core),
        "wrong_first_action_in_wrong_region": _first_action_in_core(
            wrong["post_training_evaluation"], wrong_core),
        "plasticity_off_control_unchanged_and_no_action": (
            control["initial_weights"] == control["final_weights"] and
            control["post_training_evaluation"]["first_action"] is None),
        "target_first_action_persists_frozen": _first_action_in_core(
            target["post_training_evaluation"], target_core),
        "wrong_first_action_persists_frozen": _first_action_in_core(
            wrong["post_training_evaluation"], wrong_core),
        "no_action_before_first_kc_spike_in_training_and_evaluation": (
            all_training_notes_valid and all(
                arms[name]["post_training_evaluation"]["no_action_before_first_kc_spike"]
                for name in arms) and baseline["no_action_before_first_kc_spike"]),
        "all_weight_updates_anatomically_dan_gated_and_locally_eligible": update_gating,
        "immutable_original_weight_floor_respected_throughout": floors_respected,
        "all_predeclared_blocks_and_presentations_completed": all(
            arm["blocks_completed"] == stage["protocol"]["training_duration"]["blocks"] and
            arm["training_presentations"] == schedule_count
            for arm in arms.values()),
        "all_scheduled_teaching_events_activate_three_dans": all(
            arm["scheduled_dan_pulse_count"] == 600 and arm["active_dan_event_count"] == 600 and
            all(len(trial["active_dan_source_ids"]) == 3
                for trial in arm["trials"] if trial["trigger_position"] is not None)
            for arm in arms.values()),
        "matched_control_performed_dan_pulses": control["scheduled_dan_pulse_count"] == 600 and
            control["active_dan_event_count"] == 600,
    }
    return {
        "experiment_id": stage["experiment_id"],
        "stage": "level4c_moving_note_learning",
        "config": config_path,
        "config_sha256": _sha256(root / config_path),
        "parents": {
            "level4b_readout_config_sha256": stage["parent_level4_readout_config_sha256"],
            "level4b_protocol_config_sha256": stage["parent_level4b_config_sha256"],
            "level4b_result_sha256": stage["parent_level4b_result_sha256"],
            "level3b_config_sha256": stage["parent_level3b_config_sha256"],
            "level3b_result_sha256": stage["parent_level3b_result_sha256"],
            "anatomy_audit_sha256": stage["anatomy_audit_sha256"],
        },
        "frozen_action_threshold_mv": threshold,
        "dan_source_ids": stage["dan_source_ids"],
        "dan_source_identities": level3b["dan_identities"],
        "training_duration": stage["protocol"]["training_duration"],
        "learning_runs": 3,
        "post_training_evaluations": "fresh note for each arm; DAN OFF and plasticity OFF",
        "baseline_naive_evaluation": baseline,
        "arms": arms,
        "final_first_actions": {
            "target_teaching": target["post_training_evaluation"]["first_action"],
            "wrong_region_teaching": wrong["post_training_evaluation"]["first_action"],
            "matched_dan_on_plasticity_off_control": control["post_training_evaluation"]["first_action"],
        },
        "criteria": criteria,
        "status": "PASS" if all(criteria.values()) else "FAIL",
        "decision": ("Level 4C met every predeclared moving-note first-action criterion. Stop after this run."
                     if all(criteria.values()) else
                     "Level 4C completed all predeclared arms and fixed-duration training, but failed one or more criteria. Preserve the result; do not tune or rerun."),
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--config", default=CONFIG_DEFAULT)
    parser.add_argument("--output", type=Path, default=Path(RESULT_DEFAULT))
    args = parser.parse_args()
    result = run_level4c(args.root, args.config)
    output = args.output if args.output.is_absolute() else args.root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "criteria": result["criteria"],
        "first_actions": result["final_first_actions"],
        "training_presentations": {key: value["training_presentations"]
                                   for key, value in result["arms"].items()},
        "weight_changes": {key: value["total_weight_changes"]
                           for key, value in result["arms"].items()},
    }, indent=2))
