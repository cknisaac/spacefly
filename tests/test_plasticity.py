"""Four dopamine gates and sparse, causal eligibility behavior."""

import math
import unittest

from project_b.neurons import LIFParameters
from project_b.plasticity import PlasticityParameters, ThreeFactorPlasticity
from project_b.simulation import SpikingSimulator
from project_b.synapses import SparseGraph, Synapse


def paired_circuit(*, drive_pre: float = 20.0):
    graph = SparseGraph(2, [Synapse(0, 1, 8.0, 2_000)])
    rule = ThreeFactorPlasticity(
        graph, [0], PlasticityParameters(
            eta=0.1, tau_pre_us=10_000, tau_eligibility_us=20_000,
            w_min_mv=0.0, w_max_mv=12.0))
    simulator = SpikingSimulator(
        [LIFParameters(refractory_us=1_000_000)] * 2,
        graph, [drive_pre, 0.0], plasticity=rule, record_spikes=True,
        record_arrivals=True)
    return graph, rule, simulator


class FourCaseGateTests(unittest.TestCase):
    def test_recent_pre_post_activity_plus_dopamine_changes_weight(self) -> None:
        graph, rule, sim = paired_circuit()
        result = sim.run_until(6_000)
        self.assertEqual([(s.time_us, s.neuron_index) for s in result.spikes],
                         [(1_000, 0), (5_000, 1)])
        eligibility = rule.eligibility_at(0, 6_000)
        self.assertAlmostEqual(
            eligibility, math.exp(-4_000 / 10_000) * math.exp(-1_000 / 20_000))
        changes = sim.apply_dopamine(1.0)
        self.assertEqual(len(changes), 1)
        self.assertAlmostEqual(changes[0].applied_delta_mv, 0.1 * eligibility)
        self.assertGreater(rule.effective_weight(0), 8.0)
        self.assertEqual(graph.weights_mv[0], 8.0)

    def test_recent_activity_without_dopamine_does_not_change_weight(self) -> None:
        _, rule, sim = paired_circuit()
        sim.run_until(6_000)
        self.assertGreater(rule.eligibility_at(0, 6_000), 0.0)
        self.assertEqual(sim.apply_dopamine(0.0), ())
        self.assertEqual(rule.effective_weight(0), 8.0)
        sim.run_until(10_000)
        self.assertEqual(rule.effective_weight(0), 8.0)

    def test_dopamine_without_recent_activity_does_not_change_weight(self) -> None:
        _, rule, sim = paired_circuit(drive_pre=0.0)
        self.assertEqual(sim.run_until(6_000).spikes, ())
        self.assertEqual(rule.eligibility_at(0, 6_000), 0.0)
        self.assertEqual(sim.apply_dopamine(1.0), ())
        self.assertEqual(rule.effective_weight(0), 8.0)

    def test_dopamine_after_long_wait_has_much_smaller_effect(self) -> None:
        _, recent_rule, recent_sim = paired_circuit()
        recent_sim.run_until(6_000)
        recent_delta = recent_sim.apply_dopamine(1.0)[0].applied_delta_mv

        _, late_rule, late_sim = paired_circuit()
        late_sim.run_until(206_000)
        self.assertEqual([(s.time_us, s.neuron_index)
                          for s in late_sim.snapshot().spikes],
                         [(1_000, 0), (5_000, 1)])
        late_delta = late_sim.apply_dopamine(1.0)[0].applied_delta_mv
        self.assertGreater(late_delta, 0.0)
        self.assertLess(late_delta, recent_delta / 1_000)
        self.assertAlmostEqual(
            late_rule.eligibility_at(0, 206_000)
            / recent_rule.eligibility_at(0, 6_000),
            math.exp(-200_000 / 20_000))


class LocalRuleTests(unittest.TestCase):
    def test_pair_order_simultaneity_and_unpaired_spikes(self) -> None:
        graph = SparseGraph(2, [Synapse(0, 1, 1.0, 1_000)])
        parameters = PlasticityParameters(0.2, 10_000, 20_000, 0.0, 2.0)
        post_first = ThreeFactorPlasticity(graph, [0], parameters)
        post_first.observe_spikes(1_000, [1])
        post_first.observe_spikes(2_000, [0])
        self.assertEqual(post_first.eligibility_at(0, 2_000), 0.0)
        self.assertEqual(post_first.apply_dopamine(2_000, 1.0), ())

        simultaneous = ThreeFactorPlasticity(graph, [0], parameters)
        simultaneous.observe_spikes(1_000, [0, 1])
        self.assertEqual(simultaneous.eligibility_at(0, 1_000), 0.0)
        self.assertEqual(simultaneous.apply_dopamine(1_000, 1.0), ())
        simultaneous.observe_spikes(2_000, [1])
        self.assertAlmostEqual(simultaneous.eligibility_at(0, 2_000),
                               math.exp(-1_000 / 10_000))

    def test_only_masked_sparse_edge_changes_and_negative_dopamine(self) -> None:
        graph = SparseGraph(3, [Synapse(0, 1, 1.0, 1_000),
                                Synapse(0, 2, 2.0, 1_000)])
        rule = ThreeFactorPlasticity(
            graph, [0], PlasticityParameters(0.2, 10_000, 20_000, 0.0, 3.0))
        rule.observe_spikes(1_000, [0])
        rule.observe_spikes(2_000, [1, 2])
        self.assertEqual(len(rule.apply_dopamine(2_000, -1.0)), 1)
        self.assertLess(rule.effective_weight(0), 1.0)
        self.assertEqual(rule.effective_weight(1), 2.0)
        self.assertEqual(graph.weights_mv, (1.0, 2.0))

    def test_weight_bounds_and_validation(self) -> None:
        graph = SparseGraph(2, [Synapse(0, 1, 1.0, 1_000)])
        rule = ThreeFactorPlasticity(
            graph, [0], PlasticityParameters(10.0, 10_000, 20_000, 0.0, 1.5))
        rule.observe_spikes(1_000, [0])
        rule.observe_spikes(2_000, [1])
        self.assertEqual(rule.apply_dopamine(2_000, 1.0)[0].new_weight_mv, 1.5)
        self.assertEqual(rule.apply_dopamine(2_000, 1.0), ())
        with self.assertRaises(ValueError):
            rule.observe_spikes(1_000, [0])
        with self.assertRaises(ValueError):
            rule.apply_dopamine(2_000, float("nan"))
        with self.assertRaises(ValueError):
            ThreeFactorPlasticity(graph, [1], rule.parameters)

    def test_future_spikes_use_new_weight_but_queued_arrivals_keep_old_weight(self) -> None:
        graph = SparseGraph(1, [Synapse(0, 0, 0.1, 5_000)])
        rule = ThreeFactorPlasticity(
            graph, [0], PlasticityParameters(0.5, 10_000, 20_000, 0.0, 2.0))
        sim = SpikingSimulator(
            [LIFParameters(refractory_us=2_000)], graph, [20.0],
            plasticity=rule, record_spikes=True, record_arrivals=True)
        sim.run_until(4_000)
        self.assertEqual([s.time_us for s in sim.snapshot().spikes], [1_000, 4_000])
        self.assertGreater(rule.eligibility_at(0, 4_000), 0.0)
        self.assertEqual(len(sim.apply_dopamine(1.0)), 1)
        learned_weight = rule.effective_weight(0)
        sim.run_until(13_000)
        arrivals = sim.snapshot().arrivals
        self.assertEqual(arrivals[0].time_us, 6_000)
        self.assertEqual(arrivals[0].weight_mv, 0.1)
        self.assertEqual(arrivals[1].time_us, 9_000)
        self.assertEqual(arrivals[1].weight_mv, 0.1)
        self.assertTrue(any(a.weight_mv == learned_weight for a in arrivals[2:]))


if __name__ == "__main__":
    unittest.main()
