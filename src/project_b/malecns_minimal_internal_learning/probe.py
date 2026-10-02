"""Frozen, task-independent controllability probe for the minimal MaleCNS fixture."""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path

from project_b.mvp_c1.source import load_mvp_circuit
from project_b.neurons import LIFParameters
from project_b.simulation import SpikingSimulator
from project_b.synapses import SparseGraph, Synapse


def _read_config(root: Path, config_path: str = "configs/malecns_minimal_internal_learning.json") -> dict:
    config = json.loads((root / config_path)
                        .read_text(encoding="utf-8"))
    audited = json.loads((root / config["source"]["kc_mbon_audit"])
                         .read_text(encoding="utf-8"))
    audit_path = root / "docs/figures/b2_candidate_design/gamma4_contact_audit.json"
    if _sha256(audit_path) != config["source"]["kc_mbon_audit_sha256"]:
        raise ValueError("B2 KC→MBON contact-audit checksum differs")
    if audited["mbon_source_id"] != config["circuit"]["mbon_source_id"]:
        raise ValueError("MBON differs from audited KC→MBON mask")
    lookup = {int(row["kc_source_id"]): row for row in audited["kc_pairs"]}
    for cell in config["circuit"]["selected_kcs"]:
        row = lookup.get(cell["source_id"])
        if (row is None
                or row["plastic_contact_rows"] != cell["plastic_contact_row_ids"]
                or len(row["plastic_contact_rows"]) != cell["plastic_contact_rows"]):
            raise ValueError("selected KC or plastic-contact count differs from audit")
    source_pairs = _male_cns_pairs(str(root.resolve()))
    target = config["circuit"]["mbon_source_id"]
    if any((cell["source_id"], target) not in source_pairs
           for cell in config["circuit"]["selected_kcs"]):
        raise ValueError("selected pair is absent from the validated MaleCNS runtime graph")
    return config


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


@lru_cache(maxsize=1)
def _male_cns_pairs(root: str) -> frozenset[tuple[int, int]]:
    """Reuse the audited MaleCNS/B2.1 loader and verify selected source pairs."""
    circuit = load_mvp_circuit(Path(root))
    return frozenset((circuit.source_ids[int(pre)], circuit.source_ids[int(post)])
                     for pre, post in zip(circuit.graph.pre_indices,
                                           circuit.graph.post_indices))


def _simulate(config: dict, state: str, multiplier: float) -> dict:
    cells = config["circuit"]["selected_kcs"]
    active = [i for i, row in enumerate(cells) if row["state"] == state]
    if len(active) != 4:
        raise ValueError("each state must have exactly four fixed KCs")
    totals = {label: sum(c["plastic_contact_rows"] for c in cells
                         if c["state"] == label) for label in ("A", "B")}
    graph = SparseGraph(
        len(cells) + 1,
        [Synapse(i, len(cells),
                 cells[i]["plastic_contact_rows"] / totals[state] * multiplier,
                 config["overlay"]["synaptic_delay_us"])
         for i in range(len(cells))],
    )
    # Simulator time resolution is explicit and separate from neuron constants.
    neuron_config = config["overlay"]["lif"]
    neuron = LIFParameters(
        v_rest_mv=neuron_config["v_rest_mv"],
        v_reset_mv=neuron_config["v_reset_mv"],
        v_threshold_mv=neuron_config["v_threshold_mv"],
        tau_m_us=neuron_config["tau_m_us"],
        tau_syn_us=neuron_config["tau_syn_us"],
        refractory_us=neuron_config["refractory_us"],
    )
    drive = [1.2 if i in active else 0.0 for i in range(len(cells))] + [0.0]
    sim = SpikingSimulator(
        [neuron] * (len(cells) + 1), graph, drive,
        dt_us=neuron_config["dt_us"], record_neurons=[len(cells)],
        record_spikes=True,
    )
    split = config["overlay"]["observation_window_us"] // 2
    sim.run_until(split)
    checkpoint = sim.state()
    sim.run_until(config["overlay"]["observation_window_us"])
    final_state = sim.state()
    replay = SpikingSimulator(
        [neuron] * (len(cells) + 1), graph, drive,
        dt_us=neuron_config["dt_us"], record_neurons=[len(cells)],
        record_spikes=True,
    )
    replay.restore(checkpoint)
    replay.run_until(config["overlay"]["observation_window_us"])
    replay_identical = final_state == replay.state()
    snapshot = sim.snapshot()
    values = [sample.voltage_before_reset_mv for sample in snapshot.voltage_trace
              if sample.neuron_index == len(cells)]
    return {
        "state": state,
        "weight_multiplier": multiplier,
        "mbon_activity_max_voltage_mv": max(values),
        "mbon_spike_count": sum(spike.neuron_index == len(cells)
                                 for spike in snapshot.spikes),
        "active_kc_spike_counts": {
            str(cells[i]["source_id"]): sum(spike.neuron_index == i
                                            for spike in snapshot.spikes)
            for i in active
        },
        "weights_mv": list(graph.weights_mv),
        "checkpoint_replay_identical": replay_identical,
        "simulator_state_sha256": hashlib.sha256(
            json.dumps(final_state, sort_keys=True, separators=(",", ":"))
            .encode("utf-8")).hexdigest(),
    }


def run_probe(root: Path, config_path: str = "configs/malecns_minimal_internal_learning.json") -> dict:
    root = Path(root)
    config = _read_config(root, config_path)
    multipliers = config["controllability_probe"]["multipliers"]
    rows = [_simulate(config, state, multiplier)
            for state in ("A", "B") for multiplier in multipliers]
    by_a = [row["mbon_activity_max_voltage_mv"] for row in rows
            if row["state"] == "A"]
    monotonic = all(left > right for left, right in zip(by_a, by_a[1:]))
    threshold = config["controllability_probe"]["frozen_action_threshold_mv"]
    actions_a = [value <= threshold for value in by_a]
    replay_1 = _simulate(config, "A", 1.0)
    replay_2 = _simulate(config, "A", 1.0)
    passed = monotonic and (not actions_a[1]) and actions_a[2]
    return {
        "experiment_id": config["experiment_id"],
        "stage": "pretraining_controllability",
        "status": "PASS" if passed else "FAIL",
        "seed": config["overlay"]["rng_seed"],
        "rows": rows,
        "frozen_action_threshold_mv": threshold,
        "threshold_source": config["controllability_probe"]["threshold_selection"],
        "state_a_actions_by_multiplier": actions_a,
        "strictly_monotonic_state_a": monotonic,
        "deterministic_replay_identical": replay_1 == replay_2,
        "checkpoint_replay_identical": all(row["checkpoint_replay_identical"]
                                            for row in rows),
        "plasticity": "OFF",
        "checkpoint_replay": "same deterministic reset-and-replay observation; reusable simulator state digest recorded",
        "decision": ("Continue to local learning implementation." if passed else
                     "Stop. No learning implementation is authorized by this experiment gate."),
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--config", default="configs/malecns_minimal_internal_learning.json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run_probe(args.root, args.config)
    encoded = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
