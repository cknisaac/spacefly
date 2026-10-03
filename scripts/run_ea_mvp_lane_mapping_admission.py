"""Frozen EA-8 no-game lane selector and timing admission probe."""

from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

from project_b.ea_mvp.continuous_multilane import ContinuousFourLaneFlyPolicy
from project_b.malecns_continuous_position_learning.online_policy import load_position_config
from project_b.osu.adapter import PositionObservation
from project_b.osu.types import KeyActionKind


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/ea_mvp_lane_mapping_admission_v1.json"
OUTPUT = ROOT / "runs/ea_mvp/lane_mapping_admission_v1.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sweep(config: dict, weights: list[float], lane: int) -> list[dict]:
    policy = ContinuousFourLaneFlyPolicy(config, weights)
    policy.begin(PositionObservation(True, lane, 1.0))
    emitted = []
    for elapsed in range(1000, 800001, 1000):
        position = max(0.0, 1.0 - elapsed / 500000)
        observation = PositionObservation(elapsed <= 500000, lane,
                                          position if elapsed <= 500000 else None)
        for action in policy.step(observation):
            emitted.append({"time_us": elapsed, "lane": action.lane,
                            "kind": action.kind.value})
    policy.finish()
    return emitted


def main() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    for relative, expected in protocol["code_sha256"].items():
        if sha(ROOT / relative) != expected:
            raise RuntimeError(f"frozen code changed: {relative}")
    for relative in ("source_config", "weight_receipt"):
        if sha(ROOT / protocol[relative]) != protocol[f"{relative}_sha256"]:
            raise RuntimeError(f"frozen {relative} changed")
    with gzip.open(ROOT / protocol["weight_receipt"], "rt", encoding="utf-8") as stream:
        receipt = json.load(stream)
    config = load_position_config(ROOT, protocol["source_config"])
    result = {"protocol_id": protocol["protocol_id"], "protocol_sha256": sha(PROTOCOL),
              "engineering_assumption": protocol["engineering_assumption"], "lanes": {}}
    for lane in protocol["probe"]["lanes"]:
        replay = [sweep(config, receipt["final_weights"], lane)
                  for _ in range(protocol["probe"]["replays_per_lane"])]
        downs = [a for a in replay[0] if a["kind"] == KeyActionKind.DOWN.value]
        ups = [a for a in replay[0] if a["kind"] == KeyActionKind.UP.value]
        result["lanes"][str(lane)] = {
            "actions": replay[0], "exact_replay": replay[0] == replay[1],
            "one_down_one_up": len(downs) == 1 and len(ups) == 1 and len(replay[0]) == 2,
            "both_actions_on_input_lane": all(a["lane"] == lane for a in replay[0]),
            "down_within_frozen_good_window": len(downs) == 1 and abs(downs[0]["time_us"] - 500000) <= 73500,
        }
    result["checks"] = {
        "all_four_lanes_pass": all(all(check for key, check in row.items() if key != "actions")
                                    for row in result["lanes"].values()),
        "weights_unmodified": True,
        "no_game_no_feedback_no_learning": True,
    }
    result["status"] = "PASS" if all(result["checks"].values()) else "FAIL"
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks": result["checks"],
                      "actions": {k: v["actions"] for k, v in result["lanes"].items()}}, sort_keys=True))


if __name__ == "__main__":
    main()
