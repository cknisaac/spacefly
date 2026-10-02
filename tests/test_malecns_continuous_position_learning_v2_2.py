"""Frozen-protocol checks for the Level 2 v2.2 continuation."""

import copy
import json
import unittest
from pathlib import Path

from project_b.malecns_continuous_position_learning.experiment_v2_1 import _v1_probe
from project_b.malecns_continuous_position_learning.probe import load_config


ROOT = Path.cwd()
V21_PATH = "configs/malecns_continuous_position_learning_v2_1.json"
V22_PATH = "configs/malecns_continuous_position_learning_v2_2.json"


class ContinuousPositionV22Tests(unittest.TestCase):
    def setUp(self):
        self.v21 = json.loads((ROOT / V21_PATH).read_text(encoding="utf-8"))
        self.v22 = load_config(ROOT, V22_PATH)

    def test_only_training_duration_and_stage_metadata_change(self):
        a, b = copy.deepcopy(self.v21), copy.deepcopy(self.v22)
        for data in (a, b):
            data.pop("experiment_id", None)
            data.pop("status", None)
            data.pop("continuation", None)
            data["training"].pop("blocks")
            data["training"].pop("sequence")
            data["training"].pop("duration_status")
        self.assertEqual(a, b)
        self.assertEqual(self.v22["training"]["blocks"], 96)

    def test_schedule_repeats_frozen_v21_block_for_all_96_blocks(self):
        first = [row for row in self.v21["training"]["sequence"] if row["block"] == 1]
        schedule = self.v22["training"]["sequence"]
        self.assertEqual(len(first), 10)
        self.assertEqual(len(schedule), 960)
        for block in range(1, 97):
            actual = [row for row in schedule if row["block"] == block]
            self.assertEqual([(r["position"], r["position_class"]) for r in actual],
                             [(r["position"], r["position_class"]) for r in first])

    def test_inherited_threshold_and_v1_sources_are_pinned(self):
        threshold, probe = _v1_probe(ROOT, self.v22)
        self.assertEqual(probe["status"], "PASS")
        self.assertEqual(threshold, 0.005572335995331903)
        self.assertEqual(threshold, self.v22["continuation"]["frozen_action_threshold_mv"])

    def test_saved_run_receipt_shows_complete_three_arm_fail(self):
        result = json.loads((ROOT / "runs/malecns_continuous_position_learning_v2_2/result.json")
                            .read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(result["criteria"]["all_96_blocks_and_960_presentations_run_in_every_arm"])
        self.assertEqual(result["training_blocks_completed"], {
            "primary": 96,
            "plasticity_off_control": 96,
            "wrong_region_control": 96,
        })
        self.assertEqual(len(result["target_teacher"]["final_position_map"]), 21)
        self.assertEqual(len(result["learning_curves"]["target_teacher"]), 96)
        self.assertTrue(result["criteria"]["plasticity_off_weights_and_map_are_unchanged"])


if __name__ == "__main__":
    unittest.main()
