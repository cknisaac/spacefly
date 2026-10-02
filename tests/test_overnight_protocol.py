"""Predeclared map/selection rules without launching training."""

import json
import unittest

from scripts.overnight_synthetic import (
    DEFAULT_CONFIG, choose_candidate, map_for_seed, seed_range,
)


class OvernightProtocolTests(unittest.TestCase):
    def test_seed_splits_and_maps_are_independent_and_replayable(self) -> None:
        spec = json.loads(DEFAULT_CONFIG.read_text(encoding="utf-8"))
        dev = seed_range(spec["development_seeds"])
        heldout = seed_range(spec["heldout_seeds"])
        self.assertFalse(set(dev) & set(heldout))
        first = map_for_seed(dev[0], 40, spec)
        self.assertEqual(first, map_for_seed(dev[0], 40, spec))
        self.assertNotEqual(first, map_for_seed(heldout[0], 40, spec))
        times, gains = first
        self.assertEqual(len(times), 40)
        self.assertEqual(len(gains), 40)
        self.assertTrue(all(800_000 <= b-a <= 1_200_000
                            for a, b in zip(times, times[1:])))
        self.assertTrue(all(0.5 <= value <= 1.5 for value in gains))

    def test_candidate_selection_reads_only_development_rows(self) -> None:
        spec = {
            "development_seeds": {"start": 1, "count": 2},
            "candidate_readout_thresholds": [6, 8],
        }
        rows = {}
        for threshold, good in ((6, 25.0), (8, 50.0)):
            for seed in (1, 2):
                rows[f"dev:{threshold}:{seed}:on"] = {
                    "summary": {"frozen_good_or_better_percent": good,
                                "frozen_non_miss_percent": good}}
        rows["heldout:6:100:on"] = {
            "summary": {"frozen_good_or_better_percent": 100.0}}
        self.assertEqual(choose_candidate(rows, spec), 8)


if __name__ == "__main__":
    unittest.main()
