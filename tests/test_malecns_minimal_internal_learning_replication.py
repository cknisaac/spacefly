"""Independent outcome-blind MaleCNS partition replication gate."""

import json
import unittest
from pathlib import Path

from project_b.malecns_minimal_internal_learning.experiment import run_experiment
from project_b.malecns_minimal_internal_learning.probe import run_probe


ROOT = Path.cwd()
CONFIG = "configs/malecns_minimal_internal_learning_replication.json"


class MaleCNSReplicationTests(unittest.TestCase):
    def test_partition_is_disjoint_and_matches_frozen_source_order(self):
        original = json.loads((ROOT / "configs/malecns_minimal_internal_learning.json")
                              .read_text(encoding="utf-8"))
        replication = json.loads((ROOT / CONFIG).read_text(encoding="utf-8"))
        original_ids = {row["source_id"] for row in original["circuit"]["selected_kcs"]}
        replicated = replication["circuit"]["selected_kcs"]
        self.assertEqual([row["source_id"] for row in replicated],
                         [41920, 42140, 42744, 43354, 43639, 43811, 44260, 44682])
        self.assertFalse(original_ids.intersection(row["source_id"] for row in replicated))
        self.assertEqual([row["state"] for row in replicated], ["A"] * 4 + ["B"] * 4)
        self.assertEqual(replication["circuit"]["plastic_contact_count"], 159)
        self.assertEqual(replication["controllability_probe"]["frozen_action_threshold_mv"],
                         original["controllability_probe"]["frozen_action_threshold_mv"])

    def test_replication_probe_and_learning_controls_pass(self):
        probe = run_probe(ROOT, CONFIG)
        self.assertEqual(probe["status"], "PASS")
        self.assertEqual(probe["frozen_action_threshold_mv"], 0.13266897755112178)
        self.assertTrue(probe["checkpoint_replay_identical"])
        result = run_experiment(ROOT, CONFIG)
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(all(result["criteria"].values()))


if __name__ == "__main__":
    unittest.main()
