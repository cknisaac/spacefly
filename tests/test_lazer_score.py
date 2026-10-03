import json
import unittest
from pathlib import Path

from project_b.osu import (
    KeyAction,
    KeyActionKind,
    TapNote,
    load_config,
    play,
)
from project_b.osu.scoring import calculate_tap_score


ROOT = Path(__file__).resolve().parents[1]
CONFIG = load_config(ROOT / "configs/lazer_mvp.yaml")
FIXTURE_PATH = ROOT / "tests/fixtures/lazer_score_v2_vectors.json"
HIT_OFFSETS_US = {
    "PERFECT": 0,
    "GREAT": 20_000,
    "GOOD": 50_000,
    "OK": 90_000,
    "MEH": 110_000,
    "MISS": None,
}


def run_results(results):
    notes = tuple(
        TapNote(f"score-note-{index}", 0, 1_000_000 + index * 400_000)
        for index in range(len(results))
    )
    actions = []
    for note, result in zip(notes, results):
        offset = HIT_OFFSETS_US[result]
        if offset is None:
            continue
        down_us = note.time_us + offset
        actions.extend((
            KeyAction(down_us, note.lane, KeyActionKind.DOWN),
            KeyAction(down_us + 1_000, note.lane, KeyActionKind.UP),
        ))
    game_result = play(notes, actions, CONFIG)
    return notes, game_result, calculate_tap_score(notes, game_result, CONFIG)


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


class LazerTapScoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def test_score_vectors_match_pinned_csharp_score_processor(self):
        self.assertEqual(
            self.fixture["reference"]["commit"],
            "da27300fcbfa246f87c3ba1a14cbd00b68c7e9a9",
        )
        self.assertEqual(self.fixture["reference"]["scoring_mode"], "ScoreV2 default")

        for expected_scenario in self.fixture["scenarios"]:
            with self.subTest(scenario=expected_scenario["id"]):
                expected_results = [row["hit_result"]
                                    for row in expected_scenario["events"]]
                notes, game_result, score = run_results(expected_results)
                actual_results = [row.result_name for row in game_result.judgements]
                self.assertEqual(actual_results, expected_results)
                self.assertEqual(len(notes), expected_scenario["note_count"])
                self.assertAlmostEqual(
                    score.maximum_combo_score_portion,
                    expected_scenario["maximum_combo_score_portion"], delta=1e-12,
                )

                for actual_event, expected_event in zip(
                    score.events, expected_scenario["events"]
                ):
                    actual_row = actual_event.as_dict()
                    actual_row.pop("note_id")
                    assert_reference_value(self, actual_row, expected_event)

                self.assertEqual(score.total_score,
                                 expected_scenario["events"][-1]["total_score"])
                self.assertEqual(score.maximum_total_score, 1_000_000)
                self.assertEqual(score.maximum_combo, len(notes))

    def test_separate_runs_reset_combo_and_accuracy_state(self):
        _, _, previous_run = run_results(["GREAT", "MISS"])
        self.assertEqual(previous_run.combo, 0)
        self.assertEqual(previous_run.accuracy_numerator, 300)

        _, _, fresh_run = run_results(["PERFECT"])
        self.assertEqual(fresh_run.events[0].combo_before, 0)
        self.assertEqual(fresh_run.events[0].accuracy_numerator, 305)
        self.assertEqual(fresh_run.events[0].accuracy_denominator, 305)
        self.assertEqual(fresh_run.total_score, 1_000_000)

    def test_only_complete_lazer_tap_runs_are_scoreable(self):
        notes, result, _ = run_results(["PERFECT"])
        with self.assertRaisesRegex(ValueError, "fully resolved|every tap"):
            calculate_tap_score(notes, result.__class__(
                (), result.actions, result.events, result.key_down, result.total_notes,
            ), CONFIG)

    def test_score_is_rejected_for_non_lazer_profile(self):
        notes, result, _ = run_results(["PERFECT"])
        from project_b.osu.config import OsuConfig

        with self.assertRaisesRegex(ValueError, "lazer"):
            calculate_tap_score(notes, result, OsuConfig(ruleset="stable_native"))


if __name__ == "__main__":
    unittest.main()
