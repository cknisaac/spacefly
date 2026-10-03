"""Continuous one-lane EA playback with retained fly weights and membrane state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from project_b.malecns_continuous_position_learning.encoder import population_drive
from project_b.malecns_continuous_position_learning.online_readout import OnlinePositionReadout
from project_b.malecns_continuous_position_learning.probe import _lif
from project_b.osu.adapter import PolicyKeyTransition, PositionObservation
from project_b.osu.config import OsuConfig
from project_b.osu.feedback import GameFeedbackEvent
from project_b.osu.mania_game import ManiaGame, ManiaResultEvent, ManiaScoreSnapshot
from project_b.osu.types import KeyAction, TapNote
from project_b.osu.windows import ManiaHitWindows
from project_b.simulation import SpikingSimulator
from project_b.synapses import SparseGraph, Synapse


class ContinuousFrozenFlyPolicy:
    """Keep one neural simulator alive across several separated visible taps.

    ENGINEERING ASSUMPTION: a fixed readout is rearmed by a blank-to-visible
    transition. Neural membrane state and the trained synaptic weights persist.
    No note ID, target time, game score, or judgement enters the sensory port.
    """

    def __init__(self, config: dict, weights: Sequence[float]) -> None:
        self.config = config
        self.cells = tuple(config["circuit"]["selected_kcs"])
        self.weights = tuple(float(weight) for weight in weights)
        if len(self.weights) != len(self.cells) or any(weight <= 0 for weight in self.weights):
            raise ValueError("one positive retained weight is required per audited KC")
        self.dt_us = config["overlay"]["lif"]["dt_us"]
        self.n_kc = len(self.cells)
        self._sim: SpikingSimulator | None = None
        self._readout: OnlinePositionReadout | None = None
        self._time_us = 0
        self._previous_visible = False
        self._finished = False
        self.feedback: list[GameFeedbackEvent] = []
        self.neural_reset_count = 0
        self.readout_rearm_count = 0

    def _drive(self, observation: PositionObservation) -> list[float]:
        if not observation.visible:
            return [0.0] * (self.n_kc + 1)
        assert observation.position is not None
        return list(population_drive(
            observation.position, self.cells, sigma=self.config["encoder"]["sigma"],
            peak_drive_mv=self.config["encoder"]["peak_drive_mv"])) + [0.0]

    def _new_readout(self, time_us: int, position: float) -> OnlinePositionReadout:
        readout = OnlinePositionReadout(
            position_grid=list(self.config["evaluation"]["position_grid"]),
            bin_width=0.05,
            threshold_mv=self.config["continuation"]["frozen_action_threshold_mv"],
            dt_us=self.dt_us, lane=0, key_hold_us=10_000, direction=-1)
        readout.begin(time_us, position)
        self.readout_rearm_count += 1
        return readout

    def begin(self, observation: PositionObservation) -> None:
        if self._sim is not None or observation.lane != 0 or not observation.visible:
            raise ValueError("begin needs the first visible lane-0 note")
        self._sim = SpikingSimulator(
            [_lif(self.config)] * (self.n_kc + 1),
            SparseGraph(self.n_kc + 1, [
                Synapse(i, self.n_kc, self.weights[i],
                        self.config["overlay"]["synaptic_delay_us"])
                for i in range(self.n_kc)]),
            self._drive(observation), dt_us=self.dt_us,
            record_neurons=[self.n_kc], record_spikes=True)
        self.neural_reset_count = 1
        assert observation.position is not None
        self._readout = self._new_readout(0, observation.position)
        self._previous_visible = True

    def on_feedback(self, events: tuple[GameFeedbackEvent, ...]) -> None:
        self.feedback.extend(events)

    def step(self, observation: PositionObservation) -> tuple[PolicyKeyTransition, ...]:
        if self._sim is None or self._finished or observation.lane != 0:
            raise RuntimeError("begin() must precede each lane-0 step")
        self._time_us += self.dt_us
        snapshot = self._sim.run_until(self._time_us)
        voltage = snapshot.voltage_trace[-1].voltage_before_reset_mv
        emitted = ()
        if observation.visible and not self._previous_visible:
            assert observation.position is not None
            self._readout = self._new_readout(self._time_us, observation.position)
        elif self._readout is not None:
            emitted = self._readout.step(
                self._time_us, observation.position if observation.visible else None,
                voltage)
        self._sim.set_external_drive_mv(self._drive(observation))
        self._previous_visible = observation.visible
        return tuple(PolicyKeyTransition(action.time_us, action.lane, action.kind)
                     for action in emitted)

    def finish(self) -> None:
        if self._sim is None or self._finished:
            raise RuntimeError("finish() requires one active policy")
        self._finished = True
        if self._readout is not None and self._readout.finish(self._time_us):
            raise RuntimeError("unexpected trailing key action after map closed")

    @property
    def spike_count(self) -> int:
        return 0 if self._sim is None else len(self._sim.snapshot().spikes)


@dataclass(frozen=True, slots=True)
class ContinuousTapTrace:
    actions: tuple[KeyAction, ...]
    results: tuple[ManiaResultEvent, ...]
    feedback: tuple[GameFeedbackEvent, ...]
    score: ManiaScoreSnapshot
    neural_reset_count: int
    readout_rearm_count: int
    spike_count: int


def play_continuous_taps(notes: Sequence[TapNote], config: OsuConfig,
                         policy: ContinuousFrozenFlyPolicy, *,
                         visible_lead_us: int = 500_000) -> ContinuousTapTrace:
    """Play separated lane-0 taps on one game clock with one live fly state."""
    if not notes or any(type(note) is not TapNote or note.lane != 0 for note in notes):
        raise ValueError("continuous admission requires lane-0 tap notes")
    ordered = tuple(sorted(notes, key=lambda row: row.time_us))
    if tuple(notes) != ordered or len({note.note_id for note in notes}) != len(notes):
        raise ValueError("notes must be time-ordered with unique IDs")
    dt = policy.dt_us
    if (visible_lead_us <= 0 or visible_lead_us % dt
            or ordered[0].time_us < visible_lead_us
            or any(next_note.time_us - note.time_us <= visible_lead_us + 20_000
                   for note, next_note in zip(ordered, ordered[1:]))):
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
            raise AssertionError("overlapping notes in one-position admission")
        if not visible:
            return PositionObservation(False, 0, None)
        return PositionObservation(True, 0,
                                   (visible[0].time_us - at_us) / visible_lead_us)

    policy.begin(observation(start_us))
    for at_us in range(start_us + dt, stop_us + 1, dt):
        game.advance_to(at_us)
        new = game.results[delivered:]
        if new:
            feedback = tuple(GameFeedbackEvent(row.time_us, row.result)
                             for row in new if row.component == "tap")
            if any(event.available_at_us > at_us for event in feedback):
                raise AssertionError("feedback delivered before game outcome")
            policy.on_feedback(feedback)
            delivered = len(game.results)
        for transition in policy.step(observation(at_us)):
            if transition.episode_time_us != at_us - start_us or transition.lane != 0:
                raise ValueError("policy action must target current tick and lane zero")
            action = KeyAction(at_us, 0, transition.kind)
            game.apply_action(action)
            actions.append(action)
    game.finish()
    policy.finish()
    return ContinuousTapTrace(tuple(actions), tuple(game.results),
                              tuple(policy.feedback), game.score.snapshot(),
                              policy.neural_reset_count,
                              policy.readout_rearm_count, policy.spike_count)
