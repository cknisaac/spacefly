"""Causal one-lane headless game bridge; no fly plasticity or teacher here."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from project_b.osu.adapter import PolicyKeyTransition, PositionObservation
from project_b.osu.config import OsuConfig
from project_b.osu.feedback import GameFeedbackEvent
from project_b.osu.mania_game import ManiaGame, ManiaResultEvent, ManiaScoreSnapshot
from project_b.osu.types import KeyAction, TapNote
from project_b.osu.windows import ManiaHitWindows


class StreamingTapPolicy(Protocol):
    """Only present observations and already available result labels enter policy."""

    def begin(self, observation: PositionObservation) -> None: ...

    def on_feedback(self, events: tuple[GameFeedbackEvent, ...]) -> None: ...

    def step(self, observation: PositionObservation) -> Sequence[PolicyKeyTransition]: ...

    def finish(self) -> None: ...


@dataclass(frozen=True, slots=True)
class DeliveredFeedback:
    """Post-run receipt; delivery time is distinct from result event time."""

    delivered_at_us: int
    event: GameFeedbackEvent


@dataclass(frozen=True, slots=True)
class StreamingTapTrace:
    """Evaluator-only receipt returned after policy execution has ended."""

    observations: tuple[PositionObservation, ...]
    actions: tuple[KeyAction, ...]
    feedback: tuple[DeliveredFeedback, ...]
    results: tuple[ManiaResultEvent, ...]
    score: ManiaScoreSnapshot


class StreamingTapBridge:
    """Run one lane-0 tap on the game clock, delivering outcomes causally.

    The schedule is held by this game-side adapter. The policy receives only
    `PositionObservation` and stripped, already resolved game result labels.
    An action created at a tick is visible to feedback on the *next* tick.
    """

    def __init__(self, note: TapNote, config: OsuConfig, *,
                 visible_lead_us: int = 500_000, dt_us: int = 1_000) -> None:
        if not isinstance(note, TapNote) or note.lane != 0:
            raise ValueError("EA-MVP bridge requires one lane-0 tap note")
        if not isinstance(config, OsuConfig) or config.ruleset != "lazer":
            raise ValueError("EA-MVP bridge requires a lazer game config")
        if type(visible_lead_us) is not int or visible_lead_us <= 0:
            raise ValueError("visible_lead_us must be a positive integer")
        if type(dt_us) is not int or dt_us <= 0:
            raise ValueError("dt_us must be a positive integer")
        if note.time_us < visible_lead_us:
            raise ValueError("note must have a nonnegative visibility start")
        self.note = note
        self.config = config
        self.visible_lead_us = visible_lead_us
        self.dt_us = dt_us

    def _observation(self, time_us: int) -> PositionObservation:
        visible_from_us = self.note.time_us - self.visible_lead_us
        if visible_from_us <= time_us <= self.note.time_us:
            position = (self.note.time_us - time_us) / self.visible_lead_us
            return PositionObservation(True, 0, position)
        return PositionObservation(False, 0, None)

    def run(self, policy: StreamingTapPolicy) -> StreamingTapTrace:
        start_us = self.note.time_us - self.visible_lead_us
        windows = ManiaHitWindows.from_od(self.config.od, self.config.ruleset)
        stop_us = self.note.time_us + windows.expiry_offset_us + self.dt_us
        game = ManiaGame((self.note,), self.config)
        observations: list[PositionObservation] = []
        actions: list[KeyAction] = []
        feedback: list[DeliveredFeedback] = []
        delivered_result_count = 0

        def deliver(time_us: int) -> None:
            nonlocal delivered_result_count
            newly_resolved = game.results[delivered_result_count:]
            if not newly_resolved:
                return
            stripped = tuple(GameFeedbackEvent(row.time_us, row.result)
                             for row in newly_resolved if row.component == "tap")
            if stripped:
                if any(event.available_at_us > time_us for event in stripped):
                    raise AssertionError("game result delivered before availability")
                policy.on_feedback(stripped)
                feedback.extend(DeliveredFeedback(time_us, event) for event in stripped)
            delivered_result_count = len(game.results)

        first_observation = self._observation(start_us)
        policy.begin(first_observation)
        observations.append(first_observation)
        for time_us in range(start_us + self.dt_us, stop_us + 1, self.dt_us):
            game.advance_to(time_us)
            deliver(time_us)
            observation = self._observation(time_us)
            observations.append(observation)
            for transition in policy.step(observation):
                if not isinstance(transition, PolicyKeyTransition):
                    raise TypeError("policy must return PolicyKeyTransition records")
                if transition.lane != 0 or transition.episode_time_us != time_us - start_us:
                    raise ValueError("policy may emit only current-tick lane-0 actions")
                action = KeyAction(time_us, 0, transition.kind)
                game.apply_action(action)
                actions.append(action)

        game.finish()
        deliver(game.now_us)
        policy.finish()
        return StreamingTapTrace(tuple(observations), tuple(actions),
                                 tuple(feedback), tuple(game.results),
                                 game.score.snapshot())
