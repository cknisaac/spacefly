"""Fixed, deterministic Gaussian KC population code for current position."""

from __future__ import annotations

import math


def activation(position: float, preferred_position: float, sigma: float) -> float:
    """Return a unit-peak Gaussian tuning value in [0, 1]."""
    if not (math.isfinite(position) and 0.0 <= position <= 1.0):
        raise ValueError("position must be finite and within [0, 1]")
    if not (math.isfinite(preferred_position) and 0.0 <= preferred_position <= 1.0):
        raise ValueError("preferred_position must be finite and within [0, 1]")
    if not math.isfinite(sigma) or sigma <= 0:
        raise ValueError("sigma must be finite and positive")
    return math.exp(-0.5 * ((position - preferred_position) / sigma) ** 2)


def population_drive(position: float, cells: list[dict], *, sigma: float,
                     peak_drive_mv: float) -> tuple[float, ...]:
    """Encode current position only as fixed per-KC external drive."""
    if not math.isfinite(peak_drive_mv) or peak_drive_mv <= 0:
        raise ValueError("peak_drive_mv must be finite and positive")
    return tuple(peak_drive_mv * activation(
        position, cell["preferred_position"], sigma) for cell in cells)
