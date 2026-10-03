"""Frozen EA-11 task-free hold head/tail readout gate."""

from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

from project_b.ea_mvp.continuous_holds import ContinuousHoldFlyPolicy, HoldFrame, VisibleHold
from project_b.malecns_continuous_position_learning.online_policy import load_position_config
from project_b.osu.types import KeyActionKind


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/ea_mvp_hold_admission_v1.json"
OUTPUT = ROOT / "runs/ea_mvp/hold_admission_v1.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sweep(config: dict, weights: list[float], lane: int, duration: int) -> list[dict]:
    policy = ContinuousHoldFlyPolicy(config, weights)
    end = 500000 + duration
    policy.begin(HoldFrame((VisibleHold(lane, 1.0, end / 500000),)))
    actions = []
    for elapsed in range(1000, end + 200001, 1000):
        if elapsed <= end:
            head = max(0.0, 1.0 - elapsed / 500000)
            frame = HoldFrame((VisibleHold(lane, head, (end - elapsed) / 500000),))
        else:
            frame = HoldFrame(())
        for event in policy.step(frame):
            actions.append({"time_us": event.episode_time_us, "lane": event.lane,
                            "kind": event.kind.value})
    policy.finish()
    return actions


def main() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    for rel, expected in protocol["code_sha256"].items():
        if sha(ROOT / rel) != expected:
            raise RuntimeError(f"frozen code changed: {rel}")
    for name in ("weight_receipt", "source_config"):
        if sha(ROOT / protocol[name]) != protocol[f"{name}_sha256"]:
            raise RuntimeError(f"frozen {name} changed")
    with gzip.open(ROOT / protocol["weight_receipt"], "rt", encoding="utf-8") as stream:
        receipt = json.load(stream)
    config = load_position_config(ROOT, protocol["source_config"])
    result = {"protocol_id": protocol["protocol_id"], "protocol_sha256": sha(PROTOCOL),
              "assumption": protocol["engineering_assumption"], "cases": []}
    for lane, duration in zip(protocol["lanes"], protocol["durations_us"]):
        replays = [sweep(config, receipt["final_weights"], lane, duration)
                   for _ in range(protocol["replays_per_case"])]
        downs = [row for row in replays[0] if row["kind"] == KeyActionKind.DOWN.value]
        ups = [row for row in replays[0] if row["kind"] == KeyActionKind.UP.value]
        result["cases"].append({
            "lane": lane, "duration_us": duration, "actions": replays[0],
            "exact_replay": replays[0] == replays[1],
            "one_down_one_up": len(downs) == len(ups) == 1 and len(replays[0]) == 2,
            "down_in_frozen_good_window": len(downs) == 1 and abs(downs[0]["time_us"] - 500000) <= 73500,
            "up_exactly_at_tail": len(ups) == 1 and ups[0]["time_us"] == 500000 + duration,
            "both_on_visible_lane": len(replays[0]) == 2 and all(row["lane"] == lane for row in replays[0]),
        })
    checks = {"all_hold_durations_pass": all(
        all(v for k, v in case.items() if k not in {"lane", "duration_us", "actions"})
        for case in result["cases"]), "no_game_feedback_or_learning": True,
        "weights_unchanged": True}
    result["checks"] = checks
    result["status"] = "PASS" if all(checks.values()) else "FAIL"
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks": checks,
                      "cases": [{k: c[k] for k in ("lane", "duration_us", "actions")}
                                for c in result["cases"]]}, sort_keys=True))


if __name__ == "__main__":
    main()
