"""Run the frozen L1R-E pre-training controllability family."""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import sys
from collections import deque
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from project_b.neurons import LIFParameters
from project_b.simulation import SpikingSimulator
from project_b.synapses import SparseGraph, Synapse


MANIFEST_PATH = ROOT / "configs/larval_l1re_manifest_v1.json"
POLICY_PATH = ROOT / "configs/larval_l1re_electrical_family_v1_policy.json"
OUTPUT_PATH = ROOT / "runs/larval_l1re_controllability_family_v1.json"
NOMINAL_PATH = ROOT / "configs/larval_l1re_electrical_v1.json"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(payload)


def make_groups(kc_ids: list[int], count: int) -> list[list[int]]:
    base, remainder = divmod(len(kc_ids), count)
    groups: list[list[int]] = []
    cursor = 0
    for group_index in range(count):
        size = base + int(group_index < remainder)
        groups.append(kc_ids[cursor:cursor + size])
        cursor += size
    if cursor != len(kc_ids) or len({x for group in groups for x in group}) != len(kc_ids):
        raise AssertionError("KC group construction lost or duplicated a source ID")
    return groups


def run_one(
    manifest: dict,
    policy: dict,
    config: dict,
    factor: float,
    state: int | None,
) -> dict:
    nodes = manifest["nodes"]
    source_ids = [int(node["source_id"]) for node in nodes]
    index = {source_id: i for i, source_id in enumerate(source_ids)}
    kc_ids = sorted(int(node["source_id"]) for node in nodes if node["role"] == "KC")
    mbon_ids = sorted(int(node["source_id"]) for node in nodes if node["role"] == "MBON-m1")
    groups = make_groups(kc_ids, int(policy["encoder"]["state_count"]))

    delay_us = int(policy["synapse_model"]["delay_us"])
    edges = [
        Synapse(
            index[int(row["pre_id"])],
            index[int(row["post_id"])],
            int(row["contacts"]) * float(config["contact_effect_mv_per_contact"]) * factor,
            delay_us,
        )
        for row in manifest["edges"]
    ]
    graph = SparseGraph(len(nodes), edges)
    params = [
        LIFParameters(
            v_rest_mv=0.0,
            v_reset_mv=0.0,
            v_threshold_mv=float(config["threshold_mv"]),
            tau_m_us=int(config["tau_m_us"]),
            tau_syn_us=int(policy["neuron_model"]["tau_syn_us"]),
            refractory_us=int(policy["neuron_model"]["refractory_us"]),
        )
        for _ in nodes
    ]
    drive = [0.0] * len(nodes)
    intended_kcs: list[int] = []
    if state is not None:
        intended_kcs = groups[state]
        for source_id in intended_kcs:
            drive[index[source_id]] = float(config["pulse_mv"])
    mbon_indices = [index[source_id] for source_id in mbon_ids]
    simulator = SpikingSimulator(
        params,
        graph,
        drive,
        dt_us=int(policy["integration"]["dt_us"]),
        record_neurons=mbon_indices,
        record_spikes=True,
        max_queued_events=int(policy["integration"]["max_queued_events"]),
        max_scheduled_events=int(policy["integration"]["max_scheduled_events"]),
    )
    pulse_us = int(policy["encoder"]["pulse_duration_us"])
    duration_us = int(policy["integration"]["response_window_us"])
    if state is not None:
        simulator.run_until(pulse_us)
        simulator.set_external_drive_mv([0.0] * len(nodes))
    snapshot = simulator.run_until(duration_us)
    diagnostics = simulator.diagnostics()

    spikes_by_source = {str(source_ids[i]): int(value) for i, value in enumerate(snapshot.spike_counts) if value}
    intended_counts = {str(source_id): int(snapshot.spike_counts[index[source_id]]) for source_id in intended_kcs}
    mbon_counts = {str(source_id): int(snapshot.spike_counts[index[source_id]]) for source_id in mbon_ids}
    mbon_total = sum(mbon_counts.values())
    trace = [sample for sample in snapshot.voltage_trace if sample.time_us > 0]
    finite = (
        all(math.isfinite(value) for value in snapshot.voltage_mv)
        and all(math.isfinite(value) for value in snapshot.synaptic_drive_mv)
        and all(math.isfinite(sample.voltage_before_reset_mv) for sample in trace)
        and all(math.isfinite(sample.synaptic_drive_mv) for sample in trace)
    )
    actions = {
        str(threshold): bool(state is not None and mbon_total <= int(threshold))
        for threshold in policy["readout"]["thresholds_in_spikes"]
    }
    digest_payload = {
        "state": state,
        "factor": factor,
        "spikes": [
            [event.time_us, source_ids[event.neuron_index], event.voltage_before_reset_mv.hex()]
            for event in snapshot.spikes
        ],
        "final_voltage": [value.hex() for value in snapshot.voltage_mv],
        "final_synaptic_drive": [value.hex() for value in snapshot.synaptic_drive_mv],
        "events": [
            diagnostics.scheduled_events,
            diagnostics.delivered_events,
            diagnostics.peak_queued_events,
            snapshot.queued_arrivals,
        ],
        "actions": actions,
    }
    return {
        "state": state,
        "weight_factor": factor,
        "intended_kc_source_ids": intended_kcs,
        "intended_kc_spikes_by_source_id": intended_counts,
        "all_intended_kcs_activated": bool(intended_kcs) and all(value > 0 for value in intended_counts.values()),
        "spikes_by_source_id_nonzero": spikes_by_source,
        "mbon_m1_spikes_by_source_id": mbon_counts,
        "bilateral_mbon_m1_spike_count": mbon_total,
        "actions_by_threshold": actions,
        "interface_armed": state is not None,
        "mbon_voltage_summary": {
            "maximum_pre_reset_mv": max((sample.voltage_before_reset_mv for sample in trace), default=0.0),
            "minimum_pre_reset_mv": min((sample.voltage_before_reset_mv for sample in trace), default=0.0),
            "maximum_synaptic_drive_mv": max((sample.synaptic_drive_mv for sample in trace), default=0.0),
        },
        "events": {
            "scheduled": diagnostics.scheduled_events,
            "delivered": diagnostics.delivered_events,
            "peak_queued": diagnostics.peak_queued_events,
            "queued_at_end": snapshot.queued_arrivals,
            "max_spikes_one_tick": max(diagnostics.spike_counts_by_tick, default=0),
        },
        "numerical": {
            "finite": finite,
            "queue_within_bound": diagnostics.peak_queued_events <= int(policy["integration"]["max_queued_events"]),
            "scheduled_within_bound": diagnostics.scheduled_events <= int(policy["integration"]["max_scheduled_events"]),
        },
        "replay_digest": canonical_digest(digest_payload),
    }


def threshold_transition_qualifies(rows_by_factor: dict[float, dict[int, dict]], threshold: int) -> tuple[bool, dict]:
    factors = [1.0, 0.8, 0.6, 0.4, 0.2]
    action_sets = {
        factor: {state for state, row in rows_by_factor[factor].items()
                 if row["actions_by_threshold"][str(threshold)]}
        for factor in factors
    }
    nested = all(action_sets[left].issubset(action_sets[right]) for left, right in zip(factors, factors[1:]))
    transitions = {
        state for state in range(8)
        if state not in action_sets[1.0]
        and any(state in action_sets[factor] for factor in factors[1:])
    }
    low_count = len(action_sets[0.2])
    qualifies = nested and len(transitions) >= 3 and 2 <= low_count <= 6
    return qualifies, {
        "threshold": threshold,
        "action_states_by_factor": {str(factor): sorted(action_sets[factor]) for factor in factors},
        "nested": nested,
        "transition_states": sorted(transitions),
        "factor_0.2_action_state_count": low_count,
        "qualifies": qualifies,
    }


def evaluate_configuration(config: dict, baseline: dict, measurements: list[dict], policy: dict) -> dict:
    rows_by_factor: dict[float, dict[int, dict]] = {factor: {} for factor in (1.0, 0.8, 0.6, 0.4, 0.2)}
    for row in measurements:
        rows_by_factor[float(row["weight_factor"])][int(row["state"])] = row

    zero_ok = (
        not baseline["spikes_by_source_id_nonzero"]
        and not baseline["interface_armed"]
        and not any(baseline["actions_by_threshold"].values())
        and all(baseline["numerical"].values())
    )
    replay_ok = all(row["deterministic_replay_match"] for row in measurements)
    finite_ok = all(all(row["numerical"].values()) for row in measurements)
    cues_ok = all(row["all_intended_kcs_activated"] for row in measurements)
    full_active_states = [
        state for state, row in rows_by_factor[1.0].items()
        if row["bilateral_mbon_m1_spike_count"] >= 1
    ]
    reduction_states = []
    monotone_states = []
    reversal_over_one_states = []
    for state in range(8):
        counts = [rows_by_factor[factor][state]["bilateral_mbon_m1_spike_count"]
                  for factor in (1.0, 0.8, 0.6, 0.4, 0.2)]
        if counts[0] > 0 and (counts[0] - counts[-1]) / counts[0] >= 0.30:
            reduction_states.append(state)
        if all(left >= right for left, right in zip(counts, counts[1:])):
            monotone_states.append(state)
        if any(right - left > 1 for left, right in zip(counts, counts[1:])):
            reversal_over_one_states.append(state)

    transition_reports = {}
    qualifying_thresholds = []
    for raw_threshold in policy["readout"]["thresholds_in_spikes"]:
        threshold = int(raw_threshold)
        qualifies, report = threshold_transition_qualifies(rows_by_factor, threshold)
        transition_reports[str(threshold)] = report
        if qualifies:
            qualifying_thresholds.append(threshold)
    robust_adjacent_thresholds = [
        threshold for threshold in qualifying_thresholds
        if any(abs(threshold - other) == 1 for other in qualifying_thresholds)
    ]

    checks = {
        "zero_drive_silent_disarmed_finite_bounded": zero_ok,
        "all_replays_exact": replay_ok,
        "all_driven_states_finite_bounded": finite_ok,
        "all_cues_activate_every_intended_KC": cues_ok,
        "full_weight_active_in_at_least_6_states": len(full_active_states) >= 6,
        "at_least_30_percent_reduction_in_at_least_6_states": len(reduction_states) >= 6,
        "monotone_in_at_least_7_states": len(monotone_states) >= 7,
        "no_reversal_larger_than_one_spike": not reversal_over_one_states,
        "at_least_one_action_threshold_qualifies": bool(qualifying_thresholds),
    }
    qualifies = all(checks.values())
    return {
        "config_id": config["config_id"],
        "coordinates": config["coordinates"],
        "values": {key: value for key, value in config.items() if key not in ("coordinates",)},
        "qualifies": qualifies,
        "checks": checks,
        "full_weight_active_states": full_active_states,
        "reduction_at_least_30_percent_states": reduction_states,
        "monotone_states": monotone_states,
        "reversal_over_one_spike_states": reversal_over_one_states,
        "action_threshold_reports": transition_reports,
        "qualifying_action_thresholds": qualifying_thresholds,
        "robust_at_adjacent_action_threshold": bool(robust_adjacent_thresholds),
        "robust_adjacent_qualifying_thresholds": robust_adjacent_thresholds,
    }


def largest_components(qualifiers: list[dict]) -> list[list[str]]:
    by_coord = {tuple(row["coordinates"]): row["config_id"] for row in qualifiers}
    unseen = set(by_coord)
    components: list[list[str]] = []
    while unseen:
        start = min(unseen)
        unseen.remove(start)
        queue = deque([start])
        component: list[str] = []
        while queue:
            current = queue.popleft()
            component.append(by_coord[current])
            for axis in range(4):
                for delta in (-1, 1):
                    neighbor = list(current)
                    neighbor[axis] += delta
                    neighbor_tuple = tuple(neighbor)
                    if neighbor_tuple in unseen:
                        unseen.remove(neighbor_tuple)
                        queue.append(neighbor_tuple)
        components.append(sorted(component))
    return sorted(components, key=lambda rows: (-len(rows), rows))


def select_nominal(component: list[str], evaluations: dict[str, dict], configs: dict[str, dict]) -> dict:
    rows = [configs[config_id] for config_id in component]
    target = []
    for axis in range(4):
        values = sorted(row["coordinates"][axis] for row in rows)
        target.append(values[(len(values) - 1) // 2])
    selected = min(
        rows,
        key=lambda row: (
            sum(abs(row["coordinates"][axis] - target[axis]) for axis in range(4)),
            row["contact_effect_mv_per_contact"],
            row["pulse_mv"],
            row["tau_m_us"],
            row["threshold_mv"],
            row["config_id"],
        ),
    )
    return {
        "target_coordinate_medians_lower_on_even_tie": target,
        "selected_config_id": selected["config_id"],
        "selected_values": {key: value for key, value in selected.items() if key != "coordinates"},
        "selected_coordinates": selected["coordinates"],
        "qualifying_action_thresholds": evaluations[selected["config_id"]]["qualifying_action_thresholds"],
    }


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    if policy["status"] != "FROZEN_BEFORE_SIMULATION":
        raise RuntimeError("family policy is not frozen")
    manifest_hash = sha256(MANIFEST_PATH)
    if manifest_hash != policy["manifest"]["sha256"]:
        raise RuntimeError(f"manifest hash mismatch: {manifest_hash}")
    policy_hash = sha256(POLICY_PATH)

    axes = (
        policy["synapse_model"]["KC_to_MBON-m1_contact_effect_mv_equivalent"],
        policy["neuron_model"]["tau_m_us"],
        policy["neuron_model"]["threshold_above_rest_mv_equivalent"],
        policy["encoder"]["pulse_mv_equivalent"],
    )
    configs = []
    for ordinal, (coordinates, values) in enumerate(zip(
        itertools.product(*(range(len(axis)) for axis in axes)),
        itertools.product(*axes),
    )):
        contact, tau_m, threshold, pulse = values
        configs.append({
            "config_id": f"L1RE-{ordinal:02d}",
            "coordinates": list(coordinates),
            "contact_effect_mv_per_contact": float(contact),
            "tau_m_us": int(tau_m),
            "threshold_mv": float(threshold),
            "pulse_mv": float(pulse),
        })
    if len(configs) != int(policy["family"]["configuration_count"]):
        raise RuntimeError("resolved family size differs from frozen policy")

    all_runs: list[dict] = []
    evaluations: list[dict] = []
    factors = [float(value) for value in policy["controllability_intervention"]["KC_to_MBON-m1_weight_factors"]]
    for config in configs:
        baseline = run_one(manifest, policy, config, 1.0, None)
        measurements = []
        for factor in factors:
            for state in range(int(policy["encoder"]["state_count"])):
                first = run_one(manifest, policy, config, factor, state)
                second = run_one(manifest, policy, config, factor, state)
                first["second_replay_digest"] = second["replay_digest"]
                first["deterministic_replay_match"] = first["replay_digest"] == second["replay_digest"]
                measurements.append(first)
        evaluation = evaluate_configuration(config, baseline, measurements, policy)
        evaluations.append(evaluation)
        all_runs.append({
            "config_id": config["config_id"],
            "values": config,
            "zero_drive_baseline": baseline,
            "measurements": measurements,
        })
        print(f"{config['config_id']}: {'QUALIFY' if evaluation['qualifies'] else 'no'}", flush=True)

    qualifiers = [row for row in evaluations if row["qualifies"]]
    qualifier_ids = {row["config_id"] for row in qualifiers}
    axis_spans = []
    for axis in range(4):
        axis_spans.append(sorted({row["coordinates"][axis] for row in qualifiers}))
    components = largest_components(qualifiers)
    largest = components[0] if components else []
    evaluation_by_id = {row["config_id"]: row for row in evaluations}
    config_by_id = {row["config_id"]: row for row in configs}
    robust_in_largest = [
        config_id for config_id in largest
        if evaluation_by_id[config_id]["robust_at_adjacent_action_threshold"]
    ]
    family_checks = {
        "at_least_12_qualifiers": len(qualifiers) >= 12,
        "at_least_two_values_on_every_axis": all(len(span) >= 2 for span in axis_spans),
        "largest_face_connected_component_at_least_8": len(largest) >= 8,
        "at_least_6_component_members_robust_at_adjacent_threshold": len(robust_in_largest) >= 6,
    }
    family_pass = all(family_checks.values())
    status = "PASS" if family_pass else "FAIL"
    nominal = select_nominal(largest, evaluation_by_id, config_by_id) if family_pass else None

    result = {
        "experiment_id": "larval_l1re_controllability_family_v1",
        "variant": "L1R-E",
        "status": status,
        "frozen_inputs": {
            "manifest_path": str(MANIFEST_PATH.relative_to(ROOT)),
            "manifest_sha256": manifest_hash,
            "policy_path": str(POLICY_PATH.relative_to(ROOT)),
            "policy_sha256": policy_hash,
            "teacher_enabled": False,
            "plasticity_enabled": False,
            "training_enabled": False,
            "only_intervention": "uniform KC -> MBON-m1 weight factor",
        },
        "resolved_family": configs,
        "configuration_evaluations": evaluations,
        "family_evaluation": {
            "checks": family_checks,
            "qualifying_configuration_count": len(qualifiers),
            "qualifying_config_ids": sorted(qualifier_ids),
            "qualifying_axis_index_spans": axis_spans,
            "face_connected_components": components,
            "largest_component": largest,
            "largest_component_size": len(largest),
            "robust_adjacent_threshold_members_in_largest": robust_in_largest,
            "nominal_selection": nominal,
        },
        "runs": all_runs,
        "interpretation": (
            "Engineering-assumption pre-training controllability only. This result does not establish "
            "fly physiology, a dopamine pathway, a plasticity mechanism, or learning."
        ),
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    if family_pass:
        selected = config_by_id[nominal["selected_config_id"]]
        nominal_model = {
            "model_id": "larval_l1re_electrical_v1",
            "variant": "L1R-E",
            "status": "FROZEN_AFTER_PREDECLARED_CONTROLLABILITY_PASS",
            "manifest_sha256": manifest_hash,
            "family_policy_sha256": policy_hash,
            "controllability_result_sha256": sha256(OUTPUT_PATH),
            "selection_rule": policy["family_pass_rule"]["nominal_selection"],
            "selected_configuration": selected,
            "selected_action_threshold_spikes": min(nominal["qualifying_action_thresholds"]),
            "teacher": "artificial local port; inactive in this model gate",
            "evidence_category": "ENGINEERING ASSUMPTION",
        }
        NOMINAL_PATH.write_text(json.dumps(nominal_model, indent=2) + "\n", encoding="utf-8")
    elif NOMINAL_PATH.exists():
        raise RuntimeError("FAIL result must not overwrite or leave a nominal L1R-E model")

    print(json.dumps({
        "status": status,
        "policy_sha256": policy_hash,
        "result_sha256": sha256(OUTPUT_PATH),
        "qualifying_configurations": len(qualifiers),
        "largest_component_size": len(largest),
        "robust_members_in_largest": len(robust_in_largest),
        "family_checks": family_checks,
        "nominal": nominal,
    }, indent=2))


if __name__ == "__main__":
    main()
