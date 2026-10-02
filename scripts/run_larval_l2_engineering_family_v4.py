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

POLICY_PATH = ROOT / "configs/larval_l2_electrical_family_v4_policy.json"
MANIFEST_PATH = ROOT / "configs/larval_l2_context_subgraph_manifest_v1.json"
MODEL_PATH = ROOT / "configs/larval_l2_electrical_model_v3.json"
NEUTRAL_PATH = ROOT / "runs/larval_l2_neutral_dynamics_v3.json"
OUTPUT_PATH = ROOT / "runs/larval_l2_electrical_family_v4.json"
V4_PATH = ROOT / "configs/larval_l2_electrical_model_v4.json"
EXPECTED_MANIFEST = "97560028444a02c8bb0c68c6608fd68dcfc5c103276b67debd30b059d0f6003b"
EXPECTED_MODEL = "c5f9adcf02378ded60ad66f11f8e1e03738955b94a1ab0a1089cc99b3033f60e"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def build_model(config: dict, factor: float):
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    model = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    nodes = manifest["nodes"]
    node_ids = [int(node["source_id"]) for node in nodes]
    index = {source_id: i for i, source_id in enumerate(node_ids)}
    roles = sorted({node["role"] for node in nodes})
    role_indices = {role: [index[int(node["source_id"])] for node in nodes
                           if node["role"] == role] for role in roles}
    edge_policy = model["chemical_edges"]
    included = set(edge_policy["included_directions"])
    edges = []
    for row in manifest["edges"]:
        direction = row["direction"]
        if direction not in included:
            continue
        multiplier = factor if direction == "KC_to_MBON-d1" else 1.0
        sign = edge_policy["sign_by_direction"][direction]
        scale = config["contact_effect_mV_equivalent_per_contact"]
        weight = int(row["contacts"]) * scale * multiplier * (1 if sign == "positive" else -1)
        if weight:
            edges.append(Synapse(index[int(row["pre_id"])], index[int(row["post_id"])],
                                 weight, 2_000))
    graph = SparseGraph(len(nodes), edges)
    tau_m = int(config["tau_m_ms"] * 1_000)
    tau_syn = 5_000
    params = [LIFParameters(v_rest_mv=0.0, v_reset_mv=0.0,
                            v_threshold_mv=config["threshold_mV_equivalent"],
                            tau_m_us=tau_m, tau_syn_us=tau_syn,
                            refractory_us=2_000) for _ in nodes]
    return manifest, model, node_ids, role_indices, graph, params


def simulate(config: dict, factor: float, state: int | None):
    manifest, model, node_ids, role_indices, graph, params = build_model(config, factor)
    duration = int(json.loads(NEUTRAL_PATH.read_text(encoding="utf-8"))["duration_us"])
    ext = [0.0] * len(node_ids)
    if state is not None:
        kc_ids = sorted(node_ids[i] for i in role_indices["KC"])
        base, remainder = divmod(len(kc_ids), 8)
        sizes = [base + (i < remainder) for i in range(8)]
        offset = sum(sizes[:state])
        selected = set(kc_ids[offset:offset + sizes[state]])
        pulse = config["sensory_and_context_pulse_mV_equivalent"]
        noci = {node_ids[i] for i in role_indices["Noci-2nd-order-PN"]}
        ext = [pulse if source_id in selected or source_id in noci else 0.0
               for source_id in node_ids]
    sim = SpikingSimulator(params, graph, ext, dt_us=1_000, record_spikes=True,
                           max_queued_events=1_000_000, max_scheduled_events=5_000_000)
    if state is not None:
        sim.run_until(5_000)
        sim.set_external_drive_mv([0.0] * len(node_ids))
    snap = sim.run_until(duration)
    diag = sim.diagnostics()
    counts = {role: sum(snap.spike_counts[i] for i in inds)
              for role, inds in role_indices.items()}
    goro_spikes = counts["Goro"]
    digest_payload = {
        "counts": counts,
        "spikes": [[s.time_us, node_ids[s.neuron_index], s.voltage_before_reset_mv.hex()]
                   for s in snap.spikes],
        "events": [diag.scheduled_events, diag.delivered_events,
                   diag.peak_queued_events, snap.queued_arrivals],
    }
    return {
        "state": state,
        "kc_to_mbon_multiplier": factor,
        "spikes_by_role": counts,
        "goro_spikes": goro_spikes,
        "actions_by_threshold": {str(t): goro_spikes >= t for t in (1, 2)},
        "all_voltage_finite": all(math.isfinite(v) for v in snap.voltage_mv),
        "all_synaptic_drive_finite": all(math.isfinite(v) for v in snap.synaptic_drive_mv),
        "scheduled_events": diag.scheduled_events,
        "delivered_events": diag.delivered_events,
        "replay_digest": sha256_bytes(json.dumps(digest_payload, sort_keys=True,
                                                  separators=(",", ":")).encode()),
    }


def nested(action_sets: list[set[int]]) -> bool:
    # Factors are ordered low→high. Weights decrease from high factor to low;
    # the lower-weight action set must be a superset of every higher-weight set.
    return all(action_sets[i].issuperset(action_sets[i + 1])
               for i in range(len(action_sets) - 1))


def connected_components(configs: list[dict], qualifying: set[tuple[int, ...]]):
    remaining = set(qualifying)
    components = []
    while remaining:
        start = min(remaining)
        remaining.remove(start)
        queue = deque([start])
        component = [start]
        while queue:
            point = queue.popleft()
            for axis in range(4):
                for delta in (-1, 1):
                    neighbor = point[:axis] + (point[axis] + delta,) + point[axis + 1:]
                    if neighbor in remaining:
                        remaining.remove(neighbor)
                        queue.append(neighbor)
                        component.append(neighbor)
        components.append(component)
    return sorted(components, key=lambda c: (-len(c), min(c)))


def main() -> None:
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    manifest_sha = sha256_file(MANIFEST_PATH)
    model_sha = sha256_file(MODEL_PATH)
    if manifest_sha != EXPECTED_MANIFEST or model_sha != EXPECTED_MODEL:
        raise RuntimeError("Frozen L2 manifest/model hash mismatch; stopping before simulation")
    if policy["status"] != "FROZEN_BEFORE_FAMILY_SIMULATION":
        raise RuntimeError("Policy is not frozen before simulation")
    axes = policy["parameter_axes"]
    keys = ("contact_effect_mV_equivalent_per_contact", "tau_m_ms",
            "threshold_mV_equivalent", "sensory_and_context_pulse_mV_equivalent")
    configs = []
    for indices in itertools.product(*(range(len(axes[k]["values"])) for k in keys)):
        row = {key: axes[key]["values"][index] for key, index in zip(keys, indices)}
        row["grid_index"] = list(indices)
        configs.append(row)
    if len(configs) != policy["family_size"]:
        raise RuntimeError("Frozen policy family size mismatch")

    factors = policy["controllability_protocol"]["kc_to_mbon_d1_multipliers"]
    states = policy["controllability_protocol"]["sensory_states"]
    repeats = policy["controllability_protocol"]["replays_per_cell"]
    config_results = []
    completed = 0
    total = len(configs) * (1 + len(factors) * len(states) * repeats)
    for ci, config in enumerate(configs):
        baseline = simulate(config, 1.0, None)
        cells = []
        deterministic = True
        finite = baseline["all_voltage_finite"] and baseline["all_synaptic_drive_finite"]
        for factor in factors:
            for state in states:
                first = simulate(config, factor, state)
                second = simulate(config, factor, state) if repeats > 1 else first
                match = first["replay_digest"] == second["replay_digest"]
                deterministic &= match
                finite &= first["all_voltage_finite"] and first["all_synaptic_drive_finite"]
                finite &= second["all_voltage_finite"] and second["all_synaptic_drive_finite"]
                cells.append({**first, "replay_match": match})
                completed += repeats
        completed += 1
        by_threshold = {}
        nested_by_threshold = {}
        for threshold in (1, 2):
            sets = [set(cell["state"] for cell in cells
                        if cell["kc_to_mbon_multiplier"] == f
                        and cell["actions_by_threshold"][str(threshold)]) for f in factors]
            by_threshold[str(threshold)] = [sorted(s) for s in sets]
            nested_by_threshold[str(threshold)] = nested(sets)
        primary_sets = by_threshold["1"]
        primary_non_saturated = any(2 <= len(s) <= 6 for s in primary_sets[:-1])
        threshold2_non_saturated = any(2 <= len(s) <= 6
                                       for s in by_threshold["2"][:-1])
        baseline_silent = not any(baseline["spikes_by_role"].values())
        qualifies = (baseline_silent and finite and deterministic
                     and nested_by_threshold["1"] and primary_non_saturated)
        config_results.append({
            "grid_index": config["grid_index"],
            "parameters": {key: config[key] for key in keys},
            "zero_drive_baseline": baseline,
            "baseline_silent": baseline_silent,
            "finite": finite,
            "deterministic_replay": deterministic,
            "action_states_by_threshold_and_factor": by_threshold,
            "nested_by_threshold": nested_by_threshold,
            "primary_non_saturated": primary_non_saturated,
            "two_spike_non_saturated": threshold2_non_saturated,
            "qualifies_primary": qualifies,
            "cells": cells,
        })
        if (ci + 1) % 4 == 0:
            print(f"completed {ci+1}/{len(configs)} configurations; simulations {completed}/{total}",
                  flush=True)

    qualifying = {tuple(item["grid_index"]) for item in config_results
                  if item["qualifies_primary"]}
    components = connected_components(configs, qualifying)
    largest = components[0] if components else []
    axis_spans = []
    for axis in range(4):
        axis_spans.append(sorted({point[axis] for point in qualifying}))
    component_two_spike = sum(
        next(item for item in config_results if tuple(item["grid_index"]) == point)
        ["two_spike_non_saturated"]
        and next(item for item in config_results if tuple(item["grid_index"]) == point)
        ["nested_by_threshold"]["2"]
        for point in largest
    )
    robust = (len(qualifying) >= 12 and all(len(span) >= 2 for span in axis_spans)
              and len(largest) >= 8 and component_two_spike >= 6)
    nominal = None
    if robust:
        medians = [sorted(point[i] for point in largest)[(len(largest) - 1) // 2]
                   if len(largest) % 2 else
                   (sorted(point[i] for point in largest)[len(largest) // 2 - 1]
                    + sorted(point[i] for point in largest)[len(largest) // 2]) / 2
                   for i in range(4)]
        def nominal_key(point):
            config = next(item["parameters"] for item in config_results
                          if tuple(item["grid_index"]) == point)
            return (sum(abs(point[i] - medians[i]) for i in range(4)),
                    config["contact_effect_mV_equivalent_per_contact"],
                    config["sensory_and_context_pulse_mV_equivalent"],
                    tuple(config[key] for key in keys))
        nominal_index = min(largest, key=nominal_key)
        nominal = next(item["parameters"] for item in config_results
                       if tuple(item["grid_index"]) == nominal_index)
        v4 = {
            "model_id": "larval_l2_electrical_model_v4_engineering_family_nominal",
            "status": "FROZEN_AFTER_ROBUST_FAMILY_CONTROLLABILITY_PASS",
            "selection_basis": "Nearest member of the largest qualifying connected component to its coordinate-wise median; no task score or learning outcome used.",
            "policy_sha256": sha256_file(POLICY_PATH),
            "manifest_sha256": manifest_sha,
            "parent_v3_sha256": model_sha,
            "parameters": nominal,
            "fixed_parameters": {
                "capacitance_nF": 1.0,
                "tau_syn_ms": 5,
                "refractory_ms": 2,
                "integration_dt_ms": 1,
                "delay_ms": 2,
                "tonic_background_mV_equivalent": 0,
                "pulse_duration_ms": 5,
                "action_threshold_goro_spikes": 1,
            },
            "directions_and_signs": json.loads(MODEL_PATH.read_text(encoding="utf-8"))["chemical_edges"],
            "plasticity": {"enabled": False, "locus": "KC_to_MBON-d1", "rule": "INFERRED; not implemented"},
            "biological_scope": "Engineering simulator controllability only; values are not quantitative larval physiology.",
        }
        V4_PATH.write_text(json.dumps(v4, indent=2) + "\n", encoding="utf-8")
    report = {
        "experiment_id": "larval_l2_engineering_family_v4",
        "status": "PASS" if robust else "FAIL",
        "decision": "v4 admitted for engineering controllability only" if robust
                    else "L2 rejected under this abstraction; stop before plasticity",
        "frozen_inputs": {
            "policy_sha256": sha256_file(POLICY_PATH),
            "manifest_sha256": manifest_sha,
            "parent_model_sha256": model_sha,
            "neutral_dynamics_sha256": sha256_file(NEUTRAL_PATH),
            "family_size": len(configs),
            "weight_factors": factors,
            "sensory_states": states,
            "replays_per_cell": repeats,
            "plasticity": False,
            "teaching": False,
            "exploration": False,
        },
        "family_summary": {
            "qualifying_configurations": len(qualifying),
            "largest_face_connected_component": len(largest),
            "axis_grid_indices_present": axis_spans,
            "component_configs_retaining_two_spike_non_saturated_nested_output": component_two_spike,
            "robust_criterion_pass": robust,
            "largest_component_grid_indices": [list(p) for p in largest],
            "nominal_selection": ({"grid_index": list(nominal_index), "parameters": nominal,
                                   "v4_path": str(V4_PATH), "v4_sha256": sha256_file(V4_PATH)}
                                  if nominal is not None else None),
        },
        "interpretation": "Simulator controllability under disclosed engineering assumptions only; no quantitative biological calibration or learning result.",
        "configurations": config_results,
    }
    OUTPUT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "summary": report["family_summary"],
                      "output": str(OUTPUT_PATH), "sha256": sha256_file(OUTPUT_PATH)}, indent=2))


if __name__ == "__main__":
    main()
