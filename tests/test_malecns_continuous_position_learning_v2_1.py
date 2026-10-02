"""Frozen-protocol checks for the Level 2 v2.1 continuation."""

import copy
import json
import unittest
from pathlib import Path

from project_b.malecns_minimal_internal_learning.ltd import LocalLTD
from project_b.malecns_continuous_position_learning.experiment_v2_1 import (
    _new_presentation_rule, _v1_probe,
)


ROOT = Path.cwd()
V1_PATH = "configs/malecns_continuous_position_learning_v1.json"
V2_PATH = "configs/malecns_continuous_position_learning_v2_1.json"


class ContinuousPositionV21Tests(unittest.TestCase):
    def setUp(self):
        self.v1 = json.loads((ROOT / V1_PATH).read_text(encoding="utf-8"))
        self.v2 = json.loads((ROOT / V2_PATH).read_text(encoding="utf-8"))

    def test_only_eligibility_scope_and_duration_change(self):
        v1 = copy.deepcopy(self.v1)
        v2 = copy.deepcopy(self.v2)
        for data in (v1, v2):
            data.pop("experiment_id", None)
            data.pop("status", None)
            data.pop("continuation", None)
            data["training"].pop("blocks", None)
            data["training"].pop("sequence", None)
            data["training"].pop("eligibility_reset_scope", None)
            data["training"].pop("duration_status", None)
        self.assertEqual(v1, v2)
        self.assertEqual([x["source_id"] for x in self.v1["circuit"]["selected_kcs"]],
                         [x["source_id"] for x in self.v2["circuit"]["selected_kcs"]])
        self.assertEqual(self.v2["training"]["blocks"], 32)

    def test_frozen_schedule_repeats_without_early_stop(self):
        seq1 = [row for row in self.v1["training"]["sequence"] if row["block"] == 1]
        seq2 = self.v2["training"]["sequence"]
        self.assertEqual(len(seq2), 32 * len(seq1))
        for block in range(1, 33):
            actual = [row for row in seq2 if row["block"] == block]
            self.assertEqual([(r["position"], r["position_class"]) for r in actual],
                             [(r["position"], r["position_class"]) for r in seq1])

    def test_each_presentation_starts_with_zero_eligibility_and_keeps_weights(self):
        first = LocalLTD([0.5], tau_us=1_000_000, eta=0.00005, minimum_fraction=0.2)
        first.observe_kc_spike(0, 10_000)
        self.assertGreater(first.eligibility_at(0, 11_000), 0.0)
        carried_weights = list(first.weights)
        next_presentation = _new_presentation_rule(
            carried_weights, [0.5], self.v2["training"]["ltd"])
        self.assertEqual(next_presentation.weights, carried_weights)
        self.assertEqual(next_presentation.eligibility_at(0, 0), 0.0)

    def test_inherited_threshold_is_exactly_v1_probe_threshold(self):
        threshold, probe = _v1_probe(ROOT, self.v2)
        v1_probe = json.loads((ROOT / self.v1["controllability_probe"]["probe_result"])
                              .read_text(encoding="utf-8"))
        self.assertEqual(probe["status"], "PASS")
        self.assertEqual(threshold, v1_probe["frozen_action_threshold_mv"])
        self.assertEqual(threshold, self.v2["continuation"]["frozen_action_threshold_mv"])

    def test_saved_run_completed_all_arms_and_failed_learning_gate(self):
        result = json.loads((ROOT / "runs/malecns_continuous_position_learning_v2_1/result.json")
                            .read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(result["criteria"]["all_32_blocks_run_in_every_arm"])
        self.assertFalse(result["criteria"]["target_teaching_creates_target_core_action_region"])
        self.assertTrue(result["criteria"]["plasticity_off_does_not_learn_target_region"])
        self.assertEqual(len(result["primary"]["final_position_map"]), 21)


if __name__ == "__main__":
    unittest.main()
