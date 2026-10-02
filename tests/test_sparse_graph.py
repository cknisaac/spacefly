"""Sparse adjacency and validation, with no N×N matrix allocation."""

import sys
import unittest

from project_b.synapses import SparseGraph, Synapse


class SparseGraphTests(unittest.TestCase):
    def test_csr_outgoing_lists(self) -> None:
        graph = SparseGraph(4, [Synapse(2, 3, -1.0, 5),
                                Synapse(0, 2, 2.0, 7),
                                Synapse(0, 1, 1.0, 3)])
        self.assertEqual(graph.offsets, (0, 2, 2, 3, 3))
        self.assertEqual(graph.post_indices, (1, 2, 3))
        self.assertEqual(graph.pre_indices, (0, 0, 2))
        self.assertEqual(list(graph.outgoing_slots(1)), [])
        self.assertEqual(list(graph.outgoing_slots(2)), [2])

    def test_large_sparse_graph_storage_scales_as_n_plus_e(self) -> None:
        graph = SparseGraph(100_000, [Synapse(0, 99_999, 1.0, 1),
                                      Synapse(5, 6, -1.0, 2),
                                      Synapse(50_000, 51_000, 0.2, 3)])
        self.assertEqual(len(graph.offsets), 100_001)
        self.assertEqual(graph.edge_count, 3)
        self.assertEqual(len(graph.post_indices), 3)
        self.assertLess(sum(sys.getsizeof(value) for value in graph.__dict__.values()),
                        2_000_000)
        self.assertEqual(list(graph.outgoing_slots(99_998)), [])

    def test_invalid_edges_rejected(self) -> None:
        for kwargs in ({"delay_us": 0}, {"weight_mv": 0.0},
                       {"weight_mv": float("inf")}, {"pre": 0.5}):
            values = {"pre": 0, "post": 1, "weight_mv": 1.0, "delay_us": 1}
            values.update(kwargs)
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                Synapse(**values)
        with self.assertRaises(ValueError):
            SparseGraph(2, [Synapse(0, 2, 1.0, 1)])
        with self.assertRaises(ValueError):
            SparseGraph(0, [])


if __name__ == "__main__":
    unittest.main()
