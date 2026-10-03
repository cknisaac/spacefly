"""Causal current-position-only visual time-to-contact encoder.

ENGINEERING ASSUMPTIONS are isolated in constructor arguments and output gating.
"""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass
import math


@dataclass(frozen=True, slots=True)
class TimeToContactSample:
    screen_position: float
    velocity_per_us: float
    remaining_us: float
    countdown: float
    cue_active: bool


class ScreenTimeToContactEncoder:
    """Estimate contact from current and recent past rendered positions."""

    def __init__(self, *, dt_us: int = 1_000, velocity_window_us: int = 50_000,
                 target_lead_us: int = 500_000) -> None:
        if type(dt_us) is not int or dt_us <= 0:
            raise ValueError('dt_us must be a positive integer')
        if (type(velocity_window_us) is not int or velocity_window_us <= 0
                or velocity_window_us % dt_us):
            raise ValueError('velocity window must be a positive multiple of dt_us')
        if type(target_lead_us) is not int or target_lead_us <= 0:
            raise ValueError('target lead must be a positive integer')
        self.dt_us = dt_us
        self.velocity_window_us = velocity_window_us
        self.target_lead_us = target_lead_us
        self._history: deque[tuple[int, float]] = deque(maxlen=velocity_window_us // dt_us + 1)
        self._last_time_us: int | None = None

    def reset(self) -> None:
        self._history.clear()
        self._last_time_us = None

    def observe(self, time_us: int, screen_position: float | None) -> TimeToContactSample | None:
        if type(time_us) is not int or time_us < 0:
            raise ValueError('time_us must be a nonnegative integer')
        if screen_position is None:
            self.reset()
            return None
        if (type(screen_position) not in (int, float)
                or not math.isfinite(screen_position)
                or not 0.0 <= screen_position <= 1.0):
            raise ValueError('screen_position must be finite and in [0, 1]')
        if self._last_time_us is not None and time_us != self._last_time_us + self.dt_us:
            raise ValueError('samples must arrive at exactly dt_us intervals')
        self._last_time_us = time_us
        self._history.append((time_us, float(screen_position)))
        if len(self._history) < self._history.maxlen:
            return None
        old_time, old_position = self._history[0]
        span = time_us - old_time
        if span != self.velocity_window_us:
            return None
        displacement = float(screen_position) - old_position
        # ENGINEERING ASSUMPTION: no positive motion over the recent window means
        # there is no reliable visual approach cue, so sensory output is blank.
        if displacement <= 0.0:
            return None
        velocity_per_us = displacement / span
        remaining_us = max(0.0, (1.0 - float(screen_position)) / velocity_per_us)
        countdown = min(1.0, max(0.0, remaining_us / self.target_lead_us))
        # ENGINEERING ASSUMPTION: match EA13's trained cue onset. Return a
        # sample for logging, but the caller keeps sensory input blank until the
        # estimated contact enters the existing target_lead_us horizon.
        return TimeToContactSample(float(screen_position), velocity_per_us,
                                  remaining_us, countdown,
                                  remaining_us <= self.target_lead_us)
