"""Level 3: one real MaleCNS DAN body supplies the Level 2 local LTD gate.

The DAN's identity and γ4 contacts are measured. Its external stimulation,
LIF dynamics, binary spike-to-gate transform, and LTD are engineering overlays.
"""

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
from project_b.malecns_continuous_position_learning.probe import (
    _lif, _trial, load_config,
)
from project_b.simulation import SpikingSimulator
from project_b.synapses import SparseGraph


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_frozen_inputs(root: Path, config_path: str) -> tuple[dict, dict, dict, float]:
    stage_path = root / config_path
    stage = json.loads(stage_path.read_text(encoding="utf-8"))
    parent_path = root / stage["parent_level2_config"]
    audit_path = root / stage["anatomy_audit"]
    if _sha256(parent_path) != stage["parent_level2_config_sha256"]:
        raise ValueError("frozen Level 2 v2.5 config changed")
    if _sha256(audit_path) != stage["anatomy_audit_sha256"]:
        raise ValueError("Level 3 anatomy audit changed after bridge freeze")
    parent = load_config(root, stage["parent_level2_config"])
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if audit["status"] != "PASS":
        raise ValueError("anatomy audit did not pass")
    candidate = audit["selected_dan"]
    if (candidate["source_id"] != stage["dan_source_id"]
            or candidate["same_g4_overlap_count"] <= 0
            or audit["fixed_cohort"]["kc_source_ids"] != [
                cell["source_id"] for cell in parent["circuit"]["selected_kcs"]]):
        raise ValueError("DAN identity or cohort differs from the anatomy audit")
    if parent["training"]["blocks"] != 120 or len(parent["training"]["sequence"]) != 1200:
        raise ValueError("Level 3 must inherit the complete 120-block Level 2 schedule")
    threshold, _ = _v1_probe(root, parent)
    if threshold != parent["continuation"]["frozen_action_threshold_mv"]:
        raise ValueError("frozen Level 2 threshold changed")
    amplitude = stage["dan_stimulation"]["amplitude_mv_equivalent"]
    if not isinstance(amplitude, (int, float)) or not math.isfinite(amplitude) or amplitude <= 0:
        raise ValueError("DAN stimulation amplitude must be finite and positive")
    if stage["dan_stimulation"]["duration_us"] != 20_000:
        raise ValueError("DAN stimulation duration differs from the frozen pulse")
    revision = stage.get("pretraining_stimulus_revision")
    if revision is not None:
        original = root / revision["original_config"]
        receipt = root / revision["original_pretraining_receipt"]
        if (_sha256(original) != revision["original_config_sha256"]
                or _sha256(receipt) != revision["original_pretraining_receipt_sha256"]):
            raise ValueError("prelearning DAN stimulus revision provenance changed")
        prior = json.loads(receipt.read_text(encoding="utf-8"))
        if prior["status"] != "INCONCLUSIVE" or "target_teacher" in prior:
            raise ValueError("DAN stimulus revision followed a learning run")
    return stage, parent, audit, threshold


def _dan_spike_times(parent: dict, stage: dict, *, stimulate: bool) -> list[int]:
    """Stimulate an isolated identified DAN using the inherited LIF model."""
    stim = stage["dan_stimulation"]
    lif = parent["overlay"]["lif"]
    onset = parent["overlay"]["observation_window_us"] + parent["training"]["teacher_lag_us"]
    duration = stim["duration_us"]
    if onset % lif["dt_us"] or duration % lif["dt_us"]:
        raise ValueError("DAN pulse must align with the inherited LIF integration grid")
    simulator = SpikingSimulator(
        [_lif(parent)], SparseGraph(1, []), [0.0],
        dt_us=lif["dt_us"], record_neurons=[0], record_spikes=True)
    simulator.run_until(onset)
    if stimulate:
        simulator.set_external_drive_mv([stim["amplitude_mv_equivalent"]])
    simulator.run_until(onset + duration)
    simulator.set_external_drive_mv([0.0])
    return [spike.time_us for spike in simulator.snapshot().spikes]


def _plastic_slots(parent: dict, audit: dict) -> tuple[int, ...]:
    connected = set(audit["selected_dan"]["same_g4_overlap_kc_source_ids"])
    slots = tuple(i for i, cell in enumerate(parent["circuit"]["selected_kcs"])
                  if cell["source_id"] in connected)
    if len(slots) != audit["selected_dan"]["same_g4_overlap_count"]:
        raise ValueError("DAN-connected plastic slots differ from the anatomy audit")
    return slots


def _initial_weights(parent: dict) -> list[float]:
    cells = parent["circuit"]["selected_kcs"]
    total = sum(cell["plastic_contact_rows"] for cell in cells)
    return [cell["plastic_contact_rows"] / total for cell in cells]


def _new_rule(weights: list[float], original_weights: list[float], parent: dict,
              slots: tuple[int, ...]) -> LocalLTD:
    # Eligibility is presentation-local; the LTD floor remains anchored to the
    # immutable run-start weight vector. DAN spikes alone supply the teacher gate.
    return LocalLTD(list(weights), original_weights=original_weights,
                    plastic_slots=slots, **parent["training"]["ltd"])


def _pretraining_gate(parent: dict, stage: dict, audit: dict) -> dict:
    slots = _plastic_slots(parent, audit)
    with_stim = [_dan_spike_times(parent, stage, stimulate=True) for _ in range(3)]
    without_stim = [_dan_spike_times(parent, stage, stimulate=False) for _ in range(3)]
    weights = _initial_weights(parent)
    probe_position = 0.70
    observation = _trial(parent, probe_position, weights)
    onset = parent["overlay"]["observation_window_us"] + parent["training"]["teacher_lag_us"]
    no_dan_rule = _new_rule(weights, weights, parent, slots)
    paired_rule = _new_rule(weights, weights, parent, slots)
    for spike in observation["kc_spikes"]:
        no_dan_rule.observe_kc_spike(spike["edge_index"], spike["time_us"])
        paired_rule.observe_kc_spike(spike["edge_index"], spike["time_us"])
    no_dan_changes = no_dan_rule.teacher_pulse(
        onset + stage["dan_stimulation"]["duration_us"], teacher=bool(without_stim[0]))
    paired_spikes = with_stim[0]
    paired_gate_time = paired_spikes[0] if paired_spikes else onset + stage["dan_stimulation"]["duration_us"]
    paired_eligibility = {
        str(parent["circuit"]["selected_kcs"][slot]["source_id"]):
            paired_rule.eligibility_at(slot, paired_gate_time)
        for slot in slots
    }
    paired_changes = paired_rule.teacher_pulse(
        paired_gate_time, teacher=bool(paired_spikes))
    criteria = {
        "fixed_external_stimulation_reliably_activates_dan": all(with_stim),
        "unstimulated_dan_has_no_spikes": all(not trial for trial in without_stim),
        "observed_dan_activity_reaches_local_gate": (
            bool(paired_spikes) and any(value > 0 for value in paired_eligibility.values())
            and bool(paired_changes)),
        "no_kc_to_mbon05_weight_changes_without_dan_activity": (
            not no_dan_changes and no_dan_rule.weights == weights),
        "only_anatomically_reached_slots_can_change": all(
            change["edge_index"] in slots for change in paired_changes),
    }
    return {
        "status": "PASS" if all(criteria.values()) else "FAIL",
        "criteria": criteria,
        "probe_position": probe_position,
        "stimulated_dan_spike_times_us": with_stim,
        "unstimulated_dan_spike_times_us": without_stim,
        "kc_spike_count": len(observation["kc_spikes"]),
        "dan_connected_plastic_slots": list(slots),
        "paired_eligibility": paired_eligibility,
        "paired_weight_changes": [dict(change) for change in paired_changes],
        "no_dan_weight_changes": [dict(change) for change in no_dan_changes],
    }


def _scheduled_stimulation(policy: str, scheduled: dict) -> bool:
    if policy == "target_region":
        return scheduled["position_class"] == "target_region"
    if policy == "wrong_region":
        return scheduled["position_class"] == "wrong_region_distractor"
    if policy == "off":
        return False
    raise ValueError(f"unknown inherited teacher policy: {policy}")


def _train_arm(parent: dict, stage: dict, audit: dict, threshold: float, *, arm: str) -> dict:
    cells = parent["circuit"]["selected_kcs"]
    slots = _plastic_slots(parent, audit)
    initial = _initial_weights(parent)
    weights = list(initial)
    sequence = parent["training"]["sequence"]
    spacing = parent["training"]["trial_spacing_us"]
    window = parent["overlay"]["observation_window_us"]
    lag = parent["training"]["teacher_lag_us"]
    policy = parent["training"]["teacher_policy"][arm]
    by_block: dict[int, list[dict]] = {}
    for row in sequence:
        by_block.setdefault(row["block"], []).append(row)
    trials = []
    block_maps = []
    for block in range(1, parent["training"]["blocks"] + 1):
        for scheduled in by_block[block]:
            offset = (scheduled["presentation"] - 1) * spacing
            position = scheduled["position"]
            rule = _new_rule(weights, initial, parent, slots)
            observation = _trial(parent, position, rule.weights)
            for spike in observation["kc_spikes"]:
                rule.observe_kc_spike(spike["edge_index"], offset + spike["time_us"])
            stimulation_scheduled = _scheduled_stimulation(policy, scheduled)
            dan_spikes = (_dan_spike_times(parent, stage, stimulate=True)
                          if stimulation_scheduled else [])
            gate_time = (offset + dan_spikes[0] if dan_spikes else
                         offset + window + lag + stage["dan_stimulation"]["duration_us"])
            eligibility = {str(cell["source_id"]): rule.eligibility_at(i, gate_time)
                           for i, cell in enumerate(cells)}
            # This is the only write to KC→MBON05 weights. The inherited local
            # rule sees the observed DAN spike state, never the task policy bit.
            changes = rule.teacher_pulse(gate_time, teacher=bool(dan_spikes))
            weights = list(rule.weights)
            trials.append({
                "presentation": scheduled["presentation"],
                "block": block,
                "position": position,
                "position_class": scheduled["position_class"],
                "kc_activations": {str(cell["source_id"]): drive
                    for cell, drive in zip(cells, population_drive(
                        position, cells, sigma=parent["encoder"]["sigma"],
                        peak_drive_mv=parent["encoder"]["peak_drive_mv"]))},
                "kc_spike_counts": observation["kc_spike_counts"],
                "mbon_activity_max_voltage_mv": observation["mbon_activity_max_voltage_mv"],
                "action_before_stimulation": observation["mbon_activity_max_voltage_mv"] <= threshold,
                "eligibility_at_dan_gate": eligibility,
                "eligibility_reset_scope": "presentation_local",
                "external_stimulation_scheduled": stimulation_scheduled,
                "dan_source_id": stage["dan_source_id"],
                "dan_spike_times_us_relative_to_presentation": dan_spikes,
                "dan_activity_gate": int(bool(dan_spikes)),
                "dan_gate_time_us": gate_time,
                "weight_changes": [dict(change, source_id=cells[change["edge_index"]]["source_id"])
                                   for change in changes],
            })
        panel = _evaluate(parent, weights, threshold)
        target_lo, target_hi = parent["target_region"]["primary"]
        target_rows = [row for row in panel if target_lo <= row["position"] <= target_hi]
        block_maps.append({
            "block": block,
            "position_map": panel,
            "target_mean_mbon_mv": sum(r["mbon_activity_max_voltage_mv"]
                                        for r in target_rows) / len(target_rows),
            "target_action_count": sum(bool(r["action"]) for r in target_rows),
            "full_grid_action_count": sum(bool(r["action"]) for r in panel),
            "weights_after_block": list(weights),
            "weights_at_floor": [cells[i]["source_id"] for i, (weight, start) in
                                 enumerate(zip(weights, initial))
                                 if weight <= start * parent["training"]["ltd"]["minimum_fraction"]],
        })
    return {
        "arm": arm,
        "external_stimulation_count": sum(row["external_stimulation_scheduled"] for row in trials),
        "dan_gate_event_count": sum(row["dan_activity_gate"] for row in trials),
        "trials": trials,
        "block_maps": block_maps,
        "initial_weights": initial,
        "final_weights": list(weights),
        "final_position_map": _evaluate(parent, weights, threshold),
    }


def run_experiment(root: Path, config_path: str) -> dict:
    root = Path(root)
    stage, parent, audit, threshold = _load_frozen_inputs(root, config_path)
    pretraining = _pretraining_gate(parent, stage, audit)
    result = {
        "experiment_id": stage["experiment_id"],
        "stage": "level3_dan_bridge",
        "config": config_path,
        "config_sha256": _sha256(root / config_path),
        "parent_level2_config_sha256": stage["parent_level2_config_sha256"],
        "anatomy_audit_sha256": stage["anatomy_audit_sha256"],
        "level2_status_record": audit["level2_status_record"],
        "dan_source_id": stage["dan_source_id"],
        "dan_identity": audit["selected_dan"],
        "stimulation": stage["dan_stimulation"],
        "anatomical_plastic_kc_source_ids": audit["selected_dan"]["same_g4_overlap_kc_source_ids"],
        "frozen_action_threshold_mv": threshold,
        "encoder_sha256": _encoder_sha256(parent),
        "pretraining_gate": pretraining,
        "learning_rule_status": "ENGINEERING ASSUMPTION; inherited presentation-local LTD and parameters",
        "readout": "frozen Level 2 MBON05 maximum-voltage action threshold; no trained decoder",
    }
    if pretraining["status"] != "PASS":
        result["status"] = "INCONCLUSIVE"
        result["decision"] = "Pretraining DAN activation or causal gate failed; learning not run."
        return result

    initial = _initial_weights(parent)
    baseline = _evaluate(parent, initial, threshold)
    target = _train_arm(parent, stage, audit, threshold, arm="primary")
    off = _train_arm(parent, stage, audit, threshold, arm="plasticity_off_control")
    wrong = _train_arm(parent, stage, audit, threshold, arm="wrong_region_control")
    arms = (target, off, wrong)
    metrics = {
        "target_teacher": _arm_metrics(parent, target, baseline),
        "plasticity_off": _arm_metrics(parent, off, baseline),
        "wrong_region_teacher": _arm_metrics(parent, wrong, baseline),
    }
    locality = {
        "target_teacher": _locality(
            target, parent["locality_evaluation"]["target_teacher"]["allowed_halo"]),
        "wrong_region_teacher": _locality(
            wrong, parent["locality_evaluation"]["wrong_region_teacher"]["allowed_halo"]),
    }
    result.update({
        "baseline_position_map": baseline,
        "target_teacher": target,
        "plasticity_off_control": off,
        "wrong_region_teacher": wrong,
        "arm_metrics": metrics,
        "arm_locality": locality,
        "learning_curves": {
            "target_teacher": _curve(target, parent),
            "plasticity_off_control": _curve(off, parent),
            "wrong_region_teacher": _curve(wrong, parent),
        },
        "weights_at_ltd_floor_final": {
            arm["arm"]: [parent["circuit"]["selected_kcs"][i]["source_id"]
                         for i, (weight, start) in enumerate(zip(
                             arm["final_weights"], arm["initial_weights"]))
                         if weight <= start * parent["training"]["ltd"]["minimum_fraction"]]
            for arm in arms
        },
        "training_blocks_completed": {arm["arm"]: len(arm["block_maps"]) for arm in arms},
        "training_presentations_completed": {arm["arm"]: len(arm["trials"]) for arm in arms},
    })
    target_core = metrics["target_teacher"]["target_core_actions"]
    wrong_core = metrics["wrong_region_teacher"]["wrong_core_actions"]
    connected = set(result["anatomical_plastic_kc_source_ids"])
    criteria = {
        "all_120_blocks_and_1200_presentations_completed": all(
            len(arm["block_maps"]) == 120 and len(arm["trials"]) == 1200 for arm in arms),
        "all_scheduled_events_activated_real_dan": (
            target["external_stimulation_count"] == target["dan_gate_event_count"] == 600
            and wrong["external_stimulation_count"] == wrong["dan_gate_event_count"] == 600),
        "no_off_arm_dan_events": off["external_stimulation_count"] == off["dan_gate_event_count"] == 0,
        "target_core_3_of_3_action": bool(target_core) and all(target_core),
        "wrong_core_3_of_3_action": bool(wrong_core) and all(wrong_core),
        "wrong_region_shift_away_from_target": not any(
            metrics["wrong_region_teacher"]["target_core_actions"]),
        "plasticity_off_unchanged_and_no_action": (
            off["initial_weights"] == off["final_weights"]
            and off["final_position_map"] == baseline
            and not any(row["action"] for row in off["final_position_map"])),
        "target_action_locality": locality["target_teacher"]["locality_pass"],
        "wrong_action_locality": locality["wrong_region_teacher"]["locality_pass"],
        "target_frozen_retention": (
            target["final_position_map"] == target["block_maps"][-1]["position_map"]
            and bool(target_core) and all(target_core)),
        "wrong_frozen_retention": (
            wrong["final_position_map"] == wrong["block_maps"][-1]["position_map"]
            and bool(wrong_core) and all(wrong_core)),
        "no_update_without_dan_spike": all(
            not row["weight_changes"] for arm in arms for row in arm["trials"]
            if row["dan_activity_gate"] == 0),
        "all_updates_anatomically_reached": all(
            change["source_id"] in connected
            for arm in arms for row in arm["trials"] for change in row["weight_changes"]),
        "fixed_threshold_encoder_and_level2_parameters": (
            result["frozen_action_threshold_mv"] ==
            parent["continuation"]["frozen_action_threshold_mv"]
            and result["encoder_sha256"] == _encoder_sha256(parent)
            and _sha256(root / stage["parent_level2_config"]) ==
            stage["parent_level2_config_sha256"]),
    }
    result["criteria"] = criteria
    result["status"] = "PASS" if all(criteria.values()) else "FAIL"
    result["decision"] = (
        "A single anatomically associated MaleCNS PAM08 DAN supplied activity to the local engineering LTD gate and the frozen Level 2 action-map contract passed."
        if result["status"] == "PASS" else
        "DAN activation and causal gating passed, but the frozen Level 3 learning contract failed; no Level 2 parameter tuning followed.")
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--config", default="configs/malecns_dan_bridge_level3.json")
    parser.add_argument("--output", type=Path,
                        default=Path("runs/malecns_dan_bridge_level3/result.json"))
    args = parser.parse_args()
    result = run_experiment(args.root, args.config)
    output = args.output if args.output.is_absolute() else args.root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "pretraining_gate": result["pretraining_gate"]["criteria"],
        "criteria": result.get("criteria"),
    }, indent=2))
