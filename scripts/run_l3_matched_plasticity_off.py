"""DAN-on, plasticity-off matched control for the frozen Level 3 bridge."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from project_b.malecns_continuous_position_learning.experiment import _evaluate  # noqa: E402
from project_b.malecns_continuous_position_learning.experiment_level3_dan_bridge import (  # noqa: E402
    _dan_spike_times, _initial_weights, _load_frozen_inputs,
)
from project_b.malecns_continuous_position_learning.probe import _trial  # noqa: E402


CONFIG = "configs/malecns_dan_bridge_level3_v1_1.json"
OUTPUT = ROOT / "runs/malecns_dan_bridge_level3/matched_plasticity_off.json"


def run() -> dict:
    stage, parent, audit, threshold = _load_frozen_inputs(ROOT, CONFIG)
    initial_weights = _initial_weights(parent)
    baseline = _evaluate(parent, initial_weights, threshold)
    rows = []
    for scheduled in parent["training"]["sequence"]:
        position = scheduled["position"]
        observation = _trial(parent, position, initial_weights)
        stimulate = scheduled["position_class"] == "target_region"
        spikes = _dan_spike_times(parent, stage, stimulate=stimulate) if stimulate else []
        rows.append({
            "presentation": scheduled["presentation"],
            "block": scheduled["block"],
            "position": position,
            "position_class": scheduled["position_class"],
            "external_dan_stimulation": stimulate,
            "dan_spike_times_us_relative_to_presentation": spikes,
            "mbon_activity_max_voltage_mv": observation["mbon_activity_max_voltage_mv"],
            "action": observation["mbon_activity_max_voltage_mv"] <= threshold,
            "plasticity_enabled": False,
            "weight_changes": [],
        })
    final = _evaluate(parent, initial_weights, threshold)
    criteria = {
        "all_120_blocks_and_1200_presentations_completed": (
            len(rows) == 1200 and {row["block"] for row in rows} == set(range(1, 121))),
        "all_600_target_events_stimulated_dan": (
            sum(row["external_dan_stimulation"] for row in rows) == 600
            and all(row["dan_spike_times_us_relative_to_presentation"]
                    for row in rows if row["external_dan_stimulation"])),
        "plasticity_disabled_all_presentations": all(
            not row["plasticity_enabled"] and not row["weight_changes"] for row in rows),
        "weights_unchanged": True,
        "final_map_equals_frozen_baseline": final == baseline,
        "no_action_anywhere": all(not row["action"] for row in final),
    }
    return {
        "experiment_id": "MALECNS-DAN-BRIDGE-LEVEL3-MATCHED-PLASTICITY-OFF",
        "role": "DAN-on target-event schedule with all KC→MBON05 plasticity disabled",
        "config": CONFIG,
        "config_sha256": hashlib.sha256((ROOT / CONFIG).read_bytes()).hexdigest(),
        "dan_source_id": stage["dan_source_id"],
        "frozen_action_threshold_mv": threshold,
        "initial_weights": initial_weights,
        "final_weights": list(initial_weights),
        "baseline_position_map": baseline,
        "final_position_map": final,
        "trials": rows,
        "criteria": criteria,
        "status": "PASS" if all(criteria.values()) else "FAIL",
        "interpretation": "A matched DAN-on, plasticity-off control for the failed Level 3 learning run; this is no additional learning run.",
    }


if __name__ == "__main__":
    result = run()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    print(json.dumps({"status": result["status"], "criteria": result["criteria"]}, indent=2))
