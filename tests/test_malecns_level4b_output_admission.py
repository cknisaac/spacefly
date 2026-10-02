import unittest
from pathlib import Path

from project_b.malecns_continuous_position_learning.experiment_level4b_output_admission import (
    CONFIG_DEFAULT,
    _inputs,
    action_validity_trace,
)


ROOT = Path(__file__).resolve().parents[1]


class Level4BOutputAdmissionTests(unittest.TestCase):
    def test_frozen_protocol_uses_500ms_and_disables_learning_and_dan(self):
        stage, _, parent, threshold = _inputs(ROOT, CONFIG_DEFAULT)
        protocol = stage["protocol"]
        self.assertEqual(protocol["duration_us"], 500_000)
        self.assertEqual(protocol["action_threshold_mv"], threshold)
        self.assertEqual(protocol["encoder_sigma"], parent["encoder"]["sigma"])
        self.assertEqual(protocol["learning"], "OFF")
        self.assertEqual(protocol["dan_teaching"], "OFF; no DAN stimulation")

    def test_gate_disables_before_first_spike_and_preserves_threshold_after(self):
        run = {
            "kc_spike_events": [{"time_us": 2_000}],
            "mbon05_timecourse": [
                {"time_us": 1_000, "current_position": 1.0, "mbon05_voltage_mv": 0.0},
                {"time_us": 2_000, "current_position": 0.9, "mbon05_voltage_mv": 0.1},
                {"time_us": 3_000, "current_position": 0.8, "mbon05_voltage_mv": 0.0},
            ],
            "position_map": [
                {"position": 1.0}, {"position": 0.9}, {"position": 0.8},
            ],
        }
        gated = action_validity_trace(run, threshold_mv=0.05)
        self.assertIsNone(gated["trace"][0]["action"])
        self.assertFalse(gated["trace"][0]["output_enabled"])
        self.assertFalse(gated["trace"][1]["action"])
        self.assertTrue(gated["trace"][1]["output_enabled"])
        self.assertTrue(gated["trace"][2]["action"])


if __name__ == "__main__":
    unittest.main()
