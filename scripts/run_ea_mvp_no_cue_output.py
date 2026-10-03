"""Run frozen EA-3.1 no-cue and output-lesion panel without learning."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from project_b.malecns_continuous_position_learning.online_policy import (
    OnlineFlyPolicy, load_position_config,
)
from project_b.malecns_continuous_position_learning.online_readout import OnlinePositionReadout
from project_b.malecns_continuous_position_learning.probe import _lif
from project_b.osu.adapter import PositionObservation
from project_b.osu.types import KeyActionKind
from project_b.simulation import SpikingSimulator
from project_b.synapses import SparseGraph, Synapse


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/ea_mvp_no_cue_output_protocol.json"
OUTPUT = ROOT / "runs/ea_mvp/no_cue_output.json"


def _weights(config: dict, center: float | None, protocol: dict) -> list[float]:
    cells = config["circuit"]["selected_kcs"]
    total = sum(cell["plastic_contact_rows"] for cell in cells)
    weights = [cell["plastic_contact_rows"] / total for cell in cells]
    if center is not None:
        weights = [value * protocol["local_weight_multiplier"]
                   if abs(cell["preferred_position"] - center) <= protocol["local_half_width"]
                   else value for value, cell in zip(weights, cells)]
    return weights


def _no_cue(config: dict, protocol: dict) -> dict:
    weights = _weights(config, None, protocol)
    n_kc = len(weights)
    graph = SparseGraph(n_kc + 1, [Synapse(i, n_kc, weight,
                                          config["overlay"]["synaptic_delay_us"])
                                   for i, weight in enumerate(weights)])
    sim = SpikingSimulator([_lif(config)] * (n_kc + 1), graph,
                           [0.0] * (n_kc + 1), dt_us=1_000,
                           record_neurons=[n_kc], record_spikes=True)
    snapshot = sim.run_until(500_000)
    return {"spike_count": len(snapshot.spikes),
            "mbon_peak_mv": max((row.voltage_before_reset_mv
                                 for row in snapshot.voltage_trace), default=0.0),
            "spikes": [asdict(row) for row in snapshot.spikes],
            "arrivals": [asdict(row) for row in snapshot.arrivals],
            "mbon_voltage_trace": [asdict(row) for row in snapshot.voltage_trace],
            "queued_arrivals": snapshot.queued_arrivals}


def _cue(config: dict, weights: list[float], *, output_off: bool) -> dict:
    policy = OnlineFlyPolicy(config, weights=weights)
    policy.begin(PositionObservation(True, 0, 1.0))
    lesion = None
    if output_off:
        lesion = OnlinePositionReadout(
            position_grid=list(config["evaluation"]["position_grid"]),
            bin_width=0.05,
            threshold_mv=config["continuation"]["frozen_action_threshold_mv"],
            dt_us=1_000, lane=0, key_hold_us=10_000, direction=-1)
        lesion.begin(0, 1.0)
    actions = []
    lesion_actions = []
    for t in range(1_000, 501_000, 1_000):
        position = max(0.0, 1.0 - t / 500_000)
        actions.extend(policy.step(PositionObservation(True, 0, position)))
        if lesion is not None:
            lesion_actions.extend(lesion.step(t, position, 0.0))
    actions.extend(policy.finish())
    if lesion is not None:
        lesion_actions.extend(lesion.finish(500_000))
    downs = [row for row in actions if row.kind is KeyActionKind.DOWN]
    lesion_downs = [row for row in lesion_actions if row.kind is KeyActionKind.DOWN]
    bins = {str(row.position): row.max_voltage_mv for row in policy.decisions}
    snapshot = policy._sim.snapshot()
    source_ids = [cell["source_id"] for cell in config["circuit"]["selected_kcs"]]
    source_ids.append(config["circuit"]["mbon_source_id"])
    return {"first_down_us": downs[0].episode_time_us if downs else None,
            "first_down_position": 1.0 - downs[0].episode_time_us / 500_000 if downs else None,
            "actions": [{"episode_time_us": row.episode_time_us,
                         "lane": row.lane, "kind": row.kind.value}
                        for row in actions],
            "mbon_bin_max_mv": bins,
            "output_off_first_down_us": lesion_downs[0].time_us if lesion_downs else None,
            "source_spike_count": len(snapshot.spikes),
            "source_tagged_spikes": [
                {**asdict(row), "source_id": source_ids[row.neuron_index]}
                for row in snapshot.spikes],
            "source_tagged_arrivals": [
                {**asdict(row), "pre_source_id": source_ids[row.pre],
                 "post_source_id": source_ids[row.post]}
                for row in snapshot.arrivals],
            "mbon_voltage_trace": [asdict(row) for row in snapshot.voltage_trace],
            "readout_decisions": [asdict(row) for row in policy.decisions],
            "output_off_readout_decisions": (
                [asdict(row) for row in lesion.decisions] if lesion is not None else None),
            "queued_arrivals": snapshot.queued_arrivals}


def main() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    path = ROOT / protocol["source_config"]
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != protocol["source_config_sha256"]:
        raise RuntimeError("source config hash mismatch")
    config = load_position_config(ROOT, protocol["source_config"])
    arms = {}
    for name, run in (
        ("no_cue", lambda: _no_cue(config, protocol)),
        ("initial_cue", lambda: _cue(config, _weights(config, None, protocol), output_off=False)),
        ("local_cue", lambda: _cue(config, _weights(config, 0.5, protocol), output_off=False)),
        ("local_cue_mbon_output_off", lambda: _cue(config, _weights(config, 0.5, protocol), output_off=True)),
    ):
        records = [run() for _ in range(protocol["repeat_count"])]
        arms[name] = {"record": records[0], "replay_exact": records[0] == records[1]}
    no_cue = arms["no_cue"]["record"]
    initial = arms["initial_cue"]["record"]
    local = arms["local_cue"]["record"]
    off = arms["local_cue_mbon_output_off"]["record"]
    checks = {
        "no_cue_silent": no_cue["spike_count"] == 0 and no_cue["mbon_peak_mv"] == 0.0,
        "initial_no_down": initial["first_down_us"] is None,
        "local_mbon_reduced": (local["mbon_bin_max_mv"]["0.5"]
                               < initial["mbon_bin_max_mv"]["0.5"]),
        "local_down_near_center": (local["first_down_position"] is not None and
                                   abs(local["first_down_position"] - 0.5) <= 0.1),
        "output_off_no_down": off["output_off_first_down_us"] is None,
        "exact_replay": all(arm["replay_exact"] for arm in arms.values()),
    }
    result = {"protocol_id": protocol["protocol_id"],
              "protocol_sha256": hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
              "source_config_sha256": digest,
              "arms": arms, "checks": checks,
              "status": "PASS" if all(checks.values()) else "FAIL"}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks": checks}, sort_keys=True))


if __name__ == "__main__":
    main()
