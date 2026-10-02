import unittest
from pathlib import Path

from project_b.malecns_continuous_position_learning.experiment_level4_moving_note import (
    CONFIG_DEFAULT,
    _inputs,
    _moving_trial,
    _trajectory_position,
)


ROOT = Path(__file__).resolve().parents[1]


class Level4MovingNoteTests(unittest.TestCase):
    def test_trajectory_is_monotone_and_uses_only_current_position(self):
        duration = 100_000
        positions = [_trajectory_position(t, duration)
                     for t in range(0, duration + 1_000, 1_000)]
        self.assertEqual(positions[0], 1.0)
        self.assertEqual(positions[-1], 0.0)
        self.assertTrue(all(a >= b for a, b in zip(positions, positions[1:])))
        self.assertAlmostEqual(_trajectory_position(30_000, duration), 0.70)
        self.assertAlmostEqual(_trajectory_position(80_000, duration), 0.20)

    def test_frozen_protocol_inherits_level3b_and_fixed_threshold(self):
        stage, parent, _, threshold = _inputs(ROOT, CONFIG_DEFAULT)
        self.assertEqual(stage["dan_source_ids"], [87177, 107285, 55210])
        self.assertEqual(stage["protocol"]["action_threshold_mv"], threshold)
        self.assertEqual(stage["protocol"]["position_grid"], parent["evaluation"]["position_grid"])
        self.assertEqual(stage["protocol"]["blocks"], 120)
        self.assertEqual(stage["protocol"]["presentations"], 1200)

    def test_admitted_500ms_speed_config_preserves_all_other_level3b_settings(self):
        stage, parent, _, threshold = _inputs(
            ROOT, "configs/malecns_level4_moving_note_admitted_500ms.json")
        self.assertEqual(stage["protocol"]["duration_us"], 500_000)
        self.assertEqual(stage["protocol"]["action_threshold_mv"], threshold)
        self.assertEqual(stage["dan_source_ids"], [87177, 107285, 55210])
        self.assertEqual(stage["protocol"]["eta"], parent["training"]["ltd"]["eta"])
        self.assertEqual(stage["protocol"]["minimum_fraction"],
                         parent["training"]["ltd"]["minimum_fraction"])
        self.assertFalse(stage["admitted_speed"]["learning_authorized_by_this_config"])

    def test_one_note_produces_all_fixed_position_bins(self):
        stage, parent, _, _ = _inputs(ROOT, CONFIG_DEFAULT)
        weights = [cell["plastic_contact_rows"] / parent["circuit"]["plastic_contact_count"]
                   for cell in parent["circuit"]["selected_kcs"]]
        trial = _moving_trial(parent, weights, stage["protocol"])
        self.assertEqual([row["position"] for row in trial["position_map"]],
                         parent["evaluation"]["position_grid"])
        self.assertTrue(all(row["mbon_activity_samples"] > 0
                            for row in trial["position_map"]))
        self.assertEqual(trial["trajectory_position_start"], 1.0)
        self.assertEqual(trial["trajectory_position_end"], 0.0)


if __name__ == "__main__":
    unittest.main()
