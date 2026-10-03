"""Continuous four-lane tap playback under the frozen EA-MVP assumptions.

ENGINEERING ASSUMPTION: current visible lane identity is passed unchanged from
the fixed renderer/encoder interface to the fixed key readout. The fly circuit
supplies press timing; lane identity is not represented or learned by the
current 32-KC -> MBON05 subgraph.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from project_b.ea_mvp.continuous_v2 import ContinuousFrozenFlyPolicy
from project_b.osu.adapter import PositionObservation
from project_b.osu.config import OsuConfig
from project_b.osu.mania_game import ManiaGame, ManiaResultEvent, ManiaScoreSnapshot
from project_b.osu.types import KeyAction, TapNote
from project_b.osu.windows import ManiaHitWindows


@dataclass(frozen=True, slots=True)
class MultilaneTapTrace:
    actions: tuple[KeyAction, ...]
    results: tuple[ManiaResultEvent, ...]
    score: ManiaScoreSnapshot
    neural_reset_count: int
    readout_rearm_count: int
    spike_count: int


class ContinuousFourLaneFlyPolicy(ContinuousFrozenFlyPolicy):
    """One continuous timing circuit with a frozen observation-lane key map."""

    def begin(self, observation: PositionObservation) -> None:
        if self._sim is not None or not observation.visible or observation.lane not in range(4):
            raise ValueError("begin needs a visible note in one of four lanes")
        super().begin(PositionObservation(True, 0, observation.position))
        self._active_lane = observation.lane
        # Replace the base lane-0 readout with the fixed identity lane map.
        assert observation.position is not None
        self._readout = self._new_readout(0, observation.position, observation.lane)
        self.readout_rearm_count = 1

    def _new_readout(self, time_us: int, position: float, lane: int | None = None):
        from project_b.malecns_continuous_position_learning.online_readout import OnlinePositionReadout

        readout = OnlinePositionReadout(
            position_grid=list(self.config["evaluation"]["position_grid"]),
            bin_width=0.05,
            threshold_mv=self.config["continuation"]["frozen_action_threshold_mv"],
            dt_us=self.dt_us,
            lane=(getattr(self, "_active_lane", 0) if lane is None else lane),
            key_hold_us=10_000, direction=-1)
        readout.begin(time_us, position)
        self.readout_rearm_count += 1
        return readout

    def step(self, observation: PositionObservation):
        if observation.visible and observation.lane not in range(4):
            raise ValueError("visible lane must be in [0, 3]")
        if observation.visible and self._previous_visible and observation.lane != self._active_lane:
            raise ValueError("lane cannot change during one visible note")
        if observation.visible and not self._previous_visible:
            self._active_lane = observation.lane
        # Reuse the tested one-lane simulation/readout timing. Its observation
        # lane is translated to zero internally; emitted actions are rebound to
        # the frozen current-lane key selected at cue onset.
        translated = PositionObservation(observation.visible, 0,
                                         observation.position if observation.visible else None)
        events = super().step(translated)
        return tuple(type(event)(event.episode_time_us, self._active_lane, event.kind)
                     for event in events)


def play_continuous_multilane_taps(
    notes: Sequence[TapNote], config: OsuConfig,
    policy: ContinuousFourLaneFlyPolicy, *, visible_lead_us: int = 500_000,
) -> MultilaneTapTrace:
    """Play sequential four-key taps with one neural state and retained weights."""
    if not notes or any(type(note) is not TapNote or note.lane not in range(4)
                        for note in notes):
        raise ValueError("four-lane admission requires taps in lanes 0 through 3")
    ordered = tuple(sorted(notes, key=lambda row: row.time_us))
    if tuple(notes) != ordered or len({note.note_id for note in notes}) != len(notes):
        raise ValueError("notes must be time-ordered with unique IDs")
    dt = policy.dt_us
    if (visible_lead_us <= 0 or visible_lead_us % dt
            or ordered[0].time_us < visible_lead_us
            or any(b.time_us - a.time_us <= visible_lead_us + 20_000
                   for a, b in zip(ordered, ordered[1:]))):
        raise ValueError("notes must have nonoverlapping cue and key-release intervals")
    game = ManiaGame(ordered, config)
    start_us = ordered[0].time_us - visible_lead_us
    stop_us = ordered[-1].time_us + ManiaHitWindows.from_od(
        config.od, config.ruleset).expiry_offset_us + dt
    actions: list[KeyAction] = []
    delivered = 0

    def observation(at_us: int) -> PositionObservation:
        visible = [note for note in ordered
                   if note.time_us - visible_lead_us <= at_us <= note.time_us]
        if len(visible) > 1:
            raise AssertionError("overlapping notes in four-lane admission")
        if not visible:
            return PositionObservation(False, 0, None)
        note = visible[0]
        return PositionObservation(True, note.lane,
                                   (note.time_us - at_us) / visible_lead_us)

    policy.begin(observation(start_us))
    for at_us in range(start_us + dt, stop_us + 1, dt):
        game.advance_to(at_us)
        delivered = len(game.results)
        for transition in policy.step(observation(at_us)):
            if transition.episode_time_us != at_us - start_us:
                raise ValueError("policy action must target the current tick")
            if transition.lane not in range(4):
                raise ValueError("readout emitted an invalid lane")
            action = KeyAction(at_us, transition.lane, transition.kind)
            game.apply_action(action)
            actions.append(action)
    game.finish()
    policy.finish()
    return MultilaneTapTrace(tuple(actions), tuple(game.results), game.score.snapshot(),
                             policy.neural_reset_count, policy.readout_rearm_count,
                             policy.spike_count)
