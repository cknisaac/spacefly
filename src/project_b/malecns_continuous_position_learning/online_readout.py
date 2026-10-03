"""Causal, frame-by-frame MBON position-bin readout for the moving-note MVP."""

from __future__ import annotations

import math
from dataclasses import dataclass

from project_b.osu.types import KeyAction, KeyActionKind, require_time_us


@dataclass(frozen=True, slots=True)
class PositionBinDecision:
    position: float
    sample_count: int
    max_voltage_mv: float | None
    action: bool | None
    decision_time_us: int | None


class OnlinePositionReadout:
    """Turn one causal MBON sample stream into at most one key-down.

    ``step`` receives the current rendered position and the MBON voltage
    sampled at this tick. The voltage belongs to the previously observed
    position because the neural simulator integrates the prior tick's drive.
    A bin is evaluated only once the current observation shows that the note
    has left that bin. No later voltage samples are inspected.
    """

    def __init__(self, *, position_grid: list[float], bin_width: float,
                 threshold_mv: float, dt_us: int = 1_000,
                 lane: int = 0, key_hold_us: int = 10_000,
                 direction: int = -1) -> None:
        if (not position_grid or any(type(p) not in (int, float)
                                     or not math.isfinite(p)
                                     or not 0.0 <= p <= 1.0
                                     for p in position_grid)):
            raise ValueError("position_grid must contain finite positions in [0, 1]")
        if len(set(position_grid)) != len(position_grid):
            raise ValueError("position_grid values must be unique")
        if not math.isfinite(bin_width) or bin_width <= 0:
            raise ValueError("bin_width must be finite and positive")
        if not math.isfinite(threshold_mv):
            raise ValueError("threshold_mv must be finite")
        if type(dt_us) is not int or dt_us <= 0:
            raise ValueError("dt_us must be a positive integer")
        if type(lane) is not int or not 0 <= lane < 4:
            raise ValueError("lane must be in 0..3")
        if type(key_hold_us) is not int or key_hold_us <= 0 or key_hold_us % dt_us:
            raise ValueError("key_hold_us must be a positive multiple of dt_us")
        if type(direction) is not int or direction not in (-1, 1):
            raise ValueError("direction must be -1 (decreasing) or 1 (increasing)")

        self.position_grid = tuple(float(p) for p in position_grid)
        self.bin_width = float(bin_width)
        self.threshold_mv = float(threshold_mv)
        self.dt_us = dt_us
        self.lane = lane
        self.key_hold_us = key_hold_us
        self.direction = direction
        self.first_valid_time_us: int | None = None
        self.first_action_time_us: int | None = None
        self._last_time_us: int | None = None
        self._last_position: float | None = None
        self._key_down = False
        self._release_time_us: int | None = None
        self._max_voltage: dict[float, float] = {}
        self._sample_count: dict[float, int] = {}
        self._decisions: dict[float, PositionBinDecision] = {}

    def begin(self, time_us: int, position: float) -> None:
        """Start a fresh note from its current visible position."""
        if self._last_time_us is not None:
            raise RuntimeError("readout has already begun")
        require_time_us(time_us, "time_us")
        self._validate_position(position)
        self._last_time_us = time_us
        self._last_position = float(position)

    def step(self, time_us: int, position: float | None,
             mbon_voltage_mv: float) -> tuple[KeyAction, ...]:
        """Consume one current observation and the voltage from the last tick."""
        if self._last_time_us is None:
            raise RuntimeError("begin() must be called before step()")
        require_time_us(time_us, "time_us")
        if time_us != self._last_time_us + self.dt_us:
            raise ValueError("observations must arrive once per configured integration tick")
        if position is not None:
            self._validate_position(position)
            position = float(position)
        if type(mbon_voltage_mv) not in (int, float) or not math.isfinite(mbon_voltage_mv):
            raise ValueError("mbon_voltage_mv must be finite")

        emitted: list[KeyAction] = []
        if self._key_down and self._release_time_us is not None \
                and time_us >= self._release_time_us:
            emitted.append(KeyAction(self._release_time_us, self.lane, KeyActionKind.UP))
            self._key_down = False
            self._release_time_us = None

        if self.first_valid_time_us is None and mbon_voltage_mv > 0.0:
            self.first_valid_time_us = time_us

        sample_position = self._last_position
        if self.first_valid_time_us is not None and sample_position is not None:
            for center in self.position_grid:
                if self._contains(center, sample_position):
                    self._sample_count[center] = self._sample_count.get(center, 0) + 1
                    self._max_voltage[center] = max(
                        self._max_voltage.get(center, -math.inf),
                        float(mbon_voltage_mv))

        left_bins = [center for center in self._ordered_grid()
                     if center not in self._decisions
                     and sample_position is not None
                     and self._contains(center, sample_position)
                     and (position is None or not self._contains(center, position))]
        emitted.extend(self._close_bins(left_bins, time_us))
        self._last_position = position
        self._last_time_us = time_us
        return tuple(emitted)

    def finish(self, time_us: int) -> tuple[KeyAction, ...]:
        """Close remaining bins and return any already scheduled key release."""
        if self._last_time_us is None:
            raise RuntimeError("begin() must be called before finish()")
        require_time_us(time_us, "time_us")
        if time_us < self._last_time_us:
            raise ValueError("finish time cannot precede the latest observation")
        emitted = list(self._close_bins(
            [center for center in self._ordered_grid()
             if center not in self._decisions], time_us))
        if self._key_down and self._release_time_us is not None:
            emitted.append(KeyAction(self._release_time_us, self.lane, KeyActionKind.UP))
            self._key_down = False
            self._release_time_us = None
        self._last_time_us = time_us
        self._last_position = None
        return tuple(emitted)

    @property
    def decisions(self) -> tuple[PositionBinDecision, ...]:
        return tuple(self._decisions[center] for center in self._ordered_grid()
                     if center in self._decisions)

    def _close_bins(self, centers: list[float], time_us: int) -> list[KeyAction]:
        emitted: list[KeyAction] = []
        for center in centers:
            count = self._sample_count.get(center, 0)
            maximum = self._max_voltage.get(center)
            action = None if count == 0 else maximum <= self.threshold_mv
            self._decisions[center] = PositionBinDecision(
                center, count, maximum, action, time_us if count else None)
            if (action is True and self.first_action_time_us is None
                    and not self._key_down):
                self.first_action_time_us = time_us
                self._key_down = True
                self._release_time_us = time_us + self.key_hold_us
                emitted.append(KeyAction(time_us, self.lane, KeyActionKind.DOWN))
        return emitted

    def _contains(self, center: float, position: float) -> bool:
        return abs(position - center) <= self.bin_width / 2.0 + 1e-12

    def _ordered_grid(self) -> list[float]:
        return sorted(self.position_grid, reverse=self.direction < 0)

    @staticmethod
    def _validate_position(position: float) -> None:
        if (type(position) not in (int, float) or not math.isfinite(position)
                or not 0.0 <= position <= 1.0):
            raise ValueError("visible position must be finite and in [0, 1]")
