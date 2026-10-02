"""Overlapping artificial time-to-contact population for one visible lane."""

from __future__ import annotations

import math
from dataclasses import dataclass

from project_b.utils.time import require_time_us


@dataclass(frozen=True, slots=True)
class TimeToContactEncoder:
    """Encode a visible note as smooth drive, never as a press instruction.

    The caller supplies only the next unresolved lane-one note timestamp.
    Four neurons per preferred time have slightly offset tuning centers.
    """

    preferred_us: tuple[int, ...] = (
        500_000, 400_000, 300_000, 200_000, 150_000,
        100_000, 75_000, 50_000, 25_000, 0,
    )
    replicas: int = 4
    width_us: int = 55_000
    drive_peak_mv: float = 2.5
    visible_before_us: int = 500_000
    visible_after_us: int = 100_000

    def __post_init__(self) -> None:
        if not self.preferred_us or any(require_time_us(x, "preferred_us") < 0
                                        for x in self.preferred_us):
            raise ValueError("preferred_us must contain nonnegative times")
        if type(self.replicas) is not int or self.replicas <= 0:
            raise ValueError("replicas must be positive")
        for name in ("width_us", "visible_before_us", "visible_after_us"):
            if require_time_us(getattr(self, name), name) <= 0:
                raise ValueError(f"{name} must be positive")
        if not math.isfinite(self.drive_peak_mv) or self.drive_peak_mv <= 0:
            raise ValueError("drive_peak_mv must be finite and positive")

    @property
    def neuron_count(self) -> int:
        return len(self.preferred_us) * self.replicas

    def encode(self, time_us: int, note_time_us: int | None) -> tuple[float, ...]:
        """Return mV-equivalent drives for the sensory cells at this tick."""
        require_time_us(time_us)
        if note_time_us is None:
            return (0.0,) * self.neuron_count
        require_time_us(note_time_us, "note_time_us")
        ttc_us = note_time_us - time_us
        if not -self.visible_after_us <= ttc_us <= self.visible_before_us:
            return (0.0,) * self.neuron_count
        offsets = tuple((replica - (self.replicas - 1) / 2) * 10_000
                        for replica in range(self.replicas))
        return tuple(
            self.drive_peak_mv * math.exp(
                -0.5 * ((ttc_us - (preferred + offset)) / self.width_us) ** 2)
            for preferred in self.preferred_us for offset in offsets)
