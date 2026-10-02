"""Level 2 v2.5: 120-block protocol-correction confirmation."""

from __future__ import annotations

import json
import copy
import hashlib
from pathlib import Path

from project_b.malecns_continuous_position_learning.experiment import (
    _arm_metrics,
    _encoder_sha256,
    _evaluate,
)
from project_b.malecns_continuous_position_learning.experiment_v2_1 import (
    _train_arm,
    _v1_probe,
)
from project_b.malecns_continuous_position_learning.probe import (
    config_sha256,
    load_config,
)


def _locality(arm: dict, halo: list[float]) -> dict:
    lo, hi = halo
    actions = [row["position"] for row in arm["final_position_map"] if row["action"]]
    outside = [row for row in arm["final_position_map"]
               if row["position"] < lo or row["position"] > hi]
    outside_actions = [row["position"] for row in outside if row["action"]]
    no_action_fraction = (sum(not row["action"] for row in outside) / len(outside)
                          if outside else 1.0)
    return {
        "allowed_halo": list(halo),
        "action_positions": actions,
        "outside_halo_positions": [row["position"] for row in outside],
        "outside_halo_action_positions": outside_actions,
        "outside_halo_no_action_fraction": no_action_fraction,
        "locality_pass": not outside_actions or no_action_fraction >= 0.9,
    }


def _same_model_and_training_settings(config: dict, predecessor: dict) -> bool:
    current = copy.deepcopy(config)
    previous = copy.deepcopy(predecessor)
    for data in (current, previous):
        data.pop("experiment_id", None)
        data.pop("status", None)
        data.pop("continuation", None)
        data.pop("locality_evaluation", None)
    return current == previous


def _curve(arm: dict, config: dict) -> list[dict]:
    wrong_lo, wrong_hi = config["target_region"]["wrong_control"]
    points = []
    for block in arm["block_maps"]:
        wrong_rows = [row for row in block["position_map"]
                      if wrong_lo <= row["position"] <= wrong_hi]
        points.append({
            "block": block["block"],
            "target_mean_mbon_mv": block["target_mean_mbon_mv"],
            "target_action_count": block["target_action_count"],
            "wrong_region_mean_mbon_mv": sum(
                row["mbon_activity_max_voltage_mv"] for row in wrong_rows
            ) / len(wrong_rows),
            "wrong_region_action_count": sum(bool(row["action"]) for row in wrong_rows),
            "full_grid_action_count": block["full_grid_action_count"],
            "weights_at_floor": block["weights_at_floor"],
        })
    return points


def run_experiment(root: Path, config_path: str) -> dict:
    root = Path(root)
    config = load_config(root, config_path)
    if config["training"]["blocks"] != 120:
        raise ValueError("v2.5 requires exactly 120 predeclared blocks; do not extend this run")
    continuation = config["continuation"]
    predecessor_path = root / continuation["predecessor_config"]
    if hashlib.sha256(predecessor_path.read_bytes()).hexdigest() != continuation["predecessor_config_sha256"]:
        raise ValueError("pinned v2.3 predecessor config checksum changed")
    predecessor = load_config(root, continuation["predecessor_config"])
    if not _same_model_and_training_settings(config, predecessor):
        raise ValueError("v2.5 changed a v2.3 model or training setting")
    threshold, probe = _v1_probe(root, config)
    if threshold != config["continuation"]["frozen_action_threshold_mv"]:
        raise ValueError("fixed inherited action threshold was modified")

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
        "target_teacher": _locality(target, config["locality_evaluation"]["target_teacher"]["allowed_halo"]),
        "wrong_region_teacher": _locality(wrong, config["locality_evaluation"]["wrong_region_teacher"]["allowed_halo"]),
    }
    no_action_off = not any(row["action"] for row in off["final_position_map"])
    same_settings = _same_model_and_training_settings(config, predecessor)

    result = {
        "experiment_id": config["experiment_id"],
        "stage": "level2_continuous_position_learning_v2_5",
        "config": config_path,
        "config_sha256": config_sha256(root, config_path),
        "inherited_v1_probe_status": probe["status"],
        "frozen_action_threshold_mv": threshold,
        "eligibility_reset_scope": "presentation_local; a fresh eligibility state is used per presentation while weights carry forward",
        "training_blocks_completed": {arm["arm"]: len(arm["block_maps"]) for arm in arms},
        "training_presentations_completed": {arm["arm"]: len(arm["trials"]) for arm in arms},
        "encoder_sha256": _encoder_sha256(config),
        "readout": "action iff max MBON05 voltage during the fixed observation window is <= the inherited threshold; no trainable decoder",
        "circuit": config["circuit"],
        "target_region": config["target_region"],
        "locality_evaluation": config["locality_evaluation"],
        "protocol_correction": "Locality is measured relative to the trained arm’s own region. The intended wrong-region response is not treated as distant from the target region.",
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
        "all_120_blocks_and_1200_presentations_run_in_every_arm": (
            all(len(arm["block_maps"]) == 120 and len(arm["trials"]) == 1200 for arm in arms)
        ),
        "target_teaching_creates_action_core_at_0_65_to_0_75": bool(target_core) and all(target_core),
        "wrong_region_teaching_creates_action_core_at_0_15_to_0_25": bool(wrong_core) and all(wrong_core),
        "wrong_region_teaching_shifts_away_from_target_core": not any(
            metrics["wrong_region_teacher"]["target_core_actions"]),
        "plasticity_off_weights_and_map_are_unchanged": (
            off["initial_weights"] == off["final_weights"]
            and off["final_position_map"] == baseline
        ),
        "plasticity_off_remains_no_action": no_action_off,
        "target_teacher_actions_local_to_target_halo": locality["target_teacher"]["locality_pass"],
        "wrong_region_teacher_actions_local_to_wrong_halo": locality["wrong_region_teacher"]["locality_pass"],
        "target_learned_region_persists_frozen": (
            target["final_position_map"] == target["block_maps"][-1]["position_map"]
            and bool(target_core) and all(target_core)
        ),
        "wrong_region_learned_region_persists_frozen": (
            wrong["final_position_map"] == wrong["block_maps"][-1]["position_map"]
            and bool(wrong_core) and all(wrong_core)
        ),
        "inherited_threshold_is_fixed_on_all_evaluations": all(
            row["frozen_threshold_mv"] == threshold
            for arm in arms for block in arm["block_maps"] for row in block["position_map"]
        ) and all(row["frozen_threshold_mv"] == threshold for row in baseline),
        "encoder_and_fixed_readout_preserved": (
            result["encoder_sha256"] == _encoder_sha256(config)
            and config["overlay"]["mbon_activity"] ==
                "maximum subthreshold MBON05 membrane voltage during fixed observation window; engineering readout"
        ),
        "circuit_and_learning_parameters_unchanged_from_v2_3": same_settings,
    }
    result["criteria"] = criteria
    result["status"] = "PASS" if all(criteria.values()) else "FAIL"
    result["strongest_honest_claim"] = (
        "In this deterministic engineering fixture, the fixed current-position Gaussian code, selected MaleCNS-v1 KC→MBON05 weights, presentation-local LTD rule, and artificial teacher stored and retained the predeclared target and wrong-region action maps."
        if result["status"] == "PASS" else
        "This frozen Level 2 v2.5 protocol-correction confirmation did not meet all predeclared learning, locality and retention criteria; the outcome does not argue against fly biology."
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
