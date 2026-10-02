"""Causal game/first-action/feedback owner used at committed tick boundaries."""

from __future__ import annotations

from dataclasses import asdict

from project_b.osu.environment import GameEnvironment
from project_b.osu.types import ActionDisposition, KeyAction, KeyActionKind, TapNote
from project_b.utils.time import require_time_us

from .feedback import FeedbackScheduler, FirstActionTracker, NoteWindow


class MvpTaskSession:
    """Tracks first actions and PAM requests; no artificial pulse is a DAN spike."""

    def __init__(self, notes: tuple[NoteWindow, ...], *, teaching_enabled: bool = True):
        self.notes = notes
        self.teaching_enabled = teaching_enabled
        self.game = GameEnvironment(tuple(TapNote(n.note_id, 0, n.hit_us) for n in notes))
        self.first_action = FirstActionTracker(notes)
        self.feedback = FeedbackScheduler(enabled=teaching_enabled)
        self.time_us = 0
        self.next_onset_index = 0

    def advance_to(self, time_us: int) -> None:
        require_time_us(time_us)
        if time_us < self.time_us:
            raise ValueError("task clock reversal")
        while (self.next_onset_index < len(self.notes)
               and self.notes[self.next_onset_index].visible_from_us <= time_us):
            note = self.notes[self.next_onset_index]
            # Expiry and previously scheduled feedback precede this onset.
            self.game.advance_to(note.visible_from_us)
            self.feedback.advance_to(note.visible_from_us)
            previous = self.first_action.on_visible_onset(
                note.note_id, note.visible_from_us)
            if previous is not None and previous.category == "no_down":
                self.feedback.resolve(previous, note.visible_from_us)
            self.feedback.on_visible_onset(note.visible_from_us)
            self.next_onset_index += 1
        self.game.advance_to(time_us)
        self.feedback.advance_to(time_us)
        self.time_us = time_us

    def apply_action(self, action: KeyAction) -> None:
        self.advance_to(action.time_us)
        record = self.game.apply_action(action)
        if action.lane == 0 and action.kind is KeyActionKind.DOWN and \
                record.disposition is not ActionDisposition.REPEAT_DOWN:
            outcome = self.first_action.on_down(action.time_us, record.disposition)
            if outcome is not None:
                self.feedback.resolve(outcome, action.time_us)

    def state(self) -> dict:
        return {"identity": {"notes": [asdict(n) for n in self.notes],
                             "teaching_enabled": self.teaching_enabled},
                "time_us": self.time_us,
                "next_onset_index": self.next_onset_index,
                "game": self.game.state(),
                "first_action": self.first_action.state(),
                "feedback": self.feedback.state()}

    def restore(self, state: dict) -> None:
        """Restore all task owners together after validating the complete state."""
        if set(state) != set(self.state()) or state["identity"] != self.state()["identity"]:
            raise ValueError("task checkpoint identity differs")
        clone = MvpTaskSession(self.notes, teaching_enabled=self.teaching_enabled)
        clone.game.restore(state["game"])
        clone.first_action.restore(state["first_action"])
        clone.feedback.restore(state["feedback"])
        t, cursor = state["time_us"], state["next_onset_index"]
        if (type(t) is not int or t < 0 or type(cursor) is not int
                or not 0 <= cursor <= len(self.notes)
                or clone.game.current_time_us != t
                or clone.first_action.next_note_index != cursor
                or clone.feedback.last_time_us > t
                or any(n.visible_from_us <= t for n in self.notes[cursor:])
                or any(n.visible_from_us > t for n in self.notes[:cursor])):
            raise ValueError("task owners or cue cursor are not synchronized")
        clone.time_us = t
        clone.next_onset_index = cursor
        self.__dict__.update(clone.__dict__)
