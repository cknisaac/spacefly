"""Frozen-protocol integrity checks for MaleCNS Level 2."""

import json
import unittest
from pathlib import Path

from project_b.malecns_continuous_position_learning.encoder import activation


ROOT = Path.cwd()
CONFIG = ROOT / "configs/malecns_continuous_position_learning_v1.json"


class ContinuousPositionProtocolTests(unittest.TestCase):
    def test_encoder_is_fixed_smooth_and_peak_normalized(self):
        sigma = 0.08
        self.assertEqual(activation(0.4, 0.4, sigma), 1.0)
        self.assertAlmostEqual(activation(0.35, 0.4, sigma),
                               activation(0.45, 0.4, sigma), places=14)
        self.assertGreater(activation(0.4, 0.4, sigma),
                           activation(0.5, 0.4, sigma))

    def test_config_uses_next_32_audited_source_order_kcs_and_fixed_schedule(self):
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        audit = json.loads((ROOT / config["source"]["kc_mbon_audit"])
                           .read_text(encoding="utf-8"))
        expected = audit["kc_pairs"][16:48]
        cells = config["circuit"]["selected_kcs"]
        self.assertEqual([cell["source_id"] for cell in cells],
                         [row["kc_source_id"] for row in expected])
        self.assertTrue(all(cell["plastic_contact_row_ids"] == row["plastic_contact_rows"]
                            for cell, row in zip(cells, expected)))
        self.assertEqual(len(config["training"]["sequence"]), 80)
        self.assertEqual(config["target_region"]["primary"], [0.65, 0.75])
        self.assertEqual(config["target_region"]["wrong_control"], [0.15, 0.25])

    def test_saved_pretraining_gate_and_level2_fail_receipt_are_consistent(self):
        probe = json.loads((ROOT / "runs/malecns_continuous_position_learning_v1/controllability.json")
                           .read_text(encoding="utf-8"))
        result = json.loads((ROOT / "runs/malecns_continuous_position_learning_v1/result.json")
                            .read_text(encoding="utf-8"))
        self.assertEqual(probe["status"], "PASS")
        self.assertTrue(all(probe["criteria"].values()))
        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(result["criteria"]["position_selective_target_action"])
        self.assertFalse(result["criteria"]["wrong_region_teaching_moves_action_to_wrong_region"])
        self.assertTrue(result["criteria"]["plasticity_off_control_does_not_learn_target_region"])


if __name__ == "__main__":
    unittest.main()
