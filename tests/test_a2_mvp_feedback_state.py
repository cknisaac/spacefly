"""Pending first-action and PAM feedback survive an A2 committed boundary."""

import unittest
import tempfile
from pathlib import Path

from project_b.checkpoint import load_checkpoint, save_checkpoint
from project_b.mvp_c1 import (FeedbackScheduler, FirstActionTracker,
                              MvpTaskSession, NoteWindow)
from project_b.osu.types import ActionDisposition, KeyAction, KeyActionKind


NOTES = (NoteWindow("n1", 100_000, 900_000),
         NoteWindow("n2", 1_300_000, 2_100_000),
         NoteWindow("n3", 2_500_000, 3_300_000))


class CausalFeedbackStateTests(unittest.TestCase):
    def test_frozen_task_starts_fresh_and_never_requests_pam_current(self):
        trained = MvpTaskSession(NOTES)
        trained.advance_to(100_000)
        trained.apply_action(KeyAction(800_000, 0, KeyActionKind.DOWN))
        self.assertIsNotNone(trained.feedback.pending_early)
        frozen = MvpTaskSession(NOTES, teaching_enabled=False)
        self.assertEqual(frozen.time_us, 0)
        self.assertEqual(frozen.feedback.expected_utility, 1.0)
        frozen.advance_to(100_000)
        frozen.apply_action(KeyAction(800_000, 0, KeyActionKind.DOWN))
        self.assertEqual(frozen.feedback.decisions[0].pam_request, 0.0)
        self.assertIsNone(frozen.feedback.pending_early)
        frozen.advance_to(825_000)
        self.assertEqual(frozen.feedback.pam_current(825_000), 0.0)

    def test_coupled_task_owner_replays_pending_early_and_late_routes(self):
        original = MvpTaskSession(NOTES)
        original.advance_to(100_000)
        original.apply_action(KeyAction(800_000, 0, KeyActionKind.DOWN))
        original.apply_action(KeyAction(810_000, 0, KeyActionKind.UP))
        original.advance_to(820_000)
        resumed = MvpTaskSession(NOTES)
        resumed.restore(original.state())
        self.assertEqual(original.state(), resumed.state())
        for session in (original, resumed):
            session.advance_to(825_000)
            session.advance_to(1_300_000)
            session.apply_action(KeyAction(2_200_000, 0, KeyActionKind.DOWN))
            session.apply_action(KeyAction(2_210_000, 0, KeyActionKind.UP))
        self.assertEqual(original.state(), resumed.state())
        self.assertEqual(original.feedback.pending_late.outcome.note_id, "n2")
        late_checkpoint = original.state()
        resumed_again = MvpTaskSession(NOTES)
        resumed_again.restore(late_checkpoint)
        original.advance_to(2_500_000)
        resumed_again.advance_to(2_500_000)
        self.assertEqual(original.state(), resumed_again.state())
        self.assertEqual(original.feedback.active_pulses[-1].route,
                         "next_visible_prime")

    def test_task_state_canonical_json_bundle_resume(self):
        session = MvpTaskSession(NOTES)
        session.advance_to(100_000)
        session.apply_action(KeyAction(800_000, 0, KeyActionKind.DOWN))
        state = {"phase": "COMMITTED_TICK_AFTER_FEEDBACK_AND_LEDGER_FLUSH",
                 "time_us": session.time_us, "task": session.state()}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cut"
            save_checkpoint(path, {"candidate": "MVP-C1-task-fixture"}, state)
            loaded = load_checkpoint(path, {"candidate": "MVP-C1-task-fixture"})
        restored = MvpTaskSession(NOTES)
        restored.restore(loaded["task"])
        self.assertEqual(restored.state(), session.state())

    def test_early_flush_and_same_state_after_restore(self):
        a, fa = FirstActionTracker(NOTES), FeedbackScheduler()
        a.on_visible_onset("n1", 100_000)
        outcome = a.on_down(800_000, ActionDisposition.EARLY_MISS)
        self.assertEqual(outcome.category, "early_judged")
        decision = fa.resolve(outcome, 800_000)
        self.assertEqual((decision.utility, decision.expected_before,
                          decision.rpe, decision.pam_request), (0, 1, -1, 1))
        b, fb = FirstActionTracker(NOTES), FeedbackScheduler()
        b.restore(a.state())
        fb.restore(fa.state())
        self.assertEqual(fa.advance_to(824_000), fb.advance_to(824_000))
        self.assertEqual(fa.advance_to(825_000), fb.advance_to(825_000))
        self.assertEqual(fa.pam_current(825_000), 2.0)
        self.assertEqual(fa.state(), fb.state())
        self.assertEqual(a.on_visible_onset("n2", 1_300_000),
                         b.on_visible_onset("n2", 1_300_000))
        self.assertEqual(a.state(), b.state())

    def test_missing_action_primes_next_actual_visible_cue(self):
        first, feedback = FirstActionTracker(NOTES), FeedbackScheduler()
        first.on_visible_onset("n1", 100_000)
        no_down = first.on_visible_onset("n2", 1_300_000)
        self.assertEqual(no_down.category, "no_down")
        feedback.resolve(no_down, 1_300_000)
        pulse = feedback.on_visible_onset(1_300_000)
        self.assertEqual((pulse.start_us, pulse.end_us, pulse.amplitude),
                         (1_300_000, 1_320_000, 1.0))
        first.on_down(2_200_000, ActionDisposition.NULL_PRESS)
        late = first.on_visible_onset("n3", 2_500_000)
        self.assertEqual(late.category, "late")
        feedback.resolve(late, 2_500_000)
        self.assertAlmostEqual(feedback.pending_late.pam_request, 0.9)
        feedback.on_visible_onset(2_500_000)
        self.assertIsNone(feedback.pending_late)

    def test_too_early_null_is_failure_without_pulse(self):
        first, feedback = FirstActionTracker(NOTES), FeedbackScheduler()
        first.on_visible_onset("n1", 100_000)
        outcome = first.on_down(150_000, ActionDisposition.NULL_PRESS)
        decision = feedback.resolve(outcome, 150_000)
        self.assertEqual((outcome.category, decision.route),
                         ("too_early_null", "none"))
        self.assertIsNone(feedback.pending_early)
        self.assertIsNone(feedback.pending_late)


if __name__ == "__main__":
    unittest.main()
