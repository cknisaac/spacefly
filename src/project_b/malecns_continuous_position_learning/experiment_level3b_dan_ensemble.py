"""Level 3B: anatomy-selected PAM08 ensemble bridge, capacity-gated before learning."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from project_b.malecns_minimal_internal_learning.ltd import LocalLTD
from project_b.malecns_continuous_position_learning.encoder import population_drive
from project_b.malecns_continuous_position_learning.experiment import (
    _arm_metrics, _encoder_sha256, _evaluate,
)
from project_b.malecns_continuous_position_learning.experiment_v2_1 import _v1_probe
from project_b.malecns_continuous_position_learning.experiment_v2_5 import (
    _curve, _locality,
)
from project_b.malecns_continuous_position_learning.probe import _lif, _trial, load_config
from project_b.simulation import SpikingSimulator
from project_b.synapses import SparseGraph


CONFIG_DEFAULT = "configs/malecns_dan_bridge_level3b_ensemble.json"
CAPACITY_DEFAULT = "runs/malecns_dan_bridge_level3b/capacity.json"
RESULT_DEFAULT = "runs/malecns_dan_bridge_level3b/result.json"
LEVEL2_RECEIPT = "runs/malecns_continuous_position_learning_v2_5_corrected_floor/result.json"
EXPECTED_DANS = (87177, 107285, 55210)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_inputs(root: Path, config_path: str) -> tuple[dict, dict, dict, dict, float]:
    stage_path = root / config_path
    stage = json.loads(stage_path.read_text(encoding="utf-8"))
    parent_path = root / stage["parent_level2_config"]
    audit_path = root / stage["anatomy_audit"]
    if _sha256(parent_path) != stage["parent_level2_config_sha256"]:
        raise ValueError("frozen Level 2 v2.5 config changed")
    if _sha256(audit_path) != stage["anatomy_audit_sha256"]:
        raise ValueError("Level 3B anatomy audit changed after config freeze")
    if tuple(stage["dan_source_ids"]) != EXPECTED_DANS:
        raise ValueError("Level 3B DAN roster differs from the user-selected anatomy set")
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if not audit.get("pam08_roster_and_frozen_kc_mbon_roi_complete"):
        raise ValueError("selected PAM08 roster anatomy is incomplete")
    selected = audit["previously_audited_pam08_roster_scope"][
        "minimum_cardinality_set_for_maximum_coverage"]
    if [int(row["source_id"]) for row in selected] != list(EXPECTED_DANS):
        raise ValueError("pinned minimum-cover DAN set differs")
    coverage = {int(row["source_id"]): set(row["gamma4_kc_source_ids"])
                for row in selected}
    if set().union(*coverage.values()) != set(audit["frozen_cohort"]):
        raise ValueError("selected ensemble does not cover the frozen 32-KC cohort")
    if audit["strict_gamma4_kc_to_mbon05_kc_count"] != 32:
        raise ValueError("frozen cohort is not completely represented in γ4 anatomy")
    if audit["unknown_roi_candidate_rows_by_scope"]["audited_pam08_roster"] != 0:
        raise ValueError("selected DAN roster has unresolved ROI rows")

    parent = load_config(root, stage["parent_level2_config"])
    if parent["training"]["blocks"] != 120 or len(parent["training"]["sequence"]) != 1200:
        raise ValueError("Level 3B must inherit exactly 120 blocks and 1200 presentations")
    if [int(cell["source_id"]) for cell in parent["circuit"]["selected_kcs"]] != audit["frozen_cohort"]:
        raise ValueError("Level 3B cohort differs from the anatomy audit")
    threshold, _ = _v1_probe(root, parent)
    if threshold != parent["continuation"]["frozen_action_threshold_mv"]:
        raise ValueError("inherited fixed action threshold changed")
    if stage["dan_stimulation"] != {
        **stage["dan_stimulation"],
        "amplitude_mv_equivalent": 2.0,
        "duration_us": 20000,
    }:
        raise ValueError("Level 3B stimulation amplitude or duration changed")
    level2_path = root / LEVEL2_RECEIPT
    l2_receipt = json.loads(level2_path.read_text(encoding="utf-8"))
    if (l2_receipt["config_sha256"] != stage["parent_level2_config_sha256"]
            or l2_receipt["frozen_action_threshold_mv"] != threshold):
        raise ValueError("corrected-floor Level 2 eligibility receipt is not the frozen parent")
    return stage, parent, audit, l2_receipt, threshold


def _dan_spike_times(parent: dict, stage: dict, *, stimulate: bool) -> list[int]:
    stim = stage["dan_stimulation"]
    lif = parent["overlay"]["lif"]
    onset = parent["overlay"]["observation_window_us"] + parent["training"]["teacher_lag_us"]
    duration = stim["duration_us"]
    if onset % lif["dt_us"] or duration % lif["dt_us"]:
        raise ValueError("DAN pulse must align with the inherited LIF integration grid")
    sim = SpikingSimulator([_lif(parent)], SparseGraph(1, []), [0.0],
                           dt_us=lif["dt_us"], record_neurons=[0], record_spikes=True)
    sim.run_until(onset)
    if stimulate:
        sim.set_external_drive_mv([stim["amplitude_mv_equivalent"]])
    sim.run_until(onset + duration)
    sim.set_external_drive_mv([0.0])
    return [spike.time_us for spike in sim.snapshot().spikes]


def _ensemble_spikes(parent: dict, stage: dict, *, stimulate: bool) -> dict[int, list[int]]:
    return {dan_id: _dan_spike_times(parent, stage, stimulate=stimulate)
            for dan_id in stage["dan_source_ids"]}


def _dan_coverage(audit: dict) -> dict[int, set[int]]:
    return {int(row["source_id"]): set(row["gamma4_kc_source_ids"])
            for row in audit["previously_audited_pam08_roster_scope"][
                "minimum_cardinality_set_for_maximum_coverage"]}


def _region_eligible_ids(l2_receipt: dict, region: str) -> set[int]:
    arm_key = "target_teacher" if region == "target_region" else "wrong_region_teacher"
    eligible: set[int] = set()
    for trial in l2_receipt[arm_key]["trials"]:
        if trial["position_class"] != region or trial["teacher"] != 1:
            continue
        eligible.update(int(kc) for kc, value in trial["eligibility_at_teacher"].items()
                        if value > 0)
    return eligible


def run_capacity(root: Path, config_path: str) -> dict:
    root = Path(root)
    stage, parent, audit, l2_receipt, threshold = _load_inputs(root, config_path)
    initial = [cell["plastic_contact_rows"] /
               parent["circuit"]["plastic_contact_count"]
               for cell in parent["circuit"]["selected_kcs"]]
    cells = parent["circuit"]["selected_kcs"]
    coverage = _dan_coverage(audit)
    reachable = set().union(*coverage.values())
    ids = [int(cell["source_id"]) for cell in cells]
    frac = parent["training"]["ltd"]["minimum_fraction"]
    conditions = {}
    for label, class_name, core in (
        ("target", "target_region", parent["target_region"]["primary"]),
        ("wrong", "wrong_region_distractor", parent["target_region"]["wrong_control"]),
    ):
        eligible = _region_eligible_ids(l2_receipt, class_name)
        clamp = eligible & reachable
        weights = list(initial)
        for i, kc_id in enumerate(ids):
            if kc_id in clamp:
                weights[i] = initial[i] * frac
        panel = _evaluate(parent, weights, threshold)
        core_positions = [round(float(x), 8) for x in
                          parent["evaluation"]["position_grid"]
                          if core[0] <= x <= core[1]]
        core_rows = {round(row["position"], 8): row for row in panel}
        action_positions = [position for position in core_positions
                            if core_rows[position]["action"]]
        conditions[label] = {
            "teaching_region": [core[0], core[1]],
            "presentation_eligible_kc_ids": sorted(eligible),
            "dan_union_reachable_kc_ids": sorted(reachable),
            "clamped_kc_source_ids": sorted(clamp),
            "clamped_edge_count": len(clamp),
            "weights_clamped_to_exact_original_floor": all(
                weights[i] == initial[i] * frac for i, kc_id in enumerate(ids)
                if kc_id in clamp),
            "core_positions": core_positions,
            "core_action_positions": action_positions,
            "core_action_count": len(action_positions),
            "position_map": [{k: row[k] for k in (
                "position", "mbon_activity_max_voltage_mv", "action", "frozen_threshold_mv")}
                for row in panel],
        }
    criteria = {
        "target_core_capacity_3_of_3": conditions["target"]["core_action_count"] == 3,
        "wrong_core_capacity_3_of_3": conditions["wrong"]["core_action_count"] == 3,
        "floor_is_exactly_inherited_20_percent": frac == 0.20 and all(
            item["weights_clamped_to_exact_original_floor"] for item in conditions.values()),
        "threshold_is_inherited": threshold == parent["continuation"]["frozen_action_threshold_mv"],
        "no_training_was_executed": True,
    }
    return {
        "experiment_id": stage["experiment_id"],
        "step": "1_capacity_only",
        "config": config_path,
        "config_sha256": _sha256(root / config_path),
        "anatomy_audit_sha256": stage["anatomy_audit_sha256"],
        "parent_level2_config_sha256": stage["parent_level2_config_sha256"],
        "parent_level2_result_sha256": _sha256(root / LEVEL2_RECEIPT),
        "dan_source_ids": list(stage["dan_source_ids"]),
        "dan_union_reachable_kc_source_ids": sorted(reachable),
        "frozen_action_threshold_mv": threshold,
        "original_weight_floor_fraction": frac,
        "learning_runs": 0,
        "conditions": conditions,
        "criteria": criteria,
        "capacity_status": "PASS" if all(criteria.values()) else "FAIL",
        "training_authorized_by_capacity_gate": all(criteria.values()),
        "decision": ("Both teaching regions can cross all three frozen core positions at the capacity ceiling; proceed to the separately invoked Level 3B learning step."
                    if all(criteria.values()) else
                    "At least one frozen core cannot reach 3/3 at the capacity ceiling; stop without training."),
    }


def _pretraining_gate(parent: dict, stage: dict, audit: dict) -> dict:
    coverage = _dan_coverage(audit)
    stimulated = [_ensemble_spikes(parent, stage, stimulate=True) for _ in range(3)]
    unstimulated = [_ensemble_spikes(parent, stage, stimulate=False) for _ in range(3)]
    weights = [cell["plastic_contact_rows"] /
               parent["circuit"]["plastic_contact_count"]
               for cell in parent["circuit"]["selected_kcs"]]
    cells = parent["circuit"]["selected_kcs"]
    slot_by_id = {int(cell["source_id"]): i for i, cell in enumerate(cells)}
    connected_slots = tuple(sorted(slot_by_id[kc] for kc in set().union(*coverage.values())))
    observation = _trial(parent, 0.70, weights)
    offset = parent["overlay"]["observation_window_us"] + parent["training"]["teacher_lag_us"]
    active_dans = set(stage["dan_source_ids"])
    active_slots = tuple(sorted(slot_by_id[kc] for dan_id in active_dans
                                if stimulated[0][dan_id]
                                for kc in coverage[dan_id]))
    active_slots = tuple(sorted(set(active_slots)))
    pulse_times = [times[0] for times in stimulated[0].values() if times]
    gate_time = min(pulse_times) if pulse_times else offset + stage["dan_stimulation"]["duration_us"]
    no_dan_rule = LocalLTD(list(weights), original_weights=weights,
                           plastic_slots=connected_slots,
                           **parent["training"]["ltd"])
    paired_rule = LocalLTD(list(weights), original_weights=weights,
                           plastic_slots=active_slots,
                           **parent["training"]["ltd"])
    for spike in observation["kc_spikes"]:
        no_dan_rule.observe_kc_spike(spike["edge_index"], spike["time_us"])
        paired_rule.observe_kc_spike(spike["edge_index"], spike["time_us"])
    no_dan_changes = no_dan_rule.teacher_pulse(gate_time, teacher=False)
    paired_changes = paired_rule.teacher_pulse(gate_time, teacher=bool(active_slots))
    criteria = {
        "each_selected_dan_activates_reliably": all(
            all(trial[dan_id] for trial in stimulated) for dan_id in stage["dan_source_ids"]),
        "unstimulated_dans_have_no_spikes": all(
            not trial[dan_id] for trial in unstimulated for dan_id in stage["dan_source_ids"]),
        "connected_dan_activity_reaches_local_gate": bool(paired_changes)
            and all(change["edge_index"] in active_slots for change in paired_changes),
        "no_dan_means_no_weight_change": not no_dan_changes
            and no_dan_rule.weights == weights,
        "all_changed_kcs_have_an_anatomically_connected_active_dan": all(
            any(stimulated[0][dan_id] and cells[change["edge_index"]]["source_id"]
                in coverage[dan_id] for dan_id in stage["dan_source_ids"])
            for change in paired_changes),
    }
    return {
        "status": "PASS" if all(criteria.values()) else "FAIL",
        "criteria": criteria,
        "stimulated_dan_spike_times_us": {
            str(dan): [trial[dan] for trial in stimulated] for dan in stage["dan_source_ids"]},
        "unstimulated_dan_spike_times_us": {
            str(dan): [trial[dan] for trial in unstimulated] for dan in stage["dan_source_ids"]},
        "probe_position": 0.70,
        "anatomically_connected_active_kc_ids": [cells[i]["source_id"] for i in active_slots],
        "paired_weight_changes": [dict(change, source_id=cells[change["edge_index"]]["source_id"])
                                  for change in paired_changes],
        "no_dan_weight_changes": list(no_dan_changes),
    }


def _stimulation_scheduled(arm: str, trial: dict) -> bool:
    if arm in ("target_region", "matched_dan_on_plasticity_off_control"):
        return trial["position_class"] == "target_region"
    if arm == "wrong_region_control":
        return trial["position_class"] == "wrong_region_distractor"
    raise ValueError(f"unknown Level 3B arm: {arm}")


def _train_arm(parent: dict, stage: dict, audit: dict, threshold: float, *, arm: str) -> dict:
    cells = parent["circuit"]["selected_kcs"]
    coverage = _dan_coverage(audit)
    initial = [cell["plastic_contact_rows"] /
               parent["circuit"]["plastic_contact_count"] for cell in cells]
    weights = list(initial)
    slot_by_id = {int(cell["source_id"]): i for i, cell in enumerate(cells)}
    dan_union = set().union(*coverage.values())
    sequence = parent["training"]["sequence"]
    spacing = parent["training"]["trial_spacing_us"]
    window = parent["overlay"]["observation_window_us"]
    lag = parent["training"]["teacher_lag_us"]
    plasticity_enabled = arm != "matched_dan_on_plasticity_off_control"
    by_block: dict[int, list[dict]] = {}
    for row in sequence:
        by_block.setdefault(row["block"], []).append(row)
    trials, block_maps = [], []
    for block in range(1, parent["training"]["blocks"] + 1):
        for scheduled in by_block[block]:
            offset = (scheduled["presentation"] - 1) * spacing
            position = scheduled["position"]
            stimulate = _stimulation_scheduled(arm, scheduled)
            dan_spikes = (_ensemble_spikes(parent, stage, stimulate=True) if stimulate
                          else {dan_id: [] for dan_id in stage["dan_source_ids"]})
            active_dans = [dan_id for dan_id, times in dan_spikes.items() if times]
            active_kcs = set().union(*(coverage[dan_id] for dan_id in active_dans)) if active_dans else set()
            active_slots = tuple(sorted(slot_by_id[kc] for kc in active_kcs)) if plasticity_enabled else ()
            rule = LocalLTD(list(weights), original_weights=initial,
                            plastic_slots=active_slots, **parent["training"]["ltd"])
            observation = _trial(parent, position, rule.weights)
            for spike in observation["kc_spikes"]:
                rule.observe_kc_spike(spike["edge_index"], offset + spike["time_us"])
            times = [offset + time for dan_id in active_dans for time in dan_spikes[dan_id]]
            gate_time = min(times) if times else offset + window + lag + stage["dan_stimulation"]["duration_us"]
            changes = rule.teacher_pulse(gate_time, teacher=bool(active_slots))
            weights = list(rule.weights)
            eligible_now = [i for i in range(len(cells)) if rule.eligibility_at(i, gate_time) > 0]
            active_kc_ids = [cells[i]["source_id"] for i in active_slots]
            trial_row = {
                "presentation": scheduled["presentation"], "block": block,
                "position": position, "position_class": scheduled["position_class"],
                "kc_activations": {str(cell["source_id"]): value
                    for cell, value in zip(cells, population_drive(
                        position, cells, sigma=parent["encoder"]["sigma"],
                        peak_drive_mv=parent["encoder"]["peak_drive_mv"]))},
                "kc_spike_counts": observation["kc_spike_counts"],
                "mbon_activity_max_voltage_mv": observation["mbon_activity_max_voltage_mv"],
                "action_before_dan_gate": observation["mbon_activity_max_voltage_mv"] <= threshold,
                "eligibility_reset_scope": "presentation_local",
                "positive_eligibility_kc_source_ids": [cells[i]["source_id"] for i in eligible_now],
                "external_stimulation_scheduled": stimulate,
                "dan_spike_times_us_relative_to_presentation": {
                    str(dan): dan_spikes[dan] for dan in stage["dan_source_ids"]},
                "active_dan_source_ids": active_dans,
                "dan_gate_kc_source_ids": active_kc_ids,
                "dan_activity_gate": int(bool(active_dans)),
                "weight_changes": [dict(change,
                    source_id=cells[change["edge_index"]]["source_id"])
                    for change in changes],
            }
            trials.append(trial_row)
        panel = _evaluate(parent, weights, threshold)
        target_lo, target_hi = parent["target_region"]["primary"]
        target_rows = [row for row in panel if target_lo <= row["position"] <= target_hi]
        block_maps.append({
            "block": block, "position_map": panel,
            "target_mean_mbon_mv": sum(r["mbon_activity_max_voltage_mv"] for r in target_rows)
                                   / len(target_rows),
            "target_action_count": sum(bool(r["action"]) for r in target_rows),
            "full_grid_action_count": sum(bool(r["action"]) for r in panel),
            "weights_after_block": list(weights),
            "weights_at_floor": [cells[i]["source_id"] for i, (w, start) in
                enumerate(zip(weights, initial)) if w <= start * parent["training"]["ltd"]["minimum_fraction"]],
        })
    stim_count = sum(row["external_stimulation_scheduled"] for row in trials)
    gate_count = sum(row["dan_activity_gate"] for row in trials)
    return {"arm": arm, "external_stimulation_count": stim_count,
            "dan_gate_event_count": gate_count, "trials": trials,
            "block_maps": block_maps, "initial_weights": initial,
            "final_weights": list(weights),
            "final_position_map": _evaluate(parent, weights, threshold)}


def run_learning(root: Path, config_path: str, capacity_path: str) -> dict:
    root = Path(root)
    stage, parent, audit, _, threshold = _load_inputs(root, config_path)
    capacity_file = root / capacity_path
    capacity = json.loads(capacity_file.read_text(encoding="utf-8"))
    if (capacity.get("capacity_status") != "PASS"
            or capacity.get("training_authorized_by_capacity_gate") is not True
            or capacity.get("config_sha256") != _sha256(root / config_path)
            or capacity.get("dan_source_ids") != list(stage["dan_source_ids"])
            or not all(capacity.get("criteria", {}).values())):
        raise ValueError("capacity gate did not PASS for this exact Level 3B config")
    pretraining = _pretraining_gate(parent, stage, audit)
    base = {
        "experiment_id": stage["experiment_id"], "step": "2_learning",
        "config": config_path, "config_sha256": _sha256(root / config_path),
        "capacity_receipt": capacity_path,
        "capacity_receipt_sha256": _sha256(capacity_file),
        "anatomy_audit_sha256": stage["anatomy_audit_sha256"],
        "parent_level2_config_sha256": stage["parent_level2_config_sha256"],
        "dan_source_ids": stage["dan_source_ids"],
        "dan_identity_by_source_id": stage["dan_identities"],
        "stimulation": stage["dan_stimulation"],
        "local_gate": stage["local_gate"],
        "frozen_action_threshold_mv": threshold,
        "encoder_sha256": _encoder_sha256(parent),
        "pretraining_gate": pretraining,
        "learning_rule_status": "ENGINEERING ASSUMPTION; inherited presentation-local LTD with per-KC OR over active anatomically connected DANs.",
        "readout": "frozen Level 2 MBON05 maximum-voltage action threshold; no trained decoder",
    }
    if pretraining["status"] != "PASS":
        return {**base, "status": "INCONCLUSIVE",
                "decision": "Ensemble stimulation or causal-gate precheck failed; learning not run."}

    initial = [cell["plastic_contact_rows"] /
               parent["circuit"]["plastic_contact_count"]
               for cell in parent["circuit"]["selected_kcs"]]
    baseline = _evaluate(parent, initial, threshold)
    target = _train_arm(parent, stage, audit, threshold, arm="target_region")
    wrong = _train_arm(parent, stage, audit, threshold, arm="wrong_region_control")
    off = _train_arm(parent, stage, audit, threshold,
                     arm="matched_dan_on_plasticity_off_control")
    arms = (target, wrong, off)
    metrics = {"target_teacher": _arm_metrics(parent, target, baseline),
               "wrong_region_teacher": _arm_metrics(parent, wrong, baseline),
               "matched_dan_on_plasticity_off": _arm_metrics(parent, off, baseline)}
    locality = {
        "target_teacher": _locality(
            target, parent["locality_evaluation"]["target_teacher"]["allowed_halo"]),
        "wrong_region_teacher": _locality(
            wrong, parent["locality_evaluation"]["wrong_region_teacher"]["allowed_halo"]),
    }
    connected_ids = set().union(*_dan_coverage(audit).values())
    result = {**base,
        "baseline_position_map": baseline,
        "target_teacher": target,
        "wrong_region_teacher": wrong,
        "matched_dan_on_plasticity_off_control": off,
        "arm_metrics": metrics,
        "arm_locality": locality,
        "learning_curves": {"target_teacher": _curve(target, parent),
                            "wrong_region_teacher": _curve(wrong, parent),
                            "matched_dan_on_plasticity_off_control": _curve(off, parent)},
        "training_blocks_completed": {arm["arm"]: len(arm["block_maps"]) for arm in arms},
        "training_presentations_completed": {arm["arm"]: len(arm["trials"]) for arm in arms},
        "weights_at_ltd_floor_final": {
            arm["arm"]: [parent["circuit"]["selected_kcs"][i]["source_id"]
                for i, (weight, start) in enumerate(zip(arm["final_weights"], arm["initial_weights"]))
                if weight <= start * parent["training"]["ltd"]["minimum_fraction"]]
            for arm in arms},
    }
    target_core = metrics["target_teacher"]["target_core_actions"]
    wrong_core = metrics["wrong_region_teacher"]["wrong_core_actions"]
    target_changes = [change for trial in target["trials"] for change in trial["weight_changes"]]
    wrong_changes = [change for trial in wrong["trials"] for change in trial["weight_changes"]]
    criteria = {
        "all_120_blocks_and_1200_presentations_per_arm": all(
            len(arm["block_maps"]) == 120 and len(arm["trials"]) == 1200 for arm in arms),
        "all_scheduled_teaching_events_activate_all_three_dans": all(
            sum(trial["external_stimulation_scheduled"]
                and len(trial["active_dan_source_ids"]) == 3 for trial in arm["trials"]) == 600
            for arm in (target, wrong, off)),
        "target_core_3_of_3": len(target_core) == 3 and all(target_core),
        "wrong_core_3_of_3": len(wrong_core) == 3 and all(wrong_core),
        "target_action_locality": locality["target_teacher"]["locality_pass"],
        "wrong_action_locality": locality["wrong_region_teacher"]["locality_pass"],
        "matched_dan_on_plasticity_off_unchanged_and_no_action": (
            off["initial_weights"] == off["final_weights"]
            and off["final_position_map"] == baseline
            and not any(row["action"] for row in off["final_position_map"])),
        "target_frozen_retention": (target["final_position_map"] == target["block_maps"][-1]["position_map"]
                                    and bool(target_core) and all(target_core)),
        "wrong_frozen_retention": (wrong["final_position_map"] == wrong["block_maps"][-1]["position_map"]
                                   and bool(wrong_core) and all(wrong_core)),
        "no_update_without_anatomically_connected_active_dan": all(
            not trial["weight_changes"] for arm in arms for trial in arm["trials"]
            if not trial["dan_gate_kc_source_ids"]),
        "all_updates_have_local_eligibility_and_connected_active_dan": all(
            change["eligibility"] > 0
            and change["source_id"] in trial["dan_gate_kc_source_ids"]
            for arm in (target, wrong) for trial in arm["trials"]
            for change in trial["weight_changes"]),
        "all_updates_within_union_anatomical_mask": all(
            change["source_id"] in connected_ids for change in target_changes + wrong_changes),
        "immutable_20_percent_floor_respected": all(
            weight + 1e-15 >= start * parent["training"]["ltd"]["minimum_fraction"]
            for arm in arms for weight, start in zip(arm["final_weights"], arm["initial_weights"])),
        "fixed_threshold_encoder_and_inherited_learning_parameters": (
            threshold == parent["continuation"]["frozen_action_threshold_mv"]
            and result["encoder_sha256"] == _encoder_sha256(parent)
            and parent["training"]["blocks"] == 120
            and parent["training"]["ltd"]["eta"] == 0.00005
            and parent["training"]["ltd"]["minimum_fraction"] == 0.20),
    }
    result["criteria"] = criteria
    result["status"] = "PASS" if all(criteria.values()) else "FAIL"
    result["decision"] = (
        "The anatomy-selected PAM08 ensemble passed the frozen Level 3B target/wrong learning contract."
        if result["status"] == "PASS" else
        "The capacity gate passed and the fixed Level 3B ensemble learning run completed, but one or more frozen criteria failed; no tuning followed.")
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--config", default=CONFIG_DEFAULT)
    parser.add_argument("--mode", choices=("capacity", "learn"), required=True)
    parser.add_argument("--capacity-receipt", default=CAPACITY_DEFAULT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.mode == "capacity":
        result = run_capacity(args.root, args.config)
        default_output = Path(CAPACITY_DEFAULT)
    else:
        result = run_learning(args.root, args.config, args.capacity_receipt)
        default_output = Path(RESULT_DEFAULT)
    output = args.output or default_output
    output = output if output.is_absolute() else args.root / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    print(json.dumps({"step": result.get("step"),
                      "status": result.get("capacity_status", result.get("status")),
                      "criteria": result.get("criteria")}, indent=2))
