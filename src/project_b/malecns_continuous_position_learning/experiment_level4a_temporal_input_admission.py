"""Task-free Level 4A temporal-input admission; no teaching or learning."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from project_b.malecns_continuous_position_learning.encoder import population_drive
from project_b.malecns_continuous_position_learning.experiment_level3b_dan_ensemble import (
    CONFIG_DEFAULT as LEVEL3B_CONFIG,
    _load_inputs,
)
from project_b.malecns_continuous_position_learning.experiment_level4_moving_note import (
    LEVEL3B_RESULT,
    _sha256,
)
from project_b.malecns_continuous_position_learning.probe import _lif
from project_b.simulation import SpikingSimulator
from project_b.synapses import SparseGraph, Synapse


CONFIG_DEFAULT = "configs/malecns_level4a_temporal_input_admission.json"
RESULT_DEFAULT = "runs/malecns_level4a_temporal_input_admission/result.json"
LEVEL4_CONFIG = "configs/malecns_level4_moving_note.json"
LEVEL4_RESULT = "runs/malecns_level4_moving_note/result.json"


def _inputs(root: Path, config_path: str) -> tuple[dict, dict, dict, dict, float]:
    root = Path(root)
    stage_path = root / config_path
    stage = json.loads(stage_path.read_text(encoding="utf-8"))
    if _sha256(root / LEVEL4_CONFIG) != stage["parent_level4_config_sha256"]:
        raise ValueError("Level 4 config changed after Level 4A freeze")
    if _sha256(root / LEVEL4_RESULT) != stage["parent_level4_result_sha256"]:
        raise ValueError("Level 4 result changed after Level 4A freeze")
    if _sha256(root / LEVEL3B_CONFIG) != stage["parent_level3b_config_sha256"]:
        raise ValueError("Level 3B config changed after Level 4A freeze")
    l3, parent, audit, receipt, threshold = _load_inputs(root, LEVEL3B_CONFIG)
    protocol = stage["protocol"]
    if stage["dan_source_ids"] != l3["dan_source_ids"]:
        raise ValueError("Level 4A changed the frozen DAN ensemble identity")
    if protocol["dt_us"] != parent["overlay"]["lif"]["dt_us"]:
        raise ValueError("Level 4A changed the fixed LIF integration step")
    if protocol["encoder_sigma"] != parent["encoder"]["sigma"]:
        raise ValueError("Level 4A changed the fixed Gaussian encoder")
    if protocol["peak_drive_mv_equivalent"] != parent["encoder"]["peak_drive_mv"]:
        raise ValueError("Level 4A changed the fixed encoder amplitude")
    if protocol["action_threshold_mv"] != threshold:
        raise ValueError("Level 4A changed the fixed action threshold")
    if protocol["position_grid"] != parent["evaluation"]["position_grid"]:
        raise ValueError("Level 4A changed the inherited evaluation grid")
    expected_duration_us = [int(ms) * 1000 for ms in protocol["candidate_durations_ms"]]
    if protocol["duration_us"] != expected_duration_us:
        raise ValueError("Level 4A duration list differs from its predeclared candidates")
    if protocol["runs_per_duration"] != 2 or protocol["learning"] != "OFF" or protocol["dan_teaching"] != "OFF; no DAN stimulation":
        raise ValueError("Level 4A must remain a task-free, deterministic admission test")
    return stage, l3, parent, audit, threshold


def _position_at(t_us: int, duration_us: int) -> float:
    if not 0 <= t_us <= duration_us:
        raise ValueError("trajectory time is outside the frozen movement")
    return 1.0 - t_us / duration_us


def _run_one(parent: dict, threshold: float, duration_us: int, bin_width: float) -> dict:
    cells = parent["circuit"]["selected_kcs"]
    n_kc = len(cells)
    lif = parent["overlay"]["lif"]
    dt = lif["dt_us"]
    if duration_us <= 0 or duration_us % dt:
        raise ValueError("candidate duration must be a positive multiple of the frozen dt")
    initial_weights = [cell["plastic_contact_rows"] /
                       parent["circuit"]["plastic_contact_count"] for cell in cells]
    graph = SparseGraph(n_kc + 1, [
        Synapse(i, n_kc, initial_weights[i], parent["overlay"]["synaptic_delay_us"])
        for i in range(n_kc)
    ])
    drive = list(population_drive(
        1.0, cells, sigma=parent["encoder"]["sigma"],
        peak_drive_mv=parent["encoder"]["peak_drive_mv"])) + [0.0]
    sim = SpikingSimulator([_lif(parent)] * (n_kc + 1), graph, drive,
                           dt_us=dt, record_neurons=[n_kc], record_spikes=True)
    for tick in range(dt, duration_us + dt, dt):
        sim.run_until(tick)
        if tick < duration_us:
            position = _position_at(tick, duration_us)
            sim.set_external_drive_mv(list(population_drive(
                position, cells, sigma=parent["encoder"]["sigma"],
                peak_drive_mv=parent["encoder"]["peak_drive_mv"])) + [0.0])
    snapshot = sim.snapshot()
    voltage_by_time = {row.time_us: row.voltage_before_reset_mv
                       for row in snapshot.voltage_trace if row.neuron_index == n_kc}

    # Each voltage sample reflects the drive held during the preceding dt
    # interval. Store that interval's current position with the measurement.
    timecourse = []
    for time_us, voltage in sorted(voltage_by_time.items()):
        if time_us <= 0:
            continue
        position = _position_at(max(0, time_us - dt), duration_us)
        timecourse.append({"time_us": time_us, "current_position": position,
                           "mbon05_voltage_mv": voltage,
                           "action": voltage <= threshold})

    spike_events = []
    per_kc = {str(cell["source_id"]): 0 for cell in cells}
    for spike in snapshot.spikes:
        if spike.neuron_index >= n_kc:
            continue
        source_id = int(cells[spike.neuron_index]["source_id"])
        per_kc[str(source_id)] += 1
        spike_events.append({
            "time_us": spike.time_us,
            "current_position": _position_at(max(0, spike.time_us - dt), duration_us),
            "kc_source_id": source_id,
        })

    grid = parent["evaluation"]["position_grid"]
    half_bin = bin_width / 2.0
    position_map = []
    for position in grid:
        samples = [row["mbon05_voltage_mv"] for row in timecourse
                   if abs(row["current_position"] - position) <= half_bin + 1e-12]
        if not samples:
            raise ValueError(f"duration {duration_us} did not sample position bin {position}")
        maximum = max(samples)
        position_map.append({
            "position": position,
            "mbon05_activity_max_voltage_mv": maximum,
            "sample_count": len(samples),
            "action": maximum <= threshold,
        })
    action_positions = [row["position"] for row in position_map if row["action"]]
    return {
        "duration_us": duration_us,
        "total_kc_spikes": len(spike_events),
        "spiking_kc_source_ids": sorted(int(source_id) for source_id, count in per_kc.items() if count),
        "kc_spike_counts_by_source_id": {source_id: count for source_id, count in per_kc.items() if count},
        "kc_spike_events": spike_events,
        "mbon05_peak_voltage_mv": max((row["mbon05_voltage_mv"] for row in timecourse), default=0.0),
        "mbon05_timecourse": timecourse,
        "position_map": position_map,
        "action_positions": action_positions,
        "naive_baseline_action_everywhere": len(action_positions) == len(grid),
        "weights_changed": False,
        "dan_teaching_performed": False,
    }


def _meaningful_mbon(position_map: list[dict], threshold: float) -> dict:
    above = [row["mbon05_activity_max_voltage_mv"] > threshold for row in position_map]
    longest = run = 0
    for value in above:
        run = run + 1 if value else 0
        longest = max(longest, run)
    return {
        "bins_above_fixed_action_threshold": [row["position"] for row in position_map
                                              if row["mbon05_activity_max_voltage_mv"] > threshold],
        "longest_contiguous_above_threshold_bins": longest,
        "criterion": "at least 3 adjacent position bins exceed the fixed threshold",
        "passes": longest >= 3 and any(row["mbon05_activity_max_voltage_mv"] > 0.0
                                       for row in position_map),
    }


def run_admission(root: Path, config_path: str = CONFIG_DEFAULT) -> dict:
    root = Path(root)
    stage, level3b, parent, audit, threshold = _inputs(root, config_path)
    protocol = stage["protocol"]
    conditions = []
    for duration_ms, duration_us in zip(protocol["candidate_durations_ms"], protocol["duration_us"]):
        first = _run_one(parent, threshold, duration_us, protocol["position_bin_width"])
        replay = _run_one(parent, threshold, duration_us, protocol["position_bin_width"])
        signature_keys = ("total_kc_spikes", "spiking_kc_source_ids", "kc_spike_counts_by_source_id",
                          "kc_spike_events", "mbon05_timecourse", "position_map", "action_positions")
        first_signature = {key: first[key] for key in signature_keys}
        replay_signature = {key: replay[key] for key in signature_keys}
        first_hash = hashlib.sha256(json.dumps(first_signature, sort_keys=True,
            separators=(",", ":")).encode()).hexdigest()
        replay_hash = hashlib.sha256(json.dumps(replay_signature, sort_keys=True,
            separators=(",", ":")).encode()).hexdigest()
        meaningful = _meaningful_mbon(first["position_map"], threshold)
        gates = {
            "nonzero_kc_spiking": first["total_kc_spikes"] > 0,
            "meaningful_mbon_response": meaningful["passes"],
            "naive_baseline_not_action_everywhere": not first["naive_baseline_action_everywhere"],
            "deterministic_replay": first_hash == replay_hash,
        }
        conditions.append({
            "duration_ms": duration_ms,
            "duration_us": duration_us,
            "first_run": first,
            "replay_sha256": replay_hash,
            "first_run_signature_sha256": first_hash,
            "meaningful_mbon_response": meaningful,
            "gates": gates,
            "admission_pass": all(gates.values()),
        })
    admitted = next((row["duration_ms"] for row in conditions if row["admission_pass"]), None)
    result = {
        "experiment_id": stage["experiment_id"],
        "stage": "level4a_task_free_temporal_input_admission",
        "config": config_path,
        "config_sha256": _sha256(root / config_path),
        "parent_level4_config_sha256": stage["parent_level4_config_sha256"],
        "parent_level4_result_sha256": stage["parent_level4_result_sha256"],
        "parent_level3b_config_sha256": stage["parent_level3b_config_sha256"],
        "dan_source_ids_retained_but_not_stimulated": stage["dan_source_ids"],
        "frozen_action_threshold_mv": threshold,
        "fixed_encoder": {"sigma": parent["encoder"]["sigma"],
                          "peak_drive_mv_equivalent": parent["encoder"]["peak_drive_mv"],
                          "input": "current position only"},
        "learning_runs": 0,
        "dan_teaching_events": 0,
        "durations_tested_ms": list(protocol["candidate_durations_ms"]),
        "conditions": conditions,
        "shortest_admitted_duration_ms": admitted,
        "status": "PASS" if admitted is not None else "FAIL",
        "decision": (f"The shortest admitted moving-note duration is {admitted} ms; freeze this as the Level 4 moving-note speed. No learning was run."
                     if admitted is not None else
                     "None of the predeclared durations passed all admission gates; temporal drive/integration remains the blocker. No learning was run."),
    }
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--config", default=CONFIG_DEFAULT)
    parser.add_argument("--output", type=Path, default=Path(RESULT_DEFAULT))
    args = parser.parse_args()
    result = run_admission(args.root, args.config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"],
                      "shortest_admitted_duration_ms": result["shortest_admitted_duration_ms"],
                      "conditions": [{"duration_ms": row["duration_ms"],
                          "total_kc_spikes": row["first_run"]["total_kc_spikes"],
                          "spiking_kc_source_ids": row["first_run"]["spiking_kc_source_ids"],
                          "mbon05_peak_voltage_mv": row["first_run"]["mbon05_peak_voltage_mv"],
                          "action_positions": row["first_run"]["action_positions"],
                          "naive_baseline_action_everywhere": row["first_run"]["naive_baseline_action_everywhere"],
                          "gates": row["gates"], "admission_pass": row["admission_pass"]}
                          for row in result["conditions"]]}, indent=2))
