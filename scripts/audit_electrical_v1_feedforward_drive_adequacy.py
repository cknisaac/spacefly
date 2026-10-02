"""Independent B5.1 source/charge audit plus two direct V1 replays."""

from __future__ import annotations

from collections import defaultdict
import gzip
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from project_b.electrical_v1 import build_circuit
from project_b.electrical_v1.sensory_route_probe import SensoryRouteProbe, VISUAL_IDS
from project_b.electrical_v1.source import file_sha


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/figures/electrical_v1_feedforward_drive_adequacy"
B5 = ROOT / "docs/figures/electrical_v1_sensory_route_causality"


class Observer(SensoryRouteProbe):
    def observe(self, source_ids):
        self.observed_indices = np.array([self.dynamic_of_source[s] for s in source_ids], dtype=int)
        self.maximum_v = self.v_mv[self.observed_indices].copy()
        self.maximum_syn = self.syn_pa[self.observed_indices].copy()

    def _step(self):
        super()._step()
        if hasattr(self, "observed_indices"):
            idx = self.observed_indices
            self.maximum_v = np.maximum(self.maximum_v, self.v_mv[idx])
            self.maximum_syn = np.maximum(self.maximum_syn, self.syn_pa[idx])


def replay(circuit, onset, arm, level, source_ids, b5_protocol, saved):
    # Restore the *same* baseline checkpoint; no B5 model operation changes.
    model = Observer(circuit, seed=31001)
    model.run_until(onset)
    checkpoint = model.checkpoint()
    model.restore(checkpoint)
    model.observe(source_ids)
    current = b5_protocol["current_policy"]
    if arm == "A":
        target_ids = VISUAL_IDS
        amplitude = current["visual_levels"][level] * model.reference_pa(VISUAL_IDS[0])
    else:
        target_ids = tuple(c.source_id for c in circuit.cells if c.kind == "KC")
        amplitude = current["direct_KC_multiplier"] * model.reference_pa(target_ids[0])
    model.set_current(target_ids, amplitude)
    model.run_until(onset + b5_protocol["pulse_duration_us"])
    model.clear_current()
    model.run_until(onset + b5_protocol["post_window_us"])
    events = [e for e in model.delivered_event_log if onset <= e[0] < onset + b5_protocol["post_window_us"]]
    spikes = [s for s in model.spikes if onset <= s[0] < onset + b5_protocol["post_window_us"]]
    assert events == [tuple(e) for e in saved["delivered_events_time_us_pre_post_source_row_kind_amplitude"]]
    assert spikes == [tuple(s) for s in saved["post_spikes_time_us_source_id"]]
    assert model.boundary.checkpoint()  # untouched nominal autonomous process
    return model


def main():
    protocol_path = ROOT / "configs/electrical_v1_feedforward_drive_adequacy.json"
    protocol = json.loads(protocol_path.read_text())
    result_path = OUT / "result.json"
    result = json.loads(result_path.read_text())
    b5_protocol_path = ROOT / "configs/electrical_v1_sensory_route_causality.json"
    b5_protocol = json.loads(b5_protocol_path.read_text())
    circuit = build_circuit()
    assert result["protocol_sha256"] == file_sha(protocol_path)
    assert result["model_config_sha256"] == circuit.config_sha256 == protocol["electrical_model_config_sha256"]
    assert result["b5_protocol_sha256"] == file_sha(b5_protocol_path) == protocol["b5_protocol_sha256"]
    assert len(result["trials"]) == 120
    source = {}
    for seed in (31001, 31002, 31003):
        path = B5 / f"seed_{seed}.json.gz"
        assert result["b5_seed_file_sha256"][str(seed)] == file_sha(path)
        with gzip.open(path, "rt") as f:
            raw = json.load(f)
        for trial in raw["trials"]:
            if trial["arm"] in {"A", "E"}:
                source[(seed, trial["onset_us"], trial["arm"], trial["level"])] = trial
    checked_cells = 0
    checked_events = 0
    tau_ms = circuit.config["timing"]["synaptic_decay_us"]["value"] / 1000
    for t in result["trials"]:
        arm = "A" if t["stage"] == "visual_to_KC" else "E"
        raw = source[(t["seed"], t["onset_us"], arm, t["level"])]
        end = t["onset_us"] + protocol["measurement_window_us"]
        by_post = defaultdict(list)
        for event in raw["delivered_events_time_us_pre_post_source_row_kind_amplitude"]:
            if event[4] == "FAST" and ((arm == "A" and event[1] in VISUAL_IDS) or
                                       (arm == "E" and event[2] == 519131)):
                by_post[event[2]].append(event)
        for timing, rows in t["results_by_timing"].items():
            assert len(rows) == (107 if arm == "A" else 1)
            for r in rows:
                events = by_post[r["source_id"]]
                assert r["event_count"] == len(events)
                assert np.isclose(r["event_impulse_pa"], sum(e[5] for e in events))
                charge = 0.0
                for event in events:
                    at = event[0]
                    if timing == "bin20ms_midpoint":
                        at = t["onset_us"] + ((at - t["onset_us"]) // 20000) * 20000 + 10000
                    elif timing == "single_volley_100ms":
                        at = t["onset_us"] + 100000
                    charge += event[5] * tau_ms * (1 - math.exp(-(end - at) / (tau_ms * 1000)))
                assert np.isclose(r["fast_charge_fc"], charge, rtol=0, atol=1e-8)
                assert np.isclose(r["minimum_threshold_distance_mv"], r["onset_mv"]-r["peak_voltage_mv"])
                if r["critical_multiplier_linear"] is None:
                    assert r["peak_depolarization_mv"] == 0
                else:
                    assert np.isclose(r["critical_multiplier_linear"],
                                      (r["onset_mv"] - r["rest_mv"]) / r["peak_depolarization_mv"])
                assert r["apl_charge_fc"] == 0 and r["refractory_time_us"] == 0
                assert r["minimum_threshold_distance_mv"] > 0 if timing == "observed" else True
                checked_cells += 1
                checked_events += len(events)
    # Dynamic replay validates initial-at-rest assumption, exact frozen ODE,
    # delivery order, and reconstructed observed peaks for both stages.
    kcs = sorted(c.source_id for c in circuit.cells if c.kind == "KC")
    replay_checks = []
    for arm, level, ids in (("A", "nominal", kcs), ("E", "direct_3x", [519131])):
        onset = b5_protocol["pulse_onsets_us"][0]
        raw = source[(31001, onset, arm, level)]
        model = replay(circuit, onset, arm, level, ids, b5_protocol, raw)
        row = next(t for t in result["trials"] if t["seed"] == 31001 and t["onset_us"] == onset and
                   t["level"] == level and t["stage"] == ("visual_to_KC" if arm == "A" else "KC_to_MBON32"))
        for i, r in enumerate(row["results_by_timing"]["observed"]):
            idx = model.dynamic_of_source[r["source_id"]]
            assert np.isclose(model.maximum_v[i], r["peak_voltage_mv"], rtol=0, atol=1e-9)
            assert np.isclose(model.maximum_syn[i], r["peak_fast_current_pa"], rtol=0, atol=1e-9)
            assert np.isclose(model.v_mv[idx], r["terminal_voltage_mv"], rtol=0, atol=1e-9)
            assert model.refractory_time_us[idx] == 0
        replay_checks.append({"arm": arm, "level": level, "checked_targets": len(ids),
                              "events": len(raw["delivered_events_time_us_pre_post_source_row_kind_amplitude"]),
                              "saved_event_and_spike_trace_equal": True})
    audit = {"status": "pass", "result_sha256": file_sha(result_path),
             "protocol_sha256": file_sha(protocol_path), "checked_trials": len(result["trials"]),
             "checked_target_timing_rows": checked_cells, "checked_event_charge_terms": checked_events,
             "dynamic_replay": replay_checks}
    (OUT / "audit.json").write_text(json.dumps(audit, sort_keys=True, indent=2) + "\n")
    print(audit)


if __name__ == "__main__":
    main()
