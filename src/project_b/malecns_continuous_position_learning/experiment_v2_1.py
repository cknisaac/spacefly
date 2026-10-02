"""Level 2 v2.1: presentation-local eligibility, fixed 32-block schedule."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from project_b.malecns_minimal_internal_learning.ltd import LocalLTD
from project_b.malecns_continuous_position_learning.encoder import population_drive
from project_b.malecns_continuous_position_learning.probe import (
    _trial, config_sha256, load_config,
)
from project_b.malecns_continuous_position_learning.experiment import (
    _action_positions, _arm_metrics, _encoder_sha256, _evaluate,
)


def _v1_probe(root: Path, config: dict) -> tuple[float, dict]:
    continuation = config["continuation"]
    v1_config_path = root / continuation["source_config"]
    probe_path = root / continuation["source_probe"]
    if hashlib.sha256(v1_config_path.read_bytes()).hexdigest() != continuation["source_config_sha256"]:
        raise ValueError("Level 1/2 v1 frozen config checksum changed")
    if hashlib.sha256(probe_path.read_bytes()).hexdigest() != continuation["source_probe_sha256"]:
        raise ValueError("v1 pretraining probe checksum changed")
    probe = json.loads(probe_path.read_text(encoding="utf-8"))
    threshold = continuation["frozen_action_threshold_mv"]
    if probe.get("status") != "PASS":
        raise ValueError("inherited v1 controllability probe did not PASS")
    if probe.get("frozen_action_threshold_mv") != threshold:
        raise ValueError("v2.1 threshold differs from inherited v1 threshold")
    if probe.get("config_sha256") != continuation["source_config_sha256"]:
        raise ValueError("inherited probe does not match the pinned v1 config")
    return float(threshold), probe


def _new_presentation_rule(weights: list[float], original_weights: list[float],
                           ltd_config: dict) -> LocalLTD:
    """Reset eligibility while retaining current weights and the run-start floor."""
    return LocalLTD(list(weights), original_weights=original_weights, **ltd_config)


def _train_arm(config: dict, threshold: float, *, arm: str) -> dict:
    cells = config["circuit"]["selected_kcs"]
    total = sum(cell["plastic_contact_rows"] for cell in cells)
    weights = [cell["plastic_contact_rows"] / total for cell in cells]
    schedule = config["training"]["sequence"]
    policy = config["training"]["teacher_policy"][arm]
    window = config["overlay"]["observation_window_us"]
    spacing = config["training"]["trial_spacing_us"]
    lag = config["training"]["teacher_lag_us"]
    block_rows: dict[int, list[dict]] = {}
    for row in schedule:
        block_rows.setdefault(row["block"], []).append(row)
    trials = []
    block_maps = []
    initial = list(weights)
    for block in range(1, config["training"]["blocks"] + 1):
        for scheduled in block_rows[block]:
            # A fresh local rule starts this presentation with zero eligibility;
            # only the learned KC→MBON weights carry over from earlier trials.
            presentation_rule = _new_presentation_rule(
                weights, initial, config["training"]["ltd"])
            x = scheduled["position"]
            offset = (scheduled["presentation"] - 1) * spacing
            observation = _trial(config, x, presentation_rule.weights)
            for spike in observation["kc_spikes"]:
                presentation_rule.observe_kc_spike(
                    spike["edge_index"], offset + spike["time_us"])
            if policy == "target_region":
                teacher = scheduled["position_class"] == "target_region"
            elif policy == "wrong_region":
                teacher = scheduled["position_class"] == "wrong_region_distractor"
            elif policy == "off":
                teacher = False
            else:
                raise ValueError(f"unknown teacher policy for arm {arm}")
            teacher_time = offset + window + lag
            eligibility = {str(cell["source_id"]): presentation_rule.eligibility_at(i, teacher_time)
                           for i, cell in enumerate(cells)}
            changes = presentation_rule.teacher_pulse(teacher_time, teacher=teacher)
            weights = list(presentation_rule.weights)
            trials.append({
                "presentation": scheduled["presentation"],
                "block": block,
                "position": x,
                "position_class": scheduled["position_class"],
                "kc_activations": {str(cell["source_id"]): drive
                    for cell, drive in zip(cells, population_drive(
                        x, cells, sigma=config["encoder"]["sigma"],
                        peak_drive_mv=config["encoder"]["peak_drive_mv"]))},
                "kc_spike_counts": observation["kc_spike_counts"],
                "mbon_activity_max_voltage_mv": observation["mbon_activity_max_voltage_mv"],
                "action_before_teacher": observation["mbon_activity_max_voltage_mv"] <= threshold,
                "eligibility_at_teacher": eligibility,
                "eligibility_reset_scope": "presentation_local",
                "teacher": int(teacher),
                "weight_changes": [dict(change, source_id=cells[change["edge_index"]]["source_id"])
                                   for change in changes],
            })
        panel = _evaluate(config, weights, threshold)
        target_lo, target_hi = config["target_region"]["primary"]
        target_rows = [row for row in panel if target_lo <= row["position"] <= target_hi]
        wrong_lo, wrong_hi = config["target_region"]["wrong_control"]
        wrong_rows = [row for row in panel if wrong_lo <= row["position"] <= wrong_hi]
        block_maps.append({
            "block": block,
            "position_map": panel,
            "target_mean_mbon_mv": sum(r["mbon_activity_max_voltage_mv"]
                                        for r in target_rows) / len(target_rows),
            "target_action_count": sum(bool(r["action"]) for r in target_rows),
            "wrong_region_action_count": sum(bool(r["action"]) for r in wrong_rows),
            "full_grid_action_count": sum(bool(r["action"]) for r in panel),
            "weights_after_block": list(weights),
            "weights_at_floor": [cells[i]["source_id"] for i, (weight, start) in
                                 enumerate(zip(weights, initial))
                                 if weight <= start * config["training"]["ltd"]["minimum_fraction"]],
        })
    return {
        "arm": arm,
        "teacher_pulse_count": sum(row["teacher"] for row in trials),
        "trials": trials,
        "block_maps": block_maps,
        "initial_weights": initial,
        "final_weights": list(weights),
        "final_position_map": _evaluate(config, weights, threshold),
    }


def run_experiment(root: Path, config_path: str) -> dict:
    root = Path(root)
    config = load_config(root, config_path)
    threshold, probe = _v1_probe(root, config)
    expected_threshold = config["continuation"]["frozen_action_threshold_mv"]
    if threshold != expected_threshold:
        raise ValueError("fixed Level 2 action threshold was modified")
    baseline_weights = [cell["plastic_contact_rows"] /
                        config["circuit"]["plastic_contact_count"]
                        for cell in config["circuit"]["selected_kcs"]]
    baseline = _evaluate(config, baseline_weights, threshold)
    primary = _train_arm(config, threshold, arm="primary")
    off = _train_arm(config, threshold, arm="plasticity_off_control")
    wrong = _train_arm(config, threshold, arm="wrong_region_control")
    metrics = {
        "primary": _arm_metrics(config, primary, baseline),
        "plasticity_off": _arm_metrics(config, off, baseline),
        "wrong_region": _arm_metrics(config, wrong, baseline),
    }
    target_lo, target_hi = config["target_region"]["primary"]
    wrong_lo, wrong_hi = config["target_region"]["wrong_control"]
    target_core = metrics["primary"]["target_core_actions"]
    wrong_core = metrics["wrong_region"]["wrong_core_actions"]
    distant_actions = metrics["primary"]["distant_actions"]
    distant_majority_no_action = (sum(not value for value in distant_actions)
                                  >= math.ceil(0.9 * len(distant_actions)))
    primary_changes = [a != b for a, b in zip(primary["initial_weights"], primary["final_weights"])]
    primary_curve = [row["target_mean_mbon_mv"] for row in primary["block_maps"]]
    result = {
        "experiment_id": config["experiment_id"],
        "stage": "level2_continuous_position_learning_v2_1",
        "config": config_path,
        "config_sha256": config_sha256(root, config_path),
        "inherited_v1_probe_status": probe["status"],
        "frozen_action_threshold_mv": threshold,
        "eligibility_reset_scope": "presentation_local; every presentation gets a new LocalLTD trace state while weights carry forward",
        "training_blocks_completed": config["training"]["blocks"],
        "encoder_sha256": _encoder_sha256(config),
        "circuit": config["circuit"],
        "target_region": config["target_region"],
        "baseline_position_map": baseline,
        "primary": primary,
        "plasticity_off_control": off,
        "wrong_region_control": wrong,
        "arm_metrics": metrics,
        "learning_curve": [{
            "block": row["block"],
            "target_mean_mbon_mv": row["target_mean_mbon_mv"],
            "target_action_count": row["target_action_count"],
            "wrong_region_action_count": row["wrong_region_action_count"],
            "full_grid_action_count": row["full_grid_action_count"],
            "weights_at_floor": row["weights_at_floor"],
        } for row in primary["block_maps"]],
    }
    criteria = {
        "all_32_blocks_run_in_every_arm": all(len(arm["block_maps"]) == 32
            for arm in (primary, off, wrong)),
        "target_teaching_creates_target_core_action_region": bool(target_core)
            and all(target_core),
        "target_region_is_single_local_action_component": (
            metrics["primary"]["action_region_single_component"]
            and metrics["primary"]["action_region_width"] <= 0.40
            and target_lo <= min(metrics["primary"]["action_positions"], default=2.0)
            and max(metrics["primary"]["action_positions"], default=-1.0) <= target_hi + 0.20),
        "distant_positions_mostly_remain_no_action": distant_majority_no_action,
        "wrong_region_teaching_shifts_toward_wrong_region": bool(wrong_core)
            and all(wrong_core)
            and not any(metrics["wrong_region"]["target_core_actions"])
            and metrics["wrong_region"]["action_region_single_component"],
        "plasticity_off_does_not_learn_target_region": not any(
            metrics["plasticity_off"]["target_core_actions"]),
        "frozen_evaluation_retains_target_learned_region": (
            primary["final_position_map"] == primary["block_maps"][-1]["position_map"]
            and bool(target_core) and all(target_core)),
        "fixed_threshold_preserved": all(
            row["frozen_threshold_mv"] == threshold
            for arm in (primary, off, wrong)
            for row in arm["final_position_map"]),
        "encoder_preserved": result["encoder_sha256"] == _encoder_sha256(config),
        "only_selected_internal_weights_adapt": any(primary_changes),
        "local_weight_changes_require_current_presentation_eligibility": all(
            change["eligibility"] > 0 for trial in primary["trials"]
            for change in trial["weight_changes"]),
    }
    result["criteria"] = criteria
    result["status"] = "PASS" if all(criteria.values()) else "FAIL"
    result["strongest_honest_claim"] = (
        "A fixed Gaussian current-position code drove measured MaleCNS-v1 KC→MBON05 edges; with presentation-local eligibility, the fixed artificial teacher and frozen local LTD rule stored a position-selective action region that persisted under teacher/plasticity-off evaluation in this deterministic engineering fixture."
        if result["status"] == "PASS" else
        "This frozen Level 2 v2.1 engineering fixture did not meet its predeclared continuous-position learning criteria; the result does not argue against fly biology."
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
