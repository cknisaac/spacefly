import unittest

from project_b.malecns_continuous_position_learning.online_readout import (
    OnlinePositionReadout,
)
from project_b.osu.types import KeyActionKind


class OnlinePositionReadoutTests(unittest.TestCase):
    def test_bins_are_disabled_until_mbon_valid_and_use_maximum(self):
        readout = OnlinePositionReadout(
            position_grid=[0.5], bin_width=0.2, threshold_mv=0.01,
            dt_us=1_000,
        )
        readout.begin(0, 0.5)

        self.assertEqual(readout.step(1_000, 0.5, 0.0), ())
        self.assertIsNone(readout.first_valid_time_us)
        self.assertEqual(readout.decisions, ())

        self.assertEqual(readout.step(2_000, 0.4, 0.2), ())
        self.assertEqual(readout.first_valid_time_us, 2_000)
        # The 0.2 mV sample is paired with the previous position, 0.5.
        self.assertEqual(readout.step(3_000, 0.35, 0.001), ())

        decision, = readout.decisions
        self.assertEqual(decision.position, 0.5)
        self.assertEqual(decision.sample_count, 2)
        self.assertEqual(decision.max_voltage_mv, 0.2)
        self.assertFalse(decision.action)
        self.assertEqual(decision.decision_time_us, 3_000)
        self.assertEqual(readout.first_action_time_us, None)

    def test_first_action_has_one_fixed_hold_and_no_repeated_down(self):
        readout = OnlinePositionReadout(
            position_grid=[0.9, 0.5], bin_width=0.1, threshold_mv=0.01,
            dt_us=1_000, lane=2, key_hold_us=10_000,
        )
        readout.begin(0, 0.9)
        readout.step(1_000, 0.9, 0.005)
        down, = readout.step(2_000, 0.8, 0.005)
        self.assertIs(down.kind, KeyActionKind.DOWN)
        self.assertEqual((down.time_us, down.lane), (2_000, 2))
        self.assertEqual(readout.first_action_time_us, 2_000)

        actions = []
        for time_us in range(3_000, 12_001, 1_000):
            actions.extend(readout.step(time_us, 0.8, 0.005))
        self.assertEqual(len(actions), 1)
        self.assertIs(actions[0].kind, KeyActionKind.UP)
        self.assertEqual((actions[0].time_us, actions[0].lane), (12_000, 2))
        self.assertEqual(readout.first_action_time_us, 2_000)

    def test_absence_closes_input_and_finish_returns_scheduled_release(self):
        readout = OnlinePositionReadout(
            position_grid=[0.9, 0.5], bin_width=0.1, threshold_mv=0.01,
            dt_us=1_000, key_hold_us=10_000,
        )
        readout.begin(0, 0.9)
        readout.step(1_000, 0.9, 0.005)
        down, = readout.step(2_000, 0.8, 0.005)
        self.assertIs(down.kind, KeyActionKind.DOWN)

        self.assertEqual(readout.step(3_000, None, 0.005), ())
        self.assertEqual(readout.step(4_000, None, 0.005), ())
        release, = readout.finish(4_000)
        self.assertIs(release.kind, KeyActionKind.UP)
        self.assertEqual(release.time_us, 12_000)
        self.assertEqual([d.position for d in readout.decisions], [0.9, 0.5])
        self.assertEqual(readout.decisions[1].sample_count, 0)
        self.assertIsNone(readout.decisions[1].action)

    def test_only_a_bin_exit_makes_a_decision(self):
        readout = OnlinePositionReadout(
            position_grid=[0.5], bin_width=0.2, threshold_mv=0.01,
            dt_us=1_000,
        )
        readout.begin(0, 0.5)
        readout.step(1_000, 0.5, 0.005)
        self.assertEqual(readout.decisions, ())
        readout.finish(1_000)
        self.assertEqual(readout.decisions[0].decision_time_us, 1_000)

    def test_rejects_bad_configuration_and_noncausal_tick_sequences(self):
        with self.assertRaises(ValueError):
            OnlinePositionReadout(
                position_grid=[0.5], bin_width=0.1, threshold_mv=0.0,
                direction=True,
            )
        readout = OnlinePositionReadout(
            position_grid=[0.5], bin_width=0.1, threshold_mv=0.0,
        )
        with self.assertRaises(RuntimeError):
            readout.step(1_000, 0.5, 0.0)
        readout.begin(0, 0.5)
        with self.assertRaises(ValueError):
            readout.step(2_000, 0.5, 0.0)
        with self.assertRaises(ValueError):
            readout.step(1_000, 1.1, 0.0)


if __name__ == "__main__":
    unittest.main()
