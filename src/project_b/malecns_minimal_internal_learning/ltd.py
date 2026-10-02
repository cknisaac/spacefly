"""Small artificial teacher-gated local LTD rule for one selected KC→MBON edge per KC."""

from __future__ import annotations

import math


class LocalLTD:
    """Exponentially decaying KC eligibility followed by teacher-only depression.

    This is an engineering assumption. It has no dopamine state, LTP, recovery,
    optimizer, postsynaptic requirement, or update outside the selected edges.
    """

    def __init__(self, weights: list[float], *, original_weights: list[float] | tuple[float, ...] | None = None,
                 tau_us: int = 1_000_000,
                 eta: float = 0.03, minimum_fraction: float = 0.2,
                 plastic_slots: tuple[int, ...] | None = None) -> None:
        if not weights or tau_us <= 0 or eta <= 0 or not 0 < minimum_fraction < 1:
            raise ValueError("invalid LTD parameters")
        current = tuple(float(weight) for weight in weights)
        baseline = tuple(float(weight) for weight in
                         (weights if original_weights is None else original_weights))
        if len(current) != len(baseline):
            raise ValueError("current and original weight vectors must have equal length")
        if any(not math.isfinite(weight) or weight <= 0 for weight in baseline):
            raise ValueError("initial weights must be finite and positive")
        if any(not math.isfinite(weight) or weight <= 0 for weight in current):
            raise ValueError("current weights must be finite and positive")
        self.original_weights = baseline
        # Backwards-compatible name: historical reports use `initial` for the
        # immutable run-start weights, which now remain stable across presentations.
        self.initial = self.original_weights
        self.weights = list(current)
        self.tau_us = tau_us
        self.eta = eta
        self.minimum_fraction = minimum_fraction
        self.plastic_slots = (tuple(range(len(weights))) if plastic_slots is None
                              else tuple(sorted(set(plastic_slots))))
        if any(type(slot) is not int or not 0 <= slot < len(weights)
               for slot in self.plastic_slots):
            raise ValueError("plastic slot outside weight vector")
        floor = self.minimum_fraction
        if any(current[i] < baseline[i] * floor for i in range(len(current))):
            raise ValueError("current weight is below its original-weight floor")
        self._eligibility = [0.0] * len(weights)
        self._updated_us = [0] * len(weights)
        self._last_time_us = 0

    def observe_kc_spike(self, edge_index: int, time_us: int) -> None:
        self._check(edge_index, time_us)
        if edge_index not in self.plastic_slots:
            self._last_time_us = time_us
            return
        trace = self._eligibility[edge_index] * math.exp(
            -(time_us - self._updated_us[edge_index]) / self.tau_us)
        self._eligibility[edge_index] = trace + 1.0
        self._updated_us[edge_index] = time_us
        self._last_time_us = time_us

    def eligibility_at(self, edge_index: int, time_us: int) -> float:
        self._check(edge_index, time_us)
        if edge_index not in self.plastic_slots:
            return 0.0
        return self._eligibility[edge_index] * math.exp(
            -(time_us - self._updated_us[edge_index]) / self.tau_us)

    def teacher_pulse(self, time_us: int, *, teacher: bool) -> tuple[dict, ...]:
        if type(time_us) is not int or time_us < self._last_time_us:
            raise ValueError("times must be chronological integer microseconds")
        changes = []
        if teacher:
            for slot in self.plastic_slots:
                old = self.weights[slot]
                eligibility = self.eligibility_at(slot, time_us)
                low = self.original_weights[slot] * self.minimum_fraction
                new = max(low, old - self.eta * eligibility)
                if new < old:
                    changes.append({"edge_index": slot, "previous_weight_mv": old,
                                    "new_weight_mv": new, "eligibility": eligibility,
                                    "teacher": 1})
                    self.weights[slot] = new
        self._last_time_us = time_us
        return tuple(changes)

    def _check(self, edge_index: int, time_us: int) -> None:
        if type(edge_index) is not int or not 0 <= edge_index < len(self.weights):
            raise ValueError("edge index outside selected plastic mask")
        if type(time_us) is not int or time_us < self._last_time_us:
            raise ValueError("times must be chronological integer microseconds")
