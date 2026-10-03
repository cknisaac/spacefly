"""Judgement, utility, prediction error and modulation as distinct stages.

This module reads an already produced game judgement. It never computes a
game score or touches a neural simulator, synapse, or plasticity trace.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from project_b.osu.types import JudgementRecord, ManiaJudgement
from project_b.utils.time import require_time_us


def _unit_utility(value: float, name: str) -> float:
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    if not -1.0 <= value <= 1.0:
        raise ValueError(f"{name} must lie in [-1, 1]")
    return float(value)


@dataclass(frozen=True, slots=True)
class JudgementUtility:
    judgement: ManiaJudgement
    hit_value: int
    utility: float


class CenteredHitUtility:
    """Pure default mapping: u = 2 * (hit_value / 320) - 1."""

    def translate(self, judgement: ManiaJudgement) -> JudgementUtility:
        if type(judgement) is not ManiaJudgement:
            raise TypeError("expected a ManiaJudgement, not a score or action")
        return JudgementUtility(judgement, int(judgement),
                                2.0 * (int(judgement) / 320.0) - 1.0)


@dataclass(frozen=True, slots=True)
class RewardPrediction:
    actual_utility: float
    expected_before: float
    rpe: float
    expected_after: float


class RewardPredictor:
    """Single slowly updated expected-utility baseline.

    ``alpha`` is the exponential moving-average rate per observed outcome.
    It is an engineering prediction model, not a fly DAN population.
    """

    def __init__(self, *, initial_expected_utility: float = 0.0,
                 alpha: float = 0.1) -> None:
        self._expected_utility = _unit_utility(
            initial_expected_utility, "initial_expected_utility")
        if type(alpha) not in (int, float) or not math.isfinite(alpha) or not 0 < alpha < 1:
            raise ValueError("alpha must be finite and strictly between 0 and 1")
        self.alpha = float(alpha)

    @property
    def expected_utility(self) -> float:
        return self._expected_utility

    def preview(self, actual_utility: float) -> RewardPrediction:
        actual = _unit_utility(actual_utility, "actual_utility")
        expected = self.expected_utility
        rpe = actual - expected
        return RewardPrediction(actual, expected, rpe,
                                expected + self.alpha * rpe)

    def commit(self, prediction: RewardPrediction) -> None:
        """Accept one preview after downstream stages have succeeded."""
        if type(prediction) is not RewardPrediction:
            raise TypeError("prediction must be RewardPrediction")
        if prediction != self.preview(prediction.actual_utility):
            raise ValueError("prediction is stale or inconsistent")
        self._expected_utility = prediction.expected_after

    def observe(self, actual_utility: float) -> RewardPrediction:
        prediction = self.preview(actual_utility)
        self.commit(prediction)
        return prediction


@dataclass(frozen=True, slots=True)
class ModulatorySignal:
    time_us: int
    source_rpe: float
    amplitude: float
    kind: str = "synthetic_dopamine_like"


class RPEModulator:
    """Convert signed RPE into a signed artificial modulatory amplitude."""

    def __init__(self, *, gain: float = 1.0) -> None:
        if type(gain) not in (int, float) or not math.isfinite(gain) or gain < 0:
            raise ValueError("gain must be finite and nonnegative")
        self.gain = float(gain)

    def emit(self, time_us: int, prediction: RewardPrediction) -> ModulatorySignal:
        require_time_us(time_us)
        if type(prediction) is not RewardPrediction:
            raise TypeError("prediction must be RewardPrediction")
        amplitude = self.gain * prediction.rpe
        if not math.isfinite(amplitude):
            raise ArithmeticError("non-finite modulatory amplitude")
        return ModulatorySignal(time_us, prediction.rpe, amplitude)


@dataclass(frozen=True, slots=True)
class ReinforcementEvent:
    judgement_record: JudgementRecord
    utility: JudgementUtility
    learning_utility: float
    prediction: RewardPrediction
    modulation: ModulatorySignal


class ReinforcementPipeline:
    """Run the isolated judgement → utility → RPE → modulation chain."""

    def __init__(self, *, utility: CenteredHitUtility | None = None,
                 predictor: RewardPredictor | None = None,
                 modulator: RPEModulator | None = None) -> None:
        self.utility = utility if utility is not None else CenteredHitUtility()
        self.predictor = predictor if predictor is not None else RewardPredictor()
        self.modulator = modulator if modulator is not None else RPEModulator()
        self._last_event_time_us: int | None = None

    def process_judgement(self, record: JudgementRecord, *,
                          learning_utility: float | None = None) -> ReinforcementEvent:
        if type(record) is not JudgementRecord:
            raise TypeError("expected a resolved JudgementRecord")
        require_time_us(record.logical_event_time_us, "logical_event_time_us")
        if (self._last_event_time_us is not None
                and record.logical_event_time_us < self._last_event_time_us):
            raise ValueError("judgements must be processed chronologically")
        translated = self.utility.translate(record.judgement)
        delivered = (translated.utility if learning_utility is None
                     else _unit_utility(learning_utility, "learning_utility"))
        prediction = self.predictor.preview(delivered)
        signal = self.modulator.emit(record.logical_event_time_us, prediction)
        self.predictor.commit(prediction)
        self._last_event_time_us = record.logical_event_time_us
        return ReinforcementEvent(record, translated, delivered, prediction, signal)
