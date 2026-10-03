"""Run the frozen three-note continuous fly/game admission panel."""

from __future__ import annotations

from dataclasses import asdict
import gzip
import hashlib
import json
from pathlib import Path

from project_b.ea_mvp.continuous import ContinuousFrozenFlyPolicy, play_continuous_taps
from project_b.malecns_continuous_position_learning.online_policy import load_position_config
from project_b.osu.config import OsuConfig
from project_b.osu.types import KeyActionKind, TapNote


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/ea_mvp_continuous_one_lane_v1.json"
OUTPUT = ROOT / "runs/ea_mvp/continuous_one_lane_v1.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _arm(config: dict, weights: list[float], notes: tuple[TapNote, ...],
         protocol: dict) -> dict:
    policy = ContinuousFrozenFlyPolicy(config, weights)
    trace = play_continuous_taps(
        notes, OsuConfig(od=protocol["od"], ruleset="lazer"), policy,
        visible_lead_us=protocol["visible_lead_us"])
    return {"actions": [asdict(row) for row in trace.actions],
            "results": [asdict(row) for row in trace.results],
            "feedback": [asdict(row) for row in trace.feedback],
            "score": asdict(trace.score),
            "neural_reset_count": trace.neural_reset_count,
            "readout_rearm_count": trace.readout_rearm_count,
            "spike_count": trace.spike_count,
            "weights_unchanged": tuple(weights) == policy.weights}


def main() -> None:
    p = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    for relative_path, expected in p["code_sha256"].items():
        if _sha(ROOT / relative_path) != expected:
            raise RuntimeError(f"frozen code changed: {relative_path}")
    if _sha(ROOT / p["source_config"]) != p["source_config_sha256"]:
        raise RuntimeError("source config changed")
    receipt_path = ROOT / p["learned_receipt"]
    if _sha(receipt_path) != p["learned_receipt_sha256"]:
        raise RuntimeError("retained-weight receipt changed")
    with gzip.open(receipt_path, "rt", encoding="utf-8") as stream:
        source = json.load(stream)
    config = load_position_config(ROOT, p["source_config"])
    notes = tuple(TapNote(**row) for row in p["notes"])
    result = {"protocol_id": p["protocol_id"],
              "protocol_sha256": _sha(PROTOCOL), "arms": {}, "checks": {}}
    for arm in p["arms"]:
        weights = (source["final_weights"] if arm == "retained_learned_weights"
                   else source["initial_weights"])
        records = [_arm(config, weights, notes, p) for _ in range(p["replays_per_arm"])]
        result["arms"][arm] = {"record": records[0],
                               "exact_replay": all(row == records[0] for row in records)}
    learned = result["arms"]["retained_learned_weights"]["record"]
    control = result["arms"]["matched_initial_weights"]["record"]
    downs = [row["time_us"] for row in learned["actions"]
             if row["kind"] is KeyActionKind.DOWN]
    ups = [row["time_us"] for row in learned["actions"]
           if row["kind"] is KeyActionKind.UP]
    control_downs = [row for row in control["actions"]
                     if row["kind"] is KeyActionKind.DOWN]
    checks = {
        "learned_three_first_downs_good_or_better": len(downs) == len(notes) and all(
            abs(down - note.time_us) <= 73500 for down, note in zip(downs, notes)),
        "learned_three_ups_no_extras": len(ups) == len(notes) and
            len(learned["actions"]) == 2 * len(notes),
        "learned_three_good_judgements": len(learned["results"]) == len(notes) and
            all(row["result"] in {"PERFECT", "GREAT", "GOOD"}
                for row in learned["results"]),
        "one_neural_start_three_rearms": learned["neural_reset_count"] == 1 and
            learned["readout_rearm_count"] == len(notes),
        "control_silent_and_misses": not control_downs and
            len(control["results"]) == len(notes) and
            all(row["result"] == "MISS" for row in control["results"]),
        "feedback_only_post_result": all(
            row["available_at_us"] in {result_row["time_us"]
                                       for result_row in learned["results"]}
            for row in learned["feedback"]),
        "weights_immutable": learned["weights_unchanged"] and control["weights_unchanged"],
        "exact_replay": all(row["exact_replay"] for row in result["arms"].values()),
    }
    result["checks"] = checks
    result["status"] = "PASS" if all(checks.values()) else "FAIL"
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True, default=str) + "\n",
                      encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks": checks,
                      "learned_downs": downs}, sort_keys=True))


if __name__ == "__main__":
    main()
