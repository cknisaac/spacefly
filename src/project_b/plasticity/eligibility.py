"""Sparse pre/post eligibility traces with externally supplied dopamine."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

from project_b.synapses import SparseGraph
from project_b.utils.time import require_time_us


@dataclass(frozen=True, slots=True)
class PlasticityParameters:
    """Engineering parameters; dopamine is a dimensionless signed scalar."""

    eta: float
    tau_pre_us: int
    tau_eligibility_us: int
    w_min_mv: float
    w_max_mv: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.eta) or self.eta <= 0:
            raise ValueError("eta must be finite and positive")
        if require_time_us(self.tau_pre_us, "tau_pre_us") <= 0:
            raise ValueError("tau_pre_us must be positive")
        if require_time_us(self.tau_eligibility_us, "tau_eligibility_us") <= 0:
            raise ValueError("tau_eligibility_us must be positive")
        if not (math.isfinite(self.w_min_mv) and math.isfinite(self.w_max_mv)):
            raise ValueError("weight bounds must be finite")
        if self.w_min_mv >= self.w_max_mv:
            raise ValueError("w_min_mv must be smaller than w_max_mv")


@dataclass(frozen=True, slots=True)
class WeightChange:
    time_us: int
    edge_slot: int
    previous_weight_mv: float
    new_weight_mv: float
    eligibility: float
    dopamine: float

    @property
    def applied_delta_mv(self) -> float:
        return self.new_weight_mv - self.previous_weight_mv


class ThreeFactorPlasticity:
    """Local eligibility on selected CSR slots, gated by a dopamine event.

    Pre spikes leave an exponentially decaying presynaptic trace. A later
    post spike adds that trace to eligibility on each selected incoming edge.
    Same-batch pre/post spikes do not form a pair. Eligibility then decays
    exponentially; dopamine applies Δw = eta * eligibility * D with clipping.
    Topology and unselected weights remain immutable in ``SparseGraph``.
    """

    def __init__(
        self,
        graph: SparseGraph,
        plastic_slots: Iterable[int],
        parameters: PlasticityParameters,
    ) -> None:
        slots = tuple(sorted(set(plastic_slots)))
        if any(type(slot) is not int or not 0 <= slot < graph.edge_count for slot in slots):
            raise ValueError("plastic_slots contains an invalid edge slot")
        self.graph = graph
        self.parameters = parameters
        self.plastic_slots = slots
        self._weights = {slot: graph.weights_mv[slot] for slot in slots}
        for weight in self._weights.values():
            if not parameters.w_min_mv <= weight <= parameters.w_max_mv:
                raise ValueError("initial plastic weight lies outside bounds")
        incoming: dict[int, list[int]] = {}
        for slot in slots:
            incoming.setdefault(graph.post_indices[slot], []).append(slot)
        self._incoming = {post: tuple(edges) for post, edges in incoming.items()}
        self._pre = {graph.pre_indices[slot]: (0.0, 0) for slot in slots}
        self._eligibility = {slot: (0.0, 0) for slot in slots}
        self._last_event_time_us = 0
        self._last_spike_batch_time_us: int | None = None

    @staticmethod
    def _decayed(state: tuple[float, int], time_us: int, tau_us: int) -> float:
        value, updated_us = state
        return value * math.exp(-(time_us - updated_us) / tau_us)

    def _check_time(self, time_us: int) -> None:
        require_time_us(time_us, "time_us")
        if time_us < self._last_event_time_us:
            raise ValueError("plasticity events must be chronological")

    def observe_spikes(self, time_us: int, neuron_indices: Iterable[int]) -> None:
        """Consume the full simultaneous spike batch once for this timestamp."""
        self._check_time(time_us)
        if time_us == self._last_spike_batch_time_us:
            raise ValueError("spikes at one timestamp must be supplied in one batch")
        neurons = tuple(neuron_indices)
        if any(type(i) is not int or not 0 <= i < self.graph.neuron_count for i in neurons):
            raise ValueError("spike batch contains an invalid neuron index")
        if len(set(neurons)) != len(neurons):
            raise ValueError("spike batch contains a duplicate neuron")
        # Form post-before-current-pre pairs, so simultaneous spikes do not pair.
        for post in neurons:
            for slot in self._incoming.get(post, ()):
                pre = self.graph.pre_indices[slot]
                pre_value = self._decayed(
                    self._pre[pre], time_us, self.parameters.tau_pre_us)
                if pre_value:
                    eligibility = self._decayed(
                        self._eligibility[slot], time_us,
                        self.parameters.tau_eligibility_us)
                    updated = eligibility + pre_value
                    if not math.isfinite(updated):
                        raise ArithmeticError("non-finite eligibility trace")
                    self._eligibility[slot] = (updated, time_us)
        for pre in neurons:
            if pre in self._pre:
                pre_value = self._decayed(
                    self._pre[pre], time_us, self.parameters.tau_pre_us)
                updated = pre_value + 1.0
                if not math.isfinite(updated):
                    raise ArithmeticError("non-finite presynaptic trace")
                self._pre[pre] = (updated, time_us)
        self._last_event_time_us = time_us
        self._last_spike_batch_time_us = time_us

    def eligibility_at(self, edge_slot: int, time_us: int) -> float:
        """Read a selected edge's decayed eligibility without advancing state."""
        self._check_time(time_us)
        if type(edge_slot) is not int or edge_slot not in self._eligibility:
            raise ValueError("edge slot is not plastic")
        return self._decayed(
            self._eligibility[edge_slot], time_us,
            self.parameters.tau_eligibility_us)

    def effective_weight(self, edge_slot: int) -> float:
        if type(edge_slot) is not int or not 0 <= edge_slot < self.graph.edge_count:
            raise ValueError("edge slot outside graph")
        return self._weights.get(edge_slot, self.graph.weights_mv[edge_slot])

    def apply_dopamine(self, time_us: int, dopamine: float) -> tuple[WeightChange, ...]:
        """Apply Δw = eta * e(t) * D to only the selected edge slots."""
        self._check_time(time_us)
        if not math.isfinite(dopamine):
            raise ValueError("dopamine must be finite")
        changes: list[WeightChange] = []
        if dopamine:
            for slot in self.plastic_slots:
                eligibility = self.eligibility_at(slot, time_us)
                if eligibility == 0.0:
                    continue
                previous = self._weights[slot]
                proposed = previous + self.parameters.eta * eligibility * dopamine
                if not math.isfinite(proposed):
                    raise ArithmeticError("non-finite plastic weight update")
                updated = min(self.parameters.w_max_mv,
                              max(self.parameters.w_min_mv, proposed))
                if updated != previous:
                    changes.append(WeightChange(
                        time_us, slot, previous, updated, eligibility, dopamine))
        for change in changes:
            self._weights[change.edge_slot] = change.new_weight_mv
        self._last_event_time_us = time_us
        return tuple(changes)
