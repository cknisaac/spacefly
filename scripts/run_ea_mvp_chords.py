"""Frozen EA-10 equal-time two-chord headless game run."""

from __future__ import annotations

import gzip
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from project_b.ea_mvp.continuous_chords import ContinuousChordFlyPolicy, play_equal_time_chords
from project_b.malecns_continuous_position_learning.online_policy import load_position_config
from project_b.osu.config import OsuConfig
from project_b.osu.types import KeyActionKind, TapNote


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/ea_mvp_chords_v1.json"
OUTPUT = ROOT / "runs/ea_mvp/chords_v1.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def play(config: dict, weights: list[float], chords: tuple[tuple[TapNote, ...], ...], protocol: dict) -> dict:
    policy = ContinuousChordFlyPolicy(config, weights)
    trace = play_equal_time_chords(chords, OsuConfig(od=protocol["od"], ruleset="lazer"),
                                   policy, visible_lead_us=protocol["visible_lead_us"])
    return {"actions": [asdict(row) for row in trace.actions],
            "results": [asdict(row) for row in trace.results],
            "score": asdict(trace.score), "neural_reset_count": trace.neural_reset_count,
            "readout_rearm_count": trace.readout_rearm_count,
            "spike_count": trace.spike_count, "weights_unchanged": tuple(weights) == policy.weights}


def main() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    for rel, expected in protocol["code_sha256"].items():
        if sha(ROOT / rel) != expected:
            raise RuntimeError(f"frozen code changed: {rel}")
    for name in ("weight_receipt", "source_config", "admission_receipt"):
        if sha(ROOT / protocol[name]) != protocol[f"{name}_sha256"]:
            raise RuntimeError(f"frozen {name} changed")
    admission = json.loads((ROOT / protocol["admission_receipt"]).read_text(encoding="utf-8"))
    if admission["status"] != "PASS":
        raise RuntimeError("task-free chord admission did not pass")
    with gzip.open(ROOT / protocol["weight_receipt"], "rt", encoding="utf-8") as stream:
        source = json.load(stream)
    config = load_position_config(ROOT, protocol["source_config"])
    chords = tuple(tuple(TapNote(**note) for note in group) for group in protocol["chords"])
    notes = tuple(note for group in chords for note in group)
    result = {"protocol_id": protocol["protocol_id"], "protocol_sha256": sha(PROTOCOL), "arms": {}}
    for arm in protocol["arms"]:
        weights = source["final_weights"] if arm == "retained_lane0_trained_weights" else source["initial_weights"]
        replays = [play(config, weights, chords, protocol)
                   for _ in range(protocol["replays_per_arm"])]
        result["arms"][arm] = {"record": replays[0], "exact_replay": all(x == replays[0] for x in replays)}
    trained = result["arms"]["retained_lane0_trained_weights"]["record"]
    control = result["arms"]["matched_initial_weights"]["record"]
    downs = [x for x in trained["actions"] if x["kind"] == KeyActionKind.DOWN.value]
    ups = [x for x in trained["actions"] if x["kind"] == KeyActionKind.UP.value]
    checks = {
        "one_correct_lane_down_per_note_in_good_window": len(downs) == len(notes) and all(
            row["lane"] == note.lane and abs(row["time_us"] - note.time_us) <= 73500
            for row, note in zip(downs, notes)),
        "exact_action_counts": len(ups) == len(notes) and len(trained["actions"]) == 2 * len(notes),
        "four_good_or_better_results": len(trained["results"]) == len(notes) and all(
            row["result"] in {"PERFECT", "GREAT", "GOOD"} for row in trained["results"]),
        "one_neural_start_two_rearms": trained["neural_reset_count"] == 1
            and trained["readout_rearm_count"] == len(chords),
        "initial_weights_silent_and_four_misses": not any(
            row["kind"] == KeyActionKind.DOWN.value for row in control["actions"])
            and len(control["results"]) == len(notes)
            and all(row["result"] == "MISS" for row in control["results"]),
        "weights_unchanged": trained["weights_unchanged"] and control["weights_unchanged"],
        "exact_replay": all(arm["exact_replay"] for arm in result["arms"].values()),
        "task_free_admission_passed": admission["status"] == "PASS",
    }
    result["checks"] = checks
    result["status"] = "PASS" if all(checks.values()) else "FAIL"
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks": checks,
                      "actions": trained["actions"],
                      "results": [row["result"] for row in trained["results"]]}, sort_keys=True))


if __name__ == "__main__":
    main()
