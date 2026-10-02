"""State-machine check for the one diagnostic quiet-rearm readout."""

import unittest

from project_b.osu import KeyActionKind
from scripts.quiet_rearm_readout_development import QuietRearmReadout


class QuietRearmDiagnosticTests(unittest.TestCase):
    def test_sustained_activity_cannot_press_again_until_quiet(self) -> None:
        readout = QuietRearmReadout(range(12), on_threshold=10)
        first = readout.observe(1_000, range(12))
        self.assertEqual(first.action.kind, KeyActionKind.DOWN)
        release = readout.observe(31_000, range(12))
        self.assertEqual(release.action.kind, KeyActionKind.UP)
        self.assertFalse(readout.armed)
        self.assertIsNone(readout.observe(201_000, range(12)))
        self.assertFalse(readout.armed)
        self.assertIsNone(readout.observe(222_000, ()))
        self.assertTrue(readout.armed)
        second = readout.observe(223_000, range(12))
        self.assertEqual(second.action.kind, KeyActionKind.DOWN)
        self.assertEqual([e["time_us"] for e in readout.rearm_events], [222_000])


if __name__ == "__main__":
    unittest.main()
