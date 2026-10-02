"""Causal spike-window readout with fixed threshold and key state."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Iterable

from project_b.osu.types import KeyAction, KeyActionKind, require_lane
from project_b.utils.time import require_time_us


@dataclass(frozen=True, slots=True)
class MotorDecision:
    time_us: int
    spike_count_in_window: int
    threshold: int
    action: KeyAction


class FixedMotorReadout:
    """Lane-one key transitions from recent motor-population spikes.

    One cell's accidental spike cannot cross the population threshold.
    Mapping, thresholds, hold and cooldown are fixed, not trainable.
    """

    def __init__(self, neuron_indices: Iterable[int], *, lane: int = 0,
                 window_us: int = 20_000, on_threshold: int = 6,
                 off_threshold: int = 2, min_hold_us: int = 10_000,
                 max_hold_us: int = 30_000, cooldown_us: int = 200_000) -> None:
        indices = tuple(sorted(set(neuron_indices)))
        if not indices or any(type(i) is not int or i < 0 for i in indices):
            raise ValueError("neuron_indices must be nonempty nonnegative integers")
        require_lane(lane)
        for name, value in (("window_us", window_us), ("min_hold_us", min_hold_us),
                            ("max_hold_us", max_hold_us), ("cooldown_us", cooldown_us)):
            if require_time_us(value, name) <= 0:
                raise ValueError(f"{name} must be positive")
        if type(on_threshold) is not int or on_threshold <= 1:
            raise ValueError("on_threshold must exceed one spike")
        if type(off_threshold) is not int or not 0 <= off_threshold < on_threshold:
            raise ValueError("off_threshold must be below on_threshold")
        if min_hold_us > max_hold_us:
            raise ValueError("min_hold_us must not exceed max_hold_us")
        self.neuron_indices = indices
        self._index_set = set(indices)
        self.lane = lane
        self.window_us = window_us
        self.on_threshold = on_threshold
        self.off_threshold = off_threshold
        self.min_hold_us = min_hold_us
        self.max_hold_us = max_hold_us
        self.cooldown_us = cooldown_us
        self.key_down = False
        self._last_down_us: int | None = None
        self._last_time_us: int | None = None
        self._spike_times: deque[int] = deque()

    def observe(self, time_us: int, spiking_indices: Iterable[int]) -> MotorDecision | None:
        require_time_us(time_us)
        if self._last_time_us is not None and time_us <= self._last_time_us:
            raise ValueError("motor readout requires strictly increasing ticks")
        indices = tuple(spiking_indices)
        if any(type(i) is not int or i < 0 for i in indices):
            raise ValueError("spiking_indices contains an invalid index")
        if len(set(indices)) != len(indices):
            raise ValueError("a neuron can spike only once in a tick batch")
        self._last_time_us = time_us
        self._spike_times.extend(time_us for i in indices if i in self._index_set)
        while self._spike_times and self._spike_times[0] <= time_us - self.window_us:
            self._spike_times.popleft()
        count = len(self._spike_times)
        if self.key_down:
            assert self._last_down_us is not None
            elapsed_us = time_us - self._last_down_us
            if (elapsed_us >= self.max_hold_us
                    or (elapsed_us >= self.min_hold_us
                        and count <= self.off_threshold)):
                self.key_down = False
                return MotorDecision(time_us, count, self.on_threshold,
                                     KeyAction(time_us, self.lane, KeyActionKind.UP))
            return None
        if (count >= self.on_threshold
                and (self._last_down_us is None
                     or time_us - self._last_down_us >= self.cooldown_us)):
            self.key_down = True
            self._last_down_us = time_us
            return MotorDecision(time_us, count, self.on_threshold,
                                     KeyAction(time_us, self.lane, KeyActionKind.DOWN))
        return None

    def state(self) -> dict:
        return {"identity": [list(self.neuron_indices), self.lane, self.window_us,
                             self.on_threshold, self.off_threshold, self.min_hold_us,
                             self.max_hold_us, self.cooldown_us],
                "key_down": self.key_down,
                "last_down_us": self._last_down_us,
                "last_time_us": self._last_time_us,
                "spike_times": list(self._spike_times)}

    def restore(self, state: dict) -> None:
        if set(state) != set(self.state()) or state["identity"] != self.state()["identity"]:
            raise ValueError("motor checkpoint identity differs")
        down, last_down, last_time = (state["key_down"], state["last_down_us"],
                                      state["last_time_us"])
        times = state["spike_times"]
        if (type(down) is not bool or
                (last_time is not None and (type(last_time) is not int or last_time < 0))
                or (last_down is not None and (type(last_down) is not int or last_down < 0
                    or last_time is None or last_down > last_time))
                or (down and last_down is None)
                or not isinstance(times, list)
                or any(type(t) is not int or t < 0 or last_time is None
                       or not last_time - self.window_us < t <= last_time
                       for t in times)
                or times != sorted(times)):
            raise ValueError("invalid motor continuation state")
        self.key_down = down
        self._last_down_us = last_down
        self._last_time_us = last_time
        self._spike_times = deque(times)
