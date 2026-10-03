import json
import unittest
from pathlib import Path

from project_b.osu import (
    ActionRecord,
    JudgementRecord,
    KeyAction,
    KeyActionKind,
    TapNote,
    calculate_tap_score,
    load_config,
    play,
)


ROOT = Path(__file__).resolve().parents[1]
SCENARIOS_PATH = ROOT / "tests/fixtures/lazer_mvp_4k_score_scenarios.json"
REFERENCE_PATH = ROOT / "tests/fixtures/lazer_mvp_4k_score_reference.json"
CONFIG = load_config(ROOT / "configs/lazer_mvp.yaml")
PINNED_COMMIT = "da27300fcbfa246f87c3ba1a14cbd00b68c7e9a9"


def assert_reference_value(test, actual, expected, path="root"):
    if isinstance(expected, dict):
        test.assertEqual(set(actual), set(expected), path)
        for key in expected:
            assert_reference_value(test, actual[key], expected[key], f"{path}.{key}")
    elif isinstance(expected, list):
        test.assertEqual(len(actual), len(expected), path)
        for index, (actual_item, expected_item) in enumerate(zip(actual, expected)):
            assert_reference_value(test, actual_item, expected_item, f"{path}[{index}]")
    elif isinstance(expected, (float, int)) and not isinstance(expected, bool):
        test.assertAlmostEqual(actual, expected, delta=1e-12, msg=path)
    else:
        test.assertEqual(actual, expected, path)


def without_observed_game_times(value):
    if isinstance(value, dict):
        return {key: without_observed_game_times(item)
                for key, item in value.items() if key != "observed_game_time_us"}
    if isinstance(value, list):
        return [without_observed_game_times(item) for item in value]
    return value


def run_python_scenario(scenario):
    notes = tuple(
        TapNote(row["id"], row["lane"], row["time_us"])
        for row in scenario["notes"]
    )
    actions = tuple(
        KeyAction(row["time_us"], row["lane"], KeyActionKind(row["kind"]))
        for row in scenario["actions"]
    )
    result = play(notes, actions, CONFIG)
    score = calculate_tap_score(notes, result, CONFIG)
    score_by_note = {event.note_id: event.as_dict() for event in score.events}

    events = []
    for event in result.events:
        if isinstance(event, JudgementRecord):
            score_snapshot = score_by_note[event.note_id]
            for field in ("note_id", "note_index", "hit_result", "result_max"):
                score_snapshot.pop(field)
            events.append({
                "kind": "judgement",
                "logical_event_time_us": event.logical_event_time_us,
                "note_id": event.note_id,
                "lane": event.lane,
                "note_time_us": event.note_time_us,
                "result": event.result_name,
                "hit_error_us": event.hit_error_us,
                "score": score_snapshot,
            })
        elif isinstance(event, ActionRecord):
            events.append({
                "kind": "action",
                "event_time_us": event.action.time_us,
                "lane": event.action.lane,
                "action": event.action.kind.value,
                "disposition": event.disposition.value,
                "note_id": event.note_id,
            })
        else:
            raise AssertionError(f"unexpected game event: {event!r}")
    actions_out = [
        {"time_us": row.action.time_us, "lane": row.action.lane,
         "kind": row.action.kind.value}
        for row in result.actions
    ]
    return notes, result, score, actions_out, events


class LazerFourKScoreParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = json.loads(SCENARIOS_PATH.read_text(encoding="utf-8"))
        cls.reference = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))

    def test_event_order_and_per_judgement_score_match_pinned_lazer(self):
        self.assertEqual(self.reference["reference"]["commit"], PINNED_COMMIT)
        self.assertEqual(self.reference["reference"]["mods"], [])
        self.assertEqual(self.reference["reference"]["scoring_mode"], "ScoreV2 default")
        self.assertEqual(
            [row["id"] for row in self.reference["scenarios"]],
            [row["id"] for row in self.corpus["scenarios"]],
        )

        for scenario, expected in zip(self.corpus["scenarios"], self.reference["scenarios"]):
            with self.subTest(scenario=scenario["id"]):
                notes, result, score, actual_actions, actual_events = run_python_scenario(scenario)
                self.assertEqual(len(notes), len(scenario["notes"]))
                self.assertEqual(actual_actions, expected["actions"])
                assert_reference_value(
                    self, actual_events,
                    without_observed_game_times(expected["events"]),
                )
                self.assertEqual(result.resolved_notes, len(notes))
                self.assertEqual(score.note_count, len(notes))

    def test_lane_results_and_combo_break_recovery_are_explicit(self):
        expected_by_id = {row["id"]: row for row in self.reference["scenarios"]}

        _, mixed_result, mixed_score, _, _ = run_python_scenario(
            self.corpus["scenarios"][0]
        )
        self.assertEqual(
            [(row.note_id, row.lane, row.result_name)
             for row in mixed_result.judgements],
            [("n0", 0, "PERFECT"), ("n1", 1, "GREAT"),
             ("n2", 2, "GOOD"), ("n3", 3, "MISS")],
        )
        self.assertEqual([row.combo_after for row in mixed_score.events], [1, 2, 3, 0])
        assert_reference_value(
            self, mixed_score.events[-1].as_dict()["total_score"],
            expected_by_id["four_lane_chord_mixed_and_miss"]["events"][-1]["score"]["total_score"],
        )

        _, retry_result, retry_score, _, retry_events = run_python_scenario(
            self.corpus["scenarios"][1]
        )
        self.assertEqual(
            [(row.note_id, row.result_name) for row in retry_result.judgements],
            [("new", "PERFECT"), ("old", "MISS"), ("chord", "PERFECT")],
        )
        self.assertEqual([row.combo_after for row in retry_score.events], [1, 0, 1])
        self.assertEqual(retry_score.events[1].combo_before, 1)
        self.assertEqual(retry_score.events[2].combo_before, 0)
        self.assertEqual(retry_events[0]["disposition"], "null_press")
        old_miss = next(row for row in retry_events
                        if row.get("kind") == "judgement" and row.get("note_id") == "old")
        self.assertEqual(old_miss["logical_event_time_us"], 1_050_000)
        self.assertIsNone(old_miss["hit_error_us"])

    def test_identical_replay_resets_score_and_is_deterministic(self):
        scenario = self.corpus["scenarios"][1]
        _, result_a, score_a, actions_a, events_a = run_python_scenario(scenario)
        _, result_b, score_b, actions_b, events_b = run_python_scenario(scenario)
        self.assertEqual(result_a.events, result_b.events)
        self.assertEqual(score_a.as_dict(), score_b.as_dict())
        self.assertEqual(actions_a, actions_b)
        self.assertEqual(events_a, events_b)
        self.assertEqual(score_a.events[0].combo_before, 0)
        self.assertEqual(score_a.events[0].accuracy_numerator, 305)


if __name__ == "__main__":
    unittest.main()
