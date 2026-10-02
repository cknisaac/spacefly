"""Autonomous, checkpointable DN background generator (dn-boundary-v1)."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
import random


STREAM_NAMES = ("common", "private_519624", "private_523769",
                "replacement_519624", "replacement_523769")
LEVELS = {"low": 0.5, "nominal": 1.0, "high": 1.5}
SEEDS = (31001, 31002, 31003)


@dataclass(frozen=True)
class BoundaryCheckpoint:
    time_us: int
    signs: tuple[int, ...]
    next_flip_us: tuple[int, ...]
    rng_states: tuple[tuple, ...]


class DNBoundary:
    """Reads only fixed contract, elapsed microseconds, and dedicated RNG state."""

    def __init__(self, *, seed: int, level: str, control: str = "shared"):
        if seed not in SEEDS or level not in LEVELS or control not in {"shared", "independent", "omitted"}:
            raise ValueError("Boundary seed/level/control outside locked contract")
        self.seed = seed
        self.level = level
        self.control = control
        self.time_us = 0
        self.rng: dict[str, random.Random] = {}
        self.signs: dict[str, int] = {}
        self.next_flip_us: dict[str, int] = {}
        for name in STREAM_NAMES:
            derived = hashlib.sha256(f"dn-boundary-v1|{seed}|{name}".encode()).digest()
            rng = random.Random(int.from_bytes(derived, "big"))
            self.rng[name] = rng
            self.signs[name] = 1 if rng.random() < 0.5 else -1
            self.next_flip_us[name] = self._interval_us(rng)

    @staticmethod
    def _interval_us(rng: random.Random) -> int:
        # Inverse-CDF exponential with a locked MT19937 random stream.
        # Half-even integer-microsecond rounding; force positive delay.
        u = rng.random()
        return max(1, round(-100_000 * math.log1p(-u)))

    @property
    def next_event_us(self) -> int:
        return min(self.next_flip_us.values())

    def advance_to(self, target_us: int) -> None:
        if type(target_us) is not int or target_us < self.time_us:
            raise ValueError("Boundary clock must advance monotonically in integer microseconds")
        while self.next_event_us <= target_us:
            when = self.next_event_us
            for name in STREAM_NAMES:
                if self.next_flip_us[name] == when:
                    self.signs[name] *= -1
                    self.next_flip_us[name] = when + self._interval_us(self.rng[name])
            self.time_us = when
        self.time_us = target_us

    def normalized(self) -> tuple[float, float]:
        if self.control == "omitted":
            return (0.0, 0.0)
        s = LEVELS[self.level]
        if self.control == "shared":
            c3 = c2 = self.signs["common"]
        else:
            c3, c2 = self.signs["replacement_519624"], self.signs["replacement_523769"]
        return (s * (1 + 0.2 * c3 + 0.2 * self.signs["private_519624"]),
                s * (1 + 0.2 * c2 + 0.2 * self.signs["private_523769"]))

    def currents_pa(self, reference_519624_pa: float, reference_523769_pa: float) -> tuple[float, float]:
        if not all(type(x) in (int, float) and math.isfinite(x) and x > 0
                   for x in (reference_519624_pa, reference_523769_pa)):
            raise ValueError("DN references must be finite and positive")
        n3, n2 = self.normalized()
        return n3 * reference_519624_pa, n2 * reference_523769_pa

    def checkpoint(self) -> BoundaryCheckpoint:
        return BoundaryCheckpoint(self.time_us, tuple(self.signs[n] for n in STREAM_NAMES),
                                  tuple(self.next_flip_us[n] for n in STREAM_NAMES),
                                  tuple(self.rng[n].getstate() for n in STREAM_NAMES))

    def restore(self, state: BoundaryCheckpoint) -> None:
        if not isinstance(state, BoundaryCheckpoint) or state.time_us < 0:
            raise ValueError("Invalid boundary checkpoint")
        if len(state.signs) != len(STREAM_NAMES) or set(state.signs) - {-1, 1}:
            raise ValueError("Invalid boundary signs")
        if len(state.next_flip_us) != len(STREAM_NAMES) or any(t <= state.time_us for t in state.next_flip_us):
            raise ValueError("Invalid future flip schedule")
        if len(state.rng_states) != len(STREAM_NAMES):
            raise ValueError("Invalid RNG checkpoint")
        for name, sign, when, rng_state in zip(STREAM_NAMES, state.signs, state.next_flip_us, state.rng_states):
            self.rng[name].setstate(rng_state)
            self.signs[name] = sign
            self.next_flip_us[name] = when
        self.time_us = state.time_us
