"""Causal single-lane loop through the 128-cell synthetic circuit."""

import unittest

from project_b.experiments import (
    TinyBrainConfig, TinyLaneSession, build_tiny_brain, run_tiny_lane_one,
)
from project_b.motor import FixedMotorReadout
from project_b.osu import KeyActionKind, ManiaJudgement
from project_b.sensory import TimeToContactEncoder


class InterfaceTests(unittest.TestCase):
    def test_invalid_scale_and_queue_limit_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            TinyBrainConfig(neuron_count=99)
        with self.assertRaises(ArithmeticError):
            run_tiny_lane_one(TinyBrainConfig(
                note_count=1, exploration_probability=0.0,
                max_pending_arrivals=1))
        with self.assertRaises(ValueError):
            TinyBrainConfig(note_count=2, training_notes=1,
                            reward_utility_schedule=(0.0, 1.0))
        with self.assertRaises(ValueError):
            TinyBrainConfig(note_count=2, explicit_note_times_us=(800_000, 900_000))
        with self.assertRaises(ValueError):
            TinyBrainConfig(readout_on_threshold=1)
        with self.assertRaises(ValueError):
            TinyBrainConfig(note_count=2, cue_gain_by_note=(1.0,))

    def test_100_to_500_neuron_layout_remains_sparse_and_masked(self) -> None:
        for count in (100, 128, 500):
            with self.subTest(neurons=count):
                layout = build_tiny_brain(TinyBrainConfig(neuron_count=count))
                self.assertEqual(layout.graph.neuron_count, count)
                populations = (layout.sensory, layout.relay,
                               layout.motor, layout.inhibitory)
                self.assertEqual(set().union(*map(set, populations)), set(range(count)))
                self.assertEqual(sum(map(len, populations)), count)
                self.assertLess(layout.graph.edge_count, 20 * count)
                self.assertGreater(len(layout.plastic_slots), 0)
                self.assertTrue(all(
                    layout.graph.pre_indices[slot] in layout.relay
                    and layout.graph.post_indices[slot] in layout.motor
                    for slot in layout.plastic_slots))

    def test_smooth_causal_sensory_code_and_fixed_motor_threshold(self) -> None:
        encoder = TimeToContactEncoder()
        self.assertEqual(encoder.neuron_count, 40)
        self.assertEqual(encoder.encode(0, None), (0.0,) * 40)
        self.assertEqual(encoder.encode(0, 600_000), (0.0,) * 40)
        early = encoder.encode(0, 500_000)
        near = encoder.encode(450_000, 500_000)
        self.assertGreater(sum(value > 0.1 for value in early), 1)
        self.assertGreater(sum(value > 0.1 for value in near), 1)
        self.assertNotEqual(early, near)
        self.assertTrue(all(0 <= value <= encoder.drive_peak_mv
                            for value in near))

        readout = FixedMotorReadout(range(10, 20))
        self.assertIsNone(readout.observe(1_000, [10]))
        down = readout.observe(2_000, [10, 11, 12, 13, 14, 15])
        self.assertIsNotNone(down)
        self.assertIs(down.action.kind, KeyActionKind.DOWN)
        self.assertEqual(down.action.lane, 0)
        up = readout.observe(32_000, [])
        self.assertIsNotNone(up)
        self.assertIs(up.action.kind, KeyActionKind.UP)
        with self.assertRaises(ValueError):
            readout.observe(33_000, [10, 10, 10, 10, 10, 10])


class ClosedLoopTests(unittest.TestCase):
    def test_explicit_slow_map_and_declared_readout_settings(self) -> None:
        config = TinyBrainConfig(note_count=2,
                                 explicit_note_times_us=(800_000, 1_610_000),
                                 cue_gain_by_note=(0.8, 1.2),
                                 readout_on_threshold=8)
        session = TinyLaneSession(config)
        self.assertEqual(session.note_times_us, config.explicit_note_times_us)
        self.assertEqual(session.readout.on_threshold, 8)
        self.assertEqual(session.config.cue_gain_by_note, (0.8, 1.2))

    def test_yoked_reward_changes_learning_signal_not_game_scoring(self) -> None:
        config = TinyBrainConfig(note_count=2, training_notes=1, seed=1,
                                 reward_utility_schedule=(1.0,))
        result = run_tiny_lane_one(config)
        first = result.feedback[0].reinforcement
        self.assertEqual(first.learning_utility, 1.0)
        self.assertEqual(first.prediction.actual_utility, 1.0)
        self.assertEqual(first.utility.utility,
                         2 * int(result.judgements[0].judgement) / 320 - 1)
        second = result.feedback[1].reinforcement
        self.assertEqual(second.learning_utility, second.utility.utility)

    def test_note_to_spikes_decision_judgement_rpe_dopamine_and_plasticity(self) -> None:
        result = run_tiny_lane_one(TinyBrainConfig(note_count=4))
        self.assertEqual(result.config.neuron_count, 128)
        self.assertEqual(result.note_times_us, (800_000, 1_800_000,
                                                 2_800_000, 3_800_000))
        self.assertGreater(result.sensory_spikes, 0)
        self.assertGreater(result.relay_spikes, 0)
        self.assertGreater(result.motor_spikes, 0)
        self.assertGreater(result.inhibitory_spikes, 0)
        self.assertTrue(any(d.action.kind is KeyActionKind.DOWN
                            for d in result.decisions))
        self.assertEqual(len(result.judgements), 4)
        self.assertEqual(len(result.feedback), 4)
        self.assertTrue(all(record.lane == 0 for record in result.judgements))
        self.assertTrue(any(record.judgement is not ManiaJudgement.MISS
                            for record in result.judgements))
        self.assertTrue(any(record.judgement is ManiaJudgement.MISS
                            for record in result.judgements))
        for record, delivery in zip(result.judgements, result.feedback):
            self.assertEqual(delivery.reinforcement.judgement_record, record)
            self.assertEqual(delivery.reinforcement.modulation.source_rpe,
                             delivery.reinforcement.prediction.rpe)
            self.assertGreaterEqual(delivery.delivered_time_us, record.event_time_us)
            self.assertLess(delivery.delivered_time_us - record.event_time_us,
                            result.config.dt_us)
            self.assertTrue(all(change.time_us == delivery.delivered_time_us
                                for change in delivery.weight_changes))
        self.assertTrue(any(change.applied_delta_mv > 0
                            for feedback in result.feedback
                            for change in feedback.weight_changes))
        self.assertTrue(any(change.applied_delta_mv < 0
                            for feedback in result.feedback
                            for change in feedback.weight_changes))
        self.assertNotEqual(result.final_plastic_weights_mv,
                            result.initial_plastic_weights_mv)

    def test_no_exploration_or_modulation_cannot_fake_learning(self) -> None:
        no_exploration = run_tiny_lane_one(TinyBrainConfig(
            note_count=2, exploration_probability=0.0))
        self.assertGreater(no_exploration.sensory_spikes, 0)
        self.assertGreater(no_exploration.relay_spikes, 0)
        self.assertEqual(no_exploration.motor_spikes, 0)
        self.assertEqual(no_exploration.decisions, ())
        self.assertTrue(all(j.judgement is ManiaJudgement.MISS
                            for j in no_exploration.judgements))
        self.assertEqual(no_exploration.final_plastic_weights_mv,
                         no_exploration.initial_plastic_weights_mv)

        no_modulation = run_tiny_lane_one(TinyBrainConfig(
            note_count=4, modulation_gain=0.0))
        self.assertTrue(any(f.reinforcement.prediction.rpe != 0
                            for f in no_modulation.feedback))
        self.assertTrue(all(f.reinforcement.modulation.amplitude == 0
                            and not f.weight_changes for f in no_modulation.feedback))
        self.assertEqual(no_modulation.final_plastic_weights_mv,
                         no_modulation.initial_plastic_weights_mv)

    def test_frozen_notes_are_driven_by_learned_weights_not_exploration(self) -> None:
        config = TinyBrainConfig(note_count=16, training_notes=8)
        learned = run_tiny_lane_one(config)
        control = run_tiny_lane_one(TinyBrainConfig(
            note_count=16, training_notes=8, plasticity_enabled=False))
        learned_hits = sum(j.judgement is not ManiaJudgement.MISS
                           for j in learned.judgements[8:])
        control_hits = sum(j.judgement is not ManiaJudgement.MISS
                           for j in control.judgements[8:])
        self.assertEqual(learned_hits, 8)
        self.assertEqual(control_hits, 0)
        self.assertTrue(all(not f.weight_changes for f in learned.feedback[8:]))
        self.assertTrue(all(t < learned.note_times_us[8] - 500_000
                            for t in learned.exploration_pulses))
        self.assertEqual(control.final_plastic_weights_mv,
                         control.initial_plastic_weights_mv)

    def test_seed_replay_and_mid_map_checkpoint_roundtrip(self) -> None:
        config = TinyBrainConfig(note_count=3)
        self.assertEqual(run_tiny_lane_one(config), run_tiny_lane_one(config))
        session = TinyLaneSession(config)
        session.run_until(1_500_000)
        restored = TinyLaneSession.from_trusted_checkpoint_bytes(
            session.checkpoint_bytes())
        self.assertEqual(session.run(), restored.run())


if __name__ == "__main__":
    unittest.main()
