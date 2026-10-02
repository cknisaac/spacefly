"""Read-only peak instrumentation for the locked B5.4 sensory-entry probe."""

from __future__ import annotations

import numpy as np

from .sensory_route_probe import SensoryRouteProbe


class VisualBoundaryProbe(SensoryRouteProbe):
    """Record pre-reset voltage and delivered-current peaks without changing dynamics."""

    def __init__(self, circuit, *, seed: int):
        super().__init__(circuit, seed=seed)
        self._reset_peaks()

    def _reset_peaks(self) -> None:
        self.peak_voltage_mv = self.v_mv.copy()
        self.peak_synaptic_pa = self.syn_pa.copy()
        self.peak_apl_local = self.apl_local.copy()

    def restore(self, state: dict) -> None:
        super().restore(state)
        self._reset_peaks()

    def _integrate(self, dt_us: int) -> None:
        super()._integrate(dt_us)
        np.maximum(self.peak_voltage_mv, self.v_mv, out=self.peak_voltage_mv)
        np.maximum(self.peak_synaptic_pa, self.syn_pa, out=self.peak_synaptic_pa)
        np.maximum(self.peak_apl_local, self.apl_local, out=self.peak_apl_local)

    def _deliver_due(self, time_us: int) -> None:
        super()._deliver_due(time_us)
        np.maximum(self.peak_synaptic_pa, self.syn_pa, out=self.peak_synaptic_pa)
        np.maximum(self.peak_apl_local, self.apl_local, out=self.peak_apl_local)
