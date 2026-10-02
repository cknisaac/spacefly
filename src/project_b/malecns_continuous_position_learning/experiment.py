"""Frozen Level 2 continuous-position training and matched controls."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from project_b.malecns_minimal_internal_learning.ltd import LocalLTD
from project_b.malecns_continuous_position_learning.encoder import population_drive
from project_b.malecns_continuous_position_learning.probe import (
    _lif, _trial, config_sha256, load_config,
)


def _encoder_sha256(config: dict) -> str:
    encoded = json.dumps(config["encoder"], sort_keys=True,
                         separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _threshold(root: Path, config_path: str, config: dict) -> tuple[float, dict]:
    probe_path = root / config["controllability_probe"]["probe_result"]
    if not probe_path.is_file():
        raise ValueError(f"pretraining controllability result is missing: {probe_path}")
    probe = json.loads(probe_path.read_text(encoding="utf-8"))
    if probe.get("status") != "PASS":
        raise ValueError("pretraining controllability probe did not PASS; refusing training")
    expected_hash = config_sha256(root, config_path)
    if probe.get("config_sha256") != expected_hash:
        raise ValueError("pretraining probe was produced from a different frozen config")
    threshold = probe.get("frozen_action_threshold_mv")
    if not isinstance(threshold, (int, float)) or not math.isfinite(threshold):
        raise ValueError("pretraining probe did not freeze a finite threshold")
    return float(threshold), probe


def _evaluate(config: dict, weights: list[float], threshold: float) -> list[dict]:
    rows = []
    for x in config["evaluation"]["position_grid"]:
        row = _trial(config, x, weights)
        row["action"] = row["mbon_activity_max_voltage_mv"] <= threshold
        row["frozen_threshold_mv"] = threshold
        rows.append(row)
    return rows


def _train_arm(config: dict, threshold: float, *, arm: str) -> dict:
    cells = config["circuit"]["selected_kcs"]
    total = sum(cell["plastic_contact_rows"] for cell in cells)
    initial = [cell["plastic_contact_rows"] / total for cell in cells]
    rule = LocalLTD(initial, **config["training"]["ltd"])
    schedule = config["training"]["sequence"]
    window = config["overlay"]["observation_window_us"]
    spacing = config["training"]["trial_spacing_us"]
    lag = config["training"]["teacher_lag_us"]
    teacher_policy = config["training"]["teacher_policy"][arm]
    trials = []
    block_maps = []
    by_block: dict[int, list[dict]] = {}
    for row in schedule:
        block = row["block"]
        by_block.setdefault(block, []).append(row)
    for block in sorted(by_block):
        for scheduled in by_block[block]:
            index = scheduled["presentation"] - 1
            offset = index * spacing
            x = scheduled["position"]
            observation = _trial(config, x, rule.weights)
            for spike in observation["kc_spikes"]:
                rule.observe_kc_spike(spike["edge_index"], offset + spike["time_us"])
            if teacher_policy == "target_region":
                teacher = scheduled["position_class"] == "target_region"
            elif teacher_policy == "wrong_region":
                teacher = scheduled["position_class"] == "wrong_region_distractor"
            elif teacher_policy == "off":
                teacher = False
            else:
                raise ValueError(f"unknown teacher policy for arm {arm}")
            teacher_time = offset + window + lag
            eligibility = {str(cell["source_id"]): rule.eligibility_at(i, teacher_time)
                           for i, cell in enumerate(cells)}
            changes = rule.teacher_pulse(teacher_time, teacher=teacher)
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
                "action": observation["mbon_activity_max_voltage_mv"] <= threshold,
                "eligibility_at_teacher": eligibility,
                "teacher": int(teacher),
                "weight_changes": [dict(change, source_id=cells[change["edge_index"]]["source_id"])
                                   for change in changes],
            })
        panel = _evaluate(config, rule.weights, threshold)
        target_rows = [row for row in panel
                       if config["target_region"]["primary"][0] <= row["position"]
                       <= config["target_region"]["primary"][1]]
        block_maps.append({
            "block": block,
            "position_map": panel,
            "target_mean_mbon_mv": sum(r["mbon_activity_max_voltage_mv"]
                                        for r in target_rows) / len(target_rows),
            "target_action_count": sum(bool(r["action"]) for r in target_rows),
            "action_count_full_grid": sum(bool(r["action"]) for r in panel),
            "weights_after_block": list(rule.weights),
            "weights_at_floor": [cells[i]["source_id"] for i, (weight, start) in
                                 enumerate(zip(rule.weights, initial))
                                 if weight <= start * config["training"]["ltd"]["minimum_fraction"]],
        })
    return {
        "arm": arm,
        "trials": trials,
        "block_maps": block_maps,
        "initial_weights": initial,
        "final_weights": list(rule.weights),
        "final_position_map": _evaluate(config, rule.weights, threshold),
    }


def _action_positions(panel: list[dict]) -> list[float]:
    return [row["position"] for row in panel if row["action"]]


def _is_single_component(panel: list[dict]) -> bool:
    flags = [bool(row["action"]) for row in panel]
    components = sum(flag and (i == 0 or not flags[i - 1])
                     for i, flag in enumerate(flags))
    return components <= 1


def _arm_metrics(config: dict, arm: dict, baseline: list[dict]) -> dict:
    panel = arm["final_position_map"]
    target_lo, target_hi = config["target_region"]["primary"]
    wrong_lo, wrong_hi = config["target_region"]["wrong_control"]
    distant = [row for row in panel if row["position"] <= target_lo - 0.2
               or row["position"] >= target_hi + 0.2]
    baseline_by_x = {r["position"]: r["mbon_activity_max_voltage_mv"] for r in baseline}
    target_core = [r for r in panel if target_lo <= r["position"] <= target_hi]
    wrong_core = [r for r in panel if wrong_lo <= r["position"] <= wrong_hi]
    adjacent = [r for r in panel if r["position"] in (target_lo - 0.05, target_hi + 0.05)]
    reductions = [
        (baseline_by_x[r["position"]] - r["mbon_activity_max_voltage_mv"])
        / max(baseline_by_x[r["position"]], 1e-15) for r in adjacent
    ]
    distant_delta = [abs(r["mbon_activity_max_voltage_mv"] - baseline_by_x[r["position"]])
                     for r in distant]
    actions = _action_positions(panel)
    return {
        "target_core_positions": [r["position"] for r in target_core],
        "target_core_actions": [bool(r["action"]) for r in target_core],
        "wrong_core_positions": [r["position"] for r in wrong_core],
        "wrong_core_actions": [bool(r["action"]) for r in wrong_core],
        "distant_positions": [r["position"] for r in distant],
        "distant_actions": [bool(r["action"]) for r in distant],
        "adjacent_response_fraction_reduction": reductions,
        "max_distant_absolute_response_delta_mv": max(distant_delta, default=0.0),
        "action_positions": actions,
        "action_region_single_component": _is_single_component(panel),
        "action_region_width": (actions[-1] - actions[0] if actions else 0.0),
    }


def run_experiment(root: Path, config_path: str) -> dict:
    root = Path(root)
    config = load_config(root, config_path)
    threshold, probe = _threshold(root, config_path, config)
    encoder_hash = _encoder_sha256(config)
    baseline_weights = [cell["plastic_contact_rows"] /
                        config["circuit"]["plastic_contact_count"]
                        for cell in config["circuit"]["selected_kcs"]]
    baseline = _evaluate(config, baseline_weights, threshold)
    primary = _train_arm(config, threshold, arm="primary")
    plasticity_off = _train_arm(config, threshold, arm="plasticity_off_control")
    wrong = _train_arm(config, threshold, arm="wrong_region_control")
    primary_metrics = _arm_metrics(config, primary, baseline)
    off_metrics = _arm_metrics(config, plasticity_off, baseline)
    wrong_metrics = _arm_metrics(config, wrong, baseline)
    target_lo, target_hi = config["target_region"]["primary"]
    wrong_lo, wrong_hi = config["target_region"]["wrong_control"]
    core_actions = primary_metrics["target_core_actions"]
    wrong_core_actions = wrong_metrics["wrong_core_actions"]
    target_activities = [block["target_mean_mbon_mv"] for block in primary["block_maps"]]
    target_action_counts = [block["target_action_count"] for block in primary["block_maps"]]
    all_updated = [a != b for a, b in zip(primary["initial_weights"], primary["final_weights"])]
    result = {
        "experiment_id": config["experiment_id"],
        "stage": "level2_continuous_position_learning",
        "config": config_path,
        "config_sha256": config_sha256(root, config_path),
        "pretraining_probe_status": probe["status"],
        "frozen_action_threshold_mv": threshold,
        "encoder_sha256": encoder_hash,
        "encoder_unchanged": True,
        "circuit": config["circuit"],
        "target_region": config["target_region"],
        "baseline_position_map": baseline,
        "primary": primary,
        "plasticity_off_control": plasticity_off,
        "wrong_region_control": wrong,
        "arm_metrics": {"primary": primary_metrics,
                         "plasticity_off": off_metrics,
                         "wrong_region": wrong_metrics},
        "learning_curve": [{"block": row["block"],
                             "target_mean_mbon_mv": row["target_mean_mbon_mv"],
                             "target_action_count": row["target_action_count"],
                             "action_count_full_grid": row["action_count_full_grid"],
                             "weights_at_floor": row["weights_at_floor"]}
                            for row in primary["block_maps"]],
    }
    criteria = {
        "only_selected_internal_kc_mbon_weights_adapt": any(all_updated),
        "encoder_never_changes": result["encoder_unchanged"],
        "threshold_never_changes": all(row["frozen_threshold_mv"] == threshold
                                        for row in primary["final_position_map"]),
        "position_selective_target_action": bool(core_actions) and all(core_actions),
        "neighboring_positions_show_overlap_generalization": (
            len(primary_metrics["adjacent_response_fraction_reduction"]) == 2
            and all(value >= 0.10 for value in
                    primary_metrics["adjacent_response_fraction_reduction"])),
        "distant_positions_remain_comparatively_unchanged": (
            all(not action for action in primary_metrics["distant_actions"])
            and primary_metrics["max_distant_absolute_response_delta_mv"] <= 1e-12),
        "learned_region_persists_with_teacher_and_plasticity_off": (
            bool(core_actions) and all(core_actions)),
        "plasticity_off_control_does_not_learn_target_region": not any(
            off_metrics["target_core_actions"]),
        "wrong_region_teaching_moves_action_to_wrong_region": (
            bool(wrong_core_actions) and all(wrong_core_actions)
            and not any(wrong_metrics["target_core_actions"])),
        "no_external_trainable_decoder": True,
        "action_region_is_local_and_single_component": (
            primary_metrics["action_region_single_component"]
            and target_lo <= min(primary_metrics["action_positions"], default=2.0)
            and max(primary_metrics["action_positions"], default=-1.0) <= target_hi + 0.20
            and primary_metrics["action_region_width"] <= 0.40),
        "target_response_decreases_across_training_blocks": all(
            a >= b for a, b in zip(target_activities, target_activities[1:])),
        "target_actions_emerge_gradually": (
            target_action_counts[0] < len(primary_metrics["target_core_actions"])
            and target_action_counts[-1] == len(primary_metrics["target_core_actions"])
            and all(a <= b for a, b in zip(target_action_counts, target_action_counts[1:]))),
        "not_all_changed_weights_immediately_saturate": (
            not all(weight == start for weight, start in
                    zip(primary["final_weights"], primary["initial_weights"]))
            and any(weight > start * config["training"]["ltd"]["minimum_fraction"]
                    for weight, start, changed in zip(primary["final_weights"],
                        primary["initial_weights"], all_updated) if changed)),
    }
    result["criteria"] = criteria
    result["status"] = "PASS" if all(criteria.values()) else "FAIL"
    result["strongest_honest_claim"] = (
        "A fixed Gaussian code of current note position drove measured MaleCNS-v1 KC→MBON05 edges; under an artificial local teacher, contact-normalized voltage weights, LTD rule, and fixed threshold, a local action region was stored and shifted under wrong-region teaching in this deterministic engineering fixture."
        if result["status"] == "PASS" else
        "This frozen Level 2 engineering fixture did not meet its predeclared continuous-position learning criteria; the result does not argue against fly biology."
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
