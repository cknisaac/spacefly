"""Sequential hold playback using the admitted timing circuit.

ENGINEERING ASSUMPTION: the fixed visual encoder exposes the current head and
tail positions. The fixed readout takes the neural-timed DOWN, suppresses its
default 10-ms tap UP while a hold is active, and emits UP when the visible tail
reaches the strike line. Hold duration and lane identity are not learned.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence

from project_b.ea_mvp.continuous_multilane import ContinuousFourLaneFlyPolicy
from project_b.osu.adapter import PolicyKeyTransition, PositionObservation
from project_b.osu.config import OsuConfig
from project_b.osu.mania_game import ManiaGame, ManiaResultEvent, ManiaScoreSnapshot
from project_b.osu.types import HoldNote, KeyAction, KeyActionKind
from project_b.osu.windows import ManiaHitWindows


@dataclass(frozen=True, slots=True)
class VisibleHold:
    lane: int
    head_position: float
    tail_position: float
    head_visible: bool = True

    def __post_init__(self) -> None:
        if type(self.lane) is not int or self.lane not in range(4):
            raise ValueError("hold lane must be in 0..3")
        if (type(self.head_position) not in (int, float)
                or not math.isfinite(self.head_position)
                or not 0.0 <= self.head_position <= 1.0):
            raise ValueError("head position must be in [0, 1]")
        if type(self.tail_position) not in (int, float) or not math.isfinite(self.tail_position):
            raise ValueError("tail position must be finite")
        if type(self.head_visible) is not bool:
            raise ValueError("head_visible must be a bool")


@dataclass(frozen=True, slots=True)
class HoldFrame:
    holds: tuple[VisibleHold, ...]


@dataclass(frozen=True, slots=True)
class HoldMapTrace:
    actions: tuple[KeyAction, ...]
    results: tuple[ManiaResultEvent, ...]
    score: ManiaScoreSnapshot
    neural_reset_count: int
    readout_rearm_count: int
    spike_count: int


class ContinuousHoldFlyPolicy(ContinuousFourLaneFlyPolicy):
    """Single-hold-at-a-time policy; neural circuit supplies the head timing."""

    def begin(self, frame: HoldFrame) -> None:
        if len(frame.holds) != 1:
            raise ValueError("begin requires exactly one visible hold")
        self._held_lane: int | None = None
        self._hold_lane = frame.holds[0].lane
        self._hold_was_visible = True
        super().begin(PositionObservation(True, self._hold_lane,
                                          frame.holds[0].head_position))

    def step(self, frame: HoldFrame) -> tuple[PolicyKeyTransition, ...]:
        if len(frame.holds) > 1:
            raise ValueError("overlapping holds are outside this admission")
        visible = bool(frame.holds)
        if visible:
            hold = frame.holds[0]
            if self._hold_was_visible and hold.lane != self._hold_lane:
                raise ValueError("one visible hold cannot change lanes")
            if not self._hold_was_visible:
                self._hold_lane = hold.lane
        else:
            hold = None
        self._hold_was_visible = visible
        head_visible = hold is not None and hold.head_visible
        observation = PositionObservation(head_visible, self._hold_lane,
                                          hold.head_position if head_visible else None)
        timed = super().step(observation)
        output: list[PolicyKeyTransition] = []
        for event in timed:
            if event.kind is KeyActionKind.DOWN:
                if self._held_lane is not None:
                    raise RuntimeError("another hold began before the prior hold released")
                self._held_lane = event.lane
                output.append(event)
            # Suppress the fixed tap-duration UP while its visible hold remains.
        if hold is not None and self._held_lane is not None and hold.tail_position <= 0.0:
            output.append(PolicyKeyTransition(self._time_us, self._held_lane,
                                               KeyActionKind.UP))
            self._held_lane = None
        return tuple(output)


def play_sequential_holds(
    notes: Sequence[HoldNote], config: OsuConfig,
    policy: ContinuousHoldFlyPolicy, *, visible_lead_us: int = 500_000,
) -> HoldMapTrace:
    """Play separated hold notes whose visible head/tail positions do not overlap."""
    if not notes or any(type(note) is not HoldNote for note in notes):
        raise ValueError("at least one HoldNote is required")
    ordered = tuple(sorted(notes, key=lambda note: note.time_us))
    if tuple(notes) != ordered or len({note.note_id for note in notes}) != len(notes):
        raise ValueError("holds must be time-ordered with unique IDs")
    if (visible_lead_us <= 0 or visible_lead_us % policy.dt_us
            or ordered[0].time_us < visible_lead_us
            or any(b.time_us - a.end_time_us <= visible_lead_us + 20_000
                   for a, b in zip(ordered, ordered[1:]))):
        raise ValueError("hold visual intervals and key release intervals must not overlap")
    game = ManiaGame(ordered, config)
    start_us = ordered[0].time_us - visible_lead_us
    stop_us = ordered[-1].end_time_us + ManiaHitWindows.from_od(
        config.od, config.ruleset).expiry_offset_us * 2 + policy.dt_us
    actions: list[KeyAction] = []

    def frame(at_us: int) -> HoldFrame:
        visible = [note for note in ordered
                   if note.time_us - visible_lead_us <= at_us <= note.end_time_us]
        if len(visible) > 1:
            raise AssertionError("overlapping hold visuals")
        if not visible:
            return HoldFrame(())
        note = visible[0]
        head = max(0.0, (note.time_us - at_us) / visible_lead_us)
        tail = (note.end_time_us - at_us) / visible_lead_us
        return HoldFrame((VisibleHold(note.lane, head, tail,
                                      head_visible=at_us <= note.time_us),))

    policy.begin(frame(start_us))
    for at_us in range(start_us + policy.dt_us, stop_us + 1, policy.dt_us):
        game.advance_to(at_us)
        for transition in policy.step(frame(at_us)):
            action = KeyAction(at_us, transition.lane, transition.kind)
            game.apply_action(action)
            actions.append(action)
    game.finish()
    policy.finish()
    return HoldMapTrace(tuple(actions), tuple(game.results), game.score.snapshot(),
                        policy.neural_reset_count, policy.readout_rearm_count,
                        policy.spike_count)
