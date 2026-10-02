"""Predeclared, non-learning MaleCNS v1 traced-graph scale stress test.

Topology is source-derived. Electrical effects, drive, and LIF dynamics are
engineering overlays and are not identified by the connectome.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
import time
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from project_b.connectome.runtime_graph import ArraySparseGraph
from project_b.neurons import LIFParameters
from project_b.simulation import SpikingSimulator


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/processed/malecns_v1_traced"
OUTPUT = ROOT / "runs/malecns_v1_scale"
STAGES = (("n100", 100, 500_000), ("n1000", 1_000, 500_000),
          ("n10000", 10_000, 250_000), ("mb_subcircuit", 20_000, 100_000),
          ("larger_network", 50_000, 100_000))
SEED = 20260929
MAX_QUEUE = 2_000_000
MAX_EVENTS = 20_000_000
DT_US = 1_000
DRIVER_FRACTION = 0.01
BACKGROUND_MV = 0.8
DRIVER_MV = 1.2
WEIGHT_GAIN_MV = 0.02
WEIGHT_CAP_MV = 0.2
DELAY_US = 2_000


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _rss_bytes() -> tuple[int, int] | None:
    if os.name != "nt":
        return None
    import ctypes
    from ctypes import wintypes

    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t)]

    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    if not psapi.GetProcessMemoryInfo(kernel32.GetCurrentProcess(),
                                      ctypes.byref(counters), counters.cb):
        return None
    return int(counters.WorkingSetSize), int(counters.PeakWorkingSetSize)


def _select_more(selected: np.ndarray, target: int, pre: np.ndarray,
                 post: np.ndarray, count: np.ndarray, ids: np.ndarray) -> int:
    """One deterministic weighted boundary expansion per stage."""
    need = target - int(selected.sum())
    if need <= 0:
        return 0
    forward = selected[pre] & ~selected[post]
    backward = selected[post] & ~selected[pre]
    score = np.bincount(post[forward], weights=count[forward], minlength=len(ids))
    score += np.bincount(pre[backward], weights=count[backward], minlength=len(ids))
    score[selected] = -1
    ranked = np.lexsort((ids, -score))
    chosen = ranked[:need]
    unconnected = int(np.count_nonzero(score[chosen] == 0))
    selected[chosen] = True
    return unconnected


def _sample_manifest(stage: str, selected: np.ndarray, pre: np.ndarray,
                     post: np.ndarray, count: np.ndarray, ids: np.ndarray,
                     source_row: np.ndarray, nodes: pa.Table,
                     parent_hashes: dict, unconnected: int) -> dict:
    local = np.full(len(ids), -1, dtype=np.int32)
    selected_idx = np.flatnonzero(selected)
    local[selected_idx] = np.arange(len(selected_idx), dtype=np.int32)
    inside = selected[pre] & selected[post]
    outgoing = selected[pre] & ~selected[post]
    incoming = ~selected[pre] & selected[post]
    edge_idx = np.flatnonzero(inside)
    directory = OUTPUT / stage
    directory.mkdir(parents=True, exist_ok=True)
    selected_nodes = nodes.take(pa.array(selected_idx))
    sample_nodes = selected_nodes.append_column("local_index", pa.array(np.arange(len(selected_idx), dtype=np.uint32)))
    sample_edges = pa.table({
        "parent_source_row": pa.array(source_row[edge_idx]),
        "pre_local": pa.array(local[pre[edge_idx]]),
        "post_local": pa.array(local[post[edge_idx]]),
        "synapse_count": pa.array(count[edge_idx]),
    })
    pq.write_table(sample_nodes, directory / "neurons.parquet", compression="zstd")
    pq.write_table(sample_edges, directory / "connections.parquet", compression="zstd")
    manifest = {
        "dataset": "MaleCNS", "release": "v1.0", "scope": "official traced-only",
        "selection": "lowest-source-ID MBON anchor; one weighted boundary expansion per stage; MB stage adds all annotated KC/MBON/DAN first; ties by source ID",
        "stage": stage, "parent_sha256": parent_hashes,
        "source_id_sha256": hashlib.sha256(ids[selected_idx].tobytes()).hexdigest(),
        "neurons": int(len(selected_idx)), "directed_pairs": int(len(edge_idx)),
        "internal_synapse_count": int(count[edge_idx].sum(dtype=np.int64)),
        "outgoing_cut_pairs": int(outgoing.sum()),
        "outgoing_cut_synapses": int(count[outgoing].sum(dtype=np.int64)),
        "incoming_cut_pairs": int(incoming.sum()),
        "incoming_cut_synapses": int(count[incoming].sum(dtype=np.int64)),
        "unconnected_fill_neurons": unconnected,
        "sample_sha256": {name: _sha(directory / name)
                          for name in ("neurons.parquet", "connections.parquet")},
    }
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def _simulate(stage: str, duration_us: int, manifest: dict) -> dict:
    directory = OUTPUT / stage
    nodes = pq.read_table(directory / "neurons.parquet", columns=["source_id"])
    edges = pq.read_table(directory / "connections.parquet")
    ids = nodes["source_id"].to_numpy()
    count = edges["synapse_count"].to_numpy()
    pre = edges["pre_local"].to_numpy()
    post = edges["post_local"].to_numpy()
    row = edges["parent_source_row"].to_numpy()
    # Deliberately all-positive as a conservative recurrent-excitation stress.
    weights = np.minimum(WEIGHT_GAIN_MV * np.sqrt(count), WEIGHT_CAP_MV)
    graph = ArraySparseGraph(len(ids), pre, post, weights,
                             np.full(len(pre), DELAY_US, dtype=np.int64), row)
    rng = np.random.default_rng(SEED)
    driver_count = max(1, int(np.ceil(len(ids) * DRIVER_FRACTION)))
    drivers = np.sort(rng.choice(len(ids), driver_count, replace=False))
    drive = np.full(len(ids), BACKGROUND_MV)
    drive[drivers] = DRIVER_MV
    params = [LIFParameters()] * len(ids)
    rss_before = _rss_bytes()
    model = SpikingSimulator(params, graph, drive, dt_us=DT_US,
                             track_active_synapses=True,
                             max_queued_events=MAX_QUEUE,
                             max_scheduled_events=MAX_EVENTS)
    start = time.perf_counter()
    error = None
    try:
        model.run_until(duration_us)
    except (ArithmeticError, RuntimeError) as exc:
        error = f"{type(exc).__name__}: {exc}"
    elapsed = time.perf_counter() - start
    rss_after = _rss_bytes()
    diagnostics = model.diagnostics()
    counts = np.asarray(model.spike_counts, dtype=np.int64)
    ticks = np.asarray(diagnostics.spike_counts_by_tick, dtype=np.int64)
    actual_seconds = model.current_time_us / 1e6
    half = len(ticks) // 2
    total_spikes = int(counts.sum())
    undriven = np.ones(len(ids), dtype=bool)
    undriven[drivers] = False
    result = {
        "stage": stage, "requested_simulated_seconds": duration_us / 1e6,
        "completed_simulated_seconds": actual_seconds, "wall_seconds": elapsed,
        "status": "complete" if error is None else "safety_stop",
        "error": error, "neurons": len(ids), "directed_pairs": graph.edge_count,
        "scheduled_events": diagnostics.scheduled_events,
        "delivered_events": diagnostics.delivered_events,
        "delivered_events_per_wall_second": diagnostics.delivered_events / elapsed,
        "simulated_seconds_per_wall_second": actual_seconds / elapsed,
        "peak_queued_events": diagnostics.peak_queued_events,
        "queued_at_end": len(model._queue),
        "active_synapses": diagnostics.unique_active_synapses,
        "active_synapse_fraction": diagnostics.unique_active_synapses / graph.edge_count if graph.edge_count else 0,
        "spikes": total_spikes,
        "mean_spike_rate_hz": total_spikes / len(ids) / actual_seconds if actual_seconds else 0,
        "max_spike_rate_hz": int(counts.max()) / actual_seconds if actual_seconds else 0,
        "p95_spike_rate_hz": float(np.percentile(counts, 95)) / actual_seconds if actual_seconds else 0,
        "silent_neuron_fraction": float(np.mean(counts == 0)),
        "undriven_active_neurons": int(np.count_nonzero(counts[undriven])),
        "undriven_neurons": int(undriven.sum()),
        "first_half_spikes": int(ticks[:half].sum()),
        "second_half_spikes": int(ticks[half:].sum()),
        "max_same_tick_spike_fraction": float(ticks.max() / len(ids)) if len(ticks) else 0,
        "ticks_over_25pct_spiking": int(np.count_nonzero(ticks > len(ids) * 0.25)),
        "neurons_over_250_hz": int(np.count_nonzero(counts / actual_seconds > 250)) if actual_seconds else 0,
        "process_rss_before_sim_bytes": rss_before[0] if rss_before else None,
        "process_rss_after_sim_bytes": rss_after[0] if rss_after else None,
        "process_peak_rss_bytes": rss_after[1] if rss_after else None,
        "vram_simulation_allocated_bytes": 0,
        "vram_note": "CPU-only reference backend; no GPU tensors or kernels allocated",
        "source_id_sha256": manifest["source_id_sha256"],
    }
    (directory / "profile.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    receipt = json.loads((SOURCE / "validation_receipt.json").read_text(encoding="utf-8"))
    if receipt.get("dataset") != "MaleCNS" or receipt.get("release") != "v1.0":
        raise ValueError("validated MaleCNS v1.0 receipt required")
    parent_hashes = {name: _sha(SOURCE / name)
                     for name in ("neurons.parquet", "connections.parquet")}
    if any(parent_hashes[name] != receipt["files"][name]["sha256"]
           for name in parent_hashes):
        raise ValueError("normalized MaleCNS files differ from validated receipt")
    config = {"dataset": "MaleCNS", "release": "v1.0", "seed": SEED,
              "stages": STAGES, "dt_us": DT_US,
              "background_mv": BACKGROUND_MV, "driver_mv": DRIVER_MV,
              "driver_fraction": DRIVER_FRACTION,
              "weight_formula": "min(0.02 * sqrt(source_synapse_count), 0.2) mV; all positive",
              "delay_us": DELAY_US, "max_queue": MAX_QUEUE,
              "max_scheduled_events": MAX_EVENTS,
              "backend": "deterministic CPU reference; no plasticity",
              "python": sys.version, "numpy": np.__version__,
              "pyarrow": pa.__version__, "platform": platform.platform(),
              "parent_sha256": parent_hashes}
    (OUTPUT / "protocol.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print("protocol saved", flush=True)
    nodes = pq.read_table(SOURCE / "neurons.parquet")
    edges = pq.read_table(SOURCE / "connections.parquet")
    ids = nodes["source_id"].to_numpy()
    classes = np.asarray(nodes["cell_class"].to_pylist(), dtype=object)
    pre = edges["pre_index"].to_numpy()
    post = edges["post_index"].to_numpy()
    count = edges["synapse_count"].to_numpy()
    row = edges["source_row"].to_numpy()
    assert np.array_equal(nodes["runtime_index"].to_numpy(), np.arange(len(ids)))
    assert len(pre) == 25_563_197 and len(ids) == 165_122
    anchor = int(np.flatnonzero(classes == "MBON")[0])
    selected = np.zeros(len(ids), dtype=bool)
    selected[anchor] = True
    print(f"MBON anchor source_id={ids[anchor]}", flush=True)
    for stage, size, duration in STAGES:
        if stage == "mb_subcircuit":
            selected[np.isin(classes, ["Kenyon_Cell", "MBON", "DAN"])] = True
        unconnected = _select_more(selected, size, pre, post, count, ids)
        manifest = _sample_manifest(stage, selected, pre, post, count, ids,
                                    row, nodes, config["parent_sha256"], unconnected)
        print(f"{stage}: {manifest['neurons']} neurons, {manifest['directed_pairs']} pairs, "
              f"{manifest['internal_synapse_count']} synapses; simulation starting", flush=True)
        result = _simulate(stage, duration, manifest)
        print(f"{stage}: {result['status']}; spikes={result['spikes']}; "
              f"events/s={result['delivered_events_per_wall_second']:.0f}; "
              f"sim/s={result['simulated_seconds_per_wall_second']:.5f}", flush=True)
        if result["status"] != "complete":
            print("safety stop: subsequent stages remain eligible and will be attempted", flush=True)


if __name__ == "__main__":
    if sys.argv[1:] != ["--reproduce-failed-overlay"]:
        raise SystemExit(
            "Historical failed all-positive stress profile only. "
            "Use --reproduce-failed-overlay to reproduce it; "
            "use scripts.build_circuit_v1_policies for the current Circuit V1 policy."
        )
    main()
