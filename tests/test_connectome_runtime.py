"""Compact graph parity and bounded scale counters on an analytic chain."""

import unittest

try:
    import numpy as np
    from project_b.connectome.runtime_graph import ArraySparseGraph
except ImportError:
    np = None

from project_b.neurons import LIFParameters
from project_b.simulation import SpikingSimulator
from project_b.synapses import SparseGraph, Synapse


@unittest.skipIf(np is None, "array-backed connectome graph requires optional numpy")
class ConnectomeRuntimeTests(unittest.TestCase):
    def test_array_csr_matches_reference_and_counts_events(self):
        edges = [Synapse(1, 2, 8.0, 2000), Synapse(0, 1, 8.0, 2000)]
        compact = ArraySparseGraph(
            3, np.array([1, 0]), np.array([2, 1]),
            np.array([8.0, 8.0]), np.array([2000, 2000]),
            np.array([9, 8]),
        )
        parameters = [LIFParameters(refractory_us=100000)] * 3
        reference = SpikingSimulator(parameters, SparseGraph(3, edges), [20.0, 0.0, 0.0], record_spikes=True)
        actual = SpikingSimulator(parameters, compact, [20.0, 0.0, 0.0], record_spikes=True, track_active_synapses=True)
        expected = reference.run_until(12000)
        observed = actual.run_until(12000)
        self.assertEqual(observed.spikes, expected.spikes)
        self.assertEqual(observed.voltage_mv, expected.voltage_mv)
        self.assertEqual(actual.diagnostics().scheduled_events, 2)
        self.assertEqual(actual.diagnostics().delivered_events, 2)
        self.assertEqual(actual.diagnostics().unique_active_synapses, 2)
        self.assertEqual(len(actual.diagnostics().spike_counts_by_tick), 12)
        self.assertEqual(compact.source_rows.tolist(), [8, 9])

    def test_bad_compact_endpoint_rejected(self):
        with self.assertRaisesRegex(ValueError, "endpoint outside"):
            ArraySparseGraph(2, np.array([0]), np.array([2]), np.array([1.0]), np.array([1000]), np.array([0]))

    def test_event_safety_stop_keeps_complete_spike_batch(self):
        graph = ArraySparseGraph(
            3, np.array([0, 0]), np.array([1, 2]),
            np.array([1.0, 1.0]), np.array([2000, 2000]),
            np.array([0, 1]),
        )
        model = SpikingSimulator([LIFParameters()] * 3, graph, [20.0, 0.0, 0.0],
                                 max_scheduled_events=1)
        with self.assertRaisesRegex(RuntimeError, "scheduled event safety limit"):
            model.run_until(10000)
        self.assertEqual(model.diagnostics().scheduled_events, 0)
        self.assertEqual(sum(model.diagnostics().spike_counts_by_tick),
                         sum(model.spike_counts))
        self.assertEqual(len(model._queue), 0)


if __name__ == "__main__":
    unittest.main()
