import dataclasses
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lazer_4k_adapter_harness import build_episode, load_fixture  # noqa: E402
from project_b.osu.adapter import (  # noqa: E402
    PositionFrameObservation,
    VisibleNotePosition,
)


class LazerFourKAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = load_fixture()

    def test_frame_schema_exposes_only_current_visible_positions(self):
        self.assertEqual(
            {field.name for field in dataclasses.fields(PositionFrameObservation)},
            {"visible_notes"},
        )
        self.assertEqual(
            {field.name for field in dataclasses.fields(VisibleNotePosition)},
            {"lane", "position"},
        )
        empty = PositionFrameObservation(())
        same_lane = PositionFrameObservation((
            VisibleNotePosition(2, 0.2), VisibleNotePosition(2, 0.8),
        ))
        self.assertEqual(empty.visible_notes, ())
        self.assertEqual(len(same_lane.visible_notes), 2)

    def test_four_lane_chord_uses_one_simultaneous_position_frame(self):
        episode = build_episode(self.fixture["scenarios"][0])
        self.assertEqual(episode.as_dict()["adapter"], "headless_osu_mania_4k_tap")
        self.assertEqual(
            [(row.note_id, row.lane, row.result_name, row.hit_error_us)
             for row in episode.game_result.judgements],
            [(f"c{lane}", lane, "GREAT", -25_000) for lane in range(4)],
        )
        self.assertEqual([row.combo_after for row in episode.score.events], [1, 2, 3, 4])
        self.assertEqual(len(episode.first_action_audit), 4)
        self.assertTrue(all(row.category.value == "good_or_better"
                            for row in episode.first_action_audit))
        self.assertEqual(
            [row.episode_time_us for row in episode.policy_actions if row.kind.value == "down"],
            [975_000, 975_000, 975_000, 975_000],
        )

    def test_independent_lane_triggers_replay_deterministically(self):
        scenario = self.fixture["scenarios"][1]
        first = build_episode(scenario)
        second = build_episode(scenario)
        self.assertEqual(first.as_dict(), second.as_dict())
        self.assertEqual(
            [(row.lane, row.note_time_us, row.result_name)
             for row in first.game_result.judgements],
            [(lane, 1_000_000 + lane * 40_000, "GREAT") for lane in range(4)],
        )
        self.assertEqual(first.score.total_score, second.score.total_score)
        self.assertEqual(first.score.highest_combo, 4)

    def test_serialized_policy_trace_contains_no_schedule_or_note_identity(self):
        episode = build_episode(self.fixture["scenarios"][0])
        trace = episode.as_dict()
        self.assertEqual(trace["policy_input_fields"], ["visible_notes"])
        self.assertTrue(all(type(row).__name__ == "PositionFrameObservation"
                            for row in episode.observations))
        self.assertTrue(all(set(row) == {"tick", "visible_notes"}
                            for row in trace["policy_observations"]))
        self.assertTrue(all(set(note) == {"lane", "position"}
                            for row in trace["policy_observations"]
                            for note in row["visible_notes"]))
        self.assertIn("beatmap_notes", trace)
        self.assertIn("evaluator_note_cues", trace)
        self.assertNotIn("beatmap_notes", trace["policy_observations"][0])
        self.assertNotIn("score", trace["policy_observations"][0])


if __name__ == "__main__":
    unittest.main()
