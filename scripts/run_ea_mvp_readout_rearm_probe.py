"""Task-free three-cue test of readout rearming after a blank gap."""

from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

from project_b.ea_mvp.continuous_v2 import ContinuousFrozenFlyPolicy
from project_b.malecns_continuous_position_learning.online_policy import load_position_config
from project_b.osu.adapter import PositionObservation
from project_b.osu.types import KeyActionKind


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/ea_mvp_readout_rearm_probe_v1.json"
OUTPUT = ROOT / "runs/ea_mvp/readout_rearm_probe_v1.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run(config: dict, weights: list[float], p: dict) -> dict:
    policy = ContinuousFrozenFlyPolicy(config, weights)
    dt = p["dt_us"]
    cue_ticks = p["visible_lead_us"] // dt
    gap_ticks = p["blank_gap_us"] // dt
    span = (p["sweeps"] * cue_ticks + (p["sweeps"] - 1) * gap_ticks
            + p["blank_tail_us"] // dt)
    observations = []
    for tick in range(span + 1):
        within = tick % (cue_ticks + gap_ticks)
        sweep = tick // (cue_ticks + gap_ticks)
        if sweep < p["sweeps"] and within <= cue_ticks:
            position = 1.0 - within / cue_ticks
            observations.append(PositionObservation(True, 0, position))
        else:
            observations.append(PositionObservation(False, 0, None))
    policy.begin(observations[0])
    actions = []
    for tick, obs in enumerate(observations[1:], 1):
        actions.extend(policy.step(obs))
    policy.finish()
    downs = [a.episode_time_us for a in actions if a.kind is KeyActionKind.DOWN]
    up_count = sum(a.kind is KeyActionKind.UP for a in actions)
    cue_starts = [i * (cue_ticks + gap_ticks) * dt for i in range(p["sweeps"])]
    relative_downs = [down - start for down, start in zip(downs, cue_starts)]
    return {"downs_us": downs, "ups": up_count, "relative_downs_us": relative_downs,
            "readout_start_times_us": policy.readout_start_times,
            "one_neural_simulator": policy.neural_reset_count == 1,
            "spikes": policy._sim.snapshot().spikes,
            "weights_unchanged": tuple(weights) == policy.weights}


def main() -> None:
    p = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if _sha(ROOT / p["runner"]) != p["runner_sha256"]:
        raise RuntimeError("probe runner changed after freeze")
    if _sha(ROOT / p["continuous_policy"]) != p["continuous_policy_sha256"]:
        raise RuntimeError("continuous policy changed after probe freeze")
    if _sha(ROOT / p["source_config"]) != p["source_config_sha256"]:
        raise RuntimeError("source config changed")
    receipts = {}
    for key in ("learned_receipt", "control_receipt"):
        path = ROOT / p[key]
        hash_key = key.replace("receipt", "receipt_sha256")
        if _sha(path) != p[hash_key]:
            raise RuntimeError(f"{key} changed")
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            receipts[key] = json.load(stream)
    config = load_position_config(ROOT, p["source_config"])
    arms = {}
    for name, key in (("learned", "learned_receipt"), ("initial", "control_receipt")):
        weights = receipts[key]["final_weights"] if name == "learned" else receipts[key]["initial_weights"]
        replay = [_run(config, weights, p) for _ in range(2)]
        arms[name] = {"record": replay[0], "exact_replay": replay[0] == replay[1]}
    learned = arms["learned"]["record"]
    initial = arms["initial"]["record"]
    expected_start = [0] + [i * (p["visible_lead_us"] + p["blank_gap_us"])
                            for i in range(1, p["sweeps"])]
    # Starts are verified against the first KC spike after each cue onset.
    spike_times = [row.time_us for row in learned["spikes"] if row.neuron_index < 32]
    gate_ok = learned["readout_start_times_us"][0] == 0 and all(
        any(start <= spike_time <= readout_start < start + p["visible_lead_us"]
            for spike_time in spike_times)
        for start, readout_start in zip(expected_start[1:],
                                        learned["readout_start_times_us"][1:]))
    checks = {
        "learned_one_action_per_sweep": len(learned["relative_downs_us"]) == p["sweeps"],
        "same_sweep_relative_action_tick": len(set(learned["relative_downs_us"])) == 1,
        "initial_weights_silent": not initial["downs_us"],
        "fresh_cue_kc_spike_gates_rearm": gate_ok,
        "one_simulator_and_immutable_weights": learned["one_neural_simulator"] and
            learned["weights_unchanged"] and initial["weights_unchanged"],
        "exact_replay": all(row["exact_replay"] for row in arms.values()),
    }
    result = {"protocol_id": p["protocol_id"], "protocol_sha256": _sha(PROTOCOL),
              "arms": arms, "checks": checks,
              "status": "PASS" if all(checks.values()) else "FAIL"}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True, default=str) + "\n",
                      encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks": checks,
                      "learned_relative_downs_us": learned["relative_downs_us"],
                      "initial_downs_us": initial["downs_us"]}, sort_keys=True))


if __name__ == "__main__":
    main()
