"""Immutable presynaptic CSR adjacency with signed, delayed edges."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

from project_b.utils.time import require_time_us


@dataclass(frozen=True, slots=True)
class Synapse:
    """Fixed signed model effect; sign is not inferred from transmitter."""

    pre: int
    post: int
    weight_mv: float
    delay_us: int

    def __post_init__(self) -> None:
        if type(self.pre) is not int or type(self.post) is not int:
            raise ValueError("pre and post must be integer neuron indices")
        if not math.isfinite(self.weight_mv) or self.weight_mv == 0:
            raise ValueError("weight_mv must be finite and nonzero")
        if require_time_us(self.delay_us, "delay_us") <= 0:
            raise ValueError("delay_us must be positive")


class SparseGraph:
    """O(N+E) outgoing CSR; no pairwise N×N storage."""

    def __init__(self, neuron_count: int, edges: Iterable[Synapse]):
        if type(neuron_count) is not int or neuron_count <= 0:
            raise ValueError("neuron_count must be a positive integer")
        ordered = list(edges)
        for edge in ordered:
            if not isinstance(edge, Synapse):
                raise TypeError("edges must be Synapse records")
            if not (0 <= edge.pre < neuron_count and 0 <= edge.post < neuron_count):
                raise ValueError("synapse endpoint outside graph")
        ordered.sort(key=lambda edge: (edge.pre, edge.post, edge.delay_us, edge.weight_mv))
        counts = [0] * neuron_count
        for edge in ordered:
            counts[edge.pre] += 1
        offsets = [0]
        for count in counts:
            offsets.append(offsets[-1] + count)
        self.neuron_count = neuron_count
        self.offsets = tuple(offsets)
        self.pre_indices = tuple(edge.pre for edge in ordered)
        self.post_indices = tuple(edge.post for edge in ordered)
        self.weights_mv = tuple(edge.weight_mv for edge in ordered)
        self.delays_us = tuple(edge.delay_us for edge in ordered)

    @property
    def edge_count(self) -> int:
        return len(self.post_indices)

    def outgoing_slots(self, pre: int) -> range:
        if type(pre) is not int or not 0 <= pre < self.neuron_count:
            raise ValueError("pre outside graph")
        return range(self.offsets[pre], self.offsets[pre + 1])
