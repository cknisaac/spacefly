import dataclasses
import unittest
from pathlib import Path

from project_b.osu import (
    ActionDisposition,
    KeyAction,
    KeyActionKind,
    TapNote,
    load_config,
    play,
)
from project_b.osu.feedback import (
    FirstActionCategory,
    NoteCue,
    GameFeedbackCursor,
    GameFeedbackEvent,
    reconstruct_first_actions,
)
from project_b.osu.windows import ManiaHitWindows


ROOT = Path(__file__).resolve().parents[1]
CONFIG = load_config(ROOT / "configs/lazer_mvp.yaml")
NOTE_TIME_US = 500_000
EXPIRY_US = NOTE_TIME_US + ManiaHitWindows.from_od(8, "lazer").expiry_offset_us
NOTE = TapNote("note-a", 0, NOTE_TIME_US)
CUE = NoteCue("note-a", 0, 0, NOTE_TIME_US, EXPIRY_US)


def replay(errors_us=()):
    actions = []
    for error_us in errors_us:
        at = NOTE_TIME_US + error_us
        actions.extend((KeyAction(at, 0, KeyActionKind.DOWN),
                        KeyAction(at + 10_000, 0, KeyActionKind.UP)))
    return play([NOTE], actions, CONFIG)


class LazerFeedbackContractTests(unittest.TestCase):
    def audit(self, result):
        return reconstruct_first_actions((CUE,), result, good_window_us=73_500)[0]

    def test_game_feedback_schema_hides_note_identity_and_timing_target(self):
        fields = {field.name for field in dataclasses.fields(GameFeedbackEvent)}
        self.assertEqual(fields, {"available_at_us", "judgement_label"})

        judged = replay((0,))
        cursor = GameFeedbackCursor(judged)
        self.assertEqual(cursor.poll(NOTE_TIME_US - 1), ())
        feedback, = cursor.poll(NOTE_TIME_US)
        self.assertEqual(feedback, GameFeedbackEvent(NOTE_TIME_US, "PERFECT"))
        self.assertEqual(cursor.poll(NOTE_TIME_US), ())
        self.assertFalse(hasattr(feedback, "note_id"))
        self.assertFalse(hasattr(feedback, "note_time_us"))
        self.assertFalse(hasattr(feedback, "hit_error_us"))

    def test_early_judged_miss_is_available_at_the_press(self):
        result = replay((-160_000,))
        outcome = self.audit(result)
        self.assertEqual(outcome.category, FirstActionCategory.EARLY_JUDGED_MISS)
        self.assertEqual(outcome.first_down_us, 340_000)
        self.assertEqual(outcome.signed_error_us, -160_000)
        self.assertEqual(outcome.first_disposition, ActionDisposition.EARLY_MISS.value)
        self.assertEqual(outcome.final_judgement, "MISS")
        self.assertEqual(outcome.judgement_time_us, 340_000)
        cursor = GameFeedbackCursor(result)
        self.assertEqual(cursor.poll(339_999), ())
        self.assertEqual(cursor.poll(340_000), (GameFeedbackEvent(340_000, "MISS"),))

    def test_late_judged_result_is_delivered_when_the_game_judges_it(self):
        result = replay((90_000,))
        outcome = self.audit(result)
        self.assertEqual(outcome.category, FirstActionCategory.LATE_JUDGED)
        self.assertEqual(outcome.signed_error_us, 90_000)
        self.assertEqual(outcome.final_judgement, "OK")
        cursor = GameFeedbackCursor(result)
        self.assertEqual(cursor.poll(589_999), ())
        self.assertEqual(cursor.poll(590_000), (GameFeedbackEvent(590_000, "OK"),))

    def test_too_early_null_has_no_press_feedback_and_retry_does_not_rewrite_first_action(self):
        result = replay((-200_000, 0))
        outcome = self.audit(result)
        self.assertEqual(outcome.category, FirstActionCategory.TOO_EARLY_NULL)
        self.assertEqual(outcome.first_down_us, 300_000)
        self.assertEqual(outcome.signed_error_us, -200_000)
        self.assertEqual(outcome.first_disposition, ActionDisposition.NULL_PRESS.value)
        self.assertEqual(outcome.extra_down_count, 1)
        self.assertEqual(outcome.final_judgement, "PERFECT")
        self.assertEqual(outcome.judgement_time_us, NOTE_TIME_US)
        cursor = GameFeedbackCursor(result)
        self.assertEqual(cursor.poll(300_000), ())
        self.assertEqual(cursor.poll(NOTE_TIME_US - 1), ())
        self.assertEqual(cursor.poll(NOTE_TIME_US),
                         (GameFeedbackEvent(NOTE_TIME_US, "PERFECT"),))

    def test_no_press_and_null_then_expiry_have_same_visible_result_but_distinct_audits(self):
        no_press = replay()
        null_then_no_retry = replay((-200_000,))
        no_press_cursor = GameFeedbackCursor(no_press)
        null_cursor = GameFeedbackCursor(null_then_no_retry)
        self.assertEqual(no_press_cursor.poll(EXPIRY_US - 1), ())
        self.assertEqual(null_cursor.poll(EXPIRY_US - 1), ())
        expiry_feedback = (GameFeedbackEvent(EXPIRY_US, "MISS"),)
        self.assertEqual(no_press_cursor.poll(EXPIRY_US), expiry_feedback)
        self.assertEqual(null_cursor.poll(EXPIRY_US), expiry_feedback)
        self.assertEqual(self.audit(no_press).category, FirstActionCategory.NO_DOWN)
        self.assertEqual(self.audit(null_then_no_retry).category,
                         FirstActionCategory.TOO_EARLY_NULL)
        self.assertEqual(self.audit(no_press).judgement_time_us, EXPIRY_US)

    def test_same_time_expiry_precedes_too_late_null_action(self):
        action = KeyAction(EXPIRY_US, 0, KeyActionKind.DOWN)
        result = play([NOTE], [action], CONFIG)
        self.assertEqual(result.events[0].event_time_us, EXPIRY_US)
        self.assertEqual(result.events[1].disposition, ActionDisposition.NULL_PRESS)
        outcome = self.audit(result)
        self.assertEqual(outcome.category, FirstActionCategory.LATE_NULL)
        self.assertEqual(outcome.first_down_us, EXPIRY_US)
        self.assertEqual(outcome.final_judgement, "MISS")
        cursor = GameFeedbackCursor(result)
        self.assertEqual(cursor.poll(EXPIRY_US),
                         (GameFeedbackEvent(EXPIRY_US, "MISS"),))

    def test_audit_rejects_unsorted_cues_and_bad_good_window(self):
        second = NoteCue("note-b", 1, 0, NOTE_TIME_US, EXPIRY_US)
        result = replay()
        with self.assertRaisesRegex(ValueError, "ordered"):
            reconstruct_first_actions((second, CUE), result, good_window_us=73_500)
        with self.assertRaisesRegex(ValueError, "positive"):
            reconstruct_first_actions((CUE,), result, good_window_us=0)

    def test_feedback_cursor_rejects_time_reversal(self):
        cursor = GameFeedbackCursor(replay((0,)))
        cursor.poll(NOTE_TIME_US)
        with self.assertRaisesRegex(ValueError, "backwards"):
            cursor.poll(NOTE_TIME_US - 1)

    def test_feedback_cursor_supports_signed_negative_game_timestamps(self):
        note_time_us = -100_000
        note = TapNote("negative-note", 0, note_time_us)
        result = play([note], [KeyAction(-260_000, 0, KeyActionKind.DOWN)], CONFIG)
        cursor = GameFeedbackCursor(result)
        self.assertEqual(cursor.poll(-260_001), ())
        self.assertEqual(cursor.poll(-260_000),
                         (GameFeedbackEvent(-260_000, "MISS"),))


if __name__ == "__main__":
    unittest.main()
