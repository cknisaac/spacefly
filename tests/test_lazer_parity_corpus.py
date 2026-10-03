"""Regression tests for the frozen inputs prepared for lazer runtime parity."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from scripts.compare_lazer_reference import _differences, build_python_output


ROOT = Path(__file__).resolve().parents[1]
CORPUS_PATH = ROOT / "tests" / "fixtures" / "lazer_od8_parity_corpus.json"


class LazerParityCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))

    def test_corpus_is_pinned_to_the_declared_release(self) -> None:
        reference = self.corpus["reference"]
        self.assertEqual(reference["release"], "2026.1001.0-tachyon")
        self.assertEqual(reference["commit"], "da27300fcbfa246f87c3ba1a14cbd00b68c7e9a9")
        self.assertEqual((reference["ruleset"], reference["od"], reference["mods"],
                          reference["rate"]), ("osu!mania", 8, [], 1.0))

    def test_python_profile_matches_frozen_vectors_and_event_sequences(self) -> None:
        output = build_python_output(self.corpus)
        expected = {
            "schema_version": self.corpus["schema_version"],
            "reference": self.corpus["reference"],
            "judgement_vectors": [
                {"id": row["id"], "result": row["expected"]}
                for row in self.corpus["judgement_vectors"]
            ],
            "scenarios": [
                {"id": row["id"], "events": row["expected_events"]}
                for row in self.corpus["scenarios"]
            ],
        }
        self.assertEqual(_differences(expected, output), [])

    def test_corpus_covers_six_windows_and_runtime_order_cases(self) -> None:
        self.assertEqual(len(self.corpus["judgement_vectors"]), 24)
        self.assertEqual(len(self.corpus["scenarios"]), 8)
        self.assertEqual(len(self.corpus["source_policy_vectors"]), 1)
        scenario_ids = {row["id"] for row in self.corpus["scenarios"]}
        self.assertEqual(scenario_ids, {
            "early_judged_miss",
            "too_early_null_then_automatic_miss",
            "late_meh_at_last_successful_microsecond",
            "expiry_precedes_action_at_expiry_timestamp",
            "no_press_automatic_miss",
            "same_lane_earliest_note_and_key_transition_order",
            "same_lane_note_lock_at_next_note_start",
            "simultaneous_four_lane_chord",
        })

    def test_source_policy_vector_freezes_the_next_note_lock_boundary(self) -> None:
        vector = self.corpus["source_policy_vectors"][0]
        self.assertEqual(vector["id"], "same_lane_lock_boundary")
        self.assertEqual(vector["probe_before_next_start_us"], 1_049_999)
        self.assertEqual(vector["probe_at_next_start_us"], 1_050_000)
        self.assertEqual(vector["expected"], {
            "old_hittable_before": True,
            "old_hittable_at": False,
            "new_hittable_at": True,
            "old_result_before": "GOOD",
            "new_result_at": "PERFECT",
            "force_missed_ids_after_new_hit": ["old"],
        })

    def test_comparator_reports_reference_event_order_differences(self) -> None:
        expected = {"events": [{"kind": "judgement"}, {"kind": "action"}]}
        actual = {"events": [{"kind": "action"}, {"kind": "judgement"}]}
        self.assertEqual(_differences(expected, expected), [])
        self.assertTrue(any("$.events[0].kind" in item
                            for item in _differences(expected, actual)))


if __name__ == "__main__":
    unittest.main()
