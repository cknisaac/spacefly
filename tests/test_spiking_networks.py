"""Analytically predictable A→B, A─|B, and A→B→C circuits."""

import unittest

from project_b.neurons import LIFParameters
from project_b.simulation import SpikingSimulator
from project_b.synapses import SparseGraph, Synapse


def run_circuit(edges: list[Synapse], drives: list[float], *, dt_us: int = 1_000,
                end_us: int = 40_000):
    parameters = [LIFParameters(refractory_us=100_000) for _ in drives]
    simulator = SpikingSimulator(parameters, SparseGraph(len(drives), edges), drives,
                                 dt_us=dt_us, record_neurons=range(len(drives)),
                                 record_spikes=True, record_arrivals=True)
    return simulator.run_until(end_us)


class CircuitTests(unittest.TestCase):
    def test_excitation_a_to_b(self) -> None:
        result = run_circuit([Synapse(0, 1, 8.0, 2_000)], [20.0, 0.0])
        self.assertEqual([(s.time_us, s.neuron_index) for s in result.spikes],
                         [(1_000, 0), (5_000, 1)])
        self.assertEqual([(a.time_us, a.pre, a.post, a.weight_mv)
                          for a in result.arrivals], [(3_000, 0, 1, 8.0)])
        b = {s.time_us: s for s in result.voltage_trace if s.neuron_index == 1}
        self.assertEqual(b[3_000].voltage_before_reset_mv, 0.0)
        self.assertGreater(b[4_000].voltage_before_reset_mv, 0.0)
        self.assertGreaterEqual(b[5_000].voltage_before_reset_mv, 1.0)
        self.assertEqual(b[5_000].voltage_after_reset_mv, 0.0)

    def test_inhibition_a_to_b(self) -> None:
        baseline = run_circuit([], [20.0, 2.0])
        inhibited = run_circuit([Synapse(0, 1, -6.0, 2_000)], [20.0, 2.0])
        baseline_b = [s.time_us for s in baseline.spikes if s.neuron_index == 1]
        inhibited_b = [s.time_us for s in inhibited.spikes if s.neuron_index == 1]
        self.assertEqual(baseline_b, [7_000])
        self.assertEqual(inhibited_b, [22_000])
        baseline_trace = {s.time_us: s for s in baseline.voltage_trace
                          if s.neuron_index == 1}
        inhibited_trace = {s.time_us: s for s in inhibited.voltage_trace
                           if s.neuron_index == 1}
        self.assertLess(inhibited_trace[4_000].voltage_before_reset_mv,
                        baseline_trace[4_000].voltage_before_reset_mv)
        self.assertEqual(inhibited.arrivals[0].weight_mv, -6.0)

    def test_chain_a_to_b_to_c(self) -> None:
        result = run_circuit([Synapse(0, 1, 8.0, 2_000),
                              Synapse(1, 2, 8.0, 2_000)], [20.0, 0.0, 0.0])
        self.assertEqual([(s.time_us, s.neuron_index) for s in result.spikes],
                         [(1_000, 0), (5_000, 1), (9_000, 2)])
        self.assertEqual([(a.time_us, a.pre, a.post) for a in result.arrivals],
                         [(3_000, 0, 1), (7_000, 1, 2)])
        c = [s for s in result.voltage_trace if s.neuron_index == 2]
        self.assertTrue(all(sample.voltage_before_reset_mv == 0.0
                            for sample in c if sample.time_us <= 7_000))

    def test_off_grid_synaptic_delay_is_exact(self) -> None:
        result = run_circuit([Synapse(0, 1, 8.0, 1_250)], [20.0, 0.0],
                             end_us=10_000)
        self.assertEqual([a.time_us for a in result.arrivals], [2_250])
        self.assertEqual([(s.time_us, s.neuron_index) for s in result.spikes],
                         [(1_000, 0), (4_000, 1)])
        b = {s.time_us: s for s in result.voltage_trace if s.neuron_index == 1}
        self.assertEqual(b[2_000].voltage_before_reset_mv, 0.0)
        self.assertGreater(b[3_000].voltage_before_reset_mv, 0.0)

    def test_tick_resolution_is_configurable_without_rounding_arrival(self) -> None:
        for dt_us, expected_a, expected_arrival, expected_b in (
            (1_000, 1_000, 2_250, 4_000),
            (500, 1_000, 2_250, 4_000),
            (250, 750, 2_000, 3_750),
        ):
            with self.subTest(dt_us=dt_us):
                result = run_circuit([Synapse(0, 1, 8.0, 1_250)], [20.0, 0.0],
                                     dt_us=dt_us, end_us=10_000)
                self.assertEqual([s.time_us for s in result.spikes],
                                 [expected_a, expected_b])
                self.assertEqual([a.time_us for a in result.arrivals],
                                 [expected_arrival])

    def test_replay_and_chunking_have_identical_timestamps(self) -> None:
        edges = [Synapse(1, 2, 8.0, 2_000), Synapse(0, 1, 8.0, 2_000)]
        reference = run_circuit(edges, [20.0, 0.0, 0.0], end_us=30_000)
        reordered = run_circuit(list(reversed(edges)), [20.0, 0.0, 0.0],
                                end_us=30_000)
        self.assertEqual(reference, reordered)
        simulator = SpikingSimulator([LIFParameters(refractory_us=100_000)] * 3,
                                     SparseGraph(3, edges), [20.0, 0.0, 0.0],
                                     record_neurons=range(3), record_spikes=True,
                                     record_arrivals=True)
        partial = simulator.run_until(2_000)
        self.assertEqual(partial.queued_arrivals, 1)
        self.assertEqual(simulator.run_until(30_000), reference)

    def test_coincident_arrivals_have_canonical_order(self) -> None:
        edges = [Synapse(1, 2, -3.0, 2_000), Synapse(0, 2, 8.0, 2_000)]
        first = run_circuit(edges, [20.0, 20.0, 0.0], end_us=10_000)
        second = run_circuit(list(reversed(edges)), [20.0, 20.0, 0.0],
                             end_us=10_000)
        self.assertEqual(first, second)
        self.assertEqual([(a.time_us, a.pre, a.post) for a in first.arrivals],
                         [(3_000, 0, 2), (3_000, 1, 2)])

    def test_selective_recording_and_invalid_time(self) -> None:
        simulator = SpikingSimulator([LIFParameters()], SparseGraph(1, []), [2.0])
        result = simulator.run_until(10_000)
        self.assertEqual(result.spike_counts, (1,))
        self.assertEqual(result.spikes, ())
        self.assertEqual(result.arrivals, ())
        self.assertEqual(result.voltage_trace, ())
        for end_us in (10_001, -1, 1.0):
            with self.subTest(end_us=end_us), self.assertRaises(ValueError):
                simulator.run_until(end_us)  # type: ignore[arg-type]

    def test_external_drive_changes_only_future_intervals(self) -> None:
        simulator = SpikingSimulator([LIFParameters(refractory_us=100_000)],
                                     SparseGraph(1, []), [0.0], record_spikes=True)
        simulator.run_until(5_000)
        self.assertEqual(simulator.snapshot().spikes, ())
        simulator.set_external_drive_mv([2.0])
        simulator.run_until(12_000)
        self.assertEqual([spike.time_us for spike in simulator.snapshot().spikes],
                         [12_000])
        with self.assertRaises(ValueError):
            simulator.set_external_drive_mv([float("nan")])


if __name__ == "__main__":
    unittest.main()
