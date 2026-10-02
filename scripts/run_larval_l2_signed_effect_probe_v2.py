from __future__ import annotations

import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from project_b.neurons import LIFParameters
from project_b.simulation import SpikingSimulator
from project_b.synapses import SparseGraph, Synapse

MANIFEST_PATH = ROOT / "configs/larval_l2_subgraph_manifest_v1.json"
MODEL_PATH = ROOT / "configs/larval_l2_electrical_model_v2.json"
NEUTRAL_PATH = ROOT / "runs/larval_l2_neutral_dynamics_v1.json"  # duration only; v2 neutral is recorded below
OUTPUT_PATH = ROOT / "runs/larval_l2_signed_effect_probe_v2.json"
NEUTRAL_V2_PATH = ROOT / "runs/larval_l2_neutral_dynamics_v2.json"
PROTOCOL_PATH = ROOT / "configs/larval_l2_signed_effect_probe_v2_protocol.json"
FACTORS = (0.0, 0.25, 0.5, 1.0, 2.0, 4.0)
EXPECTED_HASHES = {
    "manifest": "84fb7af5160a405a072170466ea19e134cd12bc61ed1a7c565f301972da07c89",
    "model": "9b017e0df5a3d9e71e6224ba1c2c35343dee67cbf50a45fff62ab0ae88c1301c",
    "protocol": "77c8de4c0c617637602fe50becc788b3e854a7a8baf8cc12daf2e8454a6610ba",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def build_model(factor: float):
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    model = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    nodes = manifest["nodes"]
    node_ids = [int(node["source_id"]) for node in nodes]
    index = {source_id: i for i, source_id in enumerate(node_ids)}
    roles = {node["role"] for node in nodes}
    role_indices = {
        role: [index[int(node["source_id"])] for node in nodes if node["role"] == role]
        for role in sorted(roles)
    }
    c = model["chemical_edges"]
    unit = float(c["weight_mV_per_anatomical_contact"])
    delay = int(c["delay_us"])
    included = set(c["included_directions"])
    edges = []
    for row in manifest["edges"]:
        direction = row["direction"]
        if direction not in included:
            continue
        multiplier = factor if direction == "KC_to_MBON-d1" else 1.0
        sign = c["sign_by_direction"][direction]
        weight = int(row["contacts"]) * unit * multiplier * (1.0 if sign == "positive" else -1.0)
        if weight == 0.0:
            continue
        edges.append(Synapse(index[int(row["pre_id"])], index[int(row["post_id"])], weight, delay))
    graph = SparseGraph(len(nodes), edges)
    p = model["neuron_model"]
    params = LIFParameters(
        v_rest_mv=float(p["rest_mV"]), v_reset_mv=float(p["reset_mV"]),
        v_threshold_mv=float(p["threshold_mV"]), tau_m_us=int(p["tau_m_us"]),
        tau_syn_us=int(p["tau_syn_us"]), refractory_us=int(p["refractory_us"]),
    )
    return manifest, model, node_ids, index, role_indices, graph, [params] * len(nodes)


def run_one(factor: float, state: int):
    manifest, model, node_ids, index, role_indices, graph, params = build_model(factor)
    duration = int(json.loads(NEUTRAL_PATH.read_text(encoding="utf-8"))["duration_us"])
    dt = int(model["integration"]["dt_us"])
    sensory = model["sensory_boundary"]
    drive = float(sensory["drive_mV_equivalent"])
    pulse = int(sensory["pulse_duration_us"])
    kc_ids = sorted(node_ids[i] for i in role_indices["KC"])
    base, remainder = divmod(len(kc_ids), 8)
    sizes = [base + (i < remainder) for i in range(8)]
    groups = []
    cursor = 0
    for size in sizes:
        groups.append(kc_ids[cursor:cursor + size])
        cursor += size
    selected = set(groups[state])
    ext = [drive if source_id in selected else 0.0 for source_id in node_ids]
    sim = SpikingSimulator(params, graph, ext, dt_us=dt, record_spikes=True,
                           max_queued_events=1_000_000, max_scheduled_events=5_000_000)
    sim.run_until(pulse)
    sim.set_external_drive_mv([0.0] * len(node_ids))
    snap = sim.run_until(duration)
    diagnostics = sim.diagnostics()
    counts = {
        role: sum(snap.spike_counts[i] for i in inds)
        for role, inds in role_indices.items()
    }
    by_source = {
        role: {str(node_ids[i]): int(snap.spike_counts[i]) for i in inds}
        for role, inds in role_indices.items()
    }
    goro_indices = role_indices["Goro"]
    threshold = 1
    action = sum(snap.spike_counts[i] for i in goro_indices) >= threshold
    result = {
        "state": state,
        "factor": factor,
        "spikes_by_role": counts,
        "spikes_by_source_id": by_source,
        "action": action,
        "action_rule": "at least one Goro spike in 100 ms response window",
        "spike_times_us_by_role": {
            role: [spike.time_us for spike in snap.spikes
                   if spike.neuron_index in set(inds)]
            for role, inds in role_indices.items()
        },
        "events": {
            "scheduled": diagnostics.scheduled_events,
            "delivered": diagnostics.delivered_events,
            "peak_queued": diagnostics.peak_queued_events,
            "queued_at_end": snap.queued_arrivals,
            "max_spikes_one_tick": max(diagnostics.spike_counts_by_tick, default=0),
        },
        "numerical_pathology": {
            "all_voltage_finite": all(math.isfinite(v) for v in snap.voltage_mv),
            "all_synaptic_drive_finite": all(math.isfinite(v) for v in snap.synaptic_drive_mv),
            "safety_stop": False,
        },
        "replay_digest": sha256_bytes(json.dumps({
            "counts": counts,
            "source_counts": by_source,
            "spikes": [[s.time_us, node_ids[s.neuron_index], s.voltage_before_reset_mv.hex()]
                       for s in snap.spikes],
            "events": [diagnostics.scheduled_events, diagnostics.delivered_events,
                       diagnostics.peak_queued_events, snap.queued_arrivals],
        }, sort_keys=True, separators=(",", ":")).encode()),
    }
    return result


def run_baseline():
    manifest, model, node_ids, index, role_indices, graph, params = build_model(1.0)
    duration = int(json.loads(NEUTRAL_PATH.read_text(encoding="utf-8"))["duration_us"])
    dt = int(model["integration"]["dt_us"])
    sim = SpikingSimulator(params, graph, [0.0] * len(node_ids), dt_us=dt,
                           record_spikes=True, max_queued_events=1_000_000,
                           max_scheduled_events=5_000_000)
    snap = sim.run_until(duration)
    diagnostics = sim.diagnostics()
    counts = {role: sum(snap.spike_counts[i] for i in inds)
              for role, inds in role_indices.items()}
    return {
        "experiment_id": "larval_l2_neutral_dynamics_v2",
        "duration_us": duration,
        "spikes_by_role": counts,
        "action": sum(snap.spike_counts[i] for i in role_indices["Goro"]) >= 1,
        "action_rule": "at least one Goro spike in 100 ms response window",
        "all_voltage_finite": all(math.isfinite(v) for v in snap.voltage_mv),
        "all_synaptic_drive_finite": all(math.isfinite(v) for v in snap.synaptic_drive_mv),
        "scheduled_events": diagnostics.scheduled_events,
        "delivered_events": diagnostics.delivered_events,
    }


def main() -> None:
    input_hashes = {
        "manifest": sha256_file(MANIFEST_PATH),
        "model": sha256_file(MODEL_PATH),
        "protocol": sha256_file(PROTOCOL_PATH),
        "neutral_dynamics": sha256_file(NEUTRAL_PATH),
    }
    for key in ("manifest", "model", "protocol"):
        if input_hashes[key] != EXPECTED_HASHES[key]:
            raise RuntimeError(f"frozen {key} hash mismatch: {input_hashes[key]}")

    neutral = run_baseline()
    neutral["frozen_manifest_sha256"] = input_hashes["manifest"]
    neutral["frozen_model_sha256"] = input_hashes["model"]
    neutral["no_spontaneous_activity_or_action"] = not any(neutral["spikes_by_role"].values()) and not neutral["action"]
    NEUTRAL_V2_PATH.write_text(json.dumps(neutral, indent=2) + "\n", encoding="utf-8")
    input_hashes["neutral_dynamics_v2"] = sha256_file(NEUTRAL_V2_PATH)

    measurements = []
    deterministic_replay = True
    for factor in FACTORS:
        for state in range(8):
            first = run_one(factor, state)
            second = run_one(factor, state)
            deterministic_replay &= first["replay_digest"] == second["replay_digest"]
            first["deterministic_replay_match"] = first["replay_digest"] == second["replay_digest"]
            measurements.append(first)
    reference = json.loads(NEUTRAL_PATH.read_text(encoding="utf-8"))
    factor_one = {m["state"]: m for m in measurements if m["factor"] == 1.0}
    neutral_match = all(
        {role: factor_one[row["state"]]["spikes_by_role"][role] for role in row["spikes_by_role"]} == row["spikes_by_role"]
        and factor_one[row["state"]]["action"] == row["action"]
        for row in reference["states"] if isinstance(row["state"], int)
    )
    action_states = {
        str(factor): [m["state"] for m in measurements if m["factor"] == factor and m["action"]]
        for factor in FACTORS
    }
    any_action = any(action_states.values())
    # PASS requires actions on multiple states at some factor and non-saturated transfer.
    meaningful = False
    candidate_factors = []
    for factor in FACTORS:
        rows = [m for m in measurements if m["factor"] == factor]
        states = {m["state"] for m in rows if m["action"]}
        if len(states) > 1 and len(states) < 8:
            meaningful = True
            candidate_factors.append(factor)
    status = "PASS" if meaningful and deterministic_replay and neutral_match else "FAIL"
    report = {
        "experiment_id": "larval_l2_signed_effect_probe_v2",
        "status": status,
        "frozen_inputs": {
            "manifest_sha256": input_hashes["manifest"],
            "model_sha256": input_hashes["model"],
            "protocol_sha256": input_hashes["protocol"],
            "neutral_dynamics_sha256": input_hashes["neutral_dynamics"],
            "sweep_factors": list(FACTORS),
            "states": list(range(8)),
            "plasticity_enabled": False,
            "teaching_enabled": False,
            "exploration_enabled": False,
            "duration_us": int(reference["duration_us"]),
            "input": "unchanged 5-ms fixed current-position code pulse, then zero drive",
            "action_threshold": "unchanged: at least one Goro spike in 100 ms",
            "only_varied_quantity": "KC_to_MBON-d1 edge-weight multiplier; downstream signed effects are frozen from independent functional evidence",
            "zero_drive_neutral_sha256": input_hashes["neutral_dynamics_v2"],
        },
        "validation": {
            "frozen_hashes_match": True,
            "zero_drive_baseline_silent": neutral["no_spontaneous_activity_or_action"],
            "zero_drive_baseline_finite": neutral["all_voltage_finite"] and neutral["all_synaptic_drive_finite"],
            "factor_1_matches_neutral_dynamics": neutral_match,
            "deterministic_replay_all_48_cells": deterministic_replay,
            "action_states_by_factor": action_states,
            "factors_with_action_on_multiple_but_not_all_states": candidate_factors,
            "any_action": any_action,
            "no_numerical_pathology": all(
                item["numerical_pathology"]["all_voltage_finite"]
                and item["numerical_pathology"]["all_synaptic_drive_finite"]
                and not item["numerical_pathology"]["safety_stop"]
                for item in measurements
            ),
        },
        "measurements": measurements,
        "interpretation": "Bounded engineering controllability with literature-constrained downstream net effect classes; not unitary physiology or a learning result.",
    }
    OUTPUT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": status,
        "neutral_match": neutral_match,
        "deterministic_replay": deterministic_replay,
        "action_states_by_factor": action_states,
        "output": str(OUTPUT_PATH),
        "sha256": sha256_file(OUTPUT_PATH),
    }, indent=2))


if __name__ == "__main__":
    main()
