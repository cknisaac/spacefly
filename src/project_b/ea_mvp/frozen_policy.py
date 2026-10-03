"""Non-learning fly-to-streaming-game adapter for EA-MVP admission checks."""

from __future__ import annotations

from project_b.malecns_continuous_position_learning.online_policy import OnlineFlyPolicy
from project_b.osu.adapter import PositionObservation, PolicyKeyTransition
from project_b.osu.feedback import GameFeedbackEvent


class FrozenFlyTapPolicy:
    """Keep fly weights fixed while checking the causal game interface.

    Feedback is recorded but cannot change the fly. A future learner must use
    a separately frozen judgement-to-DAN rule and local synaptic update path.
    """

    def __init__(self, config: dict, *, weights: list[float] | None = None) -> None:
        self.fly = OnlineFlyPolicy(config, lane=0, weights=weights)
        self.dt_us = self.fly.dt_us
        self.feedback: list[GameFeedbackEvent] = []

    def begin(self, observation: PositionObservation) -> None:
        self.fly.begin(observation)

    def on_feedback(self, events: tuple[GameFeedbackEvent, ...]) -> None:
        self.feedback.extend(events)

    def step(self, observation: PositionObservation) -> tuple[PolicyKeyTransition, ...]:
        return self.fly.step(observation)

    def finish(self) -> None:
        trailing = self.fly.finish()
        if trailing:
            raise RuntimeError("fly readout emitted actions after the bridge closed")
