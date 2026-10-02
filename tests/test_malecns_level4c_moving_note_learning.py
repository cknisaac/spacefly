import unittest
from pathlib import Path

from project_b.malecns_continuous_position_learning.experiment_level4c_moving_note_learning import (
    CONFIG_DEFAULT,
    _inputs,
)


ROOT = Path(__file__).resolve().parents[1]


class Level4CMovingNoteLearningTests(unittest.TestCase):
    def test_frozen_duration_arms_and_readout_are_pinned(self):
        stage, level3b, parent, _, threshold = _inputs(ROOT, CONFIG_DEFAULT)
        protocol = stage["protocol"]
        self.assertEqual(protocol["traversal_duration_us"], 500_000)
        self.assertEqual(protocol["training_duration"]["blocks"], 120)
        self.assertEqual(protocol["training_duration"]["presentations"], 1200)
        self.assertEqual(stage["dan_source_ids"], [87177, 107285, 55210])
        self.assertEqual(protocol["eta"], parent["training"]["ltd"]["eta"])
        self.assertEqual(protocol["action_threshold_mv"], threshold)
        self.assertEqual(len(parent["circuit"]["selected_kcs"]), 32)
        self.assertEqual(level3b["dan_source_ids"], stage["dan_source_ids"])

    def test_schedule_remains_balanced_for_target_and_wrong_teaching(self):
        _, _, parent, _, _ = _inputs(ROOT, CONFIG_DEFAULT)
        schedule = parent["training"]["sequence"]
        self.assertEqual(len(schedule), 1200)
        self.assertEqual(sum(row["position_class"] == "target_region" for row in schedule), 600)
        self.assertEqual(sum(row["position_class"] == "wrong_region_distractor" for row in schedule), 600)


if __name__ == "__main__":
    unittest.main()
