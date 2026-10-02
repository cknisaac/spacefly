"""Outcome-blind cohort and frozen protocol checks for Level 2R."""

import json
import unittest
from pathlib import Path

from project_b.malecns_continuous_position_learning.experiment_level2r import (
    _fixed_settings_match,
)
from project_b.malecns_continuous_position_learning.probe import load_config


ROOT = Path.cwd()


class ContinuousPositionLevel2RTests(unittest.TestCase):
    def setUp(self):
        self.config = load_config(ROOT, "configs/malecns_continuous_position_learning_level2r.json")
        self.previous = load_config(ROOT, "configs/malecns_continuous_position_learning_v2_5.json")

    def test_new_cohort_is_next_32_unused_eligible_source_order_pairs(self):
        mask = json.loads((ROOT / self.config["source"]["runtime_mask_path"])
                          .read_text(encoding="utf-8"))["kc_pairs"]
        previous_ids = set()
        for path in (
            "configs/malecns_minimal_internal_learning.json",
            "configs/malecns_minimal_internal_learning_replication.json",
            "configs/malecns_continuous_position_learning_v1.json",
        ):
            previous_ids.update(row["source_id"] for row in
                                json.loads((ROOT / path).read_text(encoding="utf-8"))
                                ["circuit"]["selected_kcs"])
        expected = []
        for index, row in enumerate(mask):
            if index >= 48 and row["plastic_contact_rows"] and row["kc_source_id"] not in previous_ids:
                expected.append((index, row))
                if len(expected) == 32:
                    break
        self.assertEqual([row["source_mask_row_index_zero_based"]
                          for row in self.config["circuit"]["selected_kcs"]],
                         [index for index, _ in expected])
        self.assertEqual([row["source_id"] for row in self.config["circuit"]["selected_kcs"]],
                         [row["kc_source_id"] for _, row in expected])
        self.assertTrue(all(row["plastic_contact_rows"] > 0
                            for row in self.config["circuit"]["selected_kcs"]))
        self.assertEqual(len(set(row["source_id"] for row in
                                 self.config["circuit"]["selected_kcs"])), 32)

    def test_same_model_learning_and_task_contract_as_v25(self):
        self.assertTrue(_fixed_settings_match(self.config, self.previous))
        self.assertEqual(self.config["training"]["blocks"], 120)
        self.assertEqual(len(self.config["training"]["sequence"]), 1200)
        self.assertEqual(self.config["training"]["ltd"]["eta"], 0.00005)
        self.assertEqual(self.config["training"]["ltd"]["minimum_fraction"], 0.2)
        self.assertEqual(self.config["target_region"]["primary"], [0.65, 0.75])
        self.assertEqual(self.config["target_region"]["wrong_control"], [0.15, 0.25])

    def test_threshold_is_rederived_by_same_frozen_task_independent_procedure(self):
        self.assertEqual(self.config["controllability_probe"]["centers"],
                         self.previous["controllability_probe"]["centers"])
        for key in ("weakened_preferred_position_half_width", "local_test_half_width",
                    "distant_minimum_separation", "weight_multiplier", "threshold_selection"):
            self.assertEqual(self.config["controllability_probe"][key],
                             self.previous["controllability_probe"][key])
        self.assertNotEqual(self.config["controllability_probe"]["probe_result"],
                            self.previous["controllability_probe"]["probe_result"])

    def test_saved_probe_and_training_receipts_are_bound_and_complete(self):
        probe = json.loads((ROOT / "runs/malecns_continuous_position_learning_level2r/controllability.json")
                           .read_text(encoding="utf-8"))
        result = json.loads((ROOT / "runs/malecns_continuous_position_learning_level2r/result.json")
                            .read_text(encoding="utf-8"))
        self.assertEqual(probe["status"], "PASS")
        self.assertEqual(probe["config_sha256"], result["config_sha256"])
        self.assertEqual(probe["frozen_action_threshold_mv"],
                         result["frozen_action_threshold_mv"])
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(result["criteria"]["all_120_blocks_and_1200_presentations_run_in_every_arm"])
        self.assertFalse(result["criteria"]["all_three_target_core_positions_action"])
        self.assertEqual(len(result["target_teacher"]["final_position_map"]), 21)
        self.assertEqual(len(result["wrong_region_teacher"]["final_position_map"]), 21)


if __name__ == "__main__":
    unittest.main()
