"""Short nontraining sparse-reference benchmark; no connectome data required."""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import psutil

from project_b.neurons import LIFParameters
from project_b.simulation import SpikingSimulator
from project_b.synapses import SparseGraph, Synapse


def run(neuron_count: int, ticks: int, outgoing: int = 8) -> dict:
    process = psutil.Process(os.getpid())
    rss_before = process.memory_info().rss
    start = time.perf_counter()
    graph = SparseGraph(neuron_count, (
        Synapse(pre, (pre + k * 97 + 1) % neuron_count, 0.05, 2_000)
        for pre in range(neuron_count) for k in range(outgoing)))
    graph_seconds = time.perf_counter() - start
    rss_graph = process.memory_info().rss
    drive = [0.0] * neuron_count
    for i in range(0, neuron_count, 100):
        drive[i] = 1.5
    simulator = SpikingSimulator(
        [LIFParameters()] * neuron_count, graph, drive, dt_us=1_000)
    start = time.perf_counter()
    peak_queue = 0
    for tick in range(1, ticks + 1):
        snapshot = simulator.run_until(tick * 1_000)
        peak_queue = max(peak_queue, snapshot.queued_arrivals)
    simulation_seconds = time.perf_counter() - start
    return {
        "neuron_count": neuron_count,
        "edge_count": graph.edge_count,
        "ticks": ticks,
        "dt_us": 1_000,
        "simulated_seconds": ticks / 1_000,
        "graph_build_wall_seconds": graph_seconds,
        "simulation_wall_seconds": simulation_seconds,
        "simulation_wall_per_simulated_second": simulation_seconds / (ticks / 1_000),
        "rss_before_mib": rss_before / 2**20,
        "rss_after_graph_mib": rss_graph / 2**20,
        "rss_after_simulation_mib": process.memory_info().rss / 2**20,
        "peak_queued_arrivals": peak_queue,
        "total_spikes": sum(snapshot.spike_counts),
        "notes": "Synthetic ring; fixed mV-effect edges and 1% driven neurons. Snapshot construction at each tick is included; this is an upper-level reference benchmark, not a full connectome prediction."
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--neurons", type=int, required=True)
    parser.add_argument("--ticks", type=int, default=50)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.neurons < 100 or not 1 <= args.ticks <= 1000:
        parser.error("neurons must be >=100 and ticks in 1..1000")
    result = run(args.neurons, args.ticks)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
