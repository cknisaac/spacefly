"""Independent judgement → utility → RPE → modulation checks."""

import unittest

from project_b.neuromodulation import (
    CenteredHitUtility,
    RPEModulator,
    ReinforcementPipeline,
    RewardPredictor,
)
from project_b.osu import (
    JudgementRecord,
    KeyAction,
    KeyActionKind,
    ManiaJudgement,
    TapNote,
    play,
)


def judgement(value: ManiaJudgement, *, time_us: int = 0) -> JudgementRecord:
    return JudgementRecord("note", 0, 0, time_us, value, 0)


class UtilityTests(unittest.TestCase):
    def test_all_six_judgements_have_exact_centered_utility(self) -> None:
        mapper = CenteredHitUtility()
        cases = (
            (ManiaJudgement.MAX_320, 320, 1.0),
            (ManiaJudgement.GREAT_300, 300, 0.875),
            (ManiaJudgement.GOOD_200, 200, 0.25),
            (ManiaJudgement.OK_100, 100, -0.375),
            (ManiaJudgement.MEH_50, 50, -0.6875),
            (ManiaJudgement.MISS, 0, -1.0),
        )
        for label, hit_value, expected_utility in cases:
            with self.subTest(judgement=label):
                mapped = mapper.translate(label)
                self.assertIs(mapped.judgement, label)
                self.assertEqual(mapped.hit_value, hit_value)
                self.assertEqual(mapped.utility, expected_utility)
        with self.assertRaises(TypeError):
            mapper.translate(300)  # type: ignore[arg-type]


class PredictionTests(unittest.TestCase):
    def test_example_expected_point_two_actual_point_eight_yields_positive_point_six(self) -> None:
        predictor = RewardPredictor(initial_expected_utility=0.2, alpha=0.1)
        prediction = predictor.observe(0.8)
        self.assertAlmostEqual(prediction.expected_before, 0.2)
        self.assertAlmostEqual(prediction.actual_utility, 0.8)
        self.assertAlmostEqual(prediction.rpe, 0.6)
        self.assertAlmostEqual(prediction.expected_after, 0.26)
        self.assertAlmostEqual(predictor.expected_utility, 0.26)

    def test_repeated_expected_reward_reduces_surprise(self) -> None:
        predictor = RewardPredictor(initial_expected_utility=0.0, alpha=0.1)
        observations = [predictor.observe(0.8) for _ in range(20)]
        rpes = [event.rpe for event in observations]
        self.assertTrue(all(first > second > 0
                            for first, second in zip(rpes, rpes[1:])))
        self.assertGreater(predictor.expected_utility, 0.0)
        self.assertLess(predictor.expected_utility, 0.8)

    def test_unexpected_failure_produces_negative_rpe(self) -> None:
        predictor = RewardPredictor(initial_expected_utility=0.0, alpha=0.1)
        for _ in range(20):
            predictor.observe(1.0)
        failure = predictor.observe(-1.0)
        self.assertGreater(failure.expected_before, 0.8)
        self.assertLess(failure.rpe, -1.8)

    def test_invalid_utility_rate_and_stale_preview_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            RewardPredictor(alpha=1.0)
        with self.assertRaises(ValueError):
            RewardPredictor(initial_expected_utility=float("nan"))
        predictor = RewardPredictor()
        with self.assertRaises(ValueError):
            predictor.observe(320.0)
        preview = predictor.preview(0.8)
        predictor.observe(0.8)
        with self.assertRaises(ValueError):
            predictor.commit(preview)


class PipelineTests(unittest.TestCase):
    def test_yoked_learning_utility_preserves_game_judgement(self) -> None:
        pipeline = ReinforcementPipeline()
        record = judgement(ManiaJudgement.MISS)
        event = pipeline.process_judgement(record, learning_utility=0.875)
        self.assertEqual(event.judgement_record, record)
        self.assertEqual(event.utility.utility, -1.0)
        self.assertEqual(event.learning_utility, 0.875)
        self.assertEqual(event.prediction.actual_utility, 0.875)
        self.assertEqual(event.modulation.amplitude, 0.875)
        expected = pipeline.predictor.expected_utility
        with self.assertRaises(ValueError):
            pipeline.process_judgement(record, learning_utility=2.0)
        self.assertEqual(pipeline.predictor.expected_utility, expected)

    def test_actual_osu_judgement_enters_independent_chain(self) -> None:
        game = play([TapNote("n1", 0, 0)],
                    [KeyAction(0, 0, KeyActionKind.DOWN)])
        self.assertEqual(len(game.judgements), 1)
        self.assertIs(game.judgements[0].judgement, ManiaJudgement.MAX_320)
        original_game_result = play([TapNote("n1", 0, 0)],
                                    [KeyAction(0, 0, KeyActionKind.DOWN)])
        pipeline = ReinforcementPipeline(modulator=RPEModulator(gain=0.5))
        event = pipeline.process_judgement(game.judgements[0])
        self.assertEqual(event.judgement_record, game.judgements[0])
        self.assertEqual(event.utility.hit_value, 320)
        self.assertEqual(event.utility.utility, 1.0)
        self.assertEqual(event.prediction.expected_before, 0.0)
        self.assertEqual(event.prediction.rpe, 1.0)
        self.assertEqual(event.prediction.expected_after, 0.1)
        self.assertEqual(event.modulation.source_rpe, 1.0)
        self.assertEqual(event.modulation.amplitude, 0.5)
        self.assertEqual(event.modulation.kind, "synthetic_dopamine_like")
        self.assertEqual(event.modulation.time_us, game.judgements[0].event_time_us)
        self.assertEqual(game, original_game_result)
        with self.assertRaises(TypeError):
            pipeline.process_judgement(game.actions[0])  # type: ignore[arg-type]

    def test_every_judgement_tier_reaches_rpe_and_modulation(self) -> None:
        cases = (
            (ManiaJudgement.MAX_320, 1.0),
            (ManiaJudgement.GREAT_300, 0.875),
            (ManiaJudgement.GOOD_200, 0.25),
            (ManiaJudgement.OK_100, -0.375),
            (ManiaJudgement.MEH_50, -0.6875),
            (ManiaJudgement.MISS, -1.0),
        )
        for label, expected_utility in cases:
            with self.subTest(judgement=label):
                event = ReinforcementPipeline().process_judgement(judgement(label))
                self.assertEqual(event.utility.utility, expected_utility)
                self.assertEqual(event.prediction.actual_utility, expected_utility)
                self.assertEqual(event.prediction.rpe, expected_utility)
                self.assertEqual(event.modulation.amplitude, expected_utility)

    def test_judgement_utility_rpe_and_modulation_remain_distinct(self) -> None:
        pipeline = ReinforcementPipeline(
            predictor=RewardPredictor(initial_expected_utility=0.5),
            modulator=RPEModulator(gain=0.5))
        event = pipeline.process_judgement(judgement(ManiaJudgement.OK_100))
        self.assertEqual(event.utility.hit_value, 100)
        self.assertEqual(event.utility.utility, -0.375)
        self.assertEqual(event.prediction.expected_before, 0.5)
        self.assertEqual(event.prediction.rpe, -0.875)
        self.assertEqual(event.modulation.amplitude, -0.4375)

    def test_repeated_max_then_miss_reverses_modulatory_sign(self) -> None:
        pipeline = ReinforcementPipeline()
        success = [pipeline.process_judgement(
            judgement(ManiaJudgement.MAX_320, time_us=i))
            for i in range(20)]
        self.assertTrue(all(a.prediction.rpe > b.prediction.rpe > 0
                            for a, b in zip(success, success[1:])))
        missed_game = play([TapNote("unplayed", 0, 1_000_000)], [])
        self.assertIs(missed_game.judgements[0].judgement, ManiaJudgement.MISS)
        failure = pipeline.process_judgement(missed_game.judgements[0])
        self.assertLess(failure.prediction.rpe, -1.8)
        self.assertLess(failure.modulation.amplitude, 0.0)
        self.assertEqual(failure.utility.utility, -1.0)

    def test_zero_modulation_gain_and_chronological_delivery(self) -> None:
        pipeline = ReinforcementPipeline(modulator=RPEModulator(gain=0.0))
        first = pipeline.process_judgement(
            judgement(ManiaJudgement.MAX_320, time_us=100))
        self.assertEqual(first.prediction.rpe, 1.0)
        self.assertEqual(first.modulation.amplitude, 0.0)
        expected = pipeline.predictor.expected_utility
        with self.assertRaises(ValueError):
            pipeline.process_judgement(
                judgement(ManiaJudgement.MISS, time_us=99))
        self.assertEqual(pipeline.predictor.expected_utility, expected)


if __name__ == "__main__":
    unittest.main()
