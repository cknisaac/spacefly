"""Independent game/action and reward-sign audit of A8.1's replay ledger."""

from __future__ import annotations

import json
from pathlib import Path

from project_b.osu import GameEnvironment, KeyAction, KeyActionKind, TapNote
from scripts.a8_1_first_action_reward_attribution import OUT, PROTOCOL, ROOT, sha, sign
from scripts.exploration_map_diagnostic import load_long_rows


def main() -> None:
    spec = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    result = json.loads((OUT / "result.json").read_text(encoding="utf-8"))
    status = json.loads((OUT / "status.json").read_text(encoding="utf-8"))
    assert result["status"] == status["status"] == "complete"
    assert result["protocol_sha256"] == status["protocol_sha256"] == sha(PROTOCOL)
    assert status["result_sha256"] == sha(OUT / "result.json")
    assert all(sha(ROOT / name) == h for name, h in result["source_sha256"].items())
    assert result["seed"] == spec["seed"] == 2002
    assert result["exact_historical_training_event_matches"] == 377
    source = load_long_rows()[2002]
    source_events = source["training_events"][:377]
    times = source["resolved_config"]["training_note_times_us"]
    assert len(times) == 384
    game = GameEnvironment(tuple(TapNote(f"lane1-{i}", 0, t)
                                 for i,t in enumerate(times)))
    actions = result["actions"]
    assert all(a["time_us"] <= b["time_us"] for a,b in zip(actions,actions[1:]))
    for a in actions:
        action = KeyAction(a["time_us"], 0, KeyActionKind(a["kind"]))
        record = game.apply_action(action)
        assert record.disposition.value == a["disposition"]
        assert record.note_id == a["note_id"]
        associations = [i for i,t in enumerate(times)
                        if t-500_000 <= a["time_us"] <= t+game.windows.expiry_offset_us]
        assert len(associations) <= 1
        note_i = associations[0] if associations else None
        assert a["nearest_visible_note_index"] == note_i
        assert a["signed_note_offset_us"] == (
            a["time_us"]-times[note_i] if note_i is not None else None)
    game.advance_to(source_events[-1]["delivered_time_us"])
    judgements = game.result().judgements
    assert len(judgements) == 377
    rows = result["rows"]
    assert len(rows) == 377
    for i,(row,source_event,judgement) in enumerate(zip(rows,source_events,judgements)):
        assert row["one_based_outcome"] == i+1 and row["note_index"] == i
        assert row["note_time_us"] == source_event["note_time_us"] == judgement.note_time_us
        assert row["resolved_judgement"] == source_event["judgement"] == judgement.judgement.name
        assert row["resolved_hit_error_us"] == source_event["hit_error_us"] == judgement.hit_error_us
        assert row["resolved_game_utility"] == source_event["game_utility"]
        assert row["expected_utility_before"] == source_event["expected_utility_before"]
        assert row["actual_rpe"] == source_event["rpe"]
        downs = [a for a in actions if a["kind"] == "down"
                 and a["nearest_visible_note_index"] == i]
        first = downs[0] if downs else None
        scored = next((a for a in downs if a["note_id"] == f"lane1-{i}"), None)
        assert row["all_downs"] == downs and row["first_down"] == first
        assert row["scored_down"] == scored
        assert row["first_down_is_scored_down"] == (first is not None and first == scored)
        if first is None or first["disposition"] in ("null_press", "early_miss"):
            u = -1.0
        else:
            assert first["disposition"] == "hit" and first == scored
            u = source_event["game_utility"]
        d = u-source_event["expected_utility_before"]
        assert row["first_action_utility"] == u
        assert row["diagnostic_first_action_rpe"] == d
        assert row["actual_rpe_sign"] == sign(source_event["rpe"])
        assert row["diagnostic_first_action_rpe_sign"] == sign(d)
        assert row["rpe_sign_disagrees"] == (sign(source_event["rpe"]) != sign(d))
    assert result["selected"] == {str(i):rows[i-1] for i in spec["primary_outcomes_one_based"]}
    assert result["aggregate"]["rpe_sign_disagreement_count"] == sum(
        row["rpe_sign_disagrees"] for row in rows)
    assert result["aggregate"]["selected_sign_disagreement_count"] == sum(
        result["selected"][str(i)]["rpe_sign_disagrees"]
        for i in spec["primary_outcomes_one_based"])
    receipt = {
        "status": "passed", "stage": "A8.1",
        "historical_outcomes_checked": len(judgements),
        "game_actions_replayed": len(actions),
        "primary_outcomes": spec["primary_outcomes_one_based"],
        "primary_sign_disagreements": result["aggregate"]["selected_sign_disagreement_count"],
        "protocol_sha256": sha(PROTOCOL),
        "result_sha256": sha(OUT / "result.json"),
    }
    (OUT / "audit.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
