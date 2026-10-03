import dataclasses
import unittest
from pathlib import Path

from project_b.malecns_continuous_position_learning.online_policy import (
    OnlineFlyPolicy,
    PositionObservation,
    load_position_config,
)
from project_b.malecns_continuous_position_learning.experiment_level4d_final_moving_note_repair import (
    _simulate_note,
)
from project_b.osu.adapter import HeadlessManiaTapAdapter, PositionObservation
from project_b.osu import KeyActionKind, ManiaJudgement, TapNote, load_config
from project_b.osu.feedback import NoteCue
from project_b.osu.windows import ManiaHitWindows


ROOT = Path(__file__).resolve().parents[1]


def run_single_note():
    position_config = load_position_config(
        ROOT, "configs/malecns_continuous_position_learning_v2_5.json")
    policy = OnlineFlyPolicy(position_config, lane=0)
    hit_time_us = 500_000  # The environment owns this; it is never sent to policy.
    observations = [PositionObservation(True, 0, 1.0)]
    for time_us in range(1_000, hit_time_us + 2_000, 1_000):
        if time_us <= hit_time_us:
            observations.append(PositionObservation(
                True, 0, 1.0 - time_us / hit_time_us))
        else:
            observations.append(PositionObservation(False, 0, None))
    game_config = load_config(ROOT / "configs/lazer_mvp.yaml")
    hit_windows = ManiaHitWindows.from_od(game_config.od, game_config.ruleset)
    cue = NoteCue("mvp-note", 0, 0, hit_time_us,
                  hit_time_us + hit_windows.expiry_offset_us)
    adapter = HeadlessManiaTapAdapter(
        (TapNote("mvp-note", 0, hit_time_us),), (cue,), game_config,
        episode_start_time_us=0, observation_dt_us=1_000,
        good_window_us=int(hit_windows.good_ms * 1_000),
    )
    episode = adapter.run(policy, observations)
    return policy, episode


class OnlinePositionPolicyTests(unittest.TestCase):
    def test_observation_has_only_visible_lane_and_current_position(self):
        self.assertEqual(
            {field.name for field in dataclasses.fields(PositionObservation)},
            {"visible", "lane", "position"},
        )
        with self.assertRaises(ValueError):
            PositionObservation(False, 0, 0.5)
        with self.assertRaises(ValueError):
            PositionObservation(True, 0, None)

    def test_500ms_lazer_note_is_deterministic_and_uses_causal_policy(self):
        first_policy, first_episode = run_single_note()
        second_policy, second_episode = run_single_note()

        first_game = first_episode.game_result
        self.assertEqual(first_episode.as_dict(), second_episode.as_dict())
        self.assertEqual(first_episode.game_result, second_episode.game_result)
        self.assertEqual(first_policy.decisions, second_policy.decisions)
        self.assertIsNotNone(first_policy.first_valid_time_us)
        downs = [action for action in first_episode.game_actions
                 if action.kind is KeyActionKind.DOWN]
        ups = [action for action in first_episode.game_actions
               if action.kind is KeyActionKind.UP]
        self.assertEqual(downs, [])
        self.assertEqual(ups, [])

        self.assertEqual(first_game.total_notes, 1)
        self.assertEqual(first_game.resolved_notes, 1)
        self.assertEqual(first_game.judgements[0].ruleset, "lazer")
        self.assertEqual(first_game.judgements[0].note_id, "mvp-note")
        self.assertIs(first_game.judgements[0].judgement, ManiaJudgement.MISS)
        self.assertIsNone(first_game.judgements[0].hit_error_us)
        self.assertEqual(first_game.judgements[0].event_time_us, 627_501)
        self.assertEqual(first_episode.score.total_score, 0)
        self.assertEqual(first_episode.score.accuracy_denominator, 305)

    def test_online_mbon_trace_matches_independent_batch_note_simulator(self):
        config = load_position_config(
            ROOT, "configs/malecns_continuous_position_learning_v2_5.json")
        policy = OnlineFlyPolicy(config, lane=0)
        policy.begin(PositionObservation(True, 0, 1.0))
        actions = []
        for time_us in range(1_000, 501_000, 1_000):
            position = 1.0 - time_us / 500_000
            actions.extend(policy.step(PositionObservation(True, 0, position)))
        actions.extend(policy.finish())

        batch = _simulate_note(
            config, policy.weights, 500_000, 0.05, policy.threshold_mv)
        expected_trace = tuple(
            (row["time_us"], row["mbon05_voltage_mv"])
            for row in batch["mbon05_timecourse"])
        actual_trace = tuple(row for row in policy.mbon_voltage_trace if row[0] > 0)
        self.assertEqual(actual_trace, expected_trace)

        batch_first_action = batch["first_action"]
        online_downs = [action for action in actions
                        if action.kind is KeyActionKind.DOWN]
        # Closing the current bin requires observing the next position, so an
        # online decision may be exactly one integration tick later than the
        # batch evaluator's final sample timestamp.
        if batch_first_action is None:
            self.assertEqual(online_downs, [])
        else:
            self.assertLessEqual(
                batch_first_action["time_us"],
                max(action.time_us for action in online_downs))
            self.assertLessEqual(
                max(action.time_us for action in online_downs)
                - batch_first_action["time_us"],
                policy.dt_us,
            )


if __name__ == "__main__":
    unittest.main()
