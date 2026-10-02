"""B5 task-independent sensory-to-DN causal route panel.

The Electrical Model V1 configuration, source anatomy, effect values, delays,
neuron values and boundary are frozen. Pulses are independent branches from
unperturbed nominal-boundary checkpoints. Each seed is saved durably.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
import gzip
import hashlib
import json
import os
from pathlib import Path
import pickle
import platform
import time
import traceback

import numpy as np

from project_b.electrical_v1 import build_circuit
from project_b.electrical_v1.sensory_route_probe import SensoryRouteProbe, VISUAL_IDS
from project_b.electrical_v1.source import file_sha


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "configs/electrical_v1_sensory_route_causality.json"
MODEL_CONFIG_PATH = ROOT / "configs/electrical_model_v1.json"
OUT = ROOT / "docs/figures/electrical_v1_sensory_route_causality"
CODE_PATHS = (
    ROOT / "src/project_b/electrical_v1/source.py",
    ROOT / "src/project_b/electrical_v1/boundary.py",
    ROOT / "src/project_b/electrical_v1/runtime.py",
    ROOT / "src/project_b/electrical_v1/sensory_route_probe.py",
    Path(__file__),
)
TRACE_COLUMNS = ("time_us", "DNa03_voltage_mv", "DNa02_voltage_mv",
                 "DNa03_synaptic_pa", "DNa02_synaptic_pa",
                 "DNa03_boundary_pa", "DNa02_boundary_pa",
                 "APL_local_sum", "APL_local_max", "queue_length")
ARM_ORDER = ("A", "B", "C", "D", "E", "E_off", "F", "F_off")


def digest(value) -> str:
    return hashlib.sha256(pickle.dumps(value, protocol=5)).hexdigest()


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def write_json(path: Path, value: dict) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(canonical(value)+b"\n")
    os.replace(tmp, path)


def write_gzip_json(path: Path, value: dict) -> None:
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=0, compresslevel=6) as compressed:
            compressed.write(canonical(value)+b"\n")
    os.replace(tmp, path)


def read_gzip_json(path: Path) -> dict:
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def sample(model: SensoryRouteProbe) -> list:
    b3, b2 = model.boundary.currents_pa(*model.dn_reference_pa)
    return [model.current_time_us, float(model.v_mv[model.dn3]), float(model.v_mv[model.dn2]),
            float(model.syn_pa[model.dn3]), float(model.syn_pa[model.dn2]),
            b3, b2, float(np.sum(model.apl_local)), float(np.max(model.apl_local)), len(model.queue)]


def target_and_current(circuit, model: SensoryRouteProbe, arm: str, level: str,
                       protocol: dict) -> tuple[tuple[int, ...], float]:
    current = protocol["current_policy"]
    if arm in {"A", "B", "C", "D"}:
        ids = VISUAL_IDS
        multiplier = current["visual_levels"][level]
    elif arm in {"E", "E_off"}:
        ids = tuple(c.source_id for c in circuit.cells if c.kind == "KC")
        multiplier = current["direct_KC_multiplier"]
    else:
        ids = (519131,)
        multiplier = current["direct_MBON32_multiplier"]
    references = {model.reference_pa(sid) for sid in ids}
    if len(references) != 1:
        raise AssertionError("B5 stimulation class has nonuniform reference scale")
    return ids, multiplier * references.pop()


def run_trial(circuit, seed: int, state: dict, onset_us: int, arm: str,
              level: str, protocol: dict) -> dict:
    model = SensoryRouteProbe(circuit, seed=seed)
    model.restore(state)
    initial_sha = digest(state)
    initial_boundary_sha = digest(model.boundary.checkpoint())
    lesion = protocol["arms"][arm]["functional_disconnection"]
    removed = model.apply_disconnection(lesion)
    targets, amplitude = target_and_current(circuit, model, arm, level, protocol)
    pulse_end = onset_us + protocol["pulse_duration_us"]
    post_end = onset_us + protocol["post_window_us"]
    pre_start = onset_us - protocol["pre_window_us"]
    if model.current_time_us != onset_us:
        raise AssertionError("Trial did not start at frozen baseline checkpoint")
    pre_spikes = [s for s in model.spikes if pre_start <= s[0] < onset_us]
    model.set_current(targets, amplitude)
    trace = [sample(model)]
    for t in range(onset_us + protocol["trace_interval_us"], post_end+1,
                   protocol["trace_interval_us"]):
        model.run_until(t)
        if t == pulse_end:
            model.clear_current()
        trace.append(sample(model))
    if np.any(model.injected_pa) or model.plasticity_enabled or model.dan_state != 0:
        raise AssertionError("B5 trial introduced persistent input or learning")
    post_spikes = [s for s in model.spikes if onset_us <= s[0] < post_end]
    event_trace = [e for e in model.delivered_event_log if onset_us <= e[0] < post_end]
    if any(not np.isfinite(row).all() for row in (model.v_mv, model.syn_pa, model.apl_local)):
        raise ArithmeticError("Nonfinite B5 neural state")
    return {"seed": seed, "onset_us": onset_us, "arm": arm, "level": level,
            "initial_state_sha256": initial_sha,
            "initial_boundary_sha256": initial_boundary_sha,
            "terminal_boundary_sha256": digest(model.boundary.checkpoint()),
            "stimulus": {"source_ids": targets, "amplitude_pa_per_cell": amplitude,
                         "start_us": onset_us, "end_us": pulse_end,
                         "evidence": "ENGINEERING ASSUMPTION"},
            "functional_disconnection": lesion,
            "removed_source_rows": removed,
            "source_anatomical_pairs_retained": len(circuit.connections),
            "pre_spikes_time_us_source_id": pre_spikes,
            "post_spikes_time_us_source_id": post_spikes,
            "delivered_events_time_us_pre_post_source_row_kind_amplitude": event_trace,
            "trace_columns": TRACE_COLUMNS, "trace": trace,
            "final_scheduled_events": model.sequence,
            "final_delivered_events": model.delivered,
            "final_queued_events": len(model.queue),
            "final_plasticity_enabled": model.plasticity_enabled,
            "final_dan_state": model.dan_state}


def run_seed(seed: int, protocol: dict, protocol_sha: str, code_hashes: dict) -> dict:
    started = time.monotonic()
    circuit = build_circuit()
    baseline = SensoryRouteProbe(circuit, seed=seed)
    trials = []
    replay_checks = 0
    try:
        for pulse_index, onset in enumerate(protocol["pulse_onsets_us"]):
            baseline.run_until(onset)
            state = baseline.checkpoint()
            if np.any(baseline.injected_pa) or baseline.spike_counts[
                    baseline.dynamic_of_source[519131]] != 0:
                raise AssertionError("Baseline was perturbed before pulse fork")
            schedule = [(arm, level) for level in protocol["primary_levels"]
                        for arm in ("A", "B", "C", "D")]
            schedule += [(arm, protocol["direct_probe_level"]) for arm in
                         ("E", "E_off", "F", "F_off")]
            for arm, level in schedule:
                trial = run_trial(circuit, seed, state, onset, arm, level, protocol)
                if pulse_index == 0:
                    replay = run_trial(circuit, seed, state, onset, arm, level, protocol)
                    if canonical(trial) != canonical(replay):
                        raise AssertionError(f"Deterministic first-pulse replay failed: {seed}/{arm}/{level}")
                    replay_checks += 1
                trials.append(trial)
            print(f"SEED {seed} pulse {pulse_index+1}/{len(protocol['pulse_onsets_us'])}", flush=True)
        payload = {"status": "complete", "seed": seed, "protocol_sha256": protocol_sha,
                   "model_config_sha256": circuit.config_sha256,
                   "code_sha256": code_hashes,
                   "baseline_reached_us": baseline.current_time_us,
                   "trial_count": len(trials), "deterministic_replay_checks": replay_checks,
                   "trials": trials, "elapsed_wall_seconds": time.monotonic()-started}
    except Exception as exc:
        payload = {"status": "error", "seed": seed, "protocol_sha256": protocol_sha,
                   "model_config_sha256": circuit.config_sha256, "code_sha256": code_hashes,
                   "baseline_reached_us": baseline.current_time_us,
                   "trial_count": len(trials), "deterministic_replay_checks": replay_checks,
                   "trials": trials, "error": repr(exc), "traceback": traceback.format_exc(),
                   "elapsed_wall_seconds": time.monotonic()-started}
    path = OUT / f"seed_{seed}.json.gz"
    write_gzip_json(path, payload)
    return {"seed": seed, "status": payload["status"], "file": path.name,
            "file_sha256": file_sha(path), "trials": len(trials),
            "replays": replay_checks, "error": payload.get("error"),
            "elapsed_wall_seconds": payload["elapsed_wall_seconds"]}


def main() -> None:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    protocol_sha = file_sha(PROTOCOL_PATH)
    if file_sha(MODEL_CONFIG_PATH) != protocol["electrical_model_config_sha256"]:
        raise RuntimeError("Frozen Electrical Model V1 config changed")
    if (protocol["boundary_seeds"] != [31001, 31002, 31003] or
            protocol["boundary_condition"] != "A" or
            protocol["boundary_level"] != "nominal" or
            len(protocol["pulse_onsets_us"]) != 10):
        raise RuntimeError("B5 schedule differs from frozen declaration")
    OUT.mkdir(parents=True, exist_ok=True)
    code_hashes = {str(path.relative_to(ROOT)): file_sha(path) for path in CODE_PATHS}
    meta = {"protocol": protocol, "protocol_sha256": protocol_sha,
            "model_config_sha256": file_sha(MODEL_CONFIG_PATH),
            "model_config": json.loads(MODEL_CONFIG_PATH.read_text(encoding="utf-8")),
            "code_sha256": code_hashes,
            "source_manifest": json.loads((ROOT / "data/processed/malecns_v1_electrical_v1/manifest.json").read_text()),
            "python": platform.python_version(), "numpy": np.__version__,
            "trace_columns": TRACE_COLUMNS,
            "interpretation": "task-independent causal diagnostic; no motor readout or plasticity"}
    write_json(OUT / "meta.json", meta)
    rows = {}
    with ProcessPoolExecutor(max_workers=3) as pool:
        futures = {}
        for seed in protocol["boundary_seeds"]:
            path = OUT / f"seed_{seed}.json.gz"
            if path.exists():
                raw = read_gzip_json(path)
                if (raw["status"] != "complete" or raw["protocol_sha256"] != protocol_sha or
                        raw["model_config_sha256"] != file_sha(MODEL_CONFIG_PATH) or
                        raw["code_sha256"] != code_hashes):
                    raise RuntimeError(f"Incompatible/incomplete saved seed: {seed}")
                rows[seed] = {"seed": seed, "status": "complete", "file": path.name,
                              "file_sha256": file_sha(path), "trials": raw["trial_count"],
                              "replays": raw["deterministic_replay_checks"],
                              "elapsed_wall_seconds": raw["elapsed_wall_seconds"]}
                print(f"RESUME seed {seed}", flush=True)
            else:
                futures[pool.submit(run_seed, seed, protocol, protocol_sha, code_hashes)] = seed
        for future in as_completed(futures):
            row = future.result()
            rows[row["seed"]] = row
            write_json(OUT / "status.json", {"protocol_sha256": protocol_sha,
                       "completed_seeds": sorted(seed for seed, r in rows.items() if r["status"] == "complete"),
                       "errors": {str(seed): r["error"] for seed, r in rows.items() if r["status"] == "error"}})
            print(f"DONE seed {row['seed']} {row['status']} trials={row['trials']}", flush=True)
    result = {"protocol_sha256": protocol_sha, "model_config_sha256": file_sha(MODEL_CONFIG_PATH),
              "rows": [rows[seed] for seed in protocol["boundary_seeds"]],
              "complete": all(rows[seed]["status"] == "complete" for seed in protocol["boundary_seeds"]),
              "trial_count": sum(rows[seed]["trials"] for seed in protocol["boundary_seeds"]),
              "replay_checks": sum(rows[seed]["replays"] for seed in protocol["boundary_seeds"])}
    write_json(OUT / "result.json", result)
    print(f"FINAL complete={result['complete']} trials={result['trial_count']} replay={result['replay_checks']}", flush=True)


if __name__ == "__main__":
    main()
