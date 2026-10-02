"""Level 4: one continuously moving note with current-position-only input."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from project_b.malecns_continuous_position_learning.encoder import population_drive
from project_b.malecns_continuous_position_learning.experiment import _encoder_sha256, _evaluate
from project_b.malecns_continuous_position_learning.experiment_level3b_dan_ensemble import (
    CONFIG_DEFAULT as LEVEL3B_CONFIG,
    _dan_coverage,
    _dan_spike_times,
    _load_inputs,
)
from project_b.malecns_minimal_internal_learning.ltd import LocalLTD
from project_b.malecns_continuous_position_learning.probe import _lif
from project_b.simulation import SpikingSimulator
from project_b.synapses import SparseGraph, Synapse


CONFIG_DEFAULT = "configs/malecns_level4_moving_note.json"
RESULT_DEFAULT = "runs/malecns_level4_moving_note/result.json"
LEVEL3B_RESULT = "runs/malecns_dan_bridge_level3b/result.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _inputs(root: Path, config_path: str) -> tuple[dict, dict, dict, float]:
    root = Path(root)
    stage = json.loads((root / config_path).read_text(encoding="utf-8"))
    if stage["parent_level3b_config"] != LEVEL3B_CONFIG:
        raise ValueError("Level 4 must inherit the frozen Level 3B ensemble config")
    if _sha256(root / LEVEL3B_CONFIG) != stage["parent_level3b_config_sha256"]:
        raise ValueError("frozen Level 3B config changed after Level 4 protocol freeze")
    if _sha256(root / LEVEL3B_RESULT) != stage["parent_level3b_result_sha256"]:
        raise ValueError("frozen Level 3B receipt changed after Level 4 protocol freeze")
    level3b, parent, audit, _, threshold = _load_inputs(root, LEVEL3B_CONFIG)
    if level3b["dan_source_ids"] != stage["dan_source_ids"]:
        raise ValueError("Level 4 changed the frozen anatomy-selected DAN ensemble")
    expected = {
        "blocks": parent["training"]["blocks"],
        "presentations": len(parent["training"]["sequence"]),
        "trial_spacing_us": parent["training"]["trial_spacing_us"],
        "dt_us": parent["overlay"]["lif"]["dt_us"],
        "eta": parent["training"]["ltd"]["eta"],
        "eligibility_tau_us": parent["training"]["ltd"]["tau_us"],
        "minimum_fraction": parent["training"]["ltd"]["minimum_fraction"],
    }
    for key, value in expected.items():
        if stage["protocol"][key] != value:
            raise ValueError(f"Level 4 changed inherited setting {key}")
    if (type(stage["protocol"].get("duration_us")) is not int
            or stage["protocol"]["duration_us"] <= 0
            or stage["protocol"]["duration_us"] % expected["dt_us"]):
        raise ValueError("Level 4 note duration must be a positive multiple of the frozen dt")
    if stage["protocol"]["action_threshold_mv"] != threshold:
        raise ValueError("Level 4 changed the fixed Level 3B action threshold")
    if stage["protocol"]["input_rule"] != "x(t) = 1 - t / duration; encode x(t) only at each dt tick":
        raise ValueError("moving-note input rule differs from the frozen current-position-only rule")
    if stage["protocol"]["position_grid"] != parent["evaluation"]["position_grid"]:
        raise ValueError("Level 4 changed the inherited position evaluation grid")
    if stage["dan_source_ids"] != [87177, 107285, 55210]:
        raise ValueError("Level 4 changed the anatomy-selected DAN set")
    return stage, parent, audit, threshold


def _trajectory_position(t_us: int, duration_us: int) -> float:
    if not 0 <= t_us <= duration_us:
        raise ValueError("trajectory time is outside the moving-note presentation")
    return 1.0 - t_us / duration_us


def _moving_trial(parent: dict, weights: list[float], trajectory: dict) -> dict:
    cells = parent["circuit"]["selected_kcs"]
    n_kc = len(cells)
    lif = parent["overlay"]["lif"]
    duration = trajectory["duration_us"]
    dt = lif["dt_us"]
    if duration % dt:
        raise ValueError("moving-note duration must align with the inherited LIF grid")
    graph = SparseGraph(n_kc + 1, [
        Synapse(i, n_kc, weights[i], parent["overlay"]["synaptic_delay_us"])
        for i in range(n_kc)
    ])
    x0 = _trajectory_position(0, duration)
    initial_drive = list(population_drive(
        x0, cells, sigma=parent["encoder"]["sigma"],
        peak_drive_mv=parent["encoder"]["peak_drive_mv"])) + [0.0]
    sim = SpikingSimulator([_lif(parent)] * (n_kc + 1), graph, initial_drive,
                           dt_us=dt, record_neurons=[n_kc], record_spikes=True)
    for tick in range(dt, duration + dt, dt):
        sim.run_until(tick)
        if tick < duration:
            x = _trajectory_position(tick, duration)
            sim.set_external_drive_mv(list(population_drive(
                x, cells, sigma=parent["encoder"]["sigma"],
                peak_drive_mv=parent["encoder"]["peak_drive_mv"])) + [0.0])
    snapshot = sim.snapshot()
    voltage_by_time = {row.time_us: row.voltage_before_reset_mv
                       for row in snapshot.voltage_trace
                       if row.neuron_index == n_kc}
    grid = parent["evaluation"]["position_grid"]
    half_bin = trajectory["bin_width"] / 2.0
    position_map = []
    for position in grid:
        # The recorded voltage at a tick reflects the drive held over the
        # preceding integration interval, so associate it with that current x.
        samples = [voltage for time, voltage in voltage_by_time.items()
                   if abs(_trajectory_position(max(0, time - dt), duration) - position)
                   <= half_bin + 1e-12]
        if not samples:
            raise ValueError(f"moving note did not sample evaluation position {position}")
        position_map.append({
            "position": position,
            "mbon_activity_max_voltage_mv": max(samples),
            "mbon_activity_samples": len(samples),
        })
    spikes = [{"edge_index": row.neuron_index, "time_us": row.time_us}
              for row in snapshot.spikes if row.neuron_index < n_kc]
    return {
        "trajectory_position_start": 1.0,
        "trajectory_position_end": 0.0,
        "trajectory_duration_us": duration,
        "kc_spikes": spikes,
        "kc_spike_counts": {str(cell["source_id"]): sum(
            spike["edge_index"] == index for spike in spikes)
            for index, cell in enumerate(cells)},
        "position_map": position_map,
        "position_map_sha256": hashlib.sha256(json.dumps(
            position_map, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
    }


def _dan_latency(parent: dict, level3b: dict) -> int:
    onset = parent["overlay"]["observation_window_us"] + parent["training"]["teacher_lag_us"]
    observed = []
    for dan_id in level3b["dan_source_ids"]:
        times = _dan_spike_times(parent, level3b, stimulate=True)
        observed.append(times[0] - onset if times else None)
    if any(value is None for value in observed) or len(set(observed)) != 1:
        raise ValueError("selected DANs do not share the frozen pretraining spike latency")
    return int(observed[0])


def _trigger_position(arm: str, position_class: str, stage: dict) -> float | None:
    if arm == "wrong_region_teacher" and position_class == "wrong_region_distractor":
        return stage["protocol"]["wrong_region_trigger_position"]
    if arm in ("target_teacher", "matched_dan_on_plasticity_off_control") and position_class == "target_region":
        return stage["protocol"]["target_region_trigger_position"]
    return None


def _train_arm(parent: dict, stage: dict, audit: dict, threshold: float,
               dan_latency_us: int, *, arm: str) -> dict:
    cells = parent["circuit"]["selected_kcs"]
    ids = [int(cell["source_id"]) for cell in cells]
    initial = [cell["plastic_contact_rows"] / parent["circuit"]["plastic_contact_count"]
               for cell in cells]
    weights = list(initial)
    coverage = _dan_coverage(audit)
    slot_by_id = {kc_id: i for i, kc_id in enumerate(ids)}
    reachable = set().union(*coverage.values())
    connected_slots = tuple(sorted(slot_by_id[kc] for kc in reachable))
    duration = stage["protocol"]["duration_us"]
    spacing = stage["protocol"]["trial_spacing_us"]
    eta = parent["training"]["ltd"]["eta"]
    tau = parent["training"]["ltd"]["tau_us"]
    floor = parent["training"]["ltd"]["minimum_fraction"]
    pulse_duration = stage["dan_stimulation"]["duration_us"]
    pulse_amplitude = stage["dan_stimulation"]["amplitude_mv_equivalent"]
    trials, block_maps = [], []
    for scheduled in parent["training"]["sequence"]:
        offset = (scheduled["presentation"] - 1) * spacing
        moving = _moving_trial(parent, weights, stage["protocol"])
        trigger_position = _trigger_position(arm, scheduled["position_class"], stage)
        pulse_onset = None
        gate_time = None
        dan_spikes = {dan: [] for dan in stage["dan_source_ids"]}
        active_dans: list[int] = []
        if trigger_position is not None:
            crossing = round((1.0 - trigger_position) * duration)
            pulse_onset = crossing - dan_latency_us
            gate_time = pulse_onset + dan_latency_us
            if pulse_onset < 0 or pulse_onset % parent["overlay"]["lif"]["dt_us"]:
                raise ValueError("DAN pulse cannot be aligned to the moving-note crossing")
            for dan_id in stage["dan_source_ids"]:
                # The Level 3B isolated-cell pulse is reproduced with its
                # inherited amplitude, duration, LIF model and fresh rest state.
                dan_sim = SpikingSimulator([_lif(parent)], SparseGraph(1, []), [0.0],
                    dt_us=parent["overlay"]["lif"]["dt_us"], record_neurons=[0], record_spikes=True)
                dan_sim.run_until(pulse_onset)
                dan_sim.set_external_drive_mv([pulse_amplitude])
                dan_sim.run_until(pulse_onset + pulse_duration)
                times = [spike.time_us for spike in dan_sim.snapshot().spikes]
                dan_spikes[dan_id] = times
                if times:
                    active_dans.append(dan_id)
            gate_time = min((times[0] for times in dan_spikes.values() if times), default=None)
        plasticity_enabled = arm != "matched_dan_on_plasticity_off_control"
        active_kcs = set().union(*(coverage[dan] for dan in active_dans)) if active_dans else set()
        active_slots = tuple(sorted(slot_by_id[kc] for kc in active_kcs)) if plasticity_enabled else ()
        rule = LocalLTD(list(weights), original_weights=initial,
                        plastic_slots=active_slots, tau_us=tau, eta=eta,
                        minimum_fraction=floor)
        eligible_spikes = [spike for spike in moving["kc_spikes"]
                           if gate_time is not None and spike["time_us"] <= gate_time]
        for spike in eligible_spikes:
            rule.observe_kc_spike(spike["edge_index"], offset + spike["time_us"])
        absolute_gate_time = offset + gate_time if gate_time is not None else offset + duration
        changes = rule.teacher_pulse(absolute_gate_time, teacher=bool(active_slots))
        weights = list(rule.weights)
        positive_eligibility = [ids[i] for i in active_slots
                                if rule.eligibility_at(i, absolute_gate_time) > 0]
        row = {
            "presentation": scheduled["presentation"], "block": scheduled["block"],
            "scheduled_class_for_teacher_timing_only": scheduled["position_class"],
            "input_positions": "one fixed 1.0-to-0.0 moving note; current x(t) only",
            "dan_trigger_position": trigger_position,
            "dan_pulse_onset_us_relative_to_note": pulse_onset,
            "dan_spike_times_us_relative_to_note": {
                str(dan): [time - pulse_onset for time in times]
                if pulse_onset is not None else [] for dan, times in dan_spikes.items()},
            "active_dan_source_ids": active_dans,
            "dan_gate_kc_source_ids": [ids[i] for i in active_slots],
            "positive_eligibility_kc_source_ids_at_gate": positive_eligibility,
            "eligible_kc_spikes_before_gate": len(eligible_spikes),
            "weight_changes": [dict(change, source_id=ids[change["edge_index"]])
                                for change in changes],
            "teacher_presentation_class_is_not_encoder_input": True,
            **moving,
        }
        trials.append(row)
        if scheduled["presentation"] % 10 == 0:
            panel = _evaluate(parent, weights, threshold)
            block = scheduled["block"]
            block_maps.append({
                "block": block, "position_map": panel,
                "weights_after_block": list(weights),
                "weights_at_floor": [ids[i] for i, (w, start) in enumerate(zip(weights, initial))
                                     if w <= start * floor],
            })
    final_static_map = _evaluate(parent, weights, threshold)
    final_moving_map = _moving_trial(parent, weights, stage["protocol"])["position_map"]
    for panel in (final_static_map, final_moving_map):
        for point in panel:
            point["action"] = point["mbon_activity_max_voltage_mv"] <= threshold
            point["frozen_threshold_mv"] = threshold
    return {
        "arm": arm,
        "external_teaching_presentations": sum(bool(row["active_dan_source_ids"]) for row in trials),
        "dan_gate_event_count": sum(bool(row["active_dan_source_ids"]) for row in trials),
        "trials": trials, "block_maps": block_maps,
        "initial_weights": initial, "final_weights": list(weights),
        "final_static_position_map": final_static_map,
        "final_position_map": final_moving_map,
    }


def _annotate(panel: list[dict], threshold: float) -> list[dict]:
    return [dict(row, action=row["mbon_activity_max_voltage_mv"] <= threshold,
                 frozen_threshold_mv=threshold) for row in panel]


def _core_actions(panel: list[dict], core: list[float]) -> list[bool]:
    by_position = {round(row["position"], 8): row for row in panel}
    return [bool(by_position[round(position, 8)]["action"]) for position in core]


def _locality(panel: list[dict], halo: list[float]) -> dict:
    lo, hi = halo
    actions = [row["position"] for row in panel if row["action"]]
    outside = [row for row in panel if row["position"] < lo or row["position"] > hi]
    outside_actions = [row["position"] for row in outside if row["action"]]
    no_action_fraction = (sum(not row["action"] for row in outside) / len(outside)
                          if outside else 1.0)
    return {"allowed_halo": halo, "action_positions": actions,
            "outside_halo_action_positions": outside_actions,
            "outside_halo_no_action_fraction": no_action_fraction,
            "locality_pass": not outside_actions or no_action_fraction >= 0.9}


def run_level4(root: Path, config_path: str = CONFIG_DEFAULT) -> dict:
    root = Path(root)
    stage, parent, audit, threshold = _inputs(root, config_path)
    level3b_config, *_ = _load_inputs(root, LEVEL3B_CONFIG)
    latency = _dan_latency(parent, level3b_config)
    if latency != stage["protocol"]["dan_spike_latency_us"]:
        raise ValueError("measured frozen DAN pulse latency differs from preregistered Level 4 latency")
    baseline_weights = [cell["plastic_contact_rows"] / parent["circuit"]["plastic_contact_count"]
                        for cell in parent["circuit"]["selected_kcs"]]
    baseline_static = _annotate(_evaluate(parent, baseline_weights, threshold), threshold)
    baseline_moving = _annotate(
        _moving_trial(parent, baseline_weights, stage["protocol"])["position_map"], threshold)

    # Moving-note task-free capacity ceiling: clamp the union of slots that
    # actually acquire positive pre-gate eligibility on the first frozen target
    # and wrong teaching trajectories, then evaluate the moving-note bins.
    capa = {}
    coverage = _dan_coverage(audit)
    for label, position in (("target", stage["protocol"]["target_region_trigger_position"]),
                            ("wrong", stage["protocol"]["wrong_region_trigger_position"])):
        class_name = "target_region" if label == "target" else "wrong_region_distractor"
        scheduled = next(row for row in parent["training"]["sequence"]
                         if row["position_class"] == class_name)
        moving = _moving_trial(parent, baseline_weights, stage["protocol"])
        crossing = round((1.0 - position) * stage["protocol"]["duration_us"])
        pulse_onset = crossing - latency
        gate_time = pulse_onset + latency
        rule = LocalLTD(list(baseline_weights), original_weights=baseline_weights,
                        plastic_slots=tuple(range(len(baseline_weights))),
                        **parent["training"]["ltd"])
        for spike in moving["kc_spikes"]:
            if spike["time_us"] <= gate_time:
                rule.observe_kc_spike(spike["edge_index"], spike["time_us"])
        eligible = {parent["circuit"]["selected_kcs"][i]["source_id"]
                    for i in range(len(baseline_weights))
                    if rule.eligibility_at(i, gate_time) > 0}
        reachable = set().union(*coverage.values())
        clamped_ids = eligible & reachable
        weights = list(baseline_weights)
        for i, cell in enumerate(parent["circuit"]["selected_kcs"]):
            if cell["source_id"] in clamped_ids:
                weights[i] = baseline_weights[i] * parent["training"]["ltd"]["minimum_fraction"]
        ceiling = _annotate(_moving_trial(parent, weights, stage["protocol"])["position_map"], threshold)
        core = parent["target_region"]["primary"] if label == "target" else parent["target_region"]["wrong_control"]
        core_positions = [x for x in parent["evaluation"]["position_grid"] if core[0] <= x <= core[1]]
        capa[label] = {"trigger_position": position,
                       "scheduled_class": scheduled["position_class"],
                       "positive_eligibility_kc_source_ids": sorted(eligible),
                       "clamped_reachable_kc_source_ids": sorted(clamped_ids),
                       "moving_position_map": ceiling,
                       "core_positions": core_positions,
                       "core_actions": _core_actions(ceiling, core_positions),
                       "core_action_count": sum(_core_actions(ceiling, core_positions))}
    capacity_pass = all(row["core_action_count"] == 3 for row in capa.values())
    result = {
        "experiment_id": stage["experiment_id"], "stage": "level4_moving_note",
        "config": config_path, "config_sha256": _sha256(root / config_path),
        "parent_level3b_config_sha256": stage["parent_level3b_config_sha256"],
        "parent_level3b_result_sha256": stage["parent_level3b_result_sha256"],
        "dan_source_ids": stage["dan_source_ids"],
        "dan_spike_latency_us": latency,
        "frozen_action_threshold_mv": threshold,
        "encoder_sha256": _encoder_sha256(parent),
        "readout": "fixed MBON05 maximum-voltage threshold, sampled in position bins along the moving note; no trained decoder",
        "current_position_only_input_rule": stage["protocol"]["input_rule"],
        "capacity_ceiling": capa,
        "capacity_status": "PASS" if capacity_pass else "FAIL",
        "baseline_static_position_map": baseline_static,
        "baseline_moving_position_map": baseline_moving,
    }
    if not capacity_pass:
        result.update({"status": "INCONCLUSIVE",
                       "training_runs": 0,
                       "decision": "Moving-note capacity ceiling did not reach strict 3/3 in both teaching cores; training was not run."})
        return result

    target = _train_arm(parent, stage, audit, threshold, latency, arm="target_teacher")
    wrong = _train_arm(parent, stage, audit, threshold, latency, arm="wrong_region_teacher")
    off = _train_arm(parent, stage, audit, threshold, latency,
                     arm="matched_dan_on_plasticity_off_control")
    target_core = [x for x in parent["evaluation"]["position_grid"]
                   if parent["target_region"]["primary"][0] <= x <= parent["target_region"]["primary"][1]]
    wrong_core = [x for x in parent["evaluation"]["position_grid"]
                  if parent["target_region"]["wrong_control"][0] <= x <= parent["target_region"]["wrong_control"][1]]
    target_locality = _locality(target["final_position_map"], parent["locality_evaluation"]["target_teacher"]["allowed_halo"])
    wrong_locality = _locality(wrong["final_position_map"], parent["locality_evaluation"]["wrong_region_teacher"]["allowed_halo"])
    criteria = {
        "all_120_blocks_and_1200_presentations_per_arm": all(len(arm["trials"]) == 1200 and len(arm["block_maps"]) == 120 for arm in (target, wrong, off)),
        "moving_note_target_core_3_of_3": all(_core_actions(target["final_position_map"], target_core)),
        "moving_note_wrong_core_3_of_3": all(_core_actions(wrong["final_position_map"], wrong_core)),
        "target_and_wrong_actions_local_to_own_halo": target_locality["locality_pass"] and wrong_locality["locality_pass"],
        "plasticity_off_weights_and_moving_map_unchanged": off["initial_weights"] == off["final_weights"] and off["final_position_map"] == baseline_moving,
        "plasticity_off_remains_no_action": not any(row["action"] for row in off["final_position_map"]),
        "target_and_wrong_moving_maps_persist_frozen": all(_annotate(_moving_trial(parent, arm["final_weights"], stage["protocol"])["position_map"], threshold) == arm["final_position_map"] for arm in (target, wrong)),
        "exactly_600_teacher_events_per_teaching_arm_and_control": all(arm["dan_gate_event_count"] == 600 for arm in (target, wrong, off)),
        "all_teacher_events_activate_three_dans": all(sum(len(row["active_dan_source_ids"]) == 3 for row in arm["trials"]) == 600 for arm in (target, wrong, off)),
        "all_weight_updates_have_local_eligibility_and_connected_dan": all(change["eligibility"] > 0 and change["source_id"] in trial["dan_gate_kc_source_ids"] for arm in (target, wrong) for trial in arm["trials"] for change in trial["weight_changes"]),
        "all_updates_within_union_anatomical_mask": all(change["source_id"] in set().union(*coverage.values()) for arm in (target, wrong) for trial in arm["trials"] for change in trial["weight_changes"]),
        "immutable_original_weight_floor_respected": all(weight + 1e-15 >= initial * parent["training"]["ltd"]["minimum_fraction"] for arm in (target, wrong, off) for weight, initial in zip(arm["final_weights"], arm["initial_weights"])),
        "fixed_encoder_threshold_and_readout": threshold == parent["continuation"]["frozen_action_threshold_mv"] and _encoder_sha256(parent) == result["encoder_sha256"],
    }
    result.update({
        "target_teacher": target, "wrong_region_teacher": wrong,
        "matched_dan_on_plasticity_off_control": off,
        "arm_locality": {"target_teacher": target_locality, "wrong_region_teacher": wrong_locality},
        "criteria": criteria,
        "training_blocks_completed": {arm["arm"]: len(arm["block_maps"]) for arm in (target, wrong, off)},
        "training_presentations_completed": {arm["arm"]: len(arm["trials"]) for arm in (target, wrong, off)},
        "weights_at_ltd_floor_final": {arm["arm"]: [parent["circuit"]["selected_kcs"][i]["source_id"] for i, (weight, initial) in enumerate(zip(arm["final_weights"], arm["initial_weights"])) if weight <= initial * parent["training"]["ltd"]["minimum_fraction"]] for arm in (target, wrong, off)},
        "status": "PASS" if all(criteria.values()) else "FAIL",
        "decision": "Level 4 met its predeclared moving-note contract." if all(criteria.values()) else "Level 4 completed under the frozen moving-note contract but failed one or more predeclared criteria; no tuning or rerun was performed.",
    })
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--config", default=CONFIG_DEFAULT)
    parser.add_argument("--output", type=Path, default=Path(RESULT_DEFAULT))
    args = parser.parse_args()
    output = run_level4(args.root, args.config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": output["status"],
                      "capacity_status": output["capacity_status"],
                      "criteria": output.get("criteria", {}),
                      "decision": output["decision"]}, indent=2))
