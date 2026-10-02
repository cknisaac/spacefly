import unittest
from pathlib import Path

from project_b.malecns_continuous_position_learning.experiment_level4d_final_moving_note_repair import (
    CONFIG_DEFAULT,
    _inputs,
    _readout_from_timecourse,
)


ROOT = Path(__file__).resolve().parents[1]


class Level4DFinalRepairTests(unittest.TestCase):
    def test_only_locality_window_and_mbon_validity_are_repaired(self):
        stage, _, parent, _, threshold = _inputs(ROOT, CONFIG_DEFAULT)
        protocol = stage["protocol"]
        self.assertEqual(protocol["traversal_duration_us"], 500_000)
        self.assertEqual(protocol["kc_count"], 32)
        self.assertEqual(protocol["eta"], parent["training"]["ltd"]["eta"])
        self.assertEqual(protocol["eligibility_tau_us"], parent["training"]["ltd"]["tau_us"])
        self.assertEqual(protocol["weight_floor_fraction_of_immutable_original"],
                         parent["training"]["ltd"]["minimum_fraction"])
        self.assertEqual(protocol["action_threshold_mv"], threshold)
        self.assertEqual(protocol["eligibility_locality_repair"]["window_us"], 50_000)

    def test_position_readout_waits_for_mbon_validity_and_uses_bin_max(self):
        trace = [
            {"time_us": 1, "position": 1.0, "mbon05_voltage_mv": 0.0},
            {"time_us": 2, "position": 0.9, "mbon05_voltage_mv": 0.006},
            {"time_us": 3, "position": 0.9, "mbon05_voltage_mv": 0.001},
            {"time_us": 4, "position": 0.8, "mbon05_voltage_mv": 0.001},
        ]
        panel, first = _readout_from_timecourse(trace, 2, [1.0, 0.9, 0.8], 0.05, 0.0055)
        self.assertIsNone(panel[0]["action"])
        self.assertFalse(panel[1]["action"])  # bin max is 0.006, above threshold
        self.assertTrue(panel[2]["action"])
        self.assertEqual(first["time_us"], 4)
        self.assertEqual(first["position"], 0.8)


if __name__ == "__main__":
    unittest.main()
