"""Fixed pre-training controllability sweep for larval L3 C1 candidate."""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from project_b.neurons import LIFParameters
from project_b.simulation import SpikingSimulator
from project_b.synapses import SparseGraph, Synapse

MANIFEST_PATH = ROOT / "configs/larval_l3_c1_subgraph_manifest_v1.json"
MODEL_PATH = ROOT / "configs/larval_l3_c1_electrical_v1.json"
NEUTRAL_PATH = ROOT / "runs/larval_l3_c1_neutral_dynamics_v1.json"
OUTPUT_PATH = ROOT / "runs/larval_l3_c1_controllability_v1.json"
FACTORS = (0.0, 0.25, 0.5, 1.0, 2.0, 4.0)
EXPECTED_HASHES = {
    "manifest": "b54a8a7ec9e3b18f21f8df91584c33f875c3302c8e534b6020dec7290f004895",
    "model": "5e32171707409a5dffc66f0c93d48bec307d442a01ace8b8554fa82e23c91f6e",
    "neutral_dynamics": "8fa83febee7812f5ba3435592a9a4dc390f156ccd9ba929e25486bbf9b4ce7bc",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_one(factor: float, state: int):
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    model = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    nodes = manifest["nodes"]
    node_ids = [int(node["source_id"]) for node in nodes]
    index = {source_id: i for i, source_id in enumerate(node_ids)}
    role_indices = {
        role: [index[int(node["source_id"])] for node in nodes if node["role"] == role]
        for role in sorted({node["role"] for node in nodes})
    }
    chemistry = model["chemical_effects"]
    included = set(chemistry["included_directions"])
    unit = float(chemistry["weight_mV_per_contact"])
    delay = int(chemistry["delay_us"])
    edges = []
    for row in manifest["edges"]:
        direction = row["direction"]
        if direction not in included:
            continue
        multiplier = factor if direction == "KC_to_MBON-c1" else 1.0
        weight = int(row["contacts"]) * unit * multiplier
        if weight:
            edges.append(Synapse(index[int(row["pre_id"])], index[int(row["post_id"])], weight, delay))
    graph = SparseGraph(len(nodes), edges)
    p = model["neuron_model"]
    # Match the frozen neutral runner's parameter construction exactly.
    params = [LIFParameters(tau_m_us=int(p["tau_m_us"]),
                            tau_syn_us=int(p["tau_syn_us"]),
                            refractory_us=int(p["refractory_us"])) for _ in nodes]

    kc_ids = sorted(int(node["source_id"]) for node in nodes if node["role"] == "KC")
    base, remainder = divmod(len(kc_ids), 8)
    groups, cursor = [], 0
    for i in range(8):
        size = base + (i < remainder)
        groups.append(kc_ids[cursor:cursor + size])
        cursor += size
    drive = [0.0] * len(nodes)
    for source_id in groups[state]:
        drive[index[source_id]] = float(model["sensory_boundary"]["drive_mV_equivalent"])
    sim = SpikingSimulator(params, graph, drive,
                           dt_us=int(model["integration"]["dt_us"]),
                           record_spikes=True,
                           max_queued_events=1_000_000,
                           max_scheduled_events=5_000_000)
    pulse = int(model["sensory_boundary"]["pulse_duration_us"])
    duration = 100_000
    sim.run_until(pulse)
    sim.set_external_drive_mv([0.0] * len(nodes))
    snapshot = sim.run_until(duration)
    diagnostics = sim.diagnostics()
    by_role = {
        role: sum(snapshot.spike_counts[i] for i in inds)
        for role, inds in role_indices.items()
    }
    by_source = {
        role: {str(node_ids[i]): int(snapshot.spike_counts[i]) for i in inds}
        for role, inds in role_indices.items()
    }
    action_ids = [int(sid) for sid in model["action_boundary"]["readout_nodes"]]
    action_spikes = {str(sid): int(snapshot.spike_counts[index[sid]]) for sid in action_ids}
    action = sum(action_spikes.values()) >= 1
    digest_payload = {
        "roles": by_role, "sources": by_source, "action_spikes": action_spikes,
        "spikes": [[s.time_us, node_ids[s.neuron_index], s.voltage_before_reset_mv.hex()]
                   for s in snapshot.spikes],
        "events": [diagnostics.scheduled_events, diagnostics.delivered_events,
                   diagnostics.peak_queued_events, snapshot.queued_arrivals],
    }
    digest = sha256(json.dumps(digest_payload, sort_keys=True,
                               separators=(",", ":")).encode("utf-8"))
    return {
        "factor": factor,
        "state": state,
        "spikes_by_role": by_role,
        "spikes_by_source_id": by_source,
        "action_readout_spikes_by_source_id": action_spikes,
        "action": action,
        "action_rule": "at least one selected DN-VNC readout spike in the 100-ms response window",
        "spike_times_us_by_role": {
            role: [s.time_us for s in snapshot.spikes if s.neuron_index in set(inds)]
            for role, inds in role_indices.items()
        },
        "events": {
            "scheduled": diagnostics.scheduled_events,
            "delivered": diagnostics.delivered_events,
            "peak_queued": diagnostics.peak_queued_events,
            "queued_at_end": snapshot.queued_arrivals,
            "max_spikes_one_tick": max(diagnostics.spike_counts_by_tick, default=0),
        },
        "numerical_pathology": {
            "all_voltage_finite": all(math.isfinite(v) for v in snapshot.voltage_mv),
            "all_synaptic_drive_finite": all(math.isfinite(v) for v in snapshot.synaptic_drive_mv),
            "safety_stop": False,
        },
        "replay_digest": digest,
    }


def main() -> None:
    paths = {"manifest": MANIFEST_PATH, "model": MODEL_PATH,
             "neutral_dynamics": NEUTRAL_PATH}
    input_hashes = {name: sha256(path.read_bytes()) for name, path in paths.items()}
    for name, expected in EXPECTED_HASHES.items():
        if input_hashes[name] != expected:
            raise RuntimeError(f"frozen {name} hash mismatch: {input_hashes[name]}")

    measurements = []
    deterministic = True
    for factor in FACTORS:
        for state in range(8):
            first = run_one(factor, state)
            second = run_one(factor, state)
            matches = first["replay_digest"] == second["replay_digest"]
            first["deterministic_replay_match"] = matches
            deterministic &= matches
            measurements.append(first)

    neutral = json.loads(NEUTRAL_PATH.read_text(encoding="utf-8"))
    factor_one = {m["state"]: m for m in measurements if m["factor"] == 1.0}
    neutral_rows = {row["state"]: row for row in neutral["states"]
                    if isinstance(row["state"], int)}
    neutral_match = all(
        all((sum(factor_one[s]["spikes_by_role"].get(role, 0)
                 for role in ("DN-VNC CN-28/PL-17",)) if role == "DN-VNC"
             else factor_one[s]["spikes_by_role"].get(role, 0)) == value
            for role, value in row["spikes_by_role"].items())
        and factor_one[s]["action"] == row["action"]
        and factor_one[s]["action_readout_spikes_by_source_id"] == row["dn_spikes"]
        for s, row in neutral_rows.items()
    )
    action_states = {
        str(factor): [m["state"] for m in measurements
                      if m["factor"] == factor and m["action"]]
        for factor in FACTORS
    }
    mixed_factors = [factor for factor in FACTORS
                     if 1 < len(action_states[str(factor)]) < 8]
    monotone = all(
        set(action_states[str(a)]).issubset(action_states[str(b)])
        for a, b in zip(FACTORS, FACTORS[1:])
    )
    no_pathology = all(
        row["numerical_pathology"]["all_voltage_finite"]
        and row["numerical_pathology"]["all_synaptic_drive_finite"]
        and not row["numerical_pathology"]["safety_stop"]
        for row in measurements
    )
    passed = bool(mixed_factors and monotone and deterministic and neutral_match and no_pathology)
    status = "PASS" if passed else "FAIL"
    report = {
        "experiment_id": "larval_l3_c1_controllability_v1",
        "status": status,
        "frozen_inputs": {
            "manifest_sha256": input_hashes["manifest"],
            "model_sha256": input_hashes["model"],
            "neutral_dynamics_sha256": input_hashes["neutral_dynamics"],
            "duration_us": 100000,
            "states": list(range(8)),
            "kc_to_mbon_c1_weight_multipliers": list(FACTORS),
            "only_varied_quantity": "KC_to_MBON-c1 chemical-edge weight multiplier",
            "plasticity_enabled": False,
            "teaching_enabled": False,
            "exploration_enabled": False,
            "input": "Frozen ascending-KC position-bin groups; 5-ms pulse, then zero drive",
            "fixed_action_rule": "at least one spike from either frozen DN-VNC readout within 100 ms",
        },
        "validation": {
            "frozen_hashes_match": True,
            "factor_1_matches_neutral_dynamics": neutral_match,
            "deterministic_replay_all_48_cells": deterministic,
            "action_states_by_factor": action_states,
            "factors_with_actions_on_multiple_but_not_all_states": mixed_factors,
            "action_sets_monotone_non_decreasing_across_factors": monotone,
            "no_numerical_pathology_or_safety_stop": no_pathology,
            "pass_rule": "At least one factor activates 2 to 7 states, action sets are nested non-decreasing over the declared factor order, factor 1 matches frozen neutral, replay is deterministic, and all runs remain finite without safety stops.",
        },
        "measurements": measurements,
        "interpretation": "Engineering-assumption controllability only; not a biological prediction, learning result, or task-score evaluation.",
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "action_states_by_factor": action_states,
                      "monotone": monotone, "neutral_match": neutral_match,
                      "deterministic": deterministic, "no_pathology": no_pathology,
                      "result_sha256": sha256(OUTPUT_PATH.read_bytes())}, indent=2))


if __name__ == "__main__":
    main()
