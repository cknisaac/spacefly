"""Frozen-duration protocol checks for Level 2 v2.3 and v2.4."""

import copy
import json
import unittest
from pathlib import Path

from project_b.malecns_continuous_position_learning.probe import load_config
from project_b.malecns_continuous_position_learning.experiment_v2_1 import _v1_probe


ROOT = Path.cwd()
V22_PATH = ROOT / "configs/malecns_continuous_position_learning_v2_2.json"


class ContinuousPositionLongerRunTests(unittest.TestCase):
    def setUp(self):
        self.v22 = json.loads(V22_PATH.read_text(encoding="utf-8"))

    def check_version(self, version, blocks):
        path = f"configs/malecns_continuous_position_learning_v{version}.json"
        current = load_config(ROOT, path)
        a, b = copy.deepcopy(self.v22), copy.deepcopy(current)
        for data in (a, b):
            data.pop("experiment_id", None)
            data.pop("status", None)
            data.pop("continuation", None)
            data["training"].pop("blocks")
            data["training"].pop("sequence")
            data["training"].pop("duration_status")
        self.assertEqual(a, b)
        self.assertEqual(current["training"]["blocks"], blocks)
        self.assertEqual(len(current["training"]["sequence"]), blocks * 10)
        threshold, probe = _v1_probe(ROOT, current)
        self.assertEqual(probe["status"], "PASS")
        self.assertEqual(threshold, 0.005572335995331903)
        block_one = [row for row in self.v22["training"]["sequence"] if row["block"] == 1]
        for block in range(1, blocks + 1):
            rows = [row for row in current["training"]["sequence"] if row["block"] == block]
            self.assertEqual([(row["position"], row["position_class"]) for row in rows],
                             [(row["position"], row["position_class"]) for row in block_one])

    def test_v23_is_only_120_block_duration_continuation(self):
        self.check_version("2_3", 120)

    def test_v24_is_only_144_block_duration_continuation(self):
        self.check_version("2_4", 144)

    def test_both_saved_receipts_completed_their_fixed_runs(self):
        for version, blocks in (("2_3", 120), ("2_4", 144)):
            path = ROOT / f"runs/malecns_continuous_position_learning_v{version}/result.json"
            result = json.loads(path.read_text(encoding="utf-8"))
            self.assertTrue(result["criteria"][f"all_{blocks}_blocks_and_{blocks * 10}_presentations_run_in_every_arm"])
            self.assertEqual(len(result["learning_curves"]["target_teacher"]), blocks)
            self.assertEqual(len(result["target_teacher"]["final_position_map"]), 21)


if __name__ == "__main__":
    unittest.main()
