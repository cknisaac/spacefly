"""The offline shuffled-reward control preserves utility frequencies."""

import unittest

from scripts.checkpoint_controls import shuffled_utilities


class ShuffledRewardTests(unittest.TestCase):
    def test_permutation_is_reproducible_and_breaks_pairing_when_possible(self) -> None:
        utilities = (-1.0, 0.875, -1.0, 1.0)
        shuffled = shuffled_utilities(utilities, 4)
        self.assertEqual(sorted(shuffled), sorted(utilities))
        self.assertNotEqual(shuffled, utilities)
        self.assertEqual(shuffled, shuffled_utilities(utilities, 4))
        self.assertEqual(shuffled_utilities((-1.0,) * 4, 4), (-1.0,) * 4)


if __name__ == "__main__":
    unittest.main()
