"""Locked B5.5 local first-spike transfer probes; never edits Electrical Model V1.1.

Counterfactual event trains are replayed into exact frozen passive KC equations
from independently re-created neutral checkpoints. The local model stops at
each KC's first threshold crossing, before any APL/network feedback can be
interpreted. All original source rows, counts, and amplitude are retained in
timing probes. This is a sensitivity experiment, not a production simulation.
"""

from __future__ import annotations

from collections import defaultdict
import gzip
import json
import math
from pathlib import Path
import platform

import numpy as np

from project_b.electrical_v1 import build_circuit
from project_b.electrical_v1.source import file_sha
from project_b.electrical_v1.visual_boundary_probe import VisualBoundaryProbe
from run_electrical_v1_1_visual_boundary_validation import digest, shared_state


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/b5_5_visual_kc_transfer_decomposition.json"
CONFIG = ROOT / "configs/electrical_model_v1_1.json"
OUT = ROOT / "docs/figures/b5_5_visual_kc_transfer_decomposition"


def read_gzip(path: Path) -> dict:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return json.load(stream)


def save_gzip(path: Path, data: object) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as stream:
        json.dump(data, stream, sort_keys=True, separators=(",", ":"), allow_nan=False)
        stream.write("\n")


def remap(events: list[list], factor: int | str, tick: int) -> list[list]:
    """Per-KC fixed first/last midpoint; retain amplitude, row and multiplicity."""
    if not events:
        return []
    times = [e[0] for e in events]
    center = (min(times) + max(times)) / 2
    out = []
    for t, pre, row, amplitude in events:
        new_t = center if factor == "synchronous" else center + (t - center) / factor
        aligned = int(round(new_t / tick) * tick)
        out.append([aligned, pre, row, amplitude])
    return out


def passive_trace(ids: list[int], events: dict[int, list[list]], onset_us: int,
                  model: VisualBoundaryProbe, window_us: int) -> np.ndarray:
    """Exact V1.1 analytic current/LIF recurrence at frozen threshold ticks."""
    tick = model.tick_us
    steps = window_us // tick
    index = {sid: j for j, sid in enumerate(ids)}
    impulse = np.zeros((steps, len(ids)), dtype=float)
    for sid, rows in events.items():
        j = index[sid]
        for t, _, _, amp in rows:
            offset = t - onset_us
            if offset < 0 or offset >= window_us or offset % tick:
                raise AssertionError("Counterfactual arrival outside frozen tick/window")
            impulse[offset // tick, j] += amp
    dynamic = [model.dynamic_of_source[sid] for sid in ids]
    v = model.v_mv[dynamic].copy()
    syn = model.syn_pa[dynamic].copy()
    rest = model.rest_mv[dynamic]
    cap = model.cap_pf[dynamic]
    leak = model.leak_ns[dynamic]
    a = np.exp(-(tick / 1000) * leak / cap)
    decay = math.exp(-tick / model.tau_syn_us)
    diff = leak / cap - 1000 / model.tau_syn_us
    # The exact synaptic-current contribution for one tick in mV/pA.
    factor = np.where(np.isclose(diff, 0, atol=1e-12),
                      (tick / 1000) * a / cap,
                      (decay - a) / (cap * np.where(np.isclose(diff, 0, atol=1e-12), 1, diff)))
    trace = np.empty((steps, len(ids)), dtype=float)
    for step in range(steps):
        if step:
            v = rest + (v - rest) * a + syn * factor
            syn *= decay
        trace[step] = v
        syn += impulse[step]
    return trace


def results_for_trace(trace: np.ndarray, ids: list[int], onset_us: int,
                      model: VisualBoundaryProbe, multipliers: list[int]) -> dict[int, dict]:
    dynamic = [model.dynamic_of_source[sid] for sid in ids]
    rest = model.rest_mv[dynamic]
    threshold = model.onset_mv[dynamic]
    running_peak = np.maximum.accumulate(trace, axis=0)
    cols = np.arange(len(ids))
    output = {sid: {} for sid in ids}
    for multiplier in multipliers:
        scaled = rest[None, :] + multiplier * (trace - rest[None, :])
        crossed = scaled >= threshold[None, :] - 1e-12
        has_crossed = crossed.any(axis=0)
        first_index = np.argmax(crossed, axis=0)
        last_index = np.where(has_crossed, first_index, len(trace) - 1)
        peak = rest + multiplier * (running_peak[last_index, cols] - rest)
        for col, sid in enumerate(ids):
            signed_gap = float(threshold[col] - peak[col])
            output[sid][str(multiplier)] = {
                "first_spike_time_us": int(onset_us + first_index[col] * model.tick_us)
                                       if has_crossed[col] else None,
                "peak_voltage_before_first_spike_or_window_end_mv": float(peak[col]),
                "minimum_threshold_gap_mv_clamped": max(0.0, signed_gap),
                "signed_threshold_gap_at_peak_mv": signed_gap,
            }
    return output


def main() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if file_sha(CONFIG) != protocol["v1_1_config_sha256"] or file_sha(
            ROOT / "configs/electrical_model_v1.json") != protocol["v1_config_sha256"]:
        raise AssertionError("Frozen electrical configuration drifted")
    for name, sha in protocol["observed_before_probe_sha256"].items():
        if file_sha(OUT / name) != sha:
            raise AssertionError(f"Pre-matrix observed file drifted: {name}")
    circuit = build_circuit(CONFIG)
    meta = json.loads((OUT / "observed_meta.json").read_text(encoding="utf-8"))
    ids = sorted(c.source_id for c in circuit.cells if c.kind == "KC")
    assert len(ids) == 107
    ladder = protocol["families"]["amplitude"]["multipliers"]
    compression = protocol["families"]["compression"]["factors"]
    tick = protocol["integration_tick_us"]
    window = protocol["observation_window_us"]
    result_files = {}
    for seed in protocol["seeds"]:
        baseline = VisualBoundaryProbe(circuit, seed=seed)
        observed = read_gzip(OUT / f"observed_seed_{seed}.json.gz")
        trials = []
        for trial in observed["trials"]:
            onset = trial["onset_us"]
            baseline.run_until(onset)
            if digest(shared_state(baseline)) != trial["initial_shared_state_sha256"]:
                raise AssertionError("Neutral-state replay mismatch")
            for sid in ids:
                i = baseline.dynamic_of_source[sid]
                if (abs(baseline.v_mv[i] - baseline.rest_mv[i]) > 1e-12 or
                        baseline.syn_pa[i] != 0 or baseline.apl_local[i] != 0 or
                        baseline.refractory_until_us[i] > onset):
                    raise AssertionError("Local passive KC initial-state condition invalid")
            original = {r["source_id"]: r["events_time_pre_source_row_amplitude"]
                        for r in trial["kc"]}
            events = {sid: original[sid] for sid in ids}
            reference_charge = {sid: 5 * sum(e[3] for e in events[sid]) for sid in ids}
            reference_count = {sid: len(events[sid]) for sid in ids}
            rows = {sid: {"source_id": sid,
                          "cohort": next(r["cohort"] for r in trial["kc"] if r["source_id"] == sid),
                          "source_events": reference_count[sid],
                          "infinite_horizon_charge_fc": reference_charge[sid],
                          "families": {}} for sid in ids}
            for family in ("observed", *[f"compression_{f}" for f in compression], "synchronous"):
                if family == "observed":
                    current = events
                    multipliers = ladder
                else:
                    remap_factor = "synchronous" if family == "synchronous" else int(family.split("_")[1])
                    current = {sid: remap(events[sid], remap_factor, tick) for sid in ids}
                    multipliers = [1]
                for sid in ids:
                    if len(current[sid]) != reference_count[sid] or abs(
                            5 * sum(e[3] for e in current[sid]) - reference_charge[sid]) > 1e-10:
                        raise AssertionError("Timing probe violated count/charge conservation")
                trace = passive_trace(ids, current, onset, baseline, window)
                results = results_for_trace(trace, ids, onset, baseline, multipliers)
                for sid in ids:
                    rows[sid]["families"][family] = {
                        "events_time_pre_source_row_amplitude": current[sid],
                        "multipliers": results[sid],
                    }
            for r in trial["kc"]:
                sid = r["source_id"]
                observed_result = rows[sid]["families"]["observed"]["multipliers"]["1"]
                if (observed_result["first_spike_time_us"] is not None or
                        abs(observed_result["peak_voltage_before_first_spike_or_window_end_mv"] -
                            r["peak_voltage_mv"]) > 1e-10):
                    raise AssertionError("Observed local transfer diverged from saved B5.4")
                amplitude = rows[sid]["families"]["observed"]["multipliers"]
                rows[sid]["minimum_tested_amplitude_multiplier_for_first_spike"] = next(
                    (m for m in ladder if amplitude[str(m)]["first_spike_time_us"] is not None), None)
                rows[sid]["continuous_passive_critical_amplitude_multiplier"] = r[
                    "critical_multiplier_linear"]
                rows[sid]["minimum_finite_compression_for_first_spike"] = next(
                    (f for f in compression if rows[sid]["families"][f"compression_{f}"][
                        "multipliers"]["1"]["first_spike_time_us"] is not None), None)
                rows[sid]["synchronous_upper_bound_spikes"] = rows[sid]["families"][
                    "synchronous"]["multipliers"]["1"]["first_spike_time_us"] is not None
            trials.append({"seed": seed, "onset_us": onset,
                           "neutral_state_sha256": trial["initial_shared_state_sha256"],
                           "kc": [rows[sid] for sid in ids]})
        path = OUT / f"diagnostic_seed_{seed}.json.gz"
        save_gzip(path, {"seed": seed, "trials": trials,
                         "protocol_sha256": file_sha(PROTOCOL)})
        result_files[str(seed)] = file_sha(path)
    index = {"stage": "B5.5", "protocol_sha256": file_sha(PROTOCOL),
             "config_sha256": file_sha(CONFIG), "source_parent_hashes": circuit.parent_hashes,
             "python": platform.python_version(), "numpy": np.__version__,
             "seeds": protocol["seeds"], "nominal_trials": 30, "kc_rows": 3210,
             "diagnostic_file_sha256": result_files,
             "runner_sha256": file_sha(Path(__file__))}
    (OUT / "result.json").write_text(json.dumps(index, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    print(json.dumps({"status": "complete", "nominal_trials": 30,
                      "kc_rows": 3210, "seed_files": result_files}, sort_keys=True))


if __name__ == "__main__":
    main()
