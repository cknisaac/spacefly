import unittest
from pathlib import Path

from project_b.malecns_continuous_position_learning.experiment_level4a_temporal_input_admission import (
    CONFIG_DEFAULT,
    _inputs,
    _position_at,
)


ROOT = Path(__file__).resolve().parents[1]


class Level4ATemporalInputAdmissionTests(unittest.TestCase):
    def test_predeclared_duration_set_and_fixed_inherited_settings(self):
        stage, _, parent, _, threshold = _inputs(ROOT, CONFIG_DEFAULT)
        self.assertEqual(stage["protocol"]["candidate_durations_ms"],
                         [100, 250, 500, 750, 1000])
        self.assertEqual(stage["protocol"]["peak_drive_mv_equivalent"], 1.2)
        self.assertEqual(stage["protocol"]["action_threshold_mv"], threshold)
        self.assertEqual(stage["protocol"]["position_grid"], parent["evaluation"]["position_grid"])
        self.assertEqual(stage["protocol"]["learning"], "OFF")
        self.assertEqual(stage["protocol"]["dan_teaching"], "OFF; no DAN stimulation")

    def test_current_position_path_has_fixed_endpoints_at_every_duration(self):
        for duration in (100_000, 250_000, 500_000, 750_000, 1_000_000):
            self.assertEqual(_position_at(0, duration), 1.0)
            self.assertAlmostEqual(_position_at(duration, duration), 0.0)
            positions = [_position_at(t, duration)
                         for t in range(0, duration + 1_000, 1_000)]
            self.assertTrue(all(a >= b for a, b in zip(positions, positions[1:])))


if __name__ == "__main__":
    unittest.main()
