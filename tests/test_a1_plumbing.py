"""A1 generic learning-plumbing invariants; no fly-rule or task claim."""

import math
import unittest

from project_b.neurons import LIFParameters
from project_b.plasticity import PlasticityParameters, ThreeFactorPlasticity
from project_b.simulation import SpikingSimulator
from project_b.synapses import SparseGraph, Synapse


class A1PlumbingTests(unittest.TestCase):
    def test_delayed_update_is_masked_and_independent_of_spike_batch_order(self) -> None:
        graph = SparseGraph(4, (
            Synapse(0, 2, 1.0, 1_000),
            Synapse(0, 3, 0.3, 1_000),
            Synapse(1, 2, 0.6, 1_000),
        ))
        parameters = PlasticityParameters(0.5, 10_000, 20_000, 0.0, 2.0)
        rules = [ThreeFactorPlasticity(graph, (0, 2), parameters) for _ in range(2)]
        for rule, pres, posts in zip(rules, ((0, 1), (1, 0)), ((2, 3), (3, 2))):
            rule.observe_spikes(1_000, pres)
            rule.observe_spikes(2_000, posts)
            self.assertEqual(rule.apply_dopamine(3_000, 0.0), ())
        results = [rule.apply_dopamine(7_000, 0.5) for rule in rules]
        self.assertEqual(results[0], results[1])
        expected_eligibility = math.exp(-1_000 / 10_000) * math.exp(-5_000 / 20_000)
        expected_delta = 0.5 * expected_eligibility * 0.5
        self.assertEqual(tuple(change.edge_slot for change in results[0]), (0, 2))
        for rule in rules:
            self.assertAlmostEqual(rule.effective_weight(0), 1.0 + expected_delta)
            self.assertAlmostEqual(rule.effective_weight(2), 0.6 + expected_delta)
            self.assertEqual(rule.effective_weight(1), 0.3)
        self.assertEqual(graph.weights_mv, (1.0, 0.3, 0.6))

    def test_both_bounds_and_rejected_update_are_atomic(self) -> None:
        graph = SparseGraph(3, (
            Synapse(0, 2, 0.5, 1_000),
            Synapse(1, 2, 0.5, 1_000),
        ))
        bounded = ThreeFactorPlasticity(
            graph, (0,), PlasticityParameters(10.0, 10_000, 20_000, 0.2, 1.2))
        bounded.observe_spikes(1_000, (0,))
        bounded.observe_spikes(2_000, (2,))
        up = bounded.apply_dopamine(2_000, 1.0)
        self.assertEqual(up[0].new_weight_mv, 1.2)
        down = bounded.apply_dopamine(3_000, -1.0)
        self.assertEqual(down[0].previous_weight_mv, 1.2)
        self.assertEqual(down[0].new_weight_mv, 0.2)
        self.assertEqual(bounded.effective_weight(1), 0.5)

        # The first selected slot has a finite proposed value while the
        # second overflows. Neither proposed change may be committed.
        failing = ThreeFactorPlasticity(
            graph, (0, 1), PlasticityParameters(1e308, 10_000, 20_000, 0.0, 2.0))
        failing.observe_spikes(1_000, (0, 1))
        failing.observe_spikes(1_500, (1,))
        failing.observe_spikes(2_000, (2,))
        before = tuple(failing.effective_weight(slot) for slot in (0, 1))
        eligibility = tuple(failing.eligibility_at(slot, 2_000) for slot in (0, 1))
        with self.assertRaises(ArithmeticError):
            failing.apply_dopamine(2_000, 1.0)
        self.assertEqual(tuple(failing.effective_weight(slot) for slot in (0, 1)), before)
        self.assertEqual(tuple(failing.eligibility_at(slot, 2_000) for slot in (0, 1)),
                         eligibility)
        self.assertEqual(graph.weights_mv, (0.5, 0.5))

    def test_dopamine_changes_only_selected_weight_not_simulator_state(self) -> None:
        graph = SparseGraph(3, (
            Synapse(0, 1, 8.0, 2_000),
            Synapse(0, 2, 0.5, 2_000),
        ))
        rule = ThreeFactorPlasticity(
            graph, (0,), PlasticityParameters(0.1, 10_000, 20_000, 0.0, 12.0))
        sim = SpikingSimulator(
            (LIFParameters(refractory_us=1_000_000),) * 3,
            graph, (20.0, 0.0, 0.0), plasticity=rule, record_spikes=True)
        sim.run_until(6_000)
        self.assertGreater(rule.eligibility_at(0, 6_000), 0.0)
        before_snapshot = sim.snapshot()
        before_diagnostics = sim.diagnostics()
        before_queue = tuple(sim._queue)
        before_parameters = sim.parameters
        before_drive = sim.external_drive_mv
        changes = sim.apply_dopamine(1.0)
        self.assertEqual(tuple(change.edge_slot for change in changes), (0,))
        self.assertGreater(rule.effective_weight(0), 8.0)
        self.assertEqual(rule.effective_weight(1), 0.5)
        self.assertEqual(graph.weights_mv, (8.0, 0.5))
        self.assertEqual(sim.snapshot(), before_snapshot)
        self.assertEqual(sim.diagnostics(), before_diagnostics)
        self.assertEqual(tuple(sim._queue), before_queue)
        self.assertEqual(sim.parameters, before_parameters)
        self.assertEqual(sim.external_drive_mv, before_drive)


if __name__ == "__main__":
    unittest.main()
