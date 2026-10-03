"""Tap-only osu!mania Score V2 accounting for the deterministic headless game."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
import math

from .config import OsuConfig
from .types import GameResult, JudgementRecord, TapNote


MAX_SCORE = 1_000_000
_ACCURACY_POINTS = {
    "PERFECT": 305,
    "GREAT": 300,
    "GOOD": 200,
    "OK": 100,
    "MEH": 50,
    "MISS": 0,
}
_COMBO_POINTS = {
    "PERFECT": 300,
    "GREAT": 300,
    "GOOD": 200,
    "OK": 100,
    "MEH": 50,
    "MISS": 0,
}


def _combo_multiplier(combo_after: int) -> float:
    if combo_after <= 0:
        # No Miss awards combo points, but return the processor's clamped scale.
        return 0.5
    return min(max(0.5, math.log(combo_after, 4)), math.log(400, 4))


def _score_without_mods(
    accuracy: float, combo_progress: float, accuracy_progress: float,
) -> int:
    value = (
        150_000 * combo_progress
        + 850_000 * math.pow(accuracy, 2 + 2 * accuracy) * accuracy_progress
    )
    # .NET Math.Round(double) and Python round(float) both use ties-to-even.
    return int(round(value))


@dataclass(frozen=True, slots=True)
class TapScoreEvent:
    note_id: str
    note_index: int
    hit_result: str
    base_accuracy_points: int
    maximum_accuracy_points: int
    combo_before: int
    combo_after: int
    highest_combo_after: int
    accuracy_numerator: int
    accuracy_denominator: int
    accuracy_judgement_count: int
    accuracy: float
    minimum_accuracy: float
    maximum_accuracy: float
    combo_score_portion: float
    total_score_without_mods: int
    total_score: int
    total_score_delta: int
    maximum_total_score: int
    maximum_combo: int

    def as_dict(self) -> dict[str, int | float | str]:
        return {
            "note_id": self.note_id,
            "note_index": self.note_index,
            "hit_result": self.hit_result,
            "result_max": "PERFECT",
            "base_accuracy_points": self.base_accuracy_points,
            "maximum_accuracy_points": self.maximum_accuracy_points,
            "combo_before": self.combo_before,
            "combo_after": self.combo_after,
            "highest_combo_after": self.highest_combo_after,
            "accuracy_numerator": self.accuracy_numerator,
            "accuracy_denominator": self.accuracy_denominator,
            "accuracy_judgement_count": self.accuracy_judgement_count,
            "accuracy": self.accuracy,
            "minimum_accuracy": self.minimum_accuracy,
            "maximum_accuracy": self.maximum_accuracy,
            "combo_score_portion": self.combo_score_portion,
            "total_score_without_mods": self.total_score_without_mods,
            "total_score": self.total_score,
            "total_score_delta": self.total_score_delta,
            "maximum_total_score": self.maximum_total_score,
            "maximum_combo": self.maximum_combo,
        }


@dataclass(frozen=True, slots=True)
class ManiaTapScore:
    """Completed no-mod Score V2 totals and the score state after each tap."""

    note_count: int
    total_score: int
    total_score_without_mods: int
    maximum_total_score: int
    accuracy: float
    accuracy_numerator: int
    accuracy_denominator: int
    minimum_accuracy: float
    maximum_accuracy: float
    accuracy_judgement_count: int
    combo: int
    highest_combo: int
    maximum_combo: int
    combo_score_portion: float
    maximum_combo_score_portion: float
    result_counts: tuple[tuple[str, int], ...]
    events: tuple[TapScoreEvent, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "ruleset": "lazer_mania_score_v2",
            "mods": [],
            "note_count": self.note_count,
            "total_score": self.total_score,
            "total_score_without_mods": self.total_score_without_mods,
            "maximum_total_score": self.maximum_total_score,
            "accuracy": self.accuracy,
            "accuracy_numerator": self.accuracy_numerator,
            "accuracy_denominator": self.accuracy_denominator,
            "minimum_accuracy": self.minimum_accuracy,
            "maximum_accuracy": self.maximum_accuracy,
            "accuracy_judgement_count": self.accuracy_judgement_count,
            "combo": self.combo,
            "highest_combo": self.highest_combo,
            "maximum_combo": self.maximum_combo,
            "combo_score_portion": self.combo_score_portion,
            "maximum_combo_score_portion": self.maximum_combo_score_portion,
            "result_counts": dict(self.result_counts),
            "events": [event.as_dict() for event in self.events],
        }


def calculate_tap_score(
    notes: Sequence[TapNote], game_result: GameResult, config: OsuConfig,
) -> ManiaTapScore:
    """Calculate no-mod lazer Score V2 for a fully resolved tap-only beatmap.

    This runs after judgement and must remain outside the policy input path.
    Holds, mods, partial plays, and non-lazer scoring profiles are rejected.
    """
    if config.ruleset != "lazer":
        raise ValueError("Score V2 tap scoring requires the lazer ruleset")
    if not notes or any(not isinstance(note, TapNote) for note in notes):
        raise ValueError("score calculation requires one or more tap notes")
    if game_result.total_notes != len(notes):
        raise ValueError("game result note count differs from the supplied beatmap")
    if len(game_result.judgements) != len(notes):
        raise ValueError("score calculation requires every tap note to be judged")

    note_by_id = {note.note_id: note for note in notes}
    if len(note_by_id) != len(notes):
        raise ValueError("beatmap note IDs must be unique")
    for judgement in game_result.judgements:
        note = note_by_id.get(judgement.note_id)
        if (note is None or judgement.lane != note.lane
                or judgement.note_time_us != note.time_us
                or judgement.ruleset != "lazer"):
            raise ValueError("game judgement does not match the supplied lazer tap beatmap")

    note_count = len(notes)
    maximum_points_per_note = _ACCURACY_POINTS["PERFECT"]
    maximum_accuracy_points = maximum_points_per_note * note_count
    maximum_combo_score_portion = sum(
        _COMBO_POINTS["PERFECT"] * _combo_multiplier(combo)
        for combo in range(1, note_count + 1)
    )

    numerator = 0
    denominator = 0
    accuracy_count = 0
    combo = 0
    highest_combo = 0
    combo_score_portion = 0.0
    previous_total_score = 0
    result_counts: Counter[str] = Counter()
    score_events: list[TapScoreEvent] = []

    for note_index, judgement in enumerate(game_result.judgements):
        hit_result = judgement.result_name
        if hit_result not in _ACCURACY_POINTS:
            raise ValueError(f"unsupported lazer mania tap result: {hit_result}")
        base_points = _ACCURACY_POINTS[hit_result]
        maximum_points = maximum_points_per_note
        result_counts[hit_result] += 1

        combo_before = combo
        if hit_result == "MISS":
            combo = 0
        else:
            combo += 1
        highest_combo = max(highest_combo, combo)

        numerator += base_points
        denominator += maximum_points
        accuracy_count += 1
        combo_score_portion += (
            _COMBO_POINTS[hit_result] * _combo_multiplier(combo)
        )

        accuracy = numerator / denominator if denominator else 1.0
        minimum_accuracy = numerator / maximum_accuracy_points
        maximum_accuracy = (
            numerator + maximum_accuracy_points - denominator
        ) / maximum_accuracy_points
        combo_progress = (
            combo_score_portion / maximum_combo_score_portion
            if maximum_combo_score_portion > 0 else 1.0
        )
        accuracy_progress = accuracy_count / note_count
        total_score_without_mods = _score_without_mods(
            accuracy, combo_progress, accuracy_progress)
        # The frozen vector has no score multiplier mods.
        total_score = total_score_without_mods
        score_events.append(TapScoreEvent(
            note_id=judgement.note_id,
            note_index=note_index,
            hit_result=hit_result,
            base_accuracy_points=base_points,
            maximum_accuracy_points=maximum_points,
            combo_before=combo_before,
            combo_after=combo,
            highest_combo_after=highest_combo,
            accuracy_numerator=numerator,
            accuracy_denominator=denominator,
            accuracy_judgement_count=accuracy_count,
            accuracy=accuracy,
            minimum_accuracy=minimum_accuracy,
            maximum_accuracy=maximum_accuracy,
            combo_score_portion=combo_score_portion,
            total_score_without_mods=total_score_without_mods,
            total_score=total_score,
            total_score_delta=total_score - previous_total_score,
            maximum_total_score=MAX_SCORE,
            maximum_combo=note_count,
        ))
        previous_total_score = total_score

    last = score_events[-1]
    return ManiaTapScore(
        note_count=note_count,
        total_score=last.total_score,
        total_score_without_mods=last.total_score_without_mods,
        maximum_total_score=MAX_SCORE,
        accuracy=last.accuracy,
        accuracy_numerator=last.accuracy_numerator,
        accuracy_denominator=last.accuracy_denominator,
        minimum_accuracy=last.minimum_accuracy,
        maximum_accuracy=last.maximum_accuracy,
        accuracy_judgement_count=last.accuracy_judgement_count,
        combo=last.combo_after,
        highest_combo=last.highest_combo_after,
        maximum_combo=note_count,
        combo_score_portion=last.combo_score_portion,
        maximum_combo_score_portion=maximum_combo_score_portion,
        result_counts=tuple(sorted(result_counts.items())),
        events=tuple(score_events),
    )
