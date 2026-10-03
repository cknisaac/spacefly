"""Declared artificial game-label to DAN teaching boundary for EA-MVP."""

from __future__ import annotations

from dataclasses import dataclass

from project_b.osu.feedback import GameFeedbackEvent


@dataclass(frozen=True, slots=True)
class DanPulse:
    """ENGINEERING ASSUMPTION: artificial current delivered to selected DANs."""

    onset_us: int
    duration_us: int
    amplitude_mv_equivalent: float
    dan_source_ids: tuple[int, ...]
    source_label: str
    source_available_at_us: int


class JudgementDanAdapter:
    """Use only a resolved label and its availability time, never hidden error."""

    def __init__(self, *, dt_us: int, dan_source_ids: tuple[int, ...],
                 amplitude_mv_equivalent: float, duration_us: int,
                 pulse_labels: frozenset[str]) -> None:
        if type(dt_us) is not int or dt_us <= 0:
            raise ValueError("dt_us must be positive")
        if not dan_source_ids or len(set(dan_source_ids)) != len(dan_source_ids):
            raise ValueError("DAN source IDs must be a unique nonempty tuple")
        if amplitude_mv_equivalent <= 0 or duration_us <= 0 or duration_us % dt_us:
            raise ValueError("pulse amplitude/duration must be positive and tick aligned")
        allowed = {"PERFECT", "GREAT", "GOOD", "OK", "MEH", "MISS"}
        if not pulse_labels or not pulse_labels <= allowed:
            raise ValueError("pulse_labels must be a nonempty subset of tap judgements")
        self.dt_us = dt_us
        self.dan_source_ids = dan_source_ids
        self.amplitude_mv_equivalent = amplitude_mv_equivalent
        self.duration_us = duration_us
        self.pulse_labels = pulse_labels

    def translate(self, event: GameFeedbackEvent, *, observed_at_us: int) -> DanPulse | None:
        if not isinstance(event, GameFeedbackEvent):
            raise TypeError("teacher input must be a stripped GameFeedbackEvent")
        if type(observed_at_us) is not int or observed_at_us < event.available_at_us:
            raise ValueError("cannot teach before the game result is available")
        allowed = {"PERFECT", "GREAT", "GOOD", "OK", "MEH", "MISS"}
        if event.judgement_label not in allowed:
            raise ValueError("unknown tap judgement label")
        if event.judgement_label not in self.pulse_labels:
            return None
        onset_us = ((observed_at_us + self.dt_us - 1) // self.dt_us) * self.dt_us
        return DanPulse(onset_us, self.duration_us, self.amplitude_mv_equivalent,
                        self.dan_source_ids, event.judgement_label,
                        event.available_at_us)
