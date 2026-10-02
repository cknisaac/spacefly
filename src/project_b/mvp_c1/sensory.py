"""Fixed current-position KC encoder with cancelable 25-ms delay."""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass

from project_b.utils.time import require_time_us


@dataclass(frozen=True, slots=True)
class DelayedSample:
    due_us: int
    sequence: int
    note_id: str
    generation: int
    observed_position: float


class CurrentPositionKCEncoder:
    """Samples only a rendered position; note timing stays in the renderer."""

    def __init__(self, kc_source_ids: tuple[int, ...], *,
                 latency_us: int = 25_000, sigma: float = 0.125,
                 peak_current: float = 2.0):
        ids = tuple(sorted(kc_source_ids))
        if (not ids or len(set(ids)) != len(ids) or any(type(i) is not int for i in ids)
                or require_time_us(latency_us) <= 0
                or not all(math.isfinite(v) and v > 0 for v in (sigma, peak_current))):
            raise ValueError("invalid KC encoder identity")
        self.kc_source_ids = ids
        self.latency_us = latency_us
        self.sigma = sigma
        self.peak_current = peak_current
        self._centers = tuple((i % 16) / 15 for i in range(len(ids)))
        self.current_drive = [0.0] * len(ids)
        self._queue: list[tuple[int, int, DelayedSample]] = []
        self._generation: dict[str, int] = {}
        self._active_note_id: str | None = None
        self._sequence = 0
        self.observation_cursor = 0
        self.last_time_us = 0

    def observe(self, time_us: int, note_id: str, position: float) -> DelayedSample:
        require_time_us(time_us)
        if (time_us < self.last_time_us or not note_id
                or type(position) not in (int, float)
                or not math.isfinite(position) or not 0 <= position <= 1):
            raise ValueError("encoder needs current finite visible position")
        if self._active_note_id not in (None, note_id):
            raise ValueError("overlapping or uncanceled cue")
        self._active_note_id = note_id
        generation = self._generation.setdefault(note_id, 0)
        sample = DelayedSample(time_us + self.latency_us, self._sequence,
                               note_id, generation, float(position))
        heapq.heappush(self._queue, (sample.due_us, sample.sequence, sample))
        self._sequence += 1
        self.observation_cursor += 1
        self.last_time_us = time_us
        return sample

    def due_drive(self, time_us: int) -> tuple[float, ...]:
        require_time_us(time_us)
        if time_us < self.last_time_us:
            raise ValueError("encoder clock reversal")
        while self._queue and self._queue[0][0] <= time_us:
            _, _, sample = heapq.heappop(self._queue)
            if (sample.note_id == self._active_note_id
                    and sample.generation == self._generation[sample.note_id]):
                self.current_drive = [self.peak_current * math.exp(
                    -0.5 * ((sample.observed_position - center) / self.sigma) ** 2)
                    for center in self._centers]
        self.last_time_us = time_us
        return tuple(self.current_drive)

    def cancel(self, time_us: int, note_id: str) -> None:
        require_time_us(time_us)
        if time_us < self.last_time_us or note_id != self._active_note_id:
            raise ValueError("cannot cancel inactive or past cue")
        self._generation[note_id] += 1
        self._active_note_id = None
        self.current_drive = [0.0] * len(self.kc_source_ids)
        self.last_time_us = time_us

    def state(self) -> dict:
        return {"identity": {"kc_source_ids": list(self.kc_source_ids),
                             "latency_us": self.latency_us, "sigma": self.sigma,
                             "peak_current": self.peak_current},
                "current_drive": list(self.current_drive),
                "queue": [list((sample.due_us, sample.sequence, sample.note_id,
                                sample.generation, sample.observed_position))
                          for _, _, sample in sorted(self._queue)],
                "generation": dict(self._generation),
                "active_note_id": self._active_note_id,
                "sequence": self._sequence,
                "observation_cursor": self.observation_cursor,
                "last_time_us": self.last_time_us}

    def restore(self, state: dict) -> None:
        if set(state) != set(self.state()) or state["identity"] != self.state()["identity"]:
            raise ValueError("encoder checkpoint identity differs")
        drive = state["current_drive"]
        queue = [DelayedSample(*row) for row in state["queue"]]
        generation = state["generation"]
        active = state["active_note_id"]
        last = state["last_time_us"]
        if (len(drive) != len(self.kc_source_ids)
                or any(type(v) not in (int, float) or not math.isfinite(v) or v < 0
                       for v in drive)
                or type(last) is not int or last < 0
                or type(state["sequence"]) is not int or state["sequence"] < 0
                or type(state["observation_cursor"]) is not int
                or state["observation_cursor"] < 0
                or (active is not None and active not in generation)
                or any(type(v) is not int or v < 0 for v in generation.values())
                or any(s.due_us <= last or s.sequence >= state["sequence"]
                       or s.note_id not in generation
                       or s.generation > generation[s.note_id]
                       or not math.isfinite(s.observed_position)
                       or not 0 <= s.observed_position <= 1 for s in queue)
                or len({s.sequence for s in queue}) != len(queue)):
            raise ValueError("invalid delayed KC drive state")
        self.current_drive = list(drive)
        self._queue = [(s.due_us, s.sequence, s) for s in queue]
        heapq.heapify(self._queue)
        self._generation = dict(generation)
        self._active_note_id = active
        self._sequence = state["sequence"]
        self.observation_cursor = state["observation_cursor"]
        self.last_time_us = last
