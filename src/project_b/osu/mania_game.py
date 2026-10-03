"""Four-key tap and long-note game on an integer-microsecond timeline.

The older :mod:`environment` tap engine remains the frozen L0.11 parity path.
This module models long-note head, body, tail, and parent results explicitly.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import heapq
import math
from typing import Sequence

from .config import OsuConfig
from .types import HoldNote, KeyAction, KeyActionKind, ManiaJudgement, TapNote
from .windows import ManiaHitWindows


@dataclass(frozen=True, slots=True)
class ManiaResultEvent:
    note_id: str
    component: str  # tap, head, body, tail, or parent
    lane: int
    note_time_us: int
    time_us: int
    result: str
    hit_error_us: int | None


@dataclass(frozen=True, slots=True)
class ManiaActionEvent:
    action: KeyAction
    disposition: str
    note_id: str | None


@dataclass(frozen=True, slots=True)
class ManiaScoreSnapshot:
    score: int
    accuracy: float
    combo: int
    max_combo: int
    judged_accuracy_objects: int
    total_accuracy_objects: int
    result_counts: dict[str, int]


class ManiaScore:
    """Incremental no-mod Score V2 for taps and long-note parts."""

    _points = {"PERFECT": 305, "GREAT": 300, "GOOD": 200,
               "OK": 100, "MEH": 50, "MISS": 0}
    _combo_points = {**_points, "PERFECT": 300}

    def __init__(self, notes: Sequence[TapNote | HoldNote]):
        self.total_accuracy_objects = sum(2 if isinstance(n, HoldNote) else 1
                                          for n in notes)
        self._maximum_combo_portion = sum(
            300 * self._multiplier(combo)
            for combo in range(1, self.total_accuracy_objects + 1))
        self._accuracy_numerator = 0
        self._judged_accuracy_objects = 0
        self._combo_portion = 0.0
        self.combo = 0
        self.max_combo = 0
        self.counts: Counter[str] = Counter()

    @staticmethod
    def _multiplier(combo: int) -> float:
        return min(max(0.5, math.log(combo, 4)) if combo else 0.5,
                   math.log(400, 4))

    def add(self, event: ManiaResultEvent) -> None:
        self.counts[event.result] += 1
        if event.result == "COMBO_BREAK":
            self.combo = 0
        elif event.result in self._points:
            self._judged_accuracy_objects += 1
            self._accuracy_numerator += self._points[event.result]
            self.combo = self.combo + 1 if event.result != "MISS" else 0
            self.max_combo = max(self.max_combo, self.combo)
            self._combo_portion += self._combo_points[event.result] * self._multiplier(self.combo)

    def snapshot(self) -> ManiaScoreSnapshot:
        denominator = self._judged_accuracy_objects * 305
        accuracy = self._accuracy_numerator / denominator if denominator else 1.0
        combo_progress = (self._combo_portion / self._maximum_combo_portion
                          if self._maximum_combo_portion else 1.0)
        accuracy_progress = (self._judged_accuracy_objects / self.total_accuracy_objects
                             if self.total_accuracy_objects else 1.0)
        score = round(150_000 * combo_progress +
                      850_000 * accuracy ** (2 + 2 * accuracy) * accuracy_progress)
        return ManiaScoreSnapshot(score, accuracy, self.combo, self.max_combo,
                                  self._judged_accuracy_objects,
                                  self.total_accuracy_objects, dict(self.counts))


@dataclass(slots=True)
class _HoldState:
    head: str | None = None
    body: str | None = None
    tail: str | None = None
    active: bool = False


class ManiaGame:
    """Playable four-lane no-mod game with all long notes retained."""

    def __init__(self, notes: Sequence[TapNote | HoldNote], config: OsuConfig):
        if config.ruleset != "lazer":
            raise ValueError("playable long-note game currently requires lazer rules")
        self.config = config
        self.windows = ManiaHitWindows.from_od(config.od, config.ruleset)
        self.notes = tuple(notes)
        if len({n.note_id for n in notes}) != len(notes):
            raise ValueError("note IDs must be unique")
        self._lanes = tuple(tuple(sorted((n for n in notes if n.lane == lane),
                                         key=lambda n: (n.time_us, n.note_id)))
                            for lane in range(4))
        self._resolved_taps: set[str] = set()
        self._holds = {n.note_id: _HoldState() for n in notes if isinstance(n, HoldNote)}
        self.key_down = [False] * 4
        self.now_us = 0
        self.results: list[ManiaResultEvent] = []
        self.actions: list[ManiaActionEvent] = []
        self.events: list[ManiaResultEvent | ManiaActionEvent] = []
        self.score = ManiaScore(notes)
        self._expiry: list[tuple[int, int, str, str]] = []
        for note in notes:
            head_expiry = note.time_us + self.windows.expiry_offset_us
            heapq.heappush(self._expiry, (head_expiry, note.lane, note.note_id,
                                          "head" if isinstance(note, HoldNote) else "tap"))
            if isinstance(note, HoldNote):
                # Tail release windows are 1.5x the normal note windows.
                tail_expiry = note.end_time_us + math.floor(
                    (self.windows.expiry_offset_us - 1) * 1.5) + 1
                heapq.heappush(self._expiry, (tail_expiry, note.lane, note.note_id, "tail"))
        self._by_id = {n.note_id: n for n in notes}

    @property
    def resolved_objects(self) -> int:
        return len(self._resolved_taps) + sum(state.tail is not None
                                               for state in self._holds.values())

    def _emit(self, note: TapNote | HoldNote, component: str, at_us: int,
              result: str, error_us: int | None = None) -> None:
        note_time = (note.end_time_us if component == "tail" and isinstance(note, HoldNote)
                     else note.time_us)
        event = ManiaResultEvent(note.note_id, component, note.lane, note_time,
                                 at_us, result, error_us)
        self.results.append(event)
        self.events.append(event)
        self.score.add(event)
        if component == "tap":
            self._resolved_taps.add(note.note_id)
        elif isinstance(note, HoldNote) and component != "parent":
            state = self._holds[note.note_id]
            setattr(state, component, result)

    def _end_hold(self, note: HoldNote, at_us: int, grade: str,
                  error_us: int | None) -> None:
        state = self._holds[note.note_id]
        if state.tail is not None:
            return
        self._emit(note, "tail", at_us, grade, error_us)
        if grade == "MISS":
            self._emit(note, "parent", at_us, "IGNORE_MISS")
        if state.body is None:
            self._emit(note, "body", note.end_time_us,
                       "IGNORE_HIT" if grade != "MISS" else "COMBO_BREAK")
        if grade != "MISS":
            self._emit(note, "parent", at_us, "IGNORE_HIT")
        state.active = False

    def advance_to(self, time_us: int) -> None:
        if type(time_us) is not int or time_us < self.now_us:
            raise ValueError("game time must advance in integer microseconds")
        while self._expiry and self._expiry[0][0] <= time_us:
            at_us, _, note_id, component = heapq.heappop(self._expiry)
            note = self._by_id[note_id]
            if component == "tap" and note_id not in self._resolved_taps:
                self._emit(note, "tap", at_us, "MISS")
            elif component == "head" and self._holds[note_id].head is None:
                self._emit(note, "head", at_us, "MISS")
            elif component == "tail" and self._holds[note_id].tail is None:
                self._end_hold(note, at_us, "MISS", None)
        self.now_us = time_us

    def _grade(self, offset_us: int) -> str | None:
        judgement = self.windows.press_judgement(offset_us)
        return ({ManiaJudgement.MAX_320: "PERFECT", ManiaJudgement.GREAT_300: "GREAT",
                 ManiaJudgement.GOOD_200: "GOOD", ManiaJudgement.OK_100: "OK",
                 ManiaJudgement.MEH_50: "MEH", ManiaJudgement.MISS: "MISS"}
                .get(judgement))

    def _tail_grade(self, offset_us: int) -> str | None:
        """Use Lazer's 1.5x release windows without rounding the offset."""
        error = abs(offset_us)
        for window_ms, label in ((self.windows.max_ms, "PERFECT"),
                                 (self.windows.great_ms, "GREAT"),
                                 (self.windows.good_ms, "GOOD"),
                                 (self.windows.ok_ms, "OK"),
                                 (self.windows.meh_ms, "MEH"),
                                 (self.windows.miss_ms, "MISS")):
            if error * 2 <= int(window_ms * 1000) * 3:
                return label
        return None

    def _force_miss_prior(self, lane: int, target: TapNote | HoldNote, at_us: int) -> None:
        for note in self._lanes[lane]:
            end = note.end_time_us if isinstance(note, HoldNote) else note.time_us
            if end >= target.time_us:
                break
            if isinstance(note, TapNote) and note.note_id not in self._resolved_taps:
                self._emit(note, "tap", at_us, "MISS")
            elif isinstance(note, HoldNote):
                state = self._holds[note.note_id]
                if state.head is None:
                    self._emit(note, "head", at_us, "MISS")
                if state.tail is None:
                    self._end_hold(note, at_us, "MISS", None)

    def _press(self, lane: int, at_us: int) -> tuple[str, str | None]:
        notes = self._lanes[lane]
        for index, note in enumerate(notes):
            next_note = notes[index + 1] if index + 1 < len(notes) else None
            if next_note is not None and at_us >= next_note.time_us:
                continue
            if isinstance(note, TapNote):
                if note.note_id in self._resolved_taps:
                    continue
                grade = self._grade(at_us - note.time_us)
                if grade is None:
                    continue
                self._emit(note, "tap", at_us, grade, at_us - note.time_us)
            else:
                state = self._holds[note.note_id]
                if state.tail is not None:
                    continue
                if at_us > note.end_time_us + self.windows.expiry_offset_us - 1:
                    continue
                if at_us < note.time_us - int(self.windows.miss_ms * 1000):
                    continue
                state.active = True
                if state.head is None:
                    grade = self._grade(at_us - note.time_us)
                    if grade is None:
                        continue
                    self._emit(note, "head", at_us, grade, at_us - note.time_us)
                else:
                    # Re-press resumes a broken long note without a new head result.
                    return "hold_resume", note.note_id
            if grade != "MISS":
                self._force_miss_prior(lane, note, at_us)
            return ("hit" if grade != "MISS" else "early_miss"), note.note_id
        return "null_press", None

    def apply_action(self, action: KeyAction) -> ManiaActionEvent:
        self.advance_to(action.time_us)
        lane = action.lane
        if action.kind is KeyActionKind.DOWN:
            if self.key_down[lane]:
                disposition, note_id = "repeat_down", None
            else:
                self.key_down[lane] = True
                disposition, note_id = self._press(lane, action.time_us)
        elif not self.key_down[lane]:
            disposition, note_id = "repeat_up", None
        else:
            self.key_down[lane] = False
            disposition, note_id = "release", None
            for note in self._lanes[lane]:
                if not isinstance(note, HoldNote):
                    continue
                state = self._holds[note.note_id]
                if not state.active or state.tail is not None:
                    continue
                state.active = False
                offset = action.time_us - note.end_time_us
                # Lazer divides the release offset by 1.5 before grading.
                grade = self._tail_grade(offset)
                if grade is None:
                    if state.body is None:
                        self._emit(note, "body", action.time_us, "COMBO_BREAK")
                else:
                    if grade != "MISS" and (state.head == "MISS" or
                                              state.body == "COMBO_BREAK"):
                        grade = "MEH"
                    self._end_hold(note, action.time_us, grade, offset)
                note_id = note.note_id
        event = ManiaActionEvent(action, disposition, note_id)
        self.actions.append(event)
        self.events.append(event)
        return event

    def finish(self) -> ManiaScoreSnapshot:
        if self._expiry:
            self.advance_to(max(self.now_us, max(event[0] for event in self._expiry)))
        return self.score.snapshot()
