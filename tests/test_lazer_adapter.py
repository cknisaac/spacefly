import dataclasses
import unittest
from pathlib import Path

from project_b.osu import KeyActionKind, TapNote, load_config
from project_b.osu.adapter import (
    HeadlessManiaTapAdapter,
    PolicyKeyTransition,
    PositionObservation,
)
from project_b.osu.feedback import FirstActionCategory, NoteCue
from project_b.osu.windows import ManiaHitWindows


ROOT = Path(__file__).resolve().parents[1]


class PositionTriggeredPolicy:
    """Tiny contract fixture: act on a visible position, without game timing."""

    def __init__(self):
        self.observations = []
        self.acted = False

    def begin(self, observation):
        self.observations.append(observation)

    def step(self, observation):
        self.observations.append(observation)
        if (not self.acted and observation.visible
                and observation.position is not None
                and observation.position <= 0.1):
            self.acted = True
            return (
                PolicyKeyTransition(450_000, observation.lane, KeyActionKind.DOWN),
                PolicyKeyTransition(451_000, observation.lane, KeyActionKind.UP),
            )
        return ()

    def finish(self):
        return ()

    def reproducibility_metadata(self):
        return {"policy_class": type(self).__qualname__, "stochastic": False}


def make_episode(policy):
    game_config = load_config(ROOT / "configs/lazer_mvp.yaml")
    note_time_us = 600_000
    windows = ManiaHitWindows.from_od(game_config.od, game_config.ruleset)
    note = TapNote("adapter-note", 0, note_time_us)
    cue = NoteCue("adapter-note", 0, 100_000, note_time_us,
                  note_time_us + windows.expiry_offset_us)
    adapter = HeadlessManiaTapAdapter(
        (note,), (cue,), game_config,
        episode_start_time_us=100_000,
        observation_dt_us=1_000,
        good_window_us=int(windows.good_ms * 1_000),
    )
    observations = [PositionObservation(True, 0, 1.0)]
    for elapsed_us in range(1_000, 501_000, 1_000):
        position = max(0.0, 1.0 - elapsed_us / 500_000)
        observations.append(PositionObservation(True, 0, position))
    return adapter.run(policy, observations)


class LazerAdapterContractTests(unittest.TestCase):
    def test_policy_sees_only_current_observation_and_actions_translate_to_game_time(self):
        policy = PositionTriggeredPolicy()
        episode = make_episode(policy)

        self.assertEqual(
            {field.name for field in dataclasses.fields(PositionObservation)},
            {"visible", "lane", "position"},
        )
        self.assertTrue(all(type(row) is PositionObservation
                            for row in policy.observations))
        self.assertEqual(episode.as_dict()["policy_input_fields"],
                         ["visible", "lane", "position"])
        self.assertEqual(
            [(row.episode_time_us, row.kind) for row in episode.policy_actions],
            [(450_000, KeyActionKind.DOWN), (451_000, KeyActionKind.UP)],
        )
        self.assertEqual(
            [(row.time_us, row.kind) for row in episode.game_actions],
            [(550_000, KeyActionKind.DOWN), (551_000, KeyActionKind.UP)],
        )
        self.assertEqual(episode.first_action_audit[0].signed_error_us, -50_000)
        self.assertEqual(episode.first_action_audit[0].category,
                         FirstActionCategory.GOOD_OR_BETTER)
        self.assertEqual(episode.game_result.judgements[0].note_id, "adapter-note")
        self.assertEqual(episode.score.total_score, 310_148)
        self.assertEqual(episode.score.accuracy_numerator, 200)
        self.assertEqual(episode.score.accuracy_denominator, 305)
        self.assertEqual(episode.as_dict()["score"]["total_score"], 310_148)

    def test_same_config_policy_and_observation_stream_replay_identically(self):
        first = make_episode(PositionTriggeredPolicy())
        second = make_episode(PositionTriggeredPolicy())
        self.assertEqual(first.as_dict(), second.as_dict())

    def test_observation_rejects_extra_game_schedule_fields(self):
        for forbidden_field in (
            "note_time_us", "time_to_contact_us", "score", "judgement",
            "target_key",
        ):
            with self.subTest(field=forbidden_field):
                with self.assertRaises(TypeError):
                    PositionObservation(
                        True, 0, 0.5, **{forbidden_field: 600_000})


if __name__ == "__main__":
    unittest.main()
