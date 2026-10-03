"""Independent first-action reconstruction and primary metric invariants."""

from __future__ import annotations

import json
import unittest
from copy import deepcopy
from pathlib import Path

from project_b.mvp_c1.feedback import NoteWindow
from project_b.mvp_c1.first_action_audit import (
    compare_owner_outcomes, game_events_from_mvp_ledger, reconstruct_first_actions)
from project_b.mvp_c1.task_session import MvpTaskSession
from project_b.osu.types import KeyAction, KeyActionKind


ROOT = Path(__file__).resolve().parents[1]
NOTES = (NoteWindow("n1", 100_000, 900_000),
         NoteWindow("n2", 1_300_000, 2_100_000))


def checked_task(notes, actions, end_us):
    owner = MvpTaskSession(notes)
    for time_us, kind in actions:
        owner.apply_action(KeyAction(time_us, 0, KeyActionKind(kind)))
    owner.advance_to(end_us)
    audit = reconstruct_first_actions(notes, owner.game.state()["events"], end_us)
    owner.first_action.finish(end_us)
    compare_owner_outcomes(audit, owner.first_action.outcomes)
    return audit, owner


class FirstActionAuditTests(unittest.TestCase):
    def test_saved_a2_raw_ledger_null_then_scored_miss(self):
        path = ROOT / "docs/figures/a2_mvp_coupled/uninterrupted_ledger.json"
        ledger = json.loads(path.read_text(encoding="utf-8"))
        events = game_events_from_mvp_ledger(ledger)
        notes = (NoteWindow("replay-1", 100_000, 900_000),)
        audit = reconstruct_first_actions(notes, events, 1_100_000)
        row = audit.rows[0]
        self.assertEqual((row.first_down_us, row.signed_error_us,
                          row.category, row.extra_downs),
                         (190_000, -710_000, "too_early_null", 3))
        self.assertEqual(row.game_judgements[0]["judgement"], 50)
        self.assertEqual(audit.summary["first_down_success_rate"], 0.0)
        self.assertEqual(audit.summary["secondary_positive_judgement_notes"], 1)
        owner = MvpTaskSession(notes)
        for event in events:
            if event["kind"] == "action":
                action = event["record"]["action"]
                owner.apply_action(KeyAction(action["time_us"], action["lane"],
                                             KeyActionKind(action["kind"])))
        owner.advance_to(1_100_000)
        self.assertEqual(owner.game.state()["events"], events)
        owner.first_action.finish(1_100_000)
        compare_owner_outcomes(audit, owner.first_action.outcomes)

    def test_later_good_press_does_not_rescue_first_and_no_down_counts(self):
        audit, _ = checked_task(NOTES,
                                [(190_000, "down"), (220_000, "up"),
                                 (900_000, "down"), (930_000, "up")],
                                2_250_000)
        self.assertEqual([r.category for r in audit.rows],
                         ["too_early_null", "no_down"])
        self.assertEqual(audit.rows[0].extra_downs, 1)
        self.assertEqual(audit.rows[0].later_actions[1].time_us, 900_000)
        self.assertEqual(audit.summary["eligible_note_denominator"], 2)
        self.assertEqual(audit.summary["missing_action_count"], 1)
        self.assertEqual(audit.summary["first_down_success_count"], 0)
        self.assertEqual(audit.summary["secondary_positive_judgement_notes"], 1)

    def test_expiry_precedes_same_time_action_but_cue_scope_persists(self):
        expiry_us = 1_003_500
        audit, owner = checked_task(NOTES, [(expiry_us, "down"),
                                            (expiry_us + 1_000, "up")], 2_250_000)
        self.assertEqual(owner.game.state()["events"][0]["kind"], "judgement")
        self.assertEqual(owner.game.state()["events"][0]["record"]["logical_event_time_us"],
                         expiry_us)
        self.assertEqual((audit.rows[0].first_down_us, audit.rows[0].category,
                          audit.rows[0].first_disposition),
                         (expiry_us, "late", "null_press"))
        self.assertEqual(audit.rows[1].category, "no_down")

    def test_next_onset_tie_assigns_new_cue_and_repeated_down_is_not_extra(self):
        audit, _ = checked_task(NOTES, [(1_300_000, "down"),
                                        (1_300_000, "down")], 1_400_000)
        self.assertEqual(audit.rows[0].category, "no_down")
        self.assertEqual(audit.rows[1].first_down_us, 1_300_000)
        self.assertEqual(audit.rows[1].extra_downs, 0)
        self.assertEqual(audit.rows[1].scoped_actions[1].disposition, "repeat_down")

    def test_inclusive_primary_window_uses_first_down_only(self):
        early, _ = checked_task((NOTES[0],), [(827_000, "down")], 1_100_000)
        late, _ = checked_task((NOTES[0],), [(973_000, "down")], 1_100_000)
        outside, _ = checked_task((NOTES[0],), [(826_999, "down")], 1_100_000)
        self.assertEqual((early.rows[0].category, late.rows[0].category),
                         ("success", "success"))
        self.assertEqual(outside.rows[0].category, "early_judged")
        self.assertEqual(outside.summary["first_down_success_rate"], 0.0)

    def test_before_first_cue_and_simultaneous_cues_fail_closed(self):
        audit, _ = checked_task((NOTES[0],),
                                [(10_000, "down"), (20_000, "up")], 1_100_000)
        self.assertEqual(audit.rows[0].category, "no_down")
        self.assertEqual(audit.summary["background_action_count"], 2)
        simultaneous = (NoteWindow("a", 100_000, 900_000),
                        NoteWindow("b", 100_000, 900_000))
        with self.assertRaisesRegex(ValueError, "isolated"):
            reconstruct_first_actions(simultaneous, [], 1_000_000)
        with self.assertRaisesRegex(ValueError, "incomplete"):
            reconstruct_first_actions((NOTES[0],), [], 950_000)

    def test_raw_event_tamper_is_rejected(self):
        audit, owner = checked_task((NOTES[0],), [(900_000, "down")], 1_100_000)
        self.assertTrue(audit.rows[0].primary_success)
        events = deepcopy(owner.game.state()["events"])
        events[0]["record"]["note_time_us"] += 1
        with self.assertRaisesRegex(ValueError, "judgement contradicts"):
            reconstruct_first_actions((NOTES[0],), events, 1_100_000)


if __name__ == "__main__":
    unittest.main()
