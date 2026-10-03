"""Frozen EA-9 four-lane sequential-tap headless playback."""

from __future__ import annotations

import gzip
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from project_b.ea_mvp.continuous_multilane import (
    ContinuousFourLaneFlyPolicy, play_continuous_multilane_taps,
)
from project_b.malecns_continuous_position_learning.online_policy import load_position_config
from project_b.osu.config import OsuConfig
from project_b.osu.types import KeyActionKind, TapNote


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/ea_mvp_four_lane_taps_v1.json"
OUTPUT = ROOT / "runs/ea_mvp/four_lane_taps_v1.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def play(config: dict, weights: list[float], notes: tuple[TapNote, ...], protocol: dict) -> dict:
    policy = ContinuousFourLaneFlyPolicy(config, weights)
    trace = play_continuous_multilane_taps(
        notes, OsuConfig(od=protocol["od"], ruleset="lazer"), policy,
        visible_lead_us=protocol["visible_lead_us"])
    return {
        "actions": [asdict(row) for row in trace.actions],
        "results": [asdict(row) for row in trace.results],
        "score": asdict(trace.score),
        "neural_reset_count": trace.neural_reset_count,
        "readout_rearm_count": trace.readout_rearm_count,
        "spike_count": trace.spike_count,
        "weights_unchanged": tuple(weights) == policy.weights,
    }


def main() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    for relative, expected in protocol["code_sha256"].items():
        if sha(ROOT / relative) != expected:
            raise RuntimeError(f"frozen code changed: {relative}")
    for key in ("weight_receipt", "source_config"):
        if sha(ROOT / protocol[key]) != protocol[f"{key}_sha256"]:
            raise RuntimeError(f"frozen {key} changed")
    lane_receipt = ROOT / protocol["lane_mapping_receipt"]
    if sha(lane_receipt) != protocol["lane_mapping_receipt_sha256"]:
        raise RuntimeError("EA-8 lane mapping receipt changed")
    lane_result = json.loads(lane_receipt.read_text(encoding="utf-8"))
    if lane_result["status"] != "PASS":
        raise RuntimeError("EA-8 lane mapping admission did not pass")
    with gzip.open(ROOT / protocol["weight_receipt"], "rt", encoding="utf-8") as stream:
        weights_source = json.load(stream)
    config = load_position_config(ROOT, protocol["source_config"])
    notes = tuple(TapNote(**row) for row in protocol["notes"])
    result = {"protocol_id": protocol["protocol_id"],
              "protocol_sha256": sha(PROTOCOL), "arms": {}, "checks": {}}
    for arm in protocol["arms"]:
        weights = (weights_source["final_weights"] if arm == "retained_lane0_trained_weights"
                   else weights_source["initial_weights"])
        replays = [play(config, weights, notes, protocol)
                   for _ in range(protocol["replays_per_arm"])]
        result["arms"][arm] = {"record": replays[0], "exact_replay": all(x == replays[0] for x in replays)}
    trained = result["arms"]["retained_lane0_trained_weights"]["record"]
    control = result["arms"]["matched_initial_weights"]["record"]
    downs = [row for row in trained["actions"] if row["kind"] == KeyActionKind.DOWN.value]
    ups = [row for row in trained["actions"] if row["kind"] == KeyActionKind.UP.value]
    results = trained["results"]
    expected_lanes = [note.lane for note in notes]
    expected_times = [note.time_us for note in notes]
    checks = {
        "one_correct_lane_down_per_note_in_good_window": len(downs) == len(notes) and all(
            down["lane"] == lane and abs(down["time_us"] - time) <= 73500
            for down, lane, time in zip(downs, expected_lanes, expected_times)),
        "exactly_one_up_per_down_no_extra_actions": len(ups) == len(notes)
            and len(trained["actions"]) == 2 * len(notes),
        "four_good_or_better_judgements": len(results) == len(notes) and all(
            row["result"] in {"PERFECT", "GREAT", "GOOD"} for row in results),
        "one_neural_start_and_four_readout_rearms": trained["neural_reset_count"] == 1
            and trained["readout_rearm_count"] == len(notes),
        "matched_initial_weights_silent_and_miss": not any(
            row["kind"] == KeyActionKind.DOWN.value for row in control["actions"])
            and len(control["results"]) == len(notes)
            and all(row["result"] == "MISS" for row in control["results"]),
        "weights_immutable": trained["weights_unchanged"] and control["weights_unchanged"],
        "exact_replay": all(arm["exact_replay"] for arm in result["arms"].values()),
        "ea8_gate_passed": lane_result["status"] == "PASS",
    }
    result["checks"] = checks
    result["status"] = "PASS" if all(checks.values()) else "FAIL"
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True, default=str) + "\n",
                      encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks": checks,
                      "trained_actions": trained["actions"],
                      "trained_results": [x["result"] for x in results]}, sort_keys=True))


if __name__ == "__main__":
    main()
