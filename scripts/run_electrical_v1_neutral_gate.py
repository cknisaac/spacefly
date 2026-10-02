"""Run the frozen 24-condition Electrical V1 neutral operating-state gate.

All runs are task-free and plasticity-free. Each raw result is written before
moving to the next completed job. This runner must not adjust model parameters
or select favorable seeds/levels after inspecting output.
"""

from __future__ import annotations

from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import pickle
import platform
import time
import traceback

import numpy as np

from project_b.electrical_v1 import DNBoundary, NeutralCircuit, build_circuit
from project_b.electrical_v1.boundary import STREAM_NAMES
from project_b.electrical_v1.source import file_sha


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/figures/electrical_v1_neutral_gate"
PROTOCOL = ROOT / "configs/electrical_v1_neutral_gate.json"
CONFIG = ROOT / "configs/electrical_model_v1.json"
SOURCE_FILES = (
    ROOT / "src/project_b/electrical_v1/source.py",
    ROOT / "src/project_b/electrical_v1/boundary.py",
    ROOT / "src/project_b/electrical_v1/runtime.py",
    Path(__file__),
)
TRACE_COLUMNS = ("time_us", "dn3_voltage_mv", "dn2_voltage_mv", "dn3_synaptic_pa",
                 "dn2_synaptic_pa", "dn3_boundary_pa", "dn2_boundary_pa",
                 "dn3_leak_pa", "dn2_leak_pa", "dn3_refractory", "dn2_refractory",
                 "queue_length", "dan_state", "apl_calyx_state", "max_abs_apl_local")
CIRCUIT = None


def digest_object(value) -> str:
    return hashlib.sha256(pickle.dumps(value, protocol=5)).hexdigest()


def write_json(path: Path, payload: dict) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def write_gzip_json(path: Path, payload: dict) -> None:
    tmp = path.with_name(path.name + ".tmp")
    encoded = (json.dumps(payload, separators=(",", ":"), sort_keys=True, allow_nan=False) + "\n").encode()
    with tmp.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=0, compresslevel=6) as compressed:
            compressed.write(encoded)
    os.replace(tmp, path)


def read_gzip_json(path: Path) -> dict:
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def initialize_worker() -> None:
    global CIRCUIT
    CIRCUIT = build_circuit()


def boundary_ledger(seed: int, total_us: int) -> dict:
    generator = DNBoundary(seed=seed, level="nominal", control="shared")
    events = [[0, *(generator.signs[name] for name in STREAM_NAMES)]]
    while generator.next_event_us <= total_us:
        t = generator.next_event_us
        generator.advance_to(t)
        events.append([t, *(generator.signs[name] for name in STREAM_NAMES)])
    generator.advance_to(total_us)
    return {"seed": seed, "stream_names": STREAM_NAMES,
            "event_columns": ("time_us", *STREAM_NAMES), "events": events,
            "checkpoint_sha256": digest_object(generator.checkpoint()),
            "time_us": total_us, "construction": "autonomous latent signs, including unused control streams"}


def snapshot(model: NeutralCircuit) -> dict:
    return {"spike_counts": model.spike_counts.copy(),
            "outer_count": model.voltage_outer_count.copy(),
            "extreme_count": model.voltage_extreme_count.copy(),
            "voltage_samples": model.voltage_sample_count,
            "refractory_time": model.refractory_time_us.copy(),
            "scheduled": model.sequence, "delivered": model.delivered}


def sample(model: NeutralCircuit) -> list:
    d3, d2 = model.dn3, model.dn2
    b3, b2 = model.boundary.currents_pa(*model.dn_reference_pa)
    t = model.current_time_us
    return [t, float(model.v_mv[d3]), float(model.v_mv[d2]),
            float(model.syn_pa[d3]), float(model.syn_pa[d2]), b3, b2,
            float(-model.leak_ns[d3]*(model.v_mv[d3]-model.rest_mv[d3])),
            float(-model.leak_ns[d2]*(model.v_mv[d2]-model.rest_mv[d2])),
            int(t < model.refractory_until_us[d3]), int(t < model.refractory_until_us[d2]),
            len(model.queue), model.dan_state, model.apl_calyx,
            float(np.max(np.abs(model.apl_local)))]


def max_silent_gap_us(times: list[int], start_us: int, end_us: int) -> int:
    return max(b-a for a, b in zip([start_us, *times], [*times, end_us]))


def compute_metrics(model: NeutralCircuit, settle: dict, end: dict, protocol: dict,
                    expected_boundary_hash: str, replay_equal: bool) -> dict:
    start_us, obs_us = protocol["settling_us"], protocol["observation_us"]
    total_us = start_us + obs_us
    limits = protocol["criteria"]
    obs_counts = end["spike_counts"] - settle["spike_counts"]
    obs_outer = end["outer_count"] - settle["outer_count"]
    obs_extreme = end["extreme_count"] - settle["extreme_count"]
    obs_samples = end["voltage_samples"] - settle["voltage_samples"]
    obs_refractory = end["refractory_time"] - settle["refractory_time"]
    if obs_samples != obs_us // model.tick_us:
        raise AssertionError("Observation sample count is inconsistent with fixed tick")
    dn = {}
    for sid, index in ((519624, model.dn3), (523769, model.dn2)):
        times = [t for t, source in model.spikes if source == sid and start_us < t <= total_us]
        bins = model.dn_refractory_bins_us[sid][start_us//1_000_000:total_us//1_000_000]
        if len(bins) != obs_us//1_000_000:
            raise AssertionError("Incomplete exact DN refractory bins")
        second_counts = [0] * (obs_us//1_000_000)
        for t in times:
            second_counts[(t-start_us-1)//1_000_000] += 1
        dn[str(sid)] = {"observation_spikes": int(obs_counts[index]),
                        "rate_hz": int(obs_counts[index])/(obs_us/1_000_000),
                        "max_silent_gap_us": max_silent_gap_us(times, start_us, total_us),
                        "refractory_time_us": int(obs_refractory[index]),
                        "refractory_occupancy": int(obs_refractory[index])/obs_us,
                        "refractory_bins_us": list(bins),
                        "max_full_second_occupancy": max(bins)/1_000_000,
                        "violating_full_second_bins": [i+start_us//1_000_000 for i, x in enumerate(bins)
                                                      if x/1_000_000 > limits["maximum_full_second_refractory_occupancy"]],
                        "spike_counts_by_observation_second": second_counts,
                        "outer_voltage_fraction": int(obs_outer[index])/obs_samples,
                        "extreme_voltage_samples": int(obs_extreme[index])}
        if len(times) != dn[str(sid)]["observation_spikes"]:
            raise AssertionError("Spike times and counters disagree")
    by_class = Counter()
    for i, count in enumerate(obs_counts):
        by_class[model.kind[i]] += int(count)
    outer_fractions = obs_outer/obs_samples
    boundary_hash = digest_object(model.boundary.checkpoint())
    checks = {
        "boundary_clock_paired": boundary_hash == expected_boundary_hash,
        "checkpoint_replay": replay_equal,
        "finite_final_state": bool(np.all(np.isfinite(model.v_mv)) and
                                   np.all(np.isfinite(model.syn_pa)) and
                                   np.all(np.isfinite(model.apl_local)) and
                                   math.isfinite(model.apl_calyx) and math.isfinite(model.dan_state)),
        "events_accounted": model.sequence-model.delivered == len(model.queue),
        "queue_below_limit": model.peak_queued <= model.max_queued,
        "voltage_outer_fraction_all_cells": bool(np.all(outer_fractions <=
                                                          1-limits["minimum_bounded_voltage_fraction_per_cell"]+1e-12)),
        "no_extreme_voltage_all_cells": bool(np.all(obs_extreme == 0)),
        "dn_rates_below_ceiling": all(x["rate_hz"] <= limits["maximum_dn_rate_hz"] for x in dn.values()),
        "dn_refractory_below_ceiling": all(x["refractory_occupancy"] <=
                                            limits["maximum_dn_refractory_occupancy"] for x in dn.values()),
        "dn_full_seconds_below_ceiling": all(not x["violating_full_second_bins"] for x in dn.values()),
        "plasticity_off": model.plasticity_enabled is False and model.dan_state == 0.0,
    }
    if model.condition in {"A", "C"} and model.level == "nominal":
        checks["nominal_A_C_activity"] = all(
            x["observation_spikes"] >= limits["nominal_A_C_minimum_dn_spikes"] and
            x["max_silent_gap_us"] <= limits["nominal_A_C_maximum_silent_gap_us"]
            for x in dn.values())
    return {"dn": dn, "spikes_by_class_observation": dict(by_class),
            "observation_voltage_samples_per_cell": obs_samples,
            "max_outer_voltage_fraction_all_cells": float(np.max(outer_fractions)),
            "outer_voltage_violators": [model.source_ids[i] for i, x in enumerate(outer_fractions)
                                        if x > 1-limits["minimum_bounded_voltage_fraction_per_cell"]+1e-12],
            "extreme_voltage_violators": [model.source_ids[i] for i, x in enumerate(obs_extreme) if x],
            "observation_scheduled_events": end["scheduled"]-settle["scheduled"],
            "observation_delivered_events": end["delivered"]-settle["delivered"],
            "peak_queued_events_whole_run": model.peak_queued,
            "boundary_checkpoint_sha256": boundary_hash,
            "checks": checks, "base_gate_pass": all(checks.values())}


def run_one(spec: dict, protocol: dict, protocol_sha: str, code_hashes: dict,
            expected_boundary_hash: str) -> dict:
    if CIRCUIT is None:
        raise RuntimeError("Worker source circuit was not initialized")
    condition, level, seed = spec["condition"], spec["level"], spec["seed"]
    fine = spec["variant"] == "fine250"
    run_id = ("R_" if fine else "") + f"{condition}_{level}_{seed}" + ("_tick250" if fine else "")
    started = time.monotonic()
    trace = []
    model = None
    try:
        model = NeutralCircuit(CIRCUIT, condition=condition, level=level, seed=seed)
        if fine:
            model.tick_us = protocol["numerical_refinement"]["fine_tick_us"]
        tick_us = model.tick_us
        settle_us = protocol["settling_us"]
        total_us = settle_us + protocol["observation_us"]
        trace.append(sample(model))
        settle_snapshot = None
        settle_checkpoint = None
        replay_target_hash = None
        for t in range(protocol["trace_interval_us"], total_us+1, protocol["trace_interval_us"]):
            model.run_until(t)
            trace.append(sample(model))
            if t == settle_us:
                settle_snapshot = snapshot(model)
                settle_checkpoint = model.checkpoint()
            if t == settle_us + 1_000_000:
                replay_target_hash = digest_object(model.checkpoint())
        if settle_snapshot is None or settle_checkpoint is None or replay_target_hash is None:
            raise AssertionError("Missing settle or replay landmark")
        end_snapshot = snapshot(model)
        replay = NeutralCircuit(CIRCUIT, condition=condition, level=level, seed=seed)
        replay.tick_us = tick_us
        replay.restore(settle_checkpoint)
        replay.run_until(settle_us + 1_000_000)
        replay_equal = digest_object(replay.checkpoint()) == replay_target_hash
        metrics = compute_metrics(model, settle_snapshot, end_snapshot, protocol,
                                  expected_boundary_hash, replay_equal)
        payload = {"run_id": run_id, "spec": spec, "status": "complete",
                   "protocol_sha256": protocol_sha, "model_config_sha256": CIRCUIT.config_sha256,
                   "code_sha256": code_hashes, "tick_us": tick_us,
                   "trace_columns": TRACE_COLUMNS, "trace": trace,
                   "all_spikes_time_us_source_id": model.spikes,
                   "metrics": metrics, "final_summary": model.summary(),
                   "elapsed_wall_seconds": time.monotonic()-started}
    except Exception as exc:
        payload = {"run_id": run_id, "spec": spec, "status": "error",
                   "protocol_sha256": protocol_sha, "model_config_sha256": CIRCUIT.config_sha256,
                   "code_sha256": code_hashes, "trace_columns": TRACE_COLUMNS, "trace": trace,
                   "all_spikes_time_us_source_id": model.spikes if model else [],
                   "time_reached_us": model.current_time_us if model else 0,
                   "error": repr(exc), "traceback": traceback.format_exc(),
                   "elapsed_wall_seconds": time.monotonic()-started}
    path = OUT / f"{run_id}.json.gz"
    write_gzip_json(path, payload)
    return {"run_id": run_id, "status": payload["status"], "file": path.name,
            "file_sha256": file_sha(path), "metrics": payload.get("metrics"),
            "error": payload.get("error"), "wall_seconds": payload["elapsed_wall_seconds"]}


def make_specs(protocol: dict, *, refinement: bool) -> list[dict]:
    if refinement:
        r = protocol["numerical_refinement"]
        return [{"condition": r["condition"], "level": r["level"], "seed": seed,
                 "variant": "fine250"} for seed in r["seeds"]]
    return [{"condition": condition["name"], "level": level, "seed": seed, "variant": "primary"}
            for condition in protocol["conditions"] for level in condition["levels"]
            for seed in protocol["seeds"]]


def run_specs(pool, specs: list[dict], protocol: dict, protocol_sha: str,
              code_hashes: dict, boundary_hashes: dict, rows: dict) -> None:
    futures = {}
    for spec in specs:
        fine = spec["variant"] == "fine250"
        run_id = ("R_" if fine else "") + f"{spec['condition']}_{spec['level']}_{spec['seed']}" + ("_tick250" if fine else "")
        existing = OUT / f"{run_id}.json.gz"
        if existing.exists():
            raw = read_gzip_json(existing)
            if (raw["protocol_sha256"] != protocol_sha or raw["model_config_sha256"] != file_sha(CONFIG)
                    or raw["code_sha256"] != code_hashes or raw["status"] != "complete"):
                raise RuntimeError(f"Existing run is incompatible/incomplete: {existing}")
            rows[run_id] = {"run_id": run_id, "status": raw["status"], "file": existing.name,
                            "file_sha256": file_sha(existing), "metrics": raw["metrics"],
                            "wall_seconds": raw["elapsed_wall_seconds"]}
            print(f"RESUME {run_id}", flush=True)
            continue
        futures[pool.submit(run_one, spec, protocol, protocol_sha, code_hashes,
                            boundary_hashes[spec["seed"]])] = run_id
    for future in as_completed(futures):
        row = future.result()
        rows[row["run_id"]] = row
        write_json(OUT / "status.json", {"protocol_sha256": protocol_sha,
                   "complete": sorted(k for k, v in rows.items() if v["status"] == "complete"),
                   "errors": {k: v["error"] for k, v in rows.items() if v["status"] == "error"}})
        print(f"DONE {row['run_id']} {row['status']} {row['wall_seconds']:.1f}s", flush=True)


def compare_refinement(coarse: dict, fine: dict, criteria: dict) -> dict:
    if coarse["status"] != "complete" or fine["status"] != "complete":
        return {"pass": False, "error": "missing complete coarse/fine run"}
    x, y = coarse["metrics"], fine["metrics"]
    per_dn = {}
    for sid in ("519624", "523769"):
        a, b = x["dn"][sid], y["dn"][sid]
        absolute_hz = abs(a["rate_hz"]-b["rate_hz"])
        relative = absolute_hz/max(a["rate_hz"], b["rate_hz"], 1)
        bin_diff = max(abs(p-q) for p, q in zip(a["spike_counts_by_observation_second"],
                                                  b["spike_counts_by_observation_second"]))
        per_dn[sid] = {"coarse_rate_hz": a["rate_hz"], "fine_rate_hz": b["rate_hz"],
                       "absolute_rate_difference_hz": absolute_hz,
                       "relative_rate_difference": relative,
                       "maximum_second_count_difference": bin_diff,
                       "pass": (absolute_hz <= criteria["maximum_observation_rate_absolute_difference_hz"]
                                and relative <= criteria["maximum_observation_rate_relative_difference"]
                                and bin_diff <= criteria["maximum_per_second_dn_spike_count_difference"])}
    outer_diff = abs(x["max_outer_voltage_fraction_all_cells"]-
                     y["max_outer_voltage_fraction_all_cells"])
    return {"dn": per_dn, "maximum_outer_fraction_difference": outer_diff,
            "boundary_clock_equal": x["boundary_checkpoint_sha256"] == y["boundary_checkpoint_sha256"],
            "pass": (all(z["pass"] for z in per_dn.values()) and
                     outer_diff <= criteria["maximum_observation_outer_fraction_difference"] and
                     x["boundary_checkpoint_sha256"] == y["boundary_checkpoint_sha256"])}


def main() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    protocol_sha = file_sha(PROTOCOL)
    if file_sha(CONFIG) != protocol["model_config_sha256"]:
        raise RuntimeError("Frozen Electrical Model V1 config differs from predeclared gate")
    if (len(make_specs(protocol, refinement=False)) != 24 or
            len(make_specs(protocol, refinement=True)) != 3):
        raise RuntimeError("Gate schedule differs from predeclared 24+3")
    OUT.mkdir(parents=True, exist_ok=True)
    code_hashes = {str(p.relative_to(ROOT)): file_sha(p) for p in SOURCE_FILES}
    meta = {"protocol": protocol, "protocol_sha256": protocol_sha,
            "model_config": json.loads(CONFIG.read_text(encoding="utf-8")),
            "model_config_sha256": file_sha(CONFIG),
            "code_sha256": code_hashes, "source_manifest": json.loads(
                (ROOT / "data/processed/malecns_v1_electrical_v1/manifest.json").read_text()),
            "python": platform.python_version(), "numpy": np.__version__,
            "processor": platform.processor(), "trace_columns": TRACE_COLUMNS,
            "classification": "task-independent engineering operating-state gate; no learning"}
    write_json(OUT / "meta.json", meta)
    total_us = protocol["settling_us"] + protocol["observation_us"]
    boundary_hashes = {}
    for seed in protocol["seeds"]:
        ledger = boundary_ledger(seed, total_us)
        write_gzip_json(OUT / f"boundary_{seed}.json.gz", ledger)
        boundary_hashes[seed] = ledger["checkpoint_sha256"]
    rows = {}
    worker_count = min(6, os.cpu_count() or 1)
    print(f"START 24 fixed runs + 3 numerical refinements; workers={worker_count}", flush=True)
    with ProcessPoolExecutor(max_workers=worker_count, initializer=initialize_worker) as pool:
        run_specs(pool, make_specs(protocol, refinement=False), protocol, protocol_sha,
                  code_hashes, boundary_hashes, rows)
        run_specs(pool, make_specs(protocol, refinement=True), protocol, protocol_sha,
                  code_hashes, boundary_hashes, rows)
    comparison = {}
    for seed in protocol["numerical_refinement"]["seeds"]:
        comparison[str(seed)] = compare_refinement(rows[f"A_nominal_{seed}"],
                                                    rows[f"R_A_nominal_{seed}_tick250"],
                                                    protocol["numerical_refinement"])
    ordered = [rows[("R_" if spec["variant"] == "fine250" else "") +
                    f"{spec['condition']}_{spec['level']}_{spec['seed']}" +
                    ("_tick250" if spec["variant"] == "fine250" else "")]
               for spec in (make_specs(protocol, refinement=False) + make_specs(protocol, refinement=True))]
    primary = ordered[:24]
    gate_pass = (all(row["status"] == "complete" and row["metrics"]["base_gate_pass"] for row in primary)
                 and all(result["pass"] for result in comparison.values()))
    result = {"protocol_sha256": protocol_sha, "model_config_sha256": file_sha(CONFIG),
              "runs": ordered, "numerical_refinement": comparison,
              "primary_conditions_complete": sum(r["status"] == "complete" for r in primary),
              "neutral_operating_state_gate_pass": gate_pass,
              "interpretation": "Pass is engineering neutral operating-state only; not biological validity or learning"}
    write_json(OUT / "result.json", result)
    print(f"FINAL primary_complete={result['primary_conditions_complete']}/24 gate_pass={gate_pass}", flush=True)


if __name__ == "__main__":
    main()
