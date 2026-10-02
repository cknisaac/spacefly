"""Level 4B moving-note output-admission repair; no teaching or learning."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from project_b.malecns_continuous_position_learning.experiment_level4a_temporal_input_admission import (
    _inputs as _level4a_inputs,
    _run_one,
)
from project_b.malecns_continuous_position_learning.experiment_level4_moving_note import _sha256


CONFIG_DEFAULT = "configs/malecns_level4b_moving_output_admission_repair.json"
RESULT_DEFAULT = "runs/malecns_level4b_moving_output_admission_repair/result.json"
FROZEN_SPEED_CONFIG = "configs/malecns_level4_moving_note_admitted_500ms.json"


def action_validity_trace(run: dict, threshold_mv: float) -> dict:
    """Gate the inherited threshold output until this note's first KC spike."""
    spike_times = [int(event["time_us"]) for event in run["kc_spike_events"]]
    first_spike_us = min(spike_times) if spike_times else None
    trace = []
    for row in run["mbon05_timecourse"]:
        enabled = first_spike_us is not None and row["time_us"] >= first_spike_us
        trace.append({
            "time_us": row["time_us"],
            "current_position": row["current_position"],
            "mbon05_voltage_mv": row["mbon05_voltage_mv"],
            "output_enabled": enabled,
            "raw_threshold_action": row["mbon05_voltage_mv"] <= threshold_mv,
            "action": (row["mbon05_voltage_mv"] <= threshold_mv) if enabled else None,
        })

    half_bin = 0.025
    position_map = []
    for row in run["position_map"]:
        position = row["position"]
        enabled_samples = [sample["mbon05_voltage_mv"] for sample in trace
                           if sample["output_enabled"] and
                           abs(sample["current_position"] - position) <= half_bin + 1e-12]
        if not enabled_samples:
            position_map.append({
                "position": position,
                "mbon05_activity_max_voltage_mv": None,
                "sample_count": 0,
                "output_enabled": False,
                "action": None,
                "state": "disabled_before_first_kc_spike",
            })
            continue
        maximum = max(enabled_samples)
        action = maximum <= threshold_mv
        position_map.append({
            "position": position,
            "mbon05_activity_max_voltage_mv": maximum,
            "sample_count": len(enabled_samples),
            "output_enabled": True,
            "action": action,
            "state": "action" if action else "no_action",
        })
    return {
        "first_kc_spike_time_us": first_spike_us,
        "trace": trace,
        "position_map": position_map,
        "action_positions": [row["position"] for row in position_map if row["action"] is True],
        "disabled_positions": [row["position"] for row in position_map if not row["output_enabled"]],
    }


def _inputs(root: Path, config_path: str):
    root = Path(root)
    stage = json.loads((root / config_path).read_text(encoding="utf-8"))
    protocol = stage["protocol"]
    if _sha256(root / FROZEN_SPEED_CONFIG) != stage["parent_speed_config_sha256"]:
        raise ValueError("admitted 500-ms speed config changed after Level 4B freeze")
    level4a_path = root / stage["parent_level4a_result"]
    if _sha256(level4a_path) != stage["parent_level4a_result_sha256"]:
        raise ValueError("Level 4A admission receipt changed after Level 4B freeze")
    if _sha256(root / stage["parent_level3b_config"]) != stage["parent_level3b_config_sha256"]:
        raise ValueError("Level 3B parent config changed after Level 4B freeze")
    _, l3, parent, audit, threshold = _level4a_inputs(root, "configs/malecns_level4a_temporal_input_admission.json")
    if protocol["duration_us"] != 500_000 or protocol["dt_us"] != parent["overlay"]["lif"]["dt_us"]:
        raise ValueError("Level 4B must use the admitted 500-ms duration and inherited dt")
    if protocol["action_threshold_mv"] != threshold:
        raise ValueError("Level 4B changed the inherited fixed action threshold")
    if protocol["encoder_sigma"] != parent["encoder"]["sigma"]:
        raise ValueError("Level 4B changed the inherited Gaussian encoder")
    if protocol["peak_drive_mv_equivalent"] != parent["encoder"]["peak_drive_mv"]:
        raise ValueError("Level 4B changed the inherited encoder amplitude")
    if protocol["position_grid"] != parent["evaluation"]["position_grid"]:
        raise ValueError("Level 4B changed the inherited position grid")
    if protocol["learning"] != "OFF" or protocol["plasticity"] != "OFF; immutable original weights" or protocol["dan_teaching"] != "OFF; no DAN stimulation":
        raise ValueError("Level 4B must remain no-learning and no-DAN")
    if protocol["replay_count"] != 2:
        raise ValueError("Level 4B requires exactly two deterministic replays")
    return stage, l3, parent, threshold


def _signature(run: dict, gated: dict) -> dict:
    return {
        "total_kc_spikes": run["total_kc_spikes"],
        "spiking_kc_source_ids": run["spiking_kc_source_ids"],
        "kc_spike_counts_by_source_id": run["kc_spike_counts_by_source_id"],
        "kc_spike_events": run["kc_spike_events"],
        "mbon05_timecourse": run["mbon05_timecourse"],
        "output_validity_trace": gated["trace"],
        "position_map": gated["position_map"],
        "action_positions": gated["action_positions"],
    }


def run_admission(root: Path, config_path: str = CONFIG_DEFAULT) -> dict:
    root = Path(root)
    stage, l3, parent, threshold = _inputs(root, config_path)
    protocol = stage["protocol"]
    raw_runs = [_run_one(parent, threshold, protocol["duration_us"], protocol["position_bin_width"])
                for _ in range(protocol["replay_count"])]
    gated_runs = [action_validity_trace(run, threshold) for run in raw_runs]
    signatures = [_signature(run, gated) for run, gated in zip(raw_runs, gated_runs)]
    hashes = [hashlib.sha256(json.dumps(sig, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
              for sig in signatures]
    first, gated = raw_runs[0], gated_runs[0]
    first_spike_us = gated["first_kc_spike_time_us"]
    pre_spike_rows = [row for row in gated["trace"]
                      if first_spike_us is None or row["time_us"] < first_spike_us]
    target_wrong_positions = {0.15, 0.20, 0.25, 0.65, 0.70, 0.75}
    map_by_position = {row["position"]: row for row in gated["position_map"]}
    gates = {
        "kc_activity_occurs": first["total_kc_spikes"] > 0,
        "mbon05_responds": first["mbon05_peak_voltage_mv"] > 0.0,
        "no_startup_action_before_first_kc_spike": all(row["action"] is None and not row["output_enabled"]
                                                         for row in pre_spike_rows),
        "naive_target_and_wrong_regions_have_no_action": all(
            map_by_position[position]["action"] is False for position in target_wrong_positions
        ),
        "deterministic_replay": hashes[0] == hashes[1],
    }
    return {
        "experiment_id": stage["experiment_id"],
        "stage": "level4b_moving_note_output_admission_repair",
        "config": config_path,
        "config_sha256": _sha256(root / config_path),
        "parent_speed_config_sha256": stage["parent_speed_config_sha256"],
        "parent_level4a_result_sha256": stage["parent_level4a_result_sha256"],
        "parent_level3b_config_sha256": stage["parent_level3b_config_sha256"],
        "dan_source_ids_retained_but_not_stimulated": l3["dan_source_ids"],
        "duration_us": protocol["duration_us"],
        "frozen_action_threshold_mv": threshold,
        "fixed_encoder": {"sigma": parent["encoder"]["sigma"],
                           "peak_drive_mv_equivalent": parent["encoder"]["peak_drive_mv"],
                           "input": "current position only"},
        "validity_rule": protocol["action_validity_rule"],
        "learning_runs": 0,
        "dan_teaching_events": 0,
        "plasticity": "OFF; immutable original weights",
        "replay_count": len(raw_runs),
        "replay_sha256": hashes,
        "first_run": {
            **first,
            "raw_threshold_action_positions": first["action_positions"],
            "output_validity": gated,
            "position_map": gated["position_map"],
            "action_positions": gated["action_positions"],
            "disabled_positions": gated["disabled_positions"],
            "naive_baseline_action_everywhere": len(gated["action_positions"]) == len(gated["position_map"]),
        },
        "gates": gates,
        "status": "PASS" if all(gates.values()) else "FAIL",
        "decision": ("The fixed first-KC-spike validity rule passes Level 4B and is frozen for future moving-note output. No learning was run; stop here."
                     if all(gates.values()) else
                     "The fixed validity rule failed one or more Level 4B admission gates. No learning was run."),
    }


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
    print(json.dumps({"status": result["status"], "gates": result["gates"],
                      "total_kc_spikes": result["first_run"]["total_kc_spikes"],
                      "first_kc_spike_time_us": result["first_run"]["output_validity"]["first_kc_spike_time_us"],
                      "mbon05_peak_voltage_mv": result["first_run"]["mbon05_peak_voltage_mv"],
                      "action_positions": result["first_run"]["action_positions"],
                      "disabled_positions": result["first_run"]["disabled_positions"]}, indent=2))
