"""Full game-state behavior at exact boundaries and simultaneous lanes."""

import random
import unittest

from project_b.osu import (
    ActionDisposition,
    GameEnvironment,
    HoldNote,
    KeyAction,
    KeyActionKind,
    ManiaJudgement,
    OsuConfig,
    TapNote,
    play,
)
from project_b.osu.types import INT64_MAX

NOTE_TIME = 1_000_000


def down(time_us: int, lane: int = 0) -> KeyAction:
    return KeyAction(time_us, lane, KeyActionKind.DOWN)


def up(time_us: int, lane: int = 0) -> KeyAction:
    return KeyAction(time_us, lane, KeyActionKind.UP)


def single_press(error_us: int):
    return play([TapNote("n", 0, NOTE_TIME)], [down(NOTE_TIME + error_us)])


class EnvironmentTests(unittest.TestCase):
    def test_canonical_boundary_examples_both_sides(self) -> None:
        for magnitude_ms, expected_early, expected_late in [
            (0, ManiaJudgement.MAX_320, ManiaJudgement.MAX_320),
            (15, ManiaJudgement.MAX_320, ManiaJudgement.MAX_320),
            (16, ManiaJudgement.MAX_320, ManiaJudgement.MAX_320),
            (17, ManiaJudgement.GREAT_300, ManiaJudgement.GREAT_300),
            (39, ManiaJudgement.GREAT_300, ManiaJudgement.GREAT_300),
            (40, ManiaJudgement.GREAT_300, ManiaJudgement.GREAT_300),
            (41, ManiaJudgement.GOOD_200, ManiaJudgement.GOOD_200),
            (73, ManiaJudgement.GOOD_200, ManiaJudgement.GOOD_200),
            (74, ManiaJudgement.OK_100, ManiaJudgement.OK_100),
            (103, ManiaJudgement.OK_100, ManiaJudgement.OK_100),
            (104, ManiaJudgement.MEH_50, ManiaJudgement.MISS),
            (127, ManiaJudgement.MEH_50, ManiaJudgement.MISS),
            (128, ManiaJudgement.MISS, ManiaJudgement.MISS),
            (164, ManiaJudgement.MISS, ManiaJudgement.MISS),
        ]:
            for sign, expected in ((-1, expected_early), (1, expected_late)):
                with self.subTest(error_ms=magnitude_ms * sign):
                    result = single_press(sign * magnitude_ms * 1000)
                    self.assertEqual(result.judgements[0].judgement, expected)
                    self.assertEqual(result.total_notes, 1)

    def test_late_expiry_first_invalid_microsecond(self) -> None:
        on_time = single_press(103_499)
        self.assertEqual(on_time.judgements[0].judgement, ManiaJudgement.OK_100)
        self.assertEqual(on_time.judgements[0].event_time_us, NOTE_TIME + 103_499)
        expired = single_press(103_500)
        self.assertEqual(expired.judgements[0].judgement, ManiaJudgement.MISS)
        self.assertEqual(expired.judgements[0].event_time_us, NOTE_TIME + 103_500)
        self.assertIsNone(expired.judgements[0].hit_error_us)
        self.assertEqual(expired.actions[0].disposition, ActionDisposition.NULL_PRESS)
        self.assertEqual(type(expired.events[0]).__name__, "JudgementRecord")

    def test_early_miss_vs_null_press(self) -> None:
        early_miss = single_press(-164_500)
        self.assertEqual(early_miss.judgements[0].hit_error_us, -164_500)
        self.assertEqual(early_miss.actions[0].disposition, ActionDisposition.EARLY_MISS)
        too_early = single_press(-164_501)
        self.assertEqual(too_early.actions[0].disposition, ActionDisposition.NULL_PRESS)
        self.assertEqual(too_early.judgements[0].event_time_us, NOTE_TIME + 103_500)
        self.assertIsNone(too_early.judgements[0].hit_error_us)

    def test_key_state_requires_release_for_retrigger(self) -> None:
        notes = [TapNote("one", 0, NOTE_TIME), TapNote("two", 0, NOTE_TIME + 200_000)]
        held = play(notes, [down(NOTE_TIME), down(NOTE_TIME + 200_000)])
        self.assertEqual([j.judgement for j in held.judgements],
                         [ManiaJudgement.MAX_320, ManiaJudgement.MISS])
        self.assertEqual(held.actions[1].disposition, ActionDisposition.REPEAT_DOWN)
        retriggered = play(notes, [down(NOTE_TIME), up(NOTE_TIME + 1),
                                   down(NOTE_TIME + 200_000)])
        self.assertEqual([j.judgement for j in retriggered.judgements],
                         [ManiaJudgement.MAX_320, ManiaJudgement.MAX_320])
        self.assertEqual(retriggered.key_down, (True, False, False, False))

    def test_repeated_release_and_null_press_are_not_misses(self) -> None:
        result = play([], [up(0), down(1), up(2), up(3)])
        self.assertEqual(result.total_notes, 0)
        self.assertEqual(result.null_presses, 1)
        self.assertEqual([a.disposition for a in result.actions],
                         [ActionDisposition.REPEAT_UP, ActionDisposition.NULL_PRESS,
                          ActionDisposition.RELEASE, ActionDisposition.REPEAT_UP])

    def test_four_lane_chord_independent_judgements(self) -> None:
        notes = [TapNote(f"n{lane}", lane, NOTE_TIME) for lane in range(4)]
        result = play(notes, [down(NOTE_TIME, lane) for lane in (3, 0, 2, 1)])
        self.assertEqual({j.note_id: j.judgement for j in result.judgements},
                         {f"n{lane}": ManiaJudgement.MAX_320 for lane in range(4)})
        self.assertEqual([a.action.lane for a in result.actions], [3, 0, 2, 1])
        self.assertEqual(result.key_down, (True, True, True, True))

    def test_missed_lane_does_not_block_other_lanes(self) -> None:
        notes = [TapNote("left", 0, NOTE_TIME), TapNote("right", 3, NOTE_TIME)]
        result = play(notes, [down(NOTE_TIME, 3)])
        by_id = {j.note_id: j for j in result.judgements}
        self.assertEqual(by_id["right"].judgement, ManiaJudgement.MAX_320)
        self.assertEqual(by_id["left"].judgement, ManiaJudgement.MISS)
        self.assertEqual(by_id["left"].event_time_us, NOTE_TIME + 103_500)

    def test_expiry_precedes_other_lane_action_at_same_timestamp(self) -> None:
        deadline = NOTE_TIME + 103_500
        result = play([TapNote("old", 0, NOTE_TIME), TapNote("now", 1, deadline)],
                      [down(deadline, 1)])
        self.assertEqual([(j.note_id, j.judgement) for j in result.judgements],
                         [("old", ManiaJudgement.MISS),
                          ("now", ManiaJudgement.MAX_320)])

    def test_profile_choice_changes_actual_game_judgement(self) -> None:
        notes = [TapNote("n", 0, NOTE_TIME)]
        actions = [down(NOTE_TIME + 35_000)]
        native = play(notes, actions, OsuConfig(od=8, ruleset="stable_native"))
        converted = play(notes, actions, OsuConfig(od=8, ruleset="stable_convert"))
        self.assertEqual(native.judgements[0].judgement, ManiaJudgement.GREAT_300)
        self.assertEqual(converted.judgements[0].judgement, ManiaJudgement.GOOD_200)

    def test_earliest_unresolved_note_has_lane_priority(self) -> None:
        notes = [TapNote("old", 0, NOTE_TIME), TapNote("new", 0, NOTE_TIME + 100_000)]
        # Both windows are open; the old note is chosen before the newer one.
        result = play(notes, [down(NOTE_TIME + 50_000), up(NOTE_TIME + 50_000),
                              down(NOTE_TIME + 50_000)])
        self.assertEqual(result.judgements[0].note_id, "old")
        self.assertEqual(result.judgements[1].note_id, "new")
        self.assertEqual(result.actions[-1].disposition, ActionDisposition.HIT)

    def test_next_note_outside_early_miss_window_is_null(self) -> None:
        notes = [TapNote("old", 0, NOTE_TIME), TapNote("new", 0, NOTE_TIME + 200_000)]
        result = play(notes, [down(NOTE_TIME), up(NOTE_TIME), down(NOTE_TIME)])
        self.assertEqual(result.actions[-1].disposition, ActionDisposition.NULL_PRESS)
        self.assertEqual(result.judgements[-1].note_id, "new")
        self.assertEqual(result.judgements[-1].judgement, ManiaJudgement.MISS)

    def test_expired_old_note_frees_new_same_lane_note(self) -> None:
        notes = [TapNote("old", 0, NOTE_TIME), TapNote("new", 0, NOTE_TIME + 150_000)]
        result = play(notes, [down(NOTE_TIME + 150_000)])
        self.assertEqual([(j.note_id, j.judgement) for j in result.judgements],
                         [("old", ManiaJudgement.MISS), ("new", ManiaJudgement.MAX_320)])

    def test_incremental_time_and_result_snapshot(self) -> None:
        env = GameEnvironment([TapNote("n", 0, NOTE_TIME)])
        env.advance_to(NOTE_TIME)
        self.assertEqual(env.result().total_notes, 1)
        self.assertEqual(env.result().resolved_notes, 0)
        env.apply_action(down(NOTE_TIME))
        self.assertEqual(env.result().resolved_notes, 1)
        with self.assertRaises(ValueError):
            env.advance_to(NOTE_TIME - 1)
        self.assertEqual(env.finish(), env.finish())

    def test_no_action_expiry_and_signed_negative_input_time(self) -> None:
        missed = play([TapNote("n", 0, 0)], [])
        self.assertEqual(missed.judgements[0].event_time_us, 103_500)
        self.assertEqual(missed.judgements[0].judgement, ManiaJudgement.MISS)
        early = play([TapNote("n", 0, 0)], [down(-16_000)])
        self.assertEqual(early.judgements[0].judgement, ManiaJudgement.MAX_320)
        self.assertEqual(early.judgements[0].hit_error_us, -16_000)

    def test_replay_determinism_with_unsorted_actions(self) -> None:
        notes = [TapNote("a", 0, NOTE_TIME), TapNote("b", 1, NOTE_TIME)]
        actions = [down(NOTE_TIME, 1), down(NOTE_TIME, 0), up(NOTE_TIME + 1, 0)]
        self.assertEqual(play(notes, actions), play(list(reversed(notes)), actions))
        self.assertEqual(play(notes, actions), play(notes, actions))

    def test_hold_and_invalid_input_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "rejects hold"):
            GameEnvironment([HoldNote("h", 0, 1000, 2000)])
        for notes in ([TapNote("a", 0, 0), TapNote("a", 1, 0)],
                      [TapNote("a", 0, 0), TapNote("b", 0, 0)]):
            with self.subTest(notes=notes), self.assertRaises(ValueError):
                GameEnvironment(notes)
        with self.assertRaises(ValueError):
            TapNote("bad", 4, 0)
        with self.assertRaises(ValueError):
            TapNote("bad", 0, 1.5)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            KeyAction(0, 0, "down")  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            GameEnvironment([TapNote("far", 0, INT64_MAX)])

    def test_randomized_event_invariants_and_replay(self) -> None:
        rng = random.Random(314159)
        notes = [TapNote(f"n{i}", i % 4, 1_000_000 + 175_000 * i)
                 for i in range(160)]
        actions = []
        for note in notes:
            error = rng.randint(-180_000, 140_000)
            actions.extend((down(note.time_us + error, note.lane),
                            up(note.time_us + error + 1, note.lane)))
        result = play(notes, actions)
        self.assertEqual(result, play(notes, actions))
        self.assertEqual(result.total_notes, len(notes))
        self.assertEqual(result.resolved_notes, len(notes))
        self.assertEqual({j.note_id for j in result.judgements}, {n.note_id for n in notes})
        self.assertEqual(len(result.judgements), len(notes))
        self.assertEqual([e.event_time_us if hasattr(e, "event_time_us") else e.action.time_us
                          for e in result.events],
                         sorted(e.event_time_us if hasattr(e, "event_time_us") else e.action.time_us
                                for e in result.events))


if __name__ == "__main__":
    unittest.main()
