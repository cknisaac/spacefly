"""Equal-time chord playback using the admitted shared timing circuit.

ENGINEERING ASSUMPTION: the fixed frame-to-key readout holds the currently
visible lane set and fans each MBON05-timed DOWN/UP transition to every lane in
that set. The neural circuit supplies one shared timing signal; it does not
encode chord membership or learn lane combinations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from project_b.ea_mvp.continuous_multilane import ContinuousFourLaneFlyPolicy
from project_b.osu.adapter import PositionFrameObservation, PositionObservation
from project_b.osu.config import OsuConfig
from project_b.osu.mania_game import ManiaGame, ManiaResultEvent, ManiaScoreSnapshot
from project_b.osu.types import KeyAction, TapNote
from project_b.osu.windows import ManiaHitWindows


@dataclass(frozen=True, slots=True)
class ChordMapTrace:
    actions: tuple[KeyAction, ...]
    results: tuple[ManiaResultEvent, ...]
    score: ManiaScoreSnapshot
    neural_reset_count: int
    readout_rearm_count: int
    spike_count: int


def _frame_lanes(frame: PositionFrameObservation) -> tuple[int, ...]:
    lanes = tuple(sorted({row.lane for row in frame.visible_notes}))
    if frame.visible_notes and len({row.position for row in frame.visible_notes}) != 1:
        raise ValueError("this admission handles only same-position, equal-time chords")
    return lanes


class ContinuousChordFlyPolicy(ContinuousFourLaneFlyPolicy):
    """One continuous fly timing path with a frozen lane-set output fanout."""

    def begin(self, frame: PositionFrameObservation) -> None:
        lanes = _frame_lanes(frame)
        if not lanes:
            raise ValueError("begin requires a visible chord")
        self._active_lanes = lanes
        self._frame_was_visible = True
        super().begin(PositionObservation(True, 0, frame.visible_notes[0].position))

    def step(self, frame: PositionFrameObservation):
        lanes = _frame_lanes(frame)
        if lanes and self._frame_was_visible and lanes != self._active_lanes:
            raise ValueError("the visible chord lane set cannot change before a blank frame")
        if lanes and not self._frame_was_visible:
            self._active_lanes = lanes
        self._frame_was_visible = bool(lanes)
        observation = PositionObservation(bool(lanes), 0,
                                          frame.visible_notes[0].position if lanes else None)
        timed = super().step(observation)
        return tuple(type(event)(event.episode_time_us, lane, event.kind)
                     for event in timed for lane in self._active_lanes)


def play_equal_time_chords(
    chords: Sequence[Sequence[TapNote]], config: OsuConfig,
    policy: ContinuousChordFlyPolicy, *, visible_lead_us: int = 500_000,
) -> ChordMapTrace:
    """Play separated, equal-time multi-lane tap chords on one neural state."""
    groups = tuple(tuple(group) for group in chords)
    if not groups or any(not group for group in groups):
        raise ValueError("at least one nonempty chord is required")
    flattened = tuple(note for group in groups for note in group)
    if any(type(note) is not TapNote for note in flattened):
        raise ValueError("only tap chords are supported")
    for group in groups:
        if len({note.time_us for note in group}) != 1 or len({note.lane for note in group}) != len(group):
            raise ValueError("each chord must have one shared time and distinct lanes")
    if len({note.note_id for note in flattened}) != len(flattened):
        raise ValueError("note IDs must be unique")
    ordered_groups = tuple(sorted(groups, key=lambda group: group[0].time_us))
    if groups != ordered_groups:
        raise ValueError("chords must be time-ordered")
    dt = policy.dt_us
    if (visible_lead_us <= 0 or visible_lead_us % dt
            or ordered_groups[0][0].time_us < visible_lead_us
            or any(b[0].time_us - a[0].time_us <= visible_lead_us + 20_000
                   for a, b in zip(ordered_groups, ordered_groups[1:]))):
        raise ValueError("chord cue windows and key holds must not overlap")
    game = ManiaGame(flattened, config)
    start_us = ordered_groups[0][0].time_us - visible_lead_us
    stop_us = max(note.time_us for note in flattened) + ManiaHitWindows.from_od(
        config.od, config.ruleset).expiry_offset_us + dt
    actions: list[KeyAction] = []

    def frame(at_us: int) -> PositionFrameObservation:
        visible_groups = [group for group in ordered_groups
                          if group[0].time_us - visible_lead_us <= at_us <= group[0].time_us]
        if len(visible_groups) > 1:
            raise AssertionError("overlapping chord cue windows")
        if not visible_groups:
            return PositionFrameObservation(())
        group = visible_groups[0]
        position = (group[0].time_us - at_us) / visible_lead_us
        from project_b.osu.adapter import VisibleNotePosition
        return PositionFrameObservation(tuple(sorted(
            (VisibleNotePosition(note.lane, position) for note in group),
            key=lambda row: (row.lane, row.position))))

    policy.begin(frame(start_us))
    for at_us in range(start_us + dt, stop_us + 1, dt):
        game.advance_to(at_us)
        for transition in policy.step(frame(at_us)):
            action = KeyAction(at_us, transition.lane, transition.kind)
            game.apply_action(action)
            actions.append(action)
    game.finish()
    policy.finish()
    return ChordMapTrace(tuple(actions), tuple(game.results), game.score.snapshot(),
                         policy.neural_reset_count, policy.readout_rearm_count,
                         policy.spike_count)
