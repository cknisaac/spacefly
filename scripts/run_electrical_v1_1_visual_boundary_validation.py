"""Run the locked B5.4 V1/V1.1 sensory-entry comparison, without learning."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, is_dataclass
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import traceback

import numpy as np

from project_b.electrical_v1 import build_circuit
from project_b.electrical_v1.source import ADDED_VISUAL_IDS, file_sha
from project_b.electrical_v1.visual_boundary_probe import VisualBoundaryProbe


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "configs/electrical_v1_1_visual_boundary_validation.json"
V1_CONFIG = ROOT / "configs/electrical_model_v1.json"
V11_CONFIG = ROOT / "configs/electrical_model_v1_1.json"
B5_PROTOCOL = ROOT / "configs/electrical_v1_sensory_route_causality.json"
OUT = ROOT / "docs/figures/electrical_v1_1_visual_boundary_validation"
B5_OUT = ROOT / "docs/figures/electrical_v1_sensory_route_causality"
CODE_PATHS = [ROOT / p for p in (
    "src/project_b/electrical_v1/source.py", "src/project_b/electrical_v1/runtime.py",
    "src/project_b/electrical_v1/sensory_route_probe.py",
    "src/project_b/electrical_v1/visual_boundary_probe.py",
    "src/project_b/electrical_v1/boundary.py",
    "scripts/run_electrical_v1_1_visual_boundary_validation.py")]
OLD_VISUAL = (13285, 13707, 13874)
ARMS = ("v1_reference", "v1_1_connected", "v1_1_disconnected")
LEVELS = ("low", "nominal", "high")
TRACE_COLUMNS = ("time_us", "MBON32_voltage_mv", "MBON32_synaptic_pa",
                 "DNa03_voltage_mv", "DNa02_voltage_mv", "DNa03_synaptic_pa",
                 "DNa02_synaptic_pa", "DNa03_boundary_pa", "DNa02_boundary_pa",
                 "APL_local_max", "queue_length")


def canonical(value) -> bytes:
    def encode(other):
        if is_dataclass(other):
            return asdict(other)
        raise TypeError(f"Cannot canonically encode {type(other).__name__}")
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      allow_nan=False, default=encode).encode()


def digest(value) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def write_json(path: Path, value: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(canonical(value) + b"\n")
    os.replace(tmp, path)


def write_gzip(path: Path, value: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=0) as zipped:
        zipped.write(canonical(value) + b"\n")
    os.replace(tmp, path)


def read_gzip(path: Path) -> dict:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return json.load(stream)


def shared_state(model: VisualBoundaryProbe) -> dict:
    """Canonical common-source state across V1/117-body index layouts."""
    cells = []
    for sid in sorted(set(model.source_ids) - set(ADDED_VISUAL_IDS)):
        i = model.dynamic_of_source[sid]
        cells.append((sid, float(model.v_mv[i]), float(model.syn_pa[i]),
                      int(model.refractory_until_us[i]), int(model.spike_counts[i]),
                      float(model.apl_local[i]), int(model.refractory_time_us[i])))
    queued = sorted((t, model.source_ids[post], model.source_ids[pre], source_row,
                     kind, amplitude) for t, post, pre, source_row, _, kind, amplitude in model.queue)
    return {"time_us": model.current_time_us, "cells": cells,
            "boundary": model.boundary.checkpoint(),
            "queue": queued, "spikes": model.spikes,
            "apl_calyx": model.apl_calyx, "dan_state": model.dan_state,
            "dn_refractory_bins_us": model.dn_refractory_bins_us}


def trace_row(model: VisualBoundaryProbe) -> list:
    m = model.dynamic_of_source[519131]
    d3, d2 = model.dn3, model.dn2
    b3, b2 = model.boundary.currents_pa(*model.dn_reference_pa)
    return [model.current_time_us, float(model.v_mv[m]), float(model.syn_pa[m]),
            float(model.v_mv[d3]), float(model.v_mv[d2]),
            float(model.syn_pa[d3]), float(model.syn_pa[d2]),
            b3, b2, float(np.max(model.apl_local)), len(model.queue)]


def run_trial(circuit, seed: int, state: dict, onset: int, arm: str, level: str,
              protocol: dict, shared_sha: str) -> dict:
    model = VisualBoundaryProbe(circuit, seed=seed)
    model.restore(state)
    if digest(shared_state(model)) != shared_sha or model.current_time_us != onset:
        raise AssertionError("Matched initial common-source state changed")
    removed = model.apply_disconnection("aMe12_to_KC") if arm == "v1_1_disconnected" else ()
    source_ids = OLD_VISUAL if arm == "v1_reference" else tuple(sorted(OLD_VISUAL + ADDED_VISUAL_IDS))
    amplitude = protocol["visual_levels"][level] * protocol["visual_reference_pa_per_cell"]
    if {model.reference_pa(sid) for sid in source_ids} != {15.0}:
        raise AssertionError("Stimulus reference drifted")
    model.set_current(source_ids, amplitude)
    end_pulse = onset + protocol["pulse_duration_us"]
    end_trial = onset + protocol["post_window_us"]
    trace = [trace_row(model)]
    for t in range(onset + 10_000, end_trial + 1, 10_000):
        model.run_until(t)
        if t == end_pulse:
            model.clear_current()
        trace.append(trace_row(model))
    if np.any(model.injected_pa) or model.plasticity_enabled or model.dan_state != 0:
        raise AssertionError("B5.4 produced persistent input or learning")
    spikes = [s for s in model.spikes if onset <= s[0] < end_trial]
    events = [e for e in model.delivered_event_log if onset <= e[0] < end_trial]
    kcs = tuple(sorted(c.source_id for c in circuit.cells if c.kind == "KC"))
    kc_spikes = {str(sid): [t for t, spiked in spikes if spiked == sid] for sid in kcs}
    kc_events = {sid: [] for sid in kcs}
    for event in events:
        t, pre, post, row, kind, amplitude_event = event
        if kind == "FAST" and pre in source_ids and post in kc_events:
            kc_events[post].append(event)
    tau_ms = model.tau_syn_us/1000
    kcs_out = []
    for sid in kcs:
        i = model.dynamic_of_source[sid]
        charge = sum(e[5] * tau_ms * (1-math.exp(-(end_trial-e[0])/model.tau_syn_us))
                     for e in kc_events[sid])
        peak = float(model.peak_voltage_mv[i])
        kcs_out.append({"source_id": sid, "visual_event_count": len(kc_events[sid]),
                        "visual_charge_fc": charge, "peak_synaptic_pa": float(model.peak_synaptic_pa[i]),
                        "peak_voltage_mv": peak,
                        "closest_onset_margin_mv": float(model.onset_mv[i] - peak),
                        "spike_times_us": kc_spikes[str(sid)],
                        "peak_apl_local": float(model.peak_apl_local[i])})
    m = model.dynamic_of_source[519131]
    visual_spikes = {str(sid): [t for t, spiked in spikes if spiked == sid] for sid in
                     sorted(OLD_VISUAL + ADDED_VISUAL_IDS)}
    return {"seed": seed, "onset_us": onset, "level": level, "arm": arm,
            "initial_shared_state_sha256": shared_sha,
            "initial_boundary_sha256": digest(state["boundary"]),
            "terminal_boundary_sha256": digest(model.boundary.checkpoint()),
            "source_anatomical_pairs_retained": len(circuit.connections),
            "stimulus": {"source_ids": source_ids, "amplitude_pa_per_cell": amplitude,
                         "start_us": onset, "end_us": end_pulse,
                         "evidence": "ENGINEERING ASSUMPTION"},
            "functional_disconnection": "aMe12_to_KC" if arm == "v1_1_disconnected" else "none",
            "removed_source_rows": removed,
            "visual_spike_times_us_by_source_id": visual_spikes,
            "post_spikes_time_us_source_id": spikes,
            "delivered_events_time_us_pre_post_source_row_kind_amplitude": events,
            "KC": kcs_out,
            "KC_receiving_visual_count": sum(bool(x["visual_event_count"]) for x in kcs_out),
            "KC_spiking_count": sum(bool(x["spike_times_us"]) for x in kcs_out),
            "APL_peak_local_state": float(np.max(model.peak_apl_local)),
            "MBON32_spike_times_us": [t for t, sid in spikes if sid == 519131],
            "MBON32_peak_voltage_mv": float(model.peak_voltage_mv[m]),
            "MBON32_closest_onset_margin_mv": float(model.onset_mv[m]-model.peak_voltage_mv[m]),
            "DN_spike_times_us_by_id": {str(sid): [t for t, spiked in spikes if spiked == sid]
                                        for sid in (519624, 523769)},
            "trace_columns": TRACE_COLUMNS, "trace": trace,
            "final_scheduled_events": model.sequence,
            "final_delivered_events": model.delivered,
            "final_queued_events": len(model.queue),
            "peak_queued_events": model.peak_queued,
            "final_dan_state": model.dan_state,
            "final_plasticity_enabled": model.plasticity_enabled}


def run_seed(seed: int, protocol: dict, protocol_sha: str, code_hashes: dict) -> dict:
    old = build_circuit()
    new = build_circuit(V11_CONFIG)
    old_base = VisualBoundaryProbe(old, seed=seed)
    new_base = VisualBoundaryProbe(new, seed=seed)
    b5 = read_gzip(B5_OUT / f"seed_{seed}.json.gz")
    reference = {(r["onset_us"], r["level"]): r for r in b5["trials"] if r["arm"] == "A"}
    trials = []
    replay_checks = 0
    reference_checks = 0
    try:
        for onset in protocol["pulse_onsets_us"]:
            old_base.run_until(onset)
            new_base.run_until(onset)
            old_shared = digest(shared_state(old_base))
            new_shared = digest(shared_state(new_base))
            if old_shared != new_shared or old_base.boundary.checkpoint() != new_base.boundary.checkpoint():
                raise AssertionError(f"V1 and V1.1 neutral baseline diverged at {seed}/{onset}")
            states = {"v1_reference": old_base.checkpoint(),
                      "v1_1_connected": new_base.checkpoint(),
                      "v1_1_disconnected": new_base.checkpoint()}
            for level in LEVELS:
                for arm in ARMS:
                    circuit = old if arm == "v1_reference" else new
                    result = run_trial(circuit, seed, states[arm], onset, arm, level,
                                       protocol, old_shared)
                    if arm == "v1_reference":
                        original = reference[(onset, level)]
                        if (canonical(result["post_spikes_time_us_source_id"]) !=
                                canonical(original["post_spikes_time_us_source_id"]) or
                                canonical(result["delivered_events_time_us_pre_post_source_row_kind_amplitude"]) !=
                                canonical(original["delivered_events_time_us_pre_post_source_row_kind_amplitude"])):
                            raise AssertionError("V1 reference did not reproduce B5 spike/event records")
                        reference_checks += 1
                    if onset == protocol["pulse_onsets_us"][0]:
                        replay = run_trial(circuit, seed, states[arm], onset, arm, level,
                                           protocol, old_shared)
                        if canonical(result) != canonical(replay):
                            raise AssertionError("First-pulse deterministic replay failed")
                        replay_checks += 1
                    trials.append(result)
            print(f"B5.4 seed {seed} onset {onset}", flush=True)
        payload = {"status": "complete", "seed": seed,
                   "protocol_sha256": protocol_sha,
                   "config_sha256": {"v1": old.config_sha256, "v1_1": new.config_sha256},
                   "code_sha256": code_hashes, "reference_checks": reference_checks,
                   "replay_checks": replay_checks, "trials": trials}
    except Exception as exc:
        payload = {"status": "error", "seed": seed, "protocol_sha256": protocol_sha,
                   "config_sha256": {"v1": old.config_sha256, "v1_1": new.config_sha256},
                   "code_sha256": code_hashes, "reference_checks": reference_checks,
                   "replay_checks": replay_checks, "trials": trials,
                   "error": repr(exc), "traceback": traceback.format_exc()}
    path = OUT / f"seed_{seed}.json.gz"
    write_gzip(path, payload)
    return {"seed": seed, "status": payload["status"], "file": path.name,
            "file_sha256": file_sha(path), "trials": len(trials),
            "reference_checks": reference_checks, "replay_checks": replay_checks,
            "error": payload.get("error")}


def main() -> None:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    protocol_sha = file_sha(PROTOCOL_PATH)
    if (file_sha(V1_CONFIG) != protocol["v1_config_sha256"] or
            file_sha(V11_CONFIG) != protocol["v1_1_config_sha256"] or
            file_sha(B5_PROTOCOL) != protocol["b5_protocol_sha256"] or
            tuple(protocol["boundary_seeds"]) != (31001, 31002, 31003) or
            tuple(protocol["arms"]) != ARMS or tuple(protocol["visual_levels"]) != LEVELS):
        raise RuntimeError("B5.4 locked source/protocol changed")
    manifest = json.loads((ROOT / protocol["v1_1_manifest"]).read_text(encoding="utf-8"))
    if manifest["config_sha256"] != protocol["v1_1_config_sha256"]:
        raise RuntimeError("V1.1 built manifest changed")
    OUT.mkdir(parents=True, exist_ok=True)
    code_hashes = {str(path.relative_to(ROOT)): file_sha(path) for path in CODE_PATHS}
    write_json(OUT / "meta.json", {"protocol": protocol, "protocol_sha256": protocol_sha,
                                   "code_sha256": code_hashes, "v1_1_manifest": manifest,
                                   "python": platform.python_version(), "numpy": np.__version__})
    rows = {}
    with ProcessPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(run_seed, seed, protocol, protocol_sha, code_hashes): seed
                   for seed in protocol["boundary_seeds"]}
        for future in as_completed(futures):
            row = future.result()
            rows[row["seed"]] = row
            write_json(OUT / "status.json", {"completed_seeds": sorted(
                seed for seed, value in rows.items() if value["status"] == "complete"),
                "errors": {str(seed): value["error"] for seed, value in rows.items()
                           if value["status"] == "error"}})
            print(f"B5.4 done {row['seed']} {row['status']} {row['trials']} trials", flush=True)
    result = {"protocol_sha256": protocol_sha,
              "rows": [rows[seed] for seed in protocol["boundary_seeds"]],
              "complete": all(rows[seed]["status"] == "complete" for seed in protocol["boundary_seeds"]),
              "trial_count": sum(rows[seed]["trials"] for seed in protocol["boundary_seeds"]),
              "reference_checks": sum(rows[seed]["reference_checks"] for seed in protocol["boundary_seeds"]),
              "replay_checks": sum(rows[seed]["replay_checks"] for seed in protocol["boundary_seeds"])}
    write_json(OUT / "result.json", result)
    print(json.dumps(result, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
