"""Causal, score-only feedback boundary and evaluator-only action audit."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

from project_b.utils.time import require_time_us

from .types import (
    ActionDisposition,
    GameResult,
    JudgementRecord,
    KeyActionKind,
    require_lane,
)


class FirstActionCategory(str, Enum):
    GOOD_OR_BETTER = "good_or_better"
    TOO_EARLY_NULL = "too_early_null"
    EARLY_JUDGED = "early_judged"
    EARLY_JUDGED_MISS = "early_judged_miss"
    LATE_JUDGED = "late_judged"
    LATE_NULL = "late_null"
    NO_DOWN = "no_down"


@dataclass(frozen=True, slots=True)
class GameFeedbackEvent:
    """Result label available to the reinforcement orchestrator.

    Deliberately excludes note identity, scheduled note time, signed hit error,
    action disposition, and any derived target timing.
    """

    available_at_us: int
    judgement_label: str

    def __post_init__(self) -> None:
        require_time_us(self.available_at_us, "available_at_us")
        if not isinstance(self.judgement_label, str) or not self.judgement_label:
            raise ValueError("judgement_label must be a nonempty string")


@dataclass(frozen=True, slots=True)
class NoteCue:
    """Evaluator-only presentation window for reconstructing first actions."""

    note_id: str
    lane: int
    visible_from_us: int
    note_time_us: int
    visible_until_us: int

    def __post_init__(self) -> None:
        if not isinstance(self.note_id, str) or not self.note_id:
            raise ValueError("note_id must be a nonempty string")
        require_lane(self.lane)
        require_time_us(self.visible_from_us, "visible_from_us")
        require_time_us(self.note_time_us, "note_time_us")
        require_time_us(self.visible_until_us, "visible_until_us")
        if (self.visible_from_us > self.note_time_us
                or self.visible_until_us < self.note_time_us
                or self.visible_until_us < self.visible_from_us):
            raise ValueError("note cue must cover the note time")


@dataclass(frozen=True, slots=True)
class FirstActionAuditOutcome:
    """Hidden evaluator record; never pass this record to the fly policy."""

    note_id: str
    lane: int
    note_time_us: int
    first_down_us: int | None
    signed_error_us: int | None
    first_disposition: str | None
    category: FirstActionCategory
    extra_down_count: int
    final_judgement: str | None
    judgement_time_us: int | None


def game_feedback_for_judgement(record: JudgementRecord) -> GameFeedbackEvent:
    """Strip a game judgement to the result and the time it becomes available."""
    if not isinstance(record, JudgementRecord):
        raise TypeError("record must be a JudgementRecord")
    return GameFeedbackEvent(record.logical_event_time_us, record.result_name)


def _project_feedback(result: GameResult) -> tuple[GameFeedbackEvent, ...]:
    """Project a chronological raw event ledger onto visible result events.

    Null key actions generate no result event. An automatic miss is published
    only when the game engine emits its expiry judgement, not when the note is
    first shown or when an out-of-window key-down occurs.
    """
    if not isinstance(result, GameResult):
        raise TypeError("result must be a GameResult")
    feedback: list[GameFeedbackEvent] = []
    previous_time_us: int | None = None
    for event in result.events:
        if isinstance(event, JudgementRecord):
            if (previous_time_us is not None
                    and event.logical_event_time_us < previous_time_us):
                raise ValueError("game events must be chronological")
            feedback.append(game_feedback_for_judgement(event))
            previous_time_us = event.logical_event_time_us
        else:
            event_time_us = event.action.time_us
            if (previous_time_us is not None
                    and event_time_us < previous_time_us):
                raise ValueError("game events must be chronological")
            previous_time_us = event_time_us
    return tuple(feedback)


class GameFeedbackCursor:
    """Deliver result labels to reinforcement only when they become available.

    This cursor is the reinforcement-facing interface. It never returns a later
    judgement early, even when constructed from a complete offline result.
    The full projection remains private to this object.
    """

    __slots__ = ("__pending", "__offset", "__last_time_us")

    def __init__(self, result: GameResult) -> None:
        self.__pending = _project_feedback(result)
        self.__offset = 0
        self.__last_time_us: int | None = None

    def poll(self, time_us: int) -> tuple[GameFeedbackEvent, ...]:
        """Return each newly observable game result once, in event order."""
        require_time_us(time_us, "time_us")
        if self.__last_time_us is not None and time_us < self.__last_time_us:
            raise ValueError("feedback cursor time cannot move backwards")
        self.__last_time_us = time_us
        start = self.__offset
        while (self.__offset < len(self.__pending)
               and self.__pending[self.__offset].available_at_us <= time_us):
            self.__offset += 1
        return self.__pending[start:self.__offset]


def reconstruct_first_actions(
    cues: Sequence[NoteCue], result: GameResult, *, good_window_us: int,
) -> tuple[FirstActionAuditOutcome, ...]:
    """Reconstruct first DOWN per cue using schedule data for evaluation only.

    When cue windows overlap on one lane, an action belongs to the most
    recently visible cue. Repeated DOWN while a key remains held is not a new
    first action. No timing information from this result is sent to the policy.
    """
    if not cues or len({cue.note_id for cue in cues}) != len(cues):
        raise ValueError("audit requires unique note cues")
    if type(good_window_us) is not int or good_window_us <= 0:
        raise ValueError("good_window_us must be a positive integer")
    if not isinstance(result, GameResult):
        raise TypeError("result must be a GameResult")
    ordered = tuple(sorted(cues, key=lambda cue: (cue.lane, cue.visible_from_us,
                                                   cue.note_id)))
    if tuple(cues) != ordered:
        raise ValueError("note cues must be ordered by lane and visibility onset")

    downs_by_id: dict[str, list] = {cue.note_id: [] for cue in cues}
    cues_by_lane: dict[int, list[NoteCue]] = {}
    for cue in cues:
        cues_by_lane.setdefault(cue.lane, []).append(cue)

    for action_record in result.actions:
        action = action_record.action
        if action.kind is not KeyActionKind.DOWN:
            continue
        if action_record.disposition is ActionDisposition.REPEAT_DOWN:
            continue
        eligible = [cue for cue in cues_by_lane.get(action.lane, ())
                    if cue.visible_from_us <= action.time_us <= cue.visible_until_us]
        if not eligible:
            continue
        cue = max(eligible, key=lambda item: (item.visible_from_us, item.note_id))
        downs_by_id[cue.note_id].append(action_record)

    judgements_by_id = {record.note_id: record for record in result.judgements}
    outcomes: list[FirstActionAuditOutcome] = []
    for cue in cues:
        downs = downs_by_id[cue.note_id]
        first = downs[0] if downs else None
        judgement = judgements_by_id.get(cue.note_id)
        if first is None:
            error_us = None
            disposition = None
            category = FirstActionCategory.NO_DOWN
        else:
            error_us = first.action.time_us - cue.note_time_us
            disposition = first.disposition
            if abs(error_us) <= good_window_us:
                category = FirstActionCategory.GOOD_OR_BETTER
            elif error_us < 0:
                if disposition is ActionDisposition.NULL_PRESS:
                    category = FirstActionCategory.TOO_EARLY_NULL
                elif disposition is ActionDisposition.EARLY_MISS:
                    category = FirstActionCategory.EARLY_JUDGED_MISS
                else:
                    category = FirstActionCategory.EARLY_JUDGED
            elif (judgement is not None and judgement.hit_error_us is not None
                  and judgement.logical_event_time_us == first.action.time_us):
                category = FirstActionCategory.LATE_JUDGED
            else:
                category = FirstActionCategory.LATE_NULL
        outcomes.append(FirstActionAuditOutcome(
            cue.note_id, cue.lane, cue.note_time_us,
            None if first is None else first.action.time_us,
            error_us,
            None if disposition is None else disposition.value,
            category,
            max(0, len(downs) - 1),
            None if judgement is None else judgement.result_name,
            None if judgement is None else judgement.logical_event_time_us,
        ))
    return tuple(outcomes)
