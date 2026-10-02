"""Level 2R training on the next outcome-blind 32-KC cohort."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from project_b.malecns_continuous_position_learning.encoder import population_drive
from project_b.malecns_continuous_position_learning.experiment import (
    _arm_metrics,
    _encoder_sha256,
    _evaluate,
)
from project_b.malecns_continuous_position_learning.experiment_v2_1 import _train_arm
from project_b.malecns_continuous_position_learning.experiment_v2_5 import (
    _curve,
    _locality,
)
from project_b.malecns_continuous_position_learning.probe import (
    _trial,
    config_sha256,
    load_config,
)


def _fixed_settings_match(config: dict, predecessor: dict) -> bool:
    if config["encoder"] != predecessor["encoder"]:
        return False
    if config["overlay"] != predecessor["overlay"]:
        return False
    if config["training"] != predecessor["training"]:
        return False
    if config["target_region"] != predecessor["target_region"]:
        return False
    if config["locality_evaluation"] != predecessor["locality_evaluation"]:
        return False
    if config["evaluation"] != predecessor["evaluation"]:
        return False
    if config["weight_initialization"] != predecessor["weight_initialization"]:
        return False
    if config["circuit"]["mbon_source_id"] != predecessor["circuit"]["mbon_source_id"]:
        return False
    if len(config["circuit"]["selected_kcs"]) != 32:
        return False
    if config["circuit"]["plastic_edge_count"] != 32:
        return False
    return True


def _read_frozen_probe(root: Path, config_path: str, config: dict) -> tuple[float, dict]:
    probe_path = root / config["controllability_probe"]["probe_result"]
    if not probe_path.is_file():
        raise ValueError("Level 2R pretraining probe is missing; training is not authorized")
    probe = json.loads(probe_path.read_text(encoding="utf-8"))
    if probe.get("status") != "PASS":
        raise ValueError("Level 2R pretraining controllability failed; refusing training")
    if probe.get("config_sha256") != config_sha256(root, config_path):
        raise ValueError("Level 2R probe receipt does not match the frozen cohort config")
    threshold = probe.get("frozen_action_threshold_mv")
    if not isinstance(threshold, (int, float)) or not math.isfinite(threshold):
        raise ValueError("Level 2R probe did not freeze a finite action threshold")
    return float(threshold), probe


def run_experiment(root: Path, config_path: str) -> dict:
    root = Path(root)
    config = load_config(root, config_path)
    if config["training"]["blocks"] != 120 or len(config["training"]["sequence"]) != 1200:
        raise ValueError("Level 2R is frozen at 120 blocks / 1,200 presentations")
    predecessor_path = config["continuation"]["predecessor_settings_config"]
    predecessor_file = root / predecessor_path
    expected = config["continuation"]["predecessor_settings_config_sha256"]
    if hashlib.sha256(predecessor_file.read_bytes()).hexdigest() != expected:
        raise ValueError("pinned v2.5 settings config checksum changed")
    predecessor = load_config(root, predecessor_path)
    if not _fixed_settings_match(config, predecessor):
        raise ValueError("Level 2R changed a frozen v2.5 model/training parameter")

    threshold, probe = _read_frozen_probe(root, config_path, config)
    cells = config["circuit"]["selected_kcs"]
    baseline_weights = [cell["plastic_contact_rows"] /
                        config["circuit"]["plastic_contact_count"] for cell in cells]
    baseline = _evaluate(config, baseline_weights, threshold)
    target = _train_arm(config, threshold, arm="primary")
    off = _train_arm(config, threshold, arm="plasticity_off_control")
    wrong = _train_arm(config, threshold, arm="wrong_region_control")
    arms = (target, off, wrong)
    metrics = {
        "target_teacher": _arm_metrics(config, target, baseline),
        "plasticity_off": _arm_metrics(config, off, baseline),
        "wrong_region_teacher": _arm_metrics(config, wrong, baseline),
    }
    target_core = metrics["target_teacher"]["target_core_actions"]
    wrong_core = metrics["wrong_region_teacher"]["wrong_core_actions"]
    locality = {
        "target_teacher": _locality(
            target, config["locality_evaluation"]["target_teacher"]["allowed_halo"]),
        "wrong_region_teacher": _locality(
            wrong, config["locality_evaluation"]["wrong_region_teacher"]["allowed_halo"]),
    }
    off_no_action = not any(row["action"] for row in off["final_position_map"])

    result = {
        "experiment_id": config["experiment_id"],
        "stage": "level2r_new_32_kc_cohort",
        "config": config_path,
        "config_sha256": config_sha256(root, config_path),
        "cohort_selection": config["circuit"]["cohort_selection"],
        "selected_kcs": cells,
        "plastic_contact_count": config["circuit"]["plastic_contact_count"],
        "pretraining_probe_status": probe["status"],
        "pretraining_probe_path": config["controllability_probe"]["probe_result"],
        "pretraining_probe_sha256": hashlib.sha256(
            (root / config["controllability_probe"]["probe_result"]).read_bytes()).hexdigest(),
        "threshold_selection_rule": config["controllability_probe"]["threshold_selection"],
        "frozen_action_threshold_mv": threshold,
        "encoder_sha256": _encoder_sha256(config),
        "training_blocks_completed": {arm["arm"]: len(arm["block_maps"]) for arm in arms},
        "training_presentations_completed": {arm["arm"]: len(arm["trials"]) for arm in arms},
        "circuit": config["circuit"],
        "target_region": config["target_region"],
        "locality_evaluation": config["locality_evaluation"],
        "baseline_position_map": baseline,
        "target_teacher": target,
        "plasticity_off_control": off,
        "wrong_region_teacher": wrong,
        "arm_metrics": metrics,
        "arm_locality": locality,
        "learning_curves": {
            "target_teacher": _curve(target, config),
            "plasticity_off_control": _curve(off, config),
            "wrong_region_teacher": _curve(wrong, config),
        },
        "weights_at_ltd_floor_final": {
            arm["arm"]: [cells[i]["source_id"] for i, (weight, initial) in
                         enumerate(zip(arm["final_weights"], arm["initial_weights"]))
                         if weight <= initial * config["training"]["ltd"]["minimum_fraction"]]
            for arm in arms
        },
    }
    criteria = {
        "all_120_blocks_and_1200_presentations_run_in_every_arm": all(
            len(arm["block_maps"]) == 120 and len(arm["trials"]) == 1200 for arm in arms),
        "all_three_target_core_positions_action": bool(target_core) and all(target_core),
        "all_three_wrong_region_core_positions_action": bool(wrong_core) and all(wrong_core),
        "wrong_region_teaching_has_no_target_core_actions": not any(
            metrics["wrong_region_teacher"]["target_core_actions"]),
        "plasticity_off_unchanged_and_no_action": (
            off["initial_weights"] == off["final_weights"]
            and off["final_position_map"] == baseline
            and off_no_action
        ),
        "target_actions_persist_frozen": (
            target["final_position_map"] == target["block_maps"][-1]["position_map"]
            and bool(target_core) and all(target_core)),
        "wrong_region_actions_persist_frozen": (
            wrong["final_position_map"] == wrong["block_maps"][-1]["position_map"]
            and bool(wrong_core) and all(wrong_core)),
        "target_actions_local_to_target_halo": locality["target_teacher"]["locality_pass"],
        "wrong_region_actions_local_to_wrong_halo": locality["wrong_region_teacher"]["locality_pass"],
        "threshold_is_the_pretraining_probe_threshold": (
            threshold == probe["frozen_action_threshold_mv"]
            and all(row["frozen_threshold_mv"] == threshold for row in baseline)
            and all(row["frozen_threshold_mv"] == threshold
                    for arm in arms for row in arm["final_position_map"])),
        "encoder_and_readout_unchanged_from_v2_5": (
            config["encoder"] == predecessor["encoder"]
            and config["overlay"] == predecessor["overlay"]),
        "circuit_identity_and_learning_rule_unchanged": (
            config["circuit"]["mbon_source_id"] == predecessor["circuit"]["mbon_source_id"]
            and config["training"] == predecessor["training"]
            and len(cells) == 32
        ),
    }
    result["criteria"] = criteria
    result["status"] = "PASS" if all(criteria.values()) else "FAIL"
    result["strongest_honest_claim"] = (
        "For this second outcome-blind 32-KC MaleCNS-v1 cohort, the task-independent local-weakening probe froze a new threshold before training, and the same fixed engineering learning protocol met its target, wrong-region, control, frozen-retention and arm-specific locality criteria."
        if result["status"] == "PASS" else
        "This second-cohort Level 2R engineering fixture did not meet all predeclared criteria; the result does not argue against fly biology."
    )
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run_experiment(args.root, args.config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "criteria": result["criteria"]}, indent=2))
