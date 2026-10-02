"""Protocol-correction contract checks for Level 2 v2.5."""

import json
import unittest
from pathlib import Path

from project_b.malecns_continuous_position_learning.experiment_v2_1 import _v1_probe
from project_b.malecns_continuous_position_learning.experiment_v2_5 import (
    _locality,
    _same_model_and_training_settings,
)
from project_b.malecns_continuous_position_learning.probe import load_config


ROOT = Path.cwd()


class ContinuousPositionV25Tests(unittest.TestCase):
    def setUp(self):
        self.v25 = load_config(ROOT, "configs/malecns_continuous_position_learning_v2_5.json")
        self.v23 = load_config(ROOT, "configs/malecns_continuous_position_learning_v2_3.json")

    def test_model_and_training_match_v23_and_duration_is_120(self):
        self.assertTrue(_same_model_and_training_settings(self.v25, self.v23))
        self.assertEqual(self.v25["training"]["blocks"], 120)
        self.assertEqual(len(self.v25["training"]["sequence"]), 1200)
        threshold, probe = _v1_probe(ROOT, self.v25)
        self.assertEqual(probe["status"], "PASS")
        self.assertEqual(threshold, 0.005572335995331903)

    def test_arm_specific_halos_exempt_the_intended_wrong_region(self):
        positions = [round(i / 20, 2) for i in range(21)]
        wrong_arm = {"final_position_map": [
            {"position": x, "action": x in (0.15, 0.20, 0.25, 0.30)}
            for x in positions
        ]}
        locality = _locality(wrong_arm, [0.10, 0.30])
        self.assertEqual(locality["outside_halo_action_positions"], [])
        self.assertTrue(locality["locality_pass"])

    def test_protocol_correction_does_not_relabel_old_runs(self):
        for version in ("2_3", "2_4"):
            path = ROOT / f"runs/malecns_continuous_position_learning_v{version}/result.json"
            result = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "FAIL")
            self.assertFalse(result["criteria"]["distant_positions_mostly_remain_no_action"])

    def test_saved_confirmation_receipt_passes_corrected_contract(self):
        result = json.loads((ROOT / "runs/malecns_continuous_position_learning_v2_5/result.json")
                            .read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(all(result["criteria"].values()))
        self.assertEqual(len(result["target_teacher"]["final_position_map"]), 21)
        self.assertEqual(len(result["wrong_region_teacher"]["final_position_map"]), 21)
        self.assertEqual(result["arm_locality"]["target_teacher"]["outside_halo_action_positions"], [])
        self.assertEqual(result["arm_locality"]["wrong_region_teacher"]["outside_halo_action_positions"], [])


if __name__ == "__main__":
    unittest.main()
