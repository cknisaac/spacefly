"""Gate tests for the isolated MaleCNS minimal internal-learning fixture."""

import unittest

from project_b.malecns_minimal_internal_learning.ltd import LocalLTD
from project_b.malecns_minimal_internal_learning.experiment import run_experiment
from project_b.malecns_minimal_internal_learning.probe import run_probe


class LocalLTDGateTests(unittest.TestCase):
    def test_active_kc_and_teacher_depress_only_that_selected_edge(self):
        rule = LocalLTD([0.4, 0.6], eta=0.1)
        rule.observe_kc_spike(0, 1_000)
        changes = rule.teacher_pulse(2_000, teacher=True)
        self.assertEqual(len(changes), 1)
        self.assertLess(rule.weights[0], 0.4)
        self.assertEqual(rule.weights[1], 0.6)

    def test_inactive_kc_with_teacher_does_not_change_weight(self):
        rule = LocalLTD([0.4])
        self.assertEqual(rule.teacher_pulse(1_000, teacher=True), ())
        self.assertEqual(rule.weights, [0.4])

    def test_kc_activity_without_teacher_does_not_change_weight(self):
        rule = LocalLTD([0.4])
        rule.observe_kc_spike(0, 1_000)
        self.assertEqual(rule.teacher_pulse(2_000, teacher=False), ())
        self.assertEqual(rule.weights, [0.4])

    def test_plasticity_off_is_unchanged(self):
        rule = LocalLTD([0.4])
        rule.observe_kc_spike(0, 1_000)
        self.assertEqual(rule.teacher_pulse(2_000, teacher=False), ())
        self.assertEqual(rule.weights, [0.4])

    def test_nonplastic_edge_is_unchanged(self):
        rule = LocalLTD([0.4, 0.6], plastic_slots=(0,))
        rule.observe_kc_spike(0, 1_000)
        rule.observe_kc_spike(1, 1_000)
        rule.teacher_pulse(2_000, teacher=True)
        self.assertLess(rule.weights[0], 0.4)
        self.assertEqual(rule.weights[1], 0.6)


class MinimalExperimentGateTests(unittest.TestCase):
    def test_frozen_probe_passes_and_replays_exactly(self):
        result = run_probe(__import__("pathlib").Path.cwd())
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["checkpoint_replay_identical"])
        self.assertTrue(result["deterministic_replay_identical"])

    def test_fixed_training_and_matched_controls_meet_declared_gate(self):
        result = run_experiment(__import__("pathlib").Path.cwd())
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(all(result["criteria"].values()))


if __name__ == "__main__":
    unittest.main()
