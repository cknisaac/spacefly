"""Outcome-blind frozen controllability gate for Level 2."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from project_b.malecns_minimal_internal_learning.probe import _read_config
from project_b.neurons import LIFParameters
from project_b.simulation import SpikingSimulator
from project_b.synapses import SparseGraph, Synapse
from project_b.malecns_continuous_position_learning.encoder import (
    activation, population_drive,
)


def load_config(root: Path, config_path: str) -> dict:
    root = Path(root)
    config = _read_config(root, config_path)
    cells = config["circuit"]["selected_kcs"]
    if len(cells) < 20 or config["circuit"]["mbon_source_id"] != 10495:
        raise ValueError("Level 2 requires at least 20 audited KCs to MBON05")
    preferred = [cell["preferred_position"] for cell in cells]
    if preferred != sorted(preferred) or len(set(preferred)) != len(preferred):
        raise ValueError("preferred positions must be unique and source-order mapped")
    return config


def config_sha256(root: Path, config_path: str) -> str:
    return hashlib.sha256((Path(root) / config_path).read_bytes()).hexdigest()


def _lif(config: dict) -> LIFParameters:
    row = config["overlay"]["lif"]
    return LIFParameters(
        v_rest_mv=row["v_rest_mv"], v_reset_mv=row["v_reset_mv"],
        v_threshold_mv=row["v_threshold_mv"], tau_m_us=row["tau_m_us"],
        tau_syn_us=row["tau_syn_us"], refractory_us=row["refractory_us"],
    )


def _trial(config: dict, position: float, weights: list[float], *,
           checkpoint_replay: bool = False) -> dict:
    cells = config["circuit"]["selected_kcs"]
    mbon = len(cells)
    lif = config["overlay"]["lif"]
    graph = SparseGraph(mbon + 1, [
        Synapse(i, mbon, weights[i], config["overlay"]["synaptic_delay_us"])
        for i in range(mbon)
    ])
    drive = list(population_drive(
        position, cells, sigma=config["encoder"]["sigma"],
        peak_drive_mv=config["encoder"]["peak_drive_mv"])) + [0.0]
    sim = SpikingSimulator([_lif(config)] * (mbon + 1), graph, drive,
                           dt_us=lif["dt_us"], record_neurons=[mbon],
                           record_spikes=True)
    window = config["overlay"]["observation_window_us"]
    if checkpoint_replay:
        sim.run_until(window // 2)
        checkpoint = sim.state()
        sim.run_until(window)
        final_state = sim.state()
        replay = SpikingSimulator([_lif(config)] * (mbon + 1), graph, drive,
                                  dt_us=lif["dt_us"], record_neurons=[mbon],
                                  record_spikes=True)
        replay.restore(checkpoint)
        replay.run_until(window)
        replay_identical = final_state == replay.state()
    else:
        sim.run_until(window)
        replay_identical = None
    snap = sim.snapshot()
    voltages = [row.voltage_before_reset_mv for row in snap.voltage_trace
                if row.neuron_index == mbon]
    spikes = [row for row in snap.spikes if row.neuron_index < mbon]
    return {
        "position": position,
        "mbon_activity_max_voltage_mv": max(voltages),
        "mbon_spike_count": sum(row.neuron_index == mbon for row in snap.spikes),
        "kc_spike_counts": {str(cells[i]["source_id"]): sum(
            row.neuron_index == i for row in spikes) for i in range(mbon)},
        "kc_spikes": [{"edge_index": row.neuron_index, "time_us": row.time_us}
                      for row in spikes],
        "active_kc_source_ids": sorted({cells[row.neuron_index]["source_id"]
                                         for row in spikes}),
        "checkpoint_replay_identical": replay_identical,
        "simulator_state_sha256": hashlib.sha256(json.dumps(
            sim.state(), sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
    }


def _initial_weights(config: dict) -> list[float]:
    cells = config["circuit"]["selected_kcs"]
    total = sum(cell["plastic_contact_rows"] for cell in cells)
    return [cell["plastic_contact_rows"] / total for cell in cells]


def run_probe(root: Path, config_path: str) -> dict:
    root = Path(root)
    config = load_config(root, config_path)
    cells = config["circuit"]["selected_kcs"]
    weights = _initial_weights(config)
    grid = config["evaluation"]["position_grid"]
    sigma = config["encoder"]["sigma"]
    centers = config["controllability_probe"]["centers"]
    region_half_width = config["controllability_probe"]["weakened_preferred_position_half_width"]
    local_half_width = config["controllability_probe"]["local_test_half_width"]
    distant_minimum = config["controllability_probe"]["distant_minimum_separation"]
    reduction = config["controllability_probe"]["weight_multiplier"]
    baseline = [_trial(config, x, weights, checkpoint_replay=True) for x in grid]
    probe_rows = []
    local_maxima = []
    distant_minima = []
    for center in centers:
        selected = [i for i, cell in enumerate(cells)
                    if abs(cell["preferred_position"] - center) <= region_half_width]
        modified = list(weights)
        for i in selected:
            modified[i] *= reduction
        panel = [_trial(config, x, modified) for x in grid]
        local_indices = [i for i, x in enumerate(grid)
                         if abs(x - center) <= local_half_width]
        distant_indices = [i for i, x in enumerate(grid)
                           if abs(x - center) >= distant_minimum]
        local_maxima.append(max(panel[i]["mbon_activity_max_voltage_mv"]
                                for i in local_indices))
        distant_minima.append(min(baseline[i]["mbon_activity_max_voltage_mv"]
                                  for i in distant_indices))
        probe_rows.append({
            "center": center,
            "weakened_kc_source_ids": [cells[i]["source_id"] for i in selected],
            "weight_multiplier": reduction,
            "map": panel,
            "local_positions": [grid[i] for i in local_indices],
            "distant_positions": [grid[i] for i in distant_indices],
        })
    threshold = (max(local_maxima) + min(distant_minima)) / 2.0
    for row in baseline:
        row["action"] = row["mbon_activity_max_voltage_mv"] <= threshold
        row["frozen_threshold_mv"] = threshold
    for center_row in probe_rows:
        for row in center_row["map"]:
            row["action"] = row["mbon_activity_max_voltage_mv"] <= threshold
            row["frozen_threshold_mv"] = threshold
    local_crossings = []
    distant_no_action = []
    local_reduction = []
    for row in probe_rows:
        local = [r for r in row["map"] if abs(r["position"] - row["center"]) <= local_half_width]
        distant = [r for r in baseline if abs(r["position"] - row["center"]) >= distant_minimum]
        local_crossings.append(bool(local) and all(r["action"] for r in local))
        distant_no_action.append(bool(distant) and all(not r["action"] for r in distant))
        base_by_x = {r["position"]: r["mbon_activity_max_voltage_mv"] for r in baseline}
        local_reduction.append(all(r["mbon_activity_max_voltage_mv"] < base_by_x[r["position"]]
                                   for r in local))
    criteria = {
        "fixed_encoder_has_unique_overlapping_tuning": all(
            activation(x, c["preferred_position"], sigma) > 0
            for x in grid for c in cells),
        "naive_action_absent_across_full_grid": all(not r["action"] for r in baseline),
        "target_weight_reduction_crosses_action_threshold_at_all_probe_regions": all(local_crossings),
        "distant_positions_remain_no_action": all(distant_no_action),
        "weakened_local_responses_are_lower_than_matched_baseline": all(local_reduction),
        "strict_common_threshold_gap": max(local_maxima) < min(distant_minima),
        "checkpoint_replay_identical": all(r["checkpoint_replay_identical"] for r in baseline),
        "grid_replay_is_deterministic": True,
    }
    # The second pass uses the same deterministic initial weights and inputs;
    # compare the response/state digests separately from replay-only metadata.
    criteria["grid_replay_is_deterministic"] = all(
        _trial(config, x, weights)["simulator_state_sha256"] == row["simulator_state_sha256"]
        for x, row in zip(grid, baseline))
    return {
        "experiment_id": config["experiment_id"],
        "stage": "level2_pretraining_controllability",
        "status": "PASS" if all(criteria.values()) else "FAIL",
        "config": config_path,
        "config_sha256": config_sha256(root, config_path),
        "frozen_action_threshold_mv": threshold,
        "threshold_selection": config["controllability_probe"]["threshold_selection"],
        "criteria": criteria,
        "baseline_position_map": baseline,
        "controllability_regions": probe_rows,
        "encoder_audit": [{
            "position": x,
            "activation_by_kc": {str(c["source_id"]): activation(
                x, c["preferred_position"], sigma) for c in cells},
        } for x in grid],
        "local_perturbed_maxima_mv": local_maxima,
        "distant_baseline_minima_mv": distant_minima,
        "plasticity": "OFF",
        "decision": ("Freeze this threshold and proceed to the authorized Level 2 training run."
                     if all(criteria.values()) else
                     "FAIL: stop before training; do not change encoder, weights, or threshold."),
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run_probe(args.root, args.config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"],
                      "threshold_mv": result["frozen_action_threshold_mv"],
                      "criteria": result["criteria"]}, indent=2))
