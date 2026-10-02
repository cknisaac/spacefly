"""B5-only square-current and functional-disconnection probe overlay.

The frozen Electrical Model V1 config, source graph, boundary generator and
ordinary NeutralCircuit code are not changed. This subclass adds only a
declared external current to selected cells and removes named functional
outgoing events for causal controls.
"""

from __future__ import annotations

import copy
import math

import numpy as np

from .runtime import NeutralCircuit
from .source import ADDED_VISUAL_IDS


VISUAL_IDS = (13285, 13707, 13874)
MBON32_ID = 519131
DN_IDS = (519624, 523769)
LESIONS = {"none", "visual_to_KC", "aMe12_to_KC", "KC_to_MBON32", "MBON32_to_DNs"}


class SensoryRouteProbe(NeutralCircuit):
    """Neutral V1 plus task-free, rectangular current injection.

    The analytical passive-current increment is additive because the frozen
    subthreshold equation is linear. Injection is ignored during refractory
    periods. Every target and every lesion is explicit; no source row changes.
    """

    def __init__(self, circuit, *, seed: int):
        super().__init__(circuit, condition="A", level="nominal", seed=seed)
        self.injected_pa = np.zeros(len(self.v_mv), dtype=float)
        self.functional_disconnection = "none"
        self.removed_source_rows: tuple[int, ...] = ()
        self.delivered_event_log: list[tuple] = []

    def set_current(self, source_ids: tuple[int, ...], amplitude_pa: float) -> None:
        if not math.isfinite(amplitude_pa) or amplitude_pa < 0:
            raise ValueError("B5 current must be finite and nonnegative")
        allowed = {c.source_id for c in self.circuit.cells if c.kind == "sensory"} | {MBON32_ID} | {
            c.source_id for c in self.circuit.cells if c.kind == "KC"}
        if not source_ids or len(set(source_ids)) != len(source_ids) or not set(source_ids) <= allowed:
            raise ValueError("B5 injection target outside selected visual/KC/MBON32 cells")
        self.injected_pa[:] = 0
        for source_id in source_ids:
            self.injected_pa[self.dynamic_of_source[source_id]] = amplitude_pa

    def clear_current(self) -> None:
        self.injected_pa[:] = 0

    def reference_pa(self, source_id: int) -> float:
        i = self.dynamic_of_source[source_id]
        return float(self.leak_ns[i] * (self.onset_mv[i] - self.rest_mv[i]))

    def apply_disconnection(self, name: str) -> tuple[int, ...]:
        if name not in LESIONS or self.functional_disconnection != "none":
            raise ValueError("Only one named B5 disconnection is permitted")
        if name == "none":
            return ()

        def cut(pre_id: int, post_id: int) -> bool:
            if name == "visual_to_KC":
                return pre_id in VISUAL_IDS and self.circuit.cells[self.circuit.index(post_id)].kind == "KC"
            if name == "aMe12_to_KC":
                return pre_id in ADDED_VISUAL_IDS and self.circuit.cells[self.circuit.index(post_id)].kind == "KC"
            if name == "KC_to_MBON32":
                return post_id == MBON32_ID and self.circuit.cells[self.circuit.index(pre_id)].kind == "KC"
            return pre_id == MBON32_ID and post_id in DN_IDS

        removed = []
        for pre, edges in enumerate(self.outgoing):
            pre_id = self.source_ids[pre]
            kept = []
            for post, amplitude, source_row, kind in edges:
                if kind == "FAST" and cut(pre_id, self.source_ids[post]):
                    removed.append(source_row)
                else:
                    kept.append((post, amplitude, source_row, kind))
            self.outgoing[pre] = kept
        expected = {"visual_to_KC": 76, "aMe12_to_KC": 48,
                    "KC_to_MBON32": 105, "MBON32_to_DNs": 2}[name]
        if len(removed) != expected:
            raise ValueError(f"B5 lesion source-row count drifted: {name}")
        self.functional_disconnection = name
        self.removed_source_rows = tuple(sorted(removed))
        return self.removed_source_rows

    def _integrate(self, dt_us: int) -> None:
        if dt_us <= 0 or not np.any(self.injected_pa):
            super()._integrate(dt_us)
            return
        # This is the exact solution of the frozen passive subthreshold model
        # for constant injected current over the current event segment.
        free = self.current_time_us >= self.refractory_until_us
        super()._integrate(dt_us)
        decay = np.exp(-(dt_us/1000.0) * self.leak_ns/self.cap_pf)
        self.v_mv[free] += (self.injected_pa[free]/self.leak_ns[free]) * (1-decay[free])
        if not np.all(np.isfinite(self.v_mv)):
            raise ArithmeticError("Nonfinite B5 injected membrane state")

    def _deliver_due(self, time_us: int) -> None:
        due = sorted(e for e in self.queue if e[0] == time_us)
        super()._deliver_due(time_us)
        for at, post, pre, source_row, _, kind, amplitude in due:
            self.delivered_event_log.append((at, self.source_ids[pre],
                                             self.source_ids[post], source_row, kind, amplitude))

    def checkpoint(self) -> dict:
        state = super().checkpoint()
        state["b5_injected_pa"] = self.injected_pa.tolist()
        state["b5_functional_disconnection"] = self.functional_disconnection
        state["b5_removed_source_rows"] = self.removed_source_rows
        state["b5_delivered_event_log"] = self.delivered_event_log
        return state

    def restore(self, state: dict) -> None:
        if state.get("b5_functional_disconnection") != "none" or any(state.get("b5_injected_pa", [])):
            raise ValueError("B5 trials must fork from an unperturbed neutral checkpoint")
        super().restore(state)
        self.injected_pa = np.asarray(state["b5_injected_pa"], dtype=float).copy()
        self.functional_disconnection = "none"
        self.removed_source_rows = ()
        self.delivered_event_log = copy.deepcopy(state["b5_delivered_event_log"])
