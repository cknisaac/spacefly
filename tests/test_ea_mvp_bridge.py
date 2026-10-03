"""Causal game-to-policy seam checks; no fly learner or training is run."""

import dataclasses
import unittest
from pathlib import Path

from project_b.ea_mvp.bridge import StreamingTapBridge
from project_b.ea_mvp.frozen_policy import FrozenFlyTapPolicy
from project_b.malecns_continuous_position_learning.online_policy import load_position_config
from project_b.osu.adapter import PolicyKeyTransition, PositionObservation
from project_b.osu.config import OsuConfig
from project_b.osu.feedback import GameFeedbackEvent
from project_b.osu.types import KeyActionKind, TapNote


class ThresholdFixture:
    """Fixed interface fixture, not an EA-MVP neural policy."""

    def __init__(self, threshold: float | None) -> None:
        self.threshold = threshold
        self.tick = -1
        self.down_at: int | None = None
        self.received: list[tuple[int, GameFeedbackEvent]] = []
        self.first_feedback_tick: int | None = None

    def begin(self, observation: PositionObservation) -> None:
        assert observation.visible and observation.position == 1.0
        self.tick = 0

    def on_feedback(self, events: tuple[GameFeedbackEvent, ...]) -> None:
        for event in events:
            self.received.append((self.tick + 1, event))
            if self.first_feedback_tick is None:
                self.first_feedback_tick = self.tick + 1

    def step(self, observation: PositionObservation):
        self.tick += 1
        if self.threshold is None or not observation.visible:
            return ()
        if self.down_at is None and observation.position <= self.threshold:
            self.down_at = self.tick
            return (PolicyKeyTransition(self.tick * 1_000, 0, KeyActionKind.DOWN),)
        if self.down_at is not None and self.tick == self.down_at + 10:
            return (PolicyKeyTransition(self.tick * 1_000, 0, KeyActionKind.UP),)
        return ()

    def finish(self) -> None:
        pass


class StreamingTapBridgeTests(unittest.TestCase):
    def setUp(self):
        self.bridge = StreamingTapBridge(
            TapNote("one", 0, 500_000), OsuConfig(od=8, ruleset="lazer"))

    def test_good_press_feedback_follows_action_and_contains_no_schedule(self):
        policy = ThresholdFixture(0.1)
        trace = self.bridge.run(policy)
        self.assertEqual([(a.time_us, a.kind) for a in trace.actions],
                         [(450_000, KeyActionKind.DOWN), (460_000, KeyActionKind.UP)])
        self.assertEqual([(r.result, r.hit_error_us) for r in trace.results],
                         [("GOOD", -50_000)])
        self.assertEqual([(row.delivered_at_us, row.event.judgement_label)
                          for row in trace.feedback], [(451_000, "GOOD")])
        self.assertEqual(policy.first_feedback_tick, 451)
        self.assertEqual({field.name for field in dataclasses.fields(GameFeedbackEvent)},
                         {"available_at_us", "judgement_label"})
        self.assertEqual({field.name for field in dataclasses.fields(PositionObservation)},
                         {"visible", "lane", "position"})

    def test_null_press_is_not_immediate_teaching_and_expires_as_miss(self):
        trace = self.bridge.run(ThresholdFixture(0.7))
        self.assertEqual(trace.actions[0].time_us, 150_000)
        self.assertEqual([r.result for r in trace.results], ["MISS"])
        self.assertEqual(len(trace.feedback), 1)
        self.assertGreater(trace.feedback[0].delivered_at_us, 500_000)
        self.assertEqual(trace.feedback[0].event.judgement_label, "MISS")

    def test_no_down_has_same_label_only_feedback_as_null_then_expiry(self):
        trace = self.bridge.run(ThresholdFixture(None))
        self.assertEqual(trace.actions, ())
        self.assertEqual([row.event.judgement_label for row in trace.feedback], ["MISS"])
        self.assertEqual([r.hit_error_us for r in trace.results], [None])

    def test_frozen_fly_receives_current_positions_and_delayed_result_only(self):
        root = Path(__file__).resolve().parents[1]
        config = load_position_config(
            root, "configs/malecns_continuous_position_learning_v2_5.json")
        policy = FrozenFlyTapPolicy(config)
        initial_weights = tuple(policy.fly.weights)
        trace = self.bridge.run(policy)
        self.assertEqual(trace.actions, ())
        self.assertEqual(tuple(policy.fly.weights), initial_weights)
        self.assertEqual([event.judgement_label for event in policy.feedback], ["MISS"])
        self.assertTrue(all(obs.lane == 0 for obs in trace.observations))

    def test_predeclared_local_weight_probe_drives_key_without_learning(self):
        root = Path(__file__).resolve().parents[1]
        config = load_position_config(
            root, "configs/malecns_continuous_position_learning_v2_5.json")
        cells = config["circuit"]["selected_kcs"]
        total = sum(cell["plastic_contact_rows"] for cell in cells)
        weights = [cell["plastic_contact_rows"] / total for cell in cells]
        weights = [weight * 0.2 if abs(cell["preferred_position"] - 0.2) <= 0.1
                   else weight for cell, weight in zip(cells, weights)]
        policy = FrozenFlyTapPolicy(config, weights=weights)
        trace = self.bridge.run(policy)
        self.assertEqual([action.time_us for action in trace.actions
                          if action.kind is KeyActionKind.DOWN], [388_000])
        self.assertEqual([event.result for event in trace.results], ["MEH"])
        self.assertEqual([event.judgement_label for event in policy.feedback], ["MEH"])
        self.assertEqual(tuple(policy.fly.weights), tuple(weights))


if __name__ == "__main__":
    unittest.main()
