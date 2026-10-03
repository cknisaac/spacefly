"""Frozen EA-10 task-free readout fanout probe; no game or learning."""

from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

from project_b.ea_mvp.continuous_chords import ContinuousChordFlyPolicy
from project_b.malecns_continuous_position_learning.online_policy import load_position_config
from project_b.osu.adapter import PositionFrameObservation, VisibleNotePosition
from project_b.osu.types import KeyActionKind


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/ea_mvp_chord_admission_v1.json"
OUTPUT = ROOT / "runs/ea_mvp/chord_admission_v1.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sweep(config: dict, weights: list[float], lanes: list[int]) -> list[dict]:
    policy = ContinuousChordFlyPolicy(config, weights)
    frame = PositionFrameObservation(tuple(VisibleNotePosition(lane, 1.0) for lane in lanes))
    policy.begin(frame)
    actions = []
    for elapsed in range(1000, 800001, 1000):
        visible = elapsed <= 500000
        position = max(0.0, 1.0 - elapsed / 500000)
        current = PositionFrameObservation(tuple(
            VisibleNotePosition(lane, position) for lane in lanes)) if visible else PositionFrameObservation(())
        for event in policy.step(current):
            actions.append({"time_us": elapsed, "lane": event.lane, "kind": event.kind.value})
    policy.finish()
    return actions


def main() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    for relative, expected in protocol["code_sha256"].items():
        if sha(ROOT / relative) != expected:
            raise RuntimeError(f"frozen code changed: {relative}")
    for name in ("weight_receipt", "source_config"):
        if sha(ROOT / protocol[name]) != protocol[f"{name}_sha256"]:
            raise RuntimeError(f"frozen {name} changed")
    with gzip.open(ROOT / protocol["weight_receipt"], "rt", encoding="utf-8") as stream:
        receipt = json.load(stream)
    config = load_position_config(ROOT, protocol["source_config"])
    result = {"protocol_id": protocol["protocol_id"], "protocol_sha256": sha(PROTOCOL),
              "assumption": protocol["engineering_assumption"], "conditions": []}
    for lanes in protocol["lane_sets"]:
        replay = [sweep(config, receipt["final_weights"], lanes)
                  for _ in range(protocol["replays_per_lane_set"])]
        downs = [a for a in replay[0] if a["kind"] == KeyActionKind.DOWN.value]
        ups = [a for a in replay[0] if a["kind"] == KeyActionKind.UP.value]
        expected = len(lanes)
        result["conditions"].append({
            "lanes": lanes, "actions": replay[0], "exact_replay": replay[0] == replay[1],
            "one_down_and_up_per_lane": len(downs) == expected and len(ups) == expected
                and len(replay[0]) == 2 * expected,
            "only_selected_lanes": {a["lane"] for a in replay[0]} == set(lanes),
            "down_within_frozen_window": len(downs) == expected and all(
                abs(a["time_us"] - 500000) <= 73500 for a in downs),
        })
    checks = {
        "all_lane_sets_pass": all(all(v for k, v in row.items() if k not in {"lanes", "actions"})
                                   for row in result["conditions"]),
        "no_game_feedback_or_learning": True,
        "weights_unchanged": True,
    }
    result["checks"] = checks
    result["status"] = "PASS" if all(checks.values()) else "FAIL"
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks": checks,
                      "conditions": [{"lanes": row["lanes"], "actions": row["actions"]}
                                     for row in result["conditions"]]}, sort_keys=True))


if __name__ == "__main__":
    main()
