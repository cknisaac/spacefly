"""B5.1: reconstruct silent feedforward cells from saved B5 arrivals.

This script does not alter the V1 runtime or select a production parameter.
The transfer panel is read from the locked B5.1 protocol and is local to a
single postsynaptic cell before its first spike.
"""

from __future__ import annotations

from collections import defaultdict
import gzip
import hashlib
import json
import math
from pathlib import Path
import platform
import statistics

import numpy as np

from project_b.electrical_v1 import build_circuit
from project_b.electrical_v1.source import file_sha


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/electrical_v1_feedforward_drive_adequacy.json"
B5_PROTOCOL = ROOT / "configs/electrical_v1_sensory_route_causality.json"
B5 = ROOT / "docs/figures/electrical_v1_sensory_route_causality"
OUT = ROOT / "docs/figures/electrical_v1_feedforward_drive_adequacy"
VISUAL = {13285, 13707, 13874}
MBON = 519131


def save(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n",
                    encoding="utf-8")


def percentile(values: list[float], q: float) -> float | None:
    return float(np.percentile(values, q)) if values else None


def describe(values: list[float]) -> dict:
    return {"n": len(values), "min": min(values) if values else None,
            "p25": percentile(values, 25), "median": percentile(values, 50),
            "p75": percentile(values, 75), "max": max(values) if values else None}


def remap_time(time_us: int, onset_us: int, timing: str) -> int:
    if timing == "observed":
        return time_us
    if timing == "bin20ms_midpoint":
        return onset_us + ((time_us - onset_us) // 20000) * 20000 + 10000
    if timing == "single_volley_100ms":
        return onset_us + 100000
    raise AssertionError(timing)


def reconstruct(source_ids: list[int], events: dict[int, list], onset_us: int,
                circuit, timing: str, multipliers: list[float], tick_us: int,
                window_us: int) -> dict[int, dict]:
    """Exact passive pre-first-spike V1 recurrence at its 500-us tick.

    Charge is the analytical integral of the decaying current over each tick.
    No target has initial activity, boundary current, or APL current in the
    named observed B5 condition. A diagnostic spike stops the local model;
    feedback after that spike cannot change its first-spike threshold.
    """
    ids = list(source_ids)
    steps = window_us // tick_us
    currents = np.zeros((steps + 1, len(ids)), dtype=float)
    for col, sid in enumerate(ids):
        for event in events.get(sid, []):
            new_time = remap_time(int(event[0]), onset_us, timing)
            offset = new_time - onset_us
            if offset < 0 or offset >= window_us or offset % tick_us:
                raise AssertionError("Nonaligned or out-of-window diagnostic arrival")
            currents[offset // tick_us, col] += float(event[5])
    config = circuit.config
    tau_syn_ms = config["timing"]["synaptic_decay_us"]["value"] / 1000.0
    dt_ms = tick_us / 1000.0
    decay = math.exp(-dt_ms / tau_syn_ms)
    kinds = {c.source_id: c.kind for c in circuit.cells}
    params = config["spiking_classes"]
    cap = np.array([params[kinds[s]]["capacitance_pf"]["value"] for s in ids], float)
    leak = np.array([params[kinds[s]]["leak_ns"]["value"] for s in ids], float)
    rest = np.array([params[kinds[s]]["rest_mv"]["value"] for s in ids], float)
    onset = np.array([params[kinds[s]]["onset_mv"]["value"] for s in ids], float)
    iref = leak * (onset - rest)
    tau_m_ms = cap / leak
    a = np.exp(-dt_ms / tau_m_ms)
    diff = 1.0 / tau_m_ms - 1.0 / tau_syn_ms
    factor = np.where(np.isclose(diff, 0, atol=1e-12),
                      dt_ms * a / cap,
                      (decay - a) / (cap * np.where(np.isclose(diff, 0, atol=1e-12), 1.0, diff)))
    v = rest.copy()
    syn = np.zeros(len(ids), float)
    peak_v = rest.copy()
    peak_time = np.full(len(ids), onset_us, np.int64)
    syn_at_peak = np.zeros(len(ids), float)
    charge_at_peak = np.zeros(len(ids), float)
    peak_syn = np.zeros(len(ids), float)
    peak_syn_time = np.full(len(ids), onset_us, np.int64)
    charge = np.zeros(len(ids), float)
    first_spike = {float(m): np.full(len(ids), -1, np.int64) for m in multipliers if m > 0}
    # The frozen cell equation is linear until first threshold crossing.
    for step in range(steps + 1):
        t = onset_us + step * tick_us
        if step:
            old_syn = syn.copy()
            v = rest + (v - rest) * a + old_syn * factor
            syn *= decay
            charge += old_syn * tau_syn_ms * (1 - decay)
        # V1 tests threshold before arrivals on the exact tick. Record at
        # t<window end, matching B5's half-open post interval.
        if step < steps:
            better = v > peak_v
            peak_v[better] = v[better]
            peak_time[better] = t
            syn_at_peak[better] = syn[better]
            charge_at_peak[better] = charge[better]
            for m, first in first_spike.items():
                fired = (first < 0) & (rest + m * (v - rest) >= onset - 1e-12)
                first[fired] = t
            syn += currents[step]
            higher = syn > peak_syn
            peak_syn[higher] = syn[higher]
            peak_syn_time[higher] = t
    out = {}
    for col, sid in enumerate(ids):
        ev = events.get(sid, [])
        times = sorted(int(e[0]) for e in ev)
        if ev:
            impulse = sum(float(e[5]) for e in ev)
            by_time = defaultdict(float)
            for e in ev:
                by_time[int(e[0])] += float(e[5])
            unique_times = sorted(by_time)
            best_5ms = max(sum(amp for t, amp in by_time.items() if start <= t < start + 5000)
                           for start in unique_times)
        else:
            impulse = 0.0
            unique_times = []
            best_5ms = 0.0
        depol = float(peak_v[col] - rest[col])
        critical = float((onset[col] - rest[col]) / depol) if depol > 1e-12 else None
        first_panel = next((float(m) for m in multipliers if m > 0 and first_spike[float(m)][col] >= 0), None)
        previous_panel = (max((float(m) for m in multipliers if m < first_panel), default=None)
                          if first_panel is not None else None)
        out[sid] = {
            "event_count": len(ev), "event_impulse_pa": impulse,
            "first_arrival_us": times[0] if times else None,
            "last_arrival_us": times[-1] if times else None,
            "arrival_span_us": times[-1] - times[0] if times else None,
            "distinct_arrival_ticks": len(unique_times),
            "max_same_tick_impulse_pa": max(by_time.values()) if ev else 0.0,
            "best_5ms_impulse_fraction": best_5ms / impulse if impulse else None,
            "interarrival_us_median": statistics.median(b-a for a, b in zip(unique_times, unique_times[1:]))
            if len(unique_times) > 1 else None,
            "rest_mv": float(rest[col]), "onset_mv": float(onset[col]),
            "iref_pa": float(iref[col]), "peak_fast_current_pa": float(peak_syn[col]),
            "peak_fast_current_time_us": int(peak_syn_time[col]),
            "fast_charge_fc": float(charge[col]),
            "peak_voltage_mv": float(peak_v[col]), "closest_time_us": int(peak_time[col]),
            "fast_current_pa_at_closest": float(syn_at_peak[col]),
            "leak_current_pa_at_closest": float(-leak[col] * (peak_v[col] - rest[col])),
            "fast_charge_fc_to_closest": float(charge_at_peak[col]),
            "leak_charge_fc_to_closest": float(cap[col] * (peak_v[col] - rest[col]) - charge_at_peak[col]),
            "minimum_threshold_distance_mv": float(onset[col] - peak_v[col]),
            "peak_depolarization_mv": depol, "terminal_voltage_mv": float(v[col]),
            "leak_charge_fc": float(cap[col] * (v[col] - rest[col]) - charge[col]),
            "apl_charge_fc": 0.0, "refractory_time_us": 0,
            "critical_multiplier_linear": critical,
            "first_tested_spiking_multiplier": first_panel,
            "previous_nonspiking_multiplier": previous_panel,
            "first_spike_time_us_at_first_panel": int(first_spike[first_panel][col]) if first_panel is not None else None,
        }
    return out


def main() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    b5_protocol = json.loads(B5_PROTOCOL.read_text(encoding="utf-8"))
    if file_sha(B5_PROTOCOL) != protocol["b5_protocol_sha256"]:
        raise RuntimeError("B5 protocol drifted")
    circuit = build_circuit()
    if circuit.config_sha256 != protocol["electrical_model_config_sha256"]:
        raise RuntimeError("Electrical Model V1 drifted")
    source_kinds = {c.source_id: c.kind for c in circuit.cells}
    kcs = sorted(sid for sid, kind in source_kinds.items() if kind == "KC")
    if len(kcs) != 107:
        raise AssertionError("KC count drifted")
    visual_edges = {c.source_row: c for c in circuit.connections
                    if circuit.cells[c.pre].source_id in VISUAL and circuit.cells[c.post].kind == "KC"}
    kc_mbon_edges = {c.source_row: c for c in circuit.connections
                     if circuit.cells[c.pre].kind == "KC" and circuit.cells[c.post].source_id == MBON}
    if len(visual_edges) != 76 or len(kc_mbon_edges) != 105:
        raise AssertionError("Route source-row count drifted")
    contacts = {sid: 0 for sid in kcs}
    pairs = {sid: 0 for sid in kcs}
    for edge in visual_edges.values():
        sid = circuit.cells[edge.post].source_id
        contacts[sid] += edge.contacts
        pairs[sid] += 1
    mbon_contacts = sum(e.contacts for e in kc_mbon_edges.values())
    panel = protocol["transfer_function"]["input_multiplier_panel"]
    regimes = protocol["transfer_function"]["timing_regimes"]
    trials = []
    event_checks = 0
    for seed in protocol["source_conditions"]["visual_to_KC"]["seeds"]:
        with gzip.open(B5 / f"seed_{seed}.json.gz", "rt", encoding="utf-8") as f:
            raw = json.load(f)
        if raw["status"] != "complete" or raw["protocol_sha256"] != file_sha(B5_PROTOCOL):
            raise AssertionError("B5 saved seed incomplete or mismatched")
        for trial in raw["trials"]:
            if not ((trial["arm"] == "A" and trial["level"] in ("low", "nominal", "high")) or
                    (trial["arm"] == "E" and trial["level"] == "direct_3x")):
                continue
            onset_us = trial["onset_us"]
            stage = "visual_to_KC" if trial["arm"] == "A" else "KC_to_MBON32"
            targets = kcs if stage == "visual_to_KC" else [MBON]
            edge_map = visual_edges if stage == "visual_to_KC" else kc_mbon_edges
            by_target = defaultdict(list)
            presyn_spikes = {(t, sid) for t, sid in trial["post_spikes_time_us_source_id"]}
            for event in trial["delivered_events_time_us_pre_post_source_row_kind_amplitude"]:
                t, pre, post, row, kind, amp = event
                if kind != "FAST" or row not in edge_map:
                    continue
                edge = edge_map[row]
                if (pre != circuit.cells[edge.pre].source_id or
                        post != circuit.cells[edge.post].source_id or
                        abs(amp - edge.weight_pa) > 1e-12 or
                        (t - b5_protocol["stage_criteria"]["chemical_delay_us"], pre) not in presyn_spikes):
                    raise AssertionError("B5 event failed source-row/amplitude/causality check")
                by_target[post].append(event)
                event_checks += 1
            if any(post in targets for _, post in trial["post_spikes_time_us_source_id"]):
                raise AssertionError("Postsynaptic spiking invalidates passive B5 reconstruction")
            if any(post in targets for _, _, post, _, kind, _ in trial["delivered_events_time_us_pre_post_source_row_kind_amplitude"]
                   if kind == "APL_INPUT"):
                raise AssertionError("Unexpected APL input in named stage")
            results = {regime: reconstruct(targets, by_target, onset_us, circuit, regime, panel,
                                           protocol["tick_us"], protocol["measurement_window_us"])
                       for regime in regimes}
            for sid in targets:
                for regime in regimes:
                    r = results[regime][sid]
                    r["source_id"] = sid
                    r["anatomical_contact_count"] = contacts[sid] if stage == "visual_to_KC" else mbon_contacts
                    r["anatomical_pair_count"] = pairs[sid] if stage == "visual_to_KC" else len(kc_mbon_edges)
                    r["meaningful_drive"] = (r["event_count"] > 0 and
                        r["peak_fast_current_pa"] >= 0.1 * r["iref_pa"])
            trials.append({"seed": seed, "onset_us": onset_us, "stage": stage,
                           "level": trial["level"], "stimulus": trial["stimulus"],
                           "observed_apl_local_max": max(row[8] for row in trial["trace"]),
                           "results_by_timing": {regime: [results[regime][sid] for sid in targets]
                                                 for regime in regimes}})
    OUT.mkdir(parents=True, exist_ok=True)
    result = {"protocol_sha256": file_sha(PROTOCOL), "b5_protocol_sha256": file_sha(B5_PROTOCOL),
              "model_config_sha256": circuit.config_sha256,
              "runner_sha256": file_sha(Path(__file__)),
              "b5_seed_file_sha256": {str(seed): file_sha(B5 / f"seed_{seed}.json.gz")
                                      for seed in protocol["source_conditions"]["visual_to_KC"]["seeds"]},
              "source_parent_hashes": circuit.parent_hashes,
              "python": platform.python_version(), "numpy": np.__version__,
              "trial_count": len(trials), "source_event_checks": event_checks,
              "visual_pair_count": len(visual_edges), "visual_contact_count": sum(e.contacts for e in visual_edges.values()),
              "KC_to_MBON_pair_count": len(kc_mbon_edges), "KC_to_MBON_contact_count": mbon_contacts,
              "KC_count": len(kcs), "trials": trials}
    save(OUT / "result.json", result)
    print(f"Saved {len(trials)} B5 stages, {event_checks} verified arrivals, {len(kcs)} KCs", flush=True)


if __name__ == "__main__":
    main()
