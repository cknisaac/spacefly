"""Exact subthreshold update for a current-based LIF model."""

from __future__ import annotations

import math
from dataclasses import dataclass

from project_b.utils.time import require_time_us


@dataclass(frozen=True, slots=True)
class LIFParameters:
    """Parameters in mV-equivalent drive and integer microseconds.

    The drive terms are voltage-equivalent model inputs, not measured fly
    conductances or currents. Each neuron may have its own parameter set.
    """

    v_rest_mv: float = 0.0
    v_reset_mv: float = 0.0
    v_threshold_mv: float = 1.0
    tau_m_us: int = 10_000
    tau_syn_us: int = 5_000
    refractory_us: int = 2_000

    def __post_init__(self) -> None:
        if not all(math.isfinite(v) for v in
                   (self.v_rest_mv, self.v_reset_mv, self.v_threshold_mv)):
            raise ValueError("LIF voltages must be finite")
        if self.v_threshold_mv <= max(self.v_rest_mv, self.v_reset_mv):
            raise ValueError("threshold must exceed resting and reset voltages")
        for name in ("tau_m_us", "tau_syn_us", "refractory_us"):
            value = require_time_us(getattr(self, name), name)
            if value < 0 or (name != "refractory_us" and value == 0):
                raise ValueError(f"{name} must be positive, except refractory_us may be zero")


def advance_lif(voltage_mv: float, synaptic_drive_mv: float,
                external_drive_mv: float, elapsed_us: int,
                parameters: LIFParameters) -> tuple[float, float]:
    """Integrate τm dV/dt=−(V−Vrest)+Iext+Isyn and τs dIsyn/dt=−Isyn.

    Inputs are constant except for exponentially decaying synaptic drive
    during this interval. Threshold and reset are handled by the simulator
    at integration ticks, not by this subthreshold function.
    """
    require_time_us(elapsed_us, "elapsed_us")
    if elapsed_us < 0:
        raise ValueError("elapsed_us must be nonnegative")
    if not all(math.isfinite(v) for v in
               (voltage_mv, synaptic_drive_mv, external_drive_mv)):
        raise ValueError("voltage and drives must be finite")
    if elapsed_us == 0:
        return voltage_mv, synaptic_drive_mv
    tau_m = parameters.tau_m_us
    tau_s = parameters.tau_syn_us
    membrane_decay = math.exp(-elapsed_us / tau_m)
    synaptic_decay = math.exp(-elapsed_us / tau_s)
    if tau_s == tau_m:
        synaptic_contribution = (synaptic_drive_mv * elapsed_us / tau_m
                                 * membrane_decay)
    else:
        exponent_difference = elapsed_us * (1 / tau_m - 1 / tau_s)
        synaptic_contribution = (synaptic_drive_mv * tau_s / (tau_s - tau_m)
                                 * membrane_decay * math.expm1(exponent_difference))
    voltage_after_mv = (parameters.v_rest_mv
                        + (voltage_mv - parameters.v_rest_mv) * membrane_decay
                        - external_drive_mv * math.expm1(-elapsed_us / tau_m)
                        + synaptic_contribution)
    synaptic_after_mv = synaptic_drive_mv * synaptic_decay
    if not math.isfinite(voltage_after_mv) or not math.isfinite(synaptic_after_mv):
        raise ArithmeticError("non-finite LIF state")
    return voltage_after_mv, synaptic_after_mv
