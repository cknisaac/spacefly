"""Game-domain records. No learning or biological reward is defined here."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum

from project_b.utils.time import INT64_MAX, INT64_MIN, require_time_us


def require_lane(lane: int) -> int:
    """M0 uses zero-based 4K lanes 0, 1, 2, and 3."""
    if type(lane) is not int or not 0 <= lane < 4:
        raise ValueError("lane must be an integer in 0..3")
    return lane


class ManiaJudgement(IntEnum):
    """Canonical hit value; this is not reward, score, or accuracy."""

    MISS = 0
    MEH_50 = 50
    OK_100 = 100
    GOOD_200 = 200
    GREAT_300 = 300
    MAX_320 = 320


class KeyActionKind(str, Enum):
    DOWN = "down"
    UP = "up"


class ActionDisposition(str, Enum):
    HIT = "hit"
    EARLY_MISS = "early_miss"
    NULL_PRESS = "null_press"
    RELEASE = "release"
    REPEAT_DOWN = "repeat_down"
    REPEAT_UP = "repeat_up"


@dataclass(frozen=True, slots=True)
class TapNote:
    note_id: str
    lane: int
    time_us: int

    def __post_init__(self) -> None:
        if not isinstance(self.note_id, str) or not self.note_id:
            raise ValueError("note_id must be a nonempty string")
        require_lane(self.lane)
        require_time_us(self.time_us)


@dataclass(frozen=True, slots=True)
class HoldNote:
    """Represented for validation; M0 deliberately rejects hold-note maps."""

    note_id: str
    lane: int
    time_us: int
    end_time_us: int

    def __post_init__(self) -> None:
        if not isinstance(self.note_id, str) or not self.note_id:
            raise ValueError("note_id must be a nonempty string")
        require_lane(self.lane)
        require_time_us(self.time_us)
        require_time_us(self.end_time_us, "end_time_us")
        if self.end_time_us <= self.time_us:
            raise ValueError("hold-note end_time_us must exceed time_us")


@dataclass(frozen=True, slots=True)
class KeyAction:
    time_us: int
    lane: int
    kind: KeyActionKind

    def __post_init__(self) -> None:
        require_time_us(self.time_us)
        require_lane(self.lane)
        if not isinstance(self.kind, KeyActionKind):
            raise ValueError("kind must be KeyActionKind.DOWN or KeyActionKind.UP")


@dataclass(frozen=True, slots=True)
class JudgementRecord:
    note_id: str
    lane: int
    note_time_us: int
    event_time_us: int
    judgement: ManiaJudgement
    hit_error_us: int | None  # None means automatic expiry, not an attempted hit.


@dataclass(frozen=True, slots=True)
class ActionRecord:
    action: KeyAction
    disposition: ActionDisposition
    note_id: str | None


@dataclass(frozen=True, slots=True)
class GameResult:
    judgements: tuple[JudgementRecord, ...]
    actions: tuple[ActionRecord, ...]
    events: tuple[JudgementRecord | ActionRecord, ...]
    key_down: tuple[bool, bool, bool, bool]
    total_notes: int

    @property
    def resolved_notes(self) -> int:
        return len(self.judgements)

    @property
    def null_presses(self) -> int:
        return sum(record.disposition is ActionDisposition.NULL_PRESS for record in self.actions)
