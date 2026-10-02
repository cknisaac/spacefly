"""Replay existing seed-2002 training only to compare action/reward labels."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from project_b.experiments import TinyLaneSession
from scripts.exploration_map_diagnostic import load_long_rows, load_rows
from scripts.long_continuation import atomic_json, event_record, sha
from scripts.null_press_action_cost_development import action_record
from scripts.successive_update_interference_diagnostic import (
    LONG_LEDGER, LONG_META, LONG_PROTOCOL, ORIGINAL_LEDGER, make_config,
)


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/a8_1_first_action_reward_attribution.json"
OUT = ROOT / "docs/figures/a8_1_first_action_reward_attribution"


def sign(value: float) -> int:
    return (value > 0) - (value < 0)


def main() -> None:
    spec = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert spec["stage"] == "A8.1" and spec["seed"] == 2002
    assert spec["replay_through_outcome"] == 377
    assert spec["primary_outcomes_one_based"] == [372, 373, 377]
    source = load_long_rows()[2002]
    long_protocol = json.loads(LONG_PROTOCOL.read_text(encoding="utf-8"))
    session = TinyLaneSession(make_config(2002, load_rows(ORIGINAL_LEDGER),
                                          load_long_rows(), long_protocol))
    OUT.mkdir(parents=True, exist_ok=True)
    atomic_json(OUT / "status.json", {"status": "running", "protocol_sha256": sha(PROTOCOL)})
    while session.resolved_count < 377:
        session.step()
    observed = [event_record(session, i) for i in range(377)]
    assert observed == source["training_events"][:377]
    actions, _ = action_record(session, 377)
    rows = []
    for i, event in enumerate(observed):
        downs = [a for a in actions if a["kind"] == "down"
                 and a["nearest_visible_note_index"] == i]
        first = downs[0] if downs else None
        scored = next((a for a in downs if a["note_id"] == f"lane1-{i}"), None)
        if first is None or first["disposition"] in ("null_press", "early_miss"):
            first_utility = -1.0
        elif first["disposition"] == "hit":
            assert first["note_id"] == f"lane1-{i}"
            first_utility = event["game_utility"]
        else:
            raise AssertionError((i, first["disposition"]))
        expected = event["expected_utility_before"]
        diagnostic_rpe = first_utility - expected
        row = {
            "one_based_outcome": i+1, "note_index": i,
            "note_time_us": event["note_time_us"],
            "resolved_judgement": event["judgement"],
            "resolved_hit_error_us": event["hit_error_us"],
            "resolved_game_utility": event["game_utility"],
            "expected_utility_before": expected,
            "actual_rpe": event["rpe"],
            "actual_rpe_sign": sign(event["rpe"]),
            "first_action_utility": first_utility,
            "diagnostic_first_action_rpe": diagnostic_rpe,
            "diagnostic_first_action_rpe_sign": sign(diagnostic_rpe),
            "rpe_sign_disagrees": sign(event["rpe"]) != sign(diagnostic_rpe),
            "first_down": first,
            "scored_down": scored,
            "first_down_is_scored_down": first is not None and first == scored,
            "all_downs": downs,
        }
        rows.append(row)
    selected = {str(i): rows[i-1] for i in spec["primary_outcomes_one_based"]}
    aggregate = {
        "outcomes": len(rows),
        "first_down_null_count": sum(r["first_down"] is not None and
                                     r["first_down"]["disposition"] == "null_press"
                                     for r in rows),
        "first_down_early_miss_count": sum(r["first_down"] is not None and
                                           r["first_down"]["disposition"] == "early_miss"
                                           for r in rows),
        "first_down_hit_count": sum(r["first_down"] is not None and
                                    r["first_down"]["disposition"] == "hit"
                                    for r in rows),
        "no_first_down_count": sum(r["first_down"] is None for r in rows),
        "first_down_null_then_scored_count": sum(
            r["first_down"] is not None and r["first_down"]["disposition"] == "null_press"
            and r["scored_down"] is not None for r in rows),
        "rpe_sign_disagreement_count": sum(r["rpe_sign_disagrees"] for r in rows),
        "selected_sign_disagreement_count": sum(r["rpe_sign_disagrees"] for r in selected.values()),
    }
    result = {
        "status": "complete", "study_id": spec["study_id"],
        "protocol_sha256": sha(PROTOCOL),
        "source_sha256": {
            str(p.relative_to(ROOT)): sha(p)
            for p in (LONG_LEDGER, LONG_META, LONG_PROTOCOL, ORIGINAL_LEDGER,
                      ROOT/"src/project_b/experiments/tiny_brain.py",
                      ROOT/"scripts/a8_1_first_action_reward_attribution.py")
        },
        "seed": 2002, "exact_historical_training_event_matches": len(observed),
        "aggregate": aggregate, "selected": selected, "rows": rows, "actions": actions,
        "scope": "diagnostic relabeling of unchanged deterministic replay; no new update or probe",
        "completed_utc": datetime.now(timezone.utc).isoformat(),
    }
    atomic_json(OUT / "result.json", result)
    atomic_json(OUT / "status.json", {"status": "complete", "protocol_sha256": sha(PROTOCOL),
                                      "result_sha256": sha(OUT / "result.json")})
    print(json.dumps({"aggregate": aggregate,
                      "selected": {k: {"first_down": v["first_down"],
                                       "actual_rpe": v["actual_rpe"],
                                       "first_action_rpe": v["diagnostic_first_action_rpe"],
                                       "sign_disagrees": v["rpe_sign_disagrees"]}
                                   for k,v in selected.items()}}), flush=True)


if __name__ == "__main__":
    main()
