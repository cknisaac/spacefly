"""Compact CSR adapter for selected source edges and explicit model overlays."""

from __future__ import annotations

import numpy as np


class ArraySparseGraph:
    """O(N+E) outgoing CSR compatible with the CPU reference simulator.

    Source topology/counts are supplied by the importer. The signed effects
    and delays are explicit engineering overlays, never inferred biology.
    """

    def __init__(
        self,
        neuron_count: int,
        pre_indices: np.ndarray,
        post_indices: np.ndarray,
        weights_mv: np.ndarray,
        delays_us: np.ndarray,
        source_rows: np.ndarray,
    ) -> None:
        if type(neuron_count) is not int or neuron_count <= 0:
            raise ValueError("neuron_count must be positive")
        pre = np.asarray(pre_indices, dtype=np.int64)
        post = np.asarray(post_indices, dtype=np.int64)
        weights = np.asarray(weights_mv, dtype=np.float64)
        delays = np.asarray(delays_us, dtype=np.int64)
        source = np.asarray(source_rows, dtype=np.int64)
        if not (len(pre) == len(post) == len(weights) == len(delays) == len(source)):
            raise ValueError("edge columns must have equal length")
        if (np.any(pre < 0) or np.any(pre >= neuron_count)
                or np.any(post < 0) or np.any(post >= neuron_count)):
            raise ValueError("edge endpoint outside graph")
        if np.any(~np.isfinite(weights)) or np.any(weights == 0):
            raise ValueError("weights must be finite and nonzero")
        if np.any(delays <= 0) or np.any(source < 0):
            raise ValueError("delays must be positive and source rows nonnegative")
        order = np.lexsort((weights, delays, post, pre))
        sorted_pre = pre[order]
        counts = np.bincount(sorted_pre, minlength=neuron_count)
        self.offsets = np.empty(neuron_count + 1, dtype=np.int64)
        self.offsets[0] = 0
        np.cumsum(counts, out=self.offsets[1:])
        self.neuron_count = neuron_count
        self.pre_indices = sorted_pre.astype(np.uint32)
        self.post_indices = post[order].astype(np.uint32)
        self.weights_mv = weights[order]
        self.delays_us = delays[order].astype(np.int64)
        self.source_rows = source[order].astype(np.uint32)

    @property
    def edge_count(self) -> int:
        return len(self.post_indices)

    def outgoing_slots(self, pre: int) -> range:
        if type(pre) is not int or not 0 <= pre < self.neuron_count:
            raise ValueError("pre outside graph")
        return range(int(self.offsets[pre]), int(self.offsets[pre + 1]))
