"""Independent seeded autonomous boundary currents for the three output cells."""

from __future__ import annotations

import hashlib
import math
import random


TARGETS = (10495, 11145, 10713)
MEANS = {10495: 0.5, 11145: 2.0, 10713: 2.0}
LEVELS = {"low": 0.5, "nominal": 1.0, "high": 1.5}


def _tuple_tree(value):
    return tuple(_tuple_tree(x) for x in value) if isinstance(value, list) else value


class AutonomousBoundary:
    def __init__(self, master_seed: int, level: str = "nominal"):
        if type(master_seed) is not int or master_seed < 0 or level not in LEVELS:
            raise ValueError("invalid boundary identity")
        self.master_seed, self.level = master_seed, level
        self.streams = {}
        self.signs = {}
        self.next_flip_us = {}
        self.time_us = 0
        for source in TARGETS:
            digest = hashlib.sha256(
                f"mvp-c1-boundary-v1|{master_seed}|{source}".encode()).digest()
            rng = random.Random(int.from_bytes(digest, "big"))
            self.streams[source] = rng
            self.signs[source] = 1 if rng.random() < 0.5 else -1
            self.next_flip_us[source] = self._wait(rng)

    @staticmethod
    def _wait(rng: random.Random) -> int:
        return max(1, round(-100_000 * math.log1p(-rng.random())))

    def current(self, source: int) -> float:
        return LEVELS[self.level] * MEANS[source] * (1 + 0.2 * self.signs[source])

    def next_time(self) -> int:
        return min(self.next_flip_us.values())

    def advance_to(self, time_us: int) -> list[tuple[int, int, int]]:
        if type(time_us) is not int or time_us < self.time_us:
            raise ValueError("boundary clock reversal")
        flips = []
        while self.next_time() <= time_us:
            at = self.next_time()
            for source in sorted(TARGETS):
                if self.next_flip_us[source] == at:
                    self.signs[source] = -self.signs[source]
                    self.next_flip_us[source] = at + self._wait(self.streams[source])
                    flips.append((at, source, self.signs[source]))
        self.time_us = time_us
        return flips

    def state(self) -> dict:
        return {"identity": [self.master_seed, self.level], "time_us": self.time_us,
                "signs": {str(k): v for k, v in self.signs.items()},
                "next_flip_us": {str(k): v for k, v in self.next_flip_us.items()},
                "rng_states": {str(k): list(self.streams[k].getstate()) for k in TARGETS}}

    def restore(self, state: dict) -> None:
        if set(state) != set(self.state()) or state["identity"] != [self.master_seed, self.level]:
            raise ValueError("boundary identity differs")
        clone = AutonomousBoundary(self.master_seed, self.level)
        t = state["time_us"]
        if (type(t) is not int or t < 0 or
                set(state["signs"]) != {str(k) for k in TARGETS} or
                set(state["next_flip_us"]) != {str(k) for k in TARGETS} or
                set(state["rng_states"]) != {str(k) for k in TARGETS}):
            raise ValueError("invalid boundary state")
        for source in TARGETS:
            key = str(source)
            if (type(state["signs"][key]) is not int or
                    state["signs"][key] not in (-1, 1) or
                    type(state["next_flip_us"][key]) is not int or
                    state["next_flip_us"][key] <= t):
                raise ValueError("invalid boundary flip")
            clone.streams[source].setstate(_tuple_tree(state["rng_states"][key]))
            clone.signs[source] = state["signs"][key]
            clone.next_flip_us[source] = state["next_flip_us"][key]
        clone.time_us = t
        self.__dict__.update(clone.__dict__)
