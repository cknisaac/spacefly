"""Run the frozen L1R-E v2 engineering-refinement family."""

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
sys.path.insert(0, str(ROOT / "scripts"))

from project_b.neurons import LIFParameters
from project_b.simulation import SpikingSimulator
from project_b.synapses import SparseGraph, Synapse
from run_larval_l1re_controllability_family import (
    canonical_digest,
    evaluate_configuration,
    make_groups,
)


MANIFEST_PATH = ROOT / "configs/larval_l1re_manifest_v1.json"
POLICY_PATH = ROOT / "configs/larval_l1re_electrical_family_v2_policy.json"
V1_RESULT_PATH = ROOT / "runs/larval_l1re_controllability_family_v1.json"
OUTPUT_PATH = ROOT / "runs/larval_l1re_controllability_family_v2.json"
NOMINAL_PATH = ROOT / "configs/larval_l1re_electrical_v2.json"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def run_one(manifest: dict, policy: dict, config: dict, factor: float, state: int | None) -> dict:
    nodes = manifest["nodes"]
    source_ids = [int(node["source_id"]) for node in nodes]
    index = {source_id: i for i, source_id in enumerate(source_ids)}
    roles = {int(node["source_id"]): node["role"] for node in nodes}
    kc_ids = sorted(source_id for source_id in source_ids if roles[source_id] == "KC")
    mbon_ids = sorted(source_id for source_id in source_ids if roles[source_id] == "MBON-m1")
    groups = make_groups(kc_ids, int(policy["encoder"]["state_count"]))

    graph = SparseGraph(len(nodes), [
        Synapse(
            index[int(row["pre_id"])],
            index[int(row["post_id"])],
            int(row["contacts"]) * float(config["contact_effect_mv_per_contact"]) * factor,
            int(policy["synapse_model"]["delay_us"]),
        )
        for row in manifest["edges"]
    ])
    kc_model = policy["kc_neuron_model"]
    mbon_model = policy["mbon_neuron_model"]
    params = []
    for source_id in source_ids:
        if roles[source_id] == "KC":
            model = kc_model
            tau_m = int(kc_model["tau_m_us"])
            threshold = float(kc_model["threshold_above_rest_mv_equivalent"])
        else:
            model = mbon_model
            tau_m = int(config["mbon_tau_m_us"])
            threshold = float(config["mbon_threshold_mv"])
        params.append(LIFParameters(
            v_rest_mv=float(model["v_rest_mv_equivalent"]),
            v_reset_mv=float(model["v_reset_mv_equivalent"]),
            v_threshold_mv=threshold,
            tau_m_us=tau_m,
            tau_syn_us=int(model["tau_syn_us"]),
            refractory_us=int(model["refractory_us"]),
        ))

    drive = [0.0] * len(nodes)
    for source_id in mbon_ids:
        drive[index[source_id]] = float(mbon_model["tonic_drive_mv_equivalent"])
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
    if state is not None:
        simulator.run_until(pulse_us)
        future_drive = [0.0] * len(nodes)
        for source_id in mbon_ids:
            future_drive[index[source_id]] = float(mbon_model["tonic_drive_mv_equivalent"])
        simulator.set_external_drive_mv(future_drive)
    snapshot = simulator.run_until(int(config["response_window_us"]))
    diagnostics = simulator.diagnostics()

    spikes_by_source = {
        str(source_ids[i]): int(value)
        for i, value in enumerate(snapshot.spike_counts)
        if value
    }
    intended_counts = {
        str(source_id): int(snapshot.spike_counts[index[source_id]])
        for source_id in intended_kcs
    }
    mbon_counts = {
        str(source_id): int(snapshot.spike_counts[index[source_id]])
        for source_id in mbon_ids
    }
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


def face_components(qualifiers: list[dict], axis_count: int) -> list[list[str]]:
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
            for axis in range(axis_count):
                for delta in (-1, 1):
                    neighbor = list(current)
                    neighbor[axis] += delta
                    candidate = tuple(neighbor)
                    if candidate in unseen:
                        unseen.remove(candidate)
                        queue.append(candidate)
        components.append(sorted(component))
    return sorted(components, key=lambda rows: (-len(rows), rows))


def select_nominal(component: list[str], evaluations: dict[str, dict], configs: dict[str, dict]) -> dict:
    rows = [configs[config_id] for config_id in component]
    axis_count = len(rows[0]["coordinates"])
    target = []
    for axis in range(axis_count):
        values = sorted(row["coordinates"][axis] for row in rows)
        target.append(values[(len(values) - 1) // 2])
    selected = min(
        rows,
        key=lambda row: (
            sum(abs(row["coordinates"][axis] - target[axis]) for axis in range(axis_count)),
            row["contact_effect_mv_per_contact"],
            row["pulse_mv"],
            row["response_window_us"],
            row["mbon_tau_m_us"],
            row["mbon_threshold_mv"],
            row["config_id"],
        ),
    )
    return {
        "target_coordinate_medians_lower_on_even_tie": target,
        "selected_config_id": selected["config_id"],
        "selected_configuration": selected,
        "qualifying_action_thresholds": evaluations[selected["config_id"]]["qualifying_action_thresholds"],
    }


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    if policy["status"] != "FROZEN_BEFORE_SIMULATION":
        raise RuntimeError("v2 policy is not frozen")
    if sha256(MANIFEST_PATH) != policy["manifest"]["sha256"]:
        raise RuntimeError("manifest hash mismatch")
    if sha256(V1_RESULT_PATH) != policy["revision_basis"]["predecessor_sha256"]:
        raise RuntimeError("v1 predecessor result hash mismatch")
    policy_hash = sha256(POLICY_PATH)

    axes = (
        policy["synapse_model"]["KC_to_MBON-m1_contact_effect_mv_equivalent"],
        policy["mbon_neuron_model"]["tau_m_us"],
        policy["mbon_neuron_model"]["threshold_above_rest_mv_equivalent"],
        policy["encoder"]["pulse_mv_equivalent"],
        policy["integration"]["response_window_us"],
    )
    configs = []
    for ordinal, (coordinates, values) in enumerate(zip(
        itertools.product(*(range(len(axis)) for axis in axes)),
        itertools.product(*axes),
    )):
        contact, mbon_tau, mbon_threshold, pulse, response_window = values
        configs.append({
            "config_id": f"L1RE-V2-{ordinal:03d}",
            "coordinates": list(coordinates),
            "contact_effect_mv_per_contact": float(contact),
            "mbon_tau_m_us": int(mbon_tau),
            "mbon_threshold_mv": float(mbon_threshold),
            "pulse_mv": float(pulse),
            "response_window_us": int(response_window),
        })
    if len(configs) != int(policy["family"]["configuration_count"]):
        raise RuntimeError("resolved v2 family size differs from frozen policy")

    factors = [float(value) for value in policy["controllability_intervention"]["KC_to_MBON-m1_weight_factors"]]
    all_runs = []
    evaluations = []
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
    axis_spans = [
        sorted({row["coordinates"][axis] for row in qualifiers})
        for axis in range(len(axes))
    ]
    components = face_components(qualifiers, len(axes))
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
        "experiment_id": "larval_l1re_controllability_family_v2",
        "variant": "L1R-E-v2",
        "status": status,
        "frozen_inputs": {
            "manifest_sha256": sha256(MANIFEST_PATH),
            "policy_sha256": policy_hash,
            "predecessor_result_sha256": sha256(V1_RESULT_PATH),
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
            "qualifying_config_ids": [row["config_id"] for row in qualifiers],
            "qualifying_axis_index_spans": axis_spans,
            "face_connected_components": components,
            "largest_component": largest,
            "largest_component_size": len(largest),
            "robust_adjacent_threshold_members_in_largest": robust_in_largest,
            "nominal_selection": nominal,
        },
        "runs": all_runs,
        "interpretation": (
            "Outcome-informed engineering refinement of the L1R-E spiking abstraction. "
            "It does not establish fly physiology, a dopamine pathway, a plasticity mechanism, or learning."
        ),
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    if family_pass:
        nominal_model = {
            "model_id": "larval_l1re_electrical_v2",
            "variant": "L1R-E-v2",
            "status": "FROZEN_AFTER_PREDECLARED_CONTROLLABILITY_PASS",
            "manifest_sha256": sha256(MANIFEST_PATH),
            "family_policy_sha256": policy_hash,
            "controllability_result_sha256": sha256(OUTPUT_PATH),
            "selection_rule": policy["family_pass_rule"]["nominal_selection"],
            "selected_configuration": nominal["selected_configuration"],
            "selected_action_threshold_spikes": min(nominal["qualifying_action_thresholds"]),
            "kc_neuron_model": policy["kc_neuron_model"],
            "mbon_fixed_parameters": {
                key: value for key, value in policy["mbon_neuron_model"].items()
                if key not in ("tau_m_us", "threshold_above_rest_mv_equivalent")
            },
            "synapse_delay_us": policy["synapse_model"]["delay_us"],
            "teacher": "artificial local port; inactive in the controllability gate",
            "evidence_category": "ENGINEERING REFINEMENT",
        }
        NOMINAL_PATH.write_text(json.dumps(nominal_model, indent=2) + "\n", encoding="utf-8")
    elif NOMINAL_PATH.exists():
        raise RuntimeError("FAIL result must not leave a nominal v2 model")

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
