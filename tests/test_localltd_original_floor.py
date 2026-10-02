"""Focused regression tests for the immutable LocalLTD run-start floor."""

import unittest

from project_b.malecns_minimal_internal_learning.ltd import LocalLTD


class LocalLTDOriginalFloorTests(unittest.TestCase):
    def test_floor_does_not_compound_across_fresh_presentations(self):
        baseline = [0.5]
        current = list(baseline)

        for _ in range(20):
            rule = LocalLTD(
                current,
                original_weights=baseline,
                eta=0.1,
                minimum_fraction=0.2,
            )
            rule.observe_kc_spike(0, 0)
            rule.teacher_pulse(0, teacher=True)
            current = list(rule.weights)
            self.assertGreaterEqual(current[0], 0.2 * baseline[0])

        self.assertEqual(current, [0.1])
        self.assertEqual(baseline, [0.5])

    def test_constructor_rejects_weight_below_original_floor(self):
        with self.assertRaisesRegex(ValueError, "below its original-weight floor"):
            LocalLTD([0.099], original_weights=[0.5], minimum_fraction=0.2)

    def test_constructor_rejects_mismatched_vectors(self):
        with self.assertRaisesRegex(ValueError, "equal length"):
            LocalLTD([0.5], original_weights=[0.5, 0.25])


if __name__ == "__main__":
    unittest.main()
