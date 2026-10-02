"""Outcome-blind schedule and coupled cross-state infrastructure checks."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from project_b.mvp_c1.cross_state import select_checkpoints


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads((ROOT / "configs/a5_cross_state_contract.json").read_text(encoding="utf-8"))


class SelectionTests(unittest.TestCase):
    def test_complete_deterministic_schedule(self):
        runs = (("fixture-11", 11), ("fixture-12", 12))
        cuts = select_checkpoints(CONTRACT, horizon_us=400_000, runs=runs)
        self.assertEqual([(x.run_id, x.phase, x.checkpoint_us) for x in cuts], [
            ("fixture-11", "early", 100_000),
            ("fixture-11", "middle", 200_000),
            ("fixture-11", "late", 300_000),
            ("fixture-12", "early", 100_000),
            ("fixture-12", "middle", 200_000),
            ("fixture-12", "late", 300_000)])
        self.assertEqual(cuts, select_checkpoints(CONTRACT, horizon_us=400_000, runs=runs))
        self.assertEqual([x.checkpoint_us for x in select_checkpoints(
            CONTRACT, horizon_us=1_000_000, runs=(("future", 9),))],
            [250_000, 500_000, 750_000])

    def test_invalid_or_ambiguous_schedule_rejected(self):
        for horizon in (0, 1_000, 3_000, 401_001):
            with self.subTest(horizon=horizon), self.assertRaises(ValueError):
                select_checkpoints(CONTRACT, horizon_us=horizon, runs=(("a", 1),))
        with self.assertRaises(ValueError):
            select_checkpoints(CONTRACT, horizon_us=400_000,
                               runs=(("a", 1), ("a", 2)))
        with self.assertRaises(ValueError):
            select_checkpoints(CONTRACT, horizon_us=400_000, runs=())


if __name__ == "__main__":
    unittest.main()
