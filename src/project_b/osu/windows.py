"""Versioned mania timing windows represented against integer-microsecond time."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import math

from .config import OsuConfig
from .types import ManiaJudgement, require_time_us


def rounded_abs_error_ms(error_us: int) -> int:
    """Round absolute microsecond error to integer ms, ties to even.

    The osu! wiki specifies rounded hit error but does not define the exact
    half-millisecond tie mode. Ties-to-even is the explicit M0 assumption.
    """
    require_time_us(error_us, "error_us")
    whole_ms, remainder_us = divmod(abs(error_us), 1000)
    if remainder_us > 500 or (remainder_us == 500 and whole_ms % 2 == 1):
        whole_ms += 1
    return whole_ms


@dataclass(frozen=True, slots=True)
class ManiaHitWindows:
    od: Decimal
    ruleset: str
    max_ms: Decimal | int
    great_ms: Decimal | int
    good_ms: Decimal | int
    ok_ms: Decimal | int
    meh_ms: Decimal | int
    miss_ms: Decimal | int

    @classmethod
    def from_od(cls, od: Decimal | int | str, ruleset: str = "stable_native") -> ManiaHitWindows:
        config = OsuConfig(od=od, ruleset=ruleset)
        o = config.od
        if ruleset == "stable_native":
            thresholds = (16, int(64 - 3 * o), int(97 - 3 * o),
                          int(127 - 3 * o), int(151 - 3 * o), int(188 - 3 * o))
        elif ruleset == "stable_convert":
            if o > 4:
                thresholds = (16, 34, 67, 97, 121, 158)
            else:
                thresholds = (16, 47, 77, 97, 121, 158)
        else:
            # Mirrors ManiaHitWindows' unmodded, non-Classic lazer profile.
            # DifficultyRange values are (OD 0, OD 5, OD 10), then each
            # window is floored and shifted by 0.5 ms in lazer.
            ranges = (
                (22.4, 19.4, 13.9),
                (64.0, 49.0, 34.0),
                (97.0, 82.0, 67.0),
                (127.0, 112.0, 97.0),
                (151.0, 136.0, 121.0),
                (188.0, 173.0, 158.0),
            )
            thresholds = tuple(
                Decimal(math.floor(cls._difficulty_range(float(o), values)))
                + Decimal("0.5")
                for values in ranges
            )
        if not all(a < b for a, b in zip(thresholds, thresholds[1:])):
            raise ValueError("judgement thresholds must be strictly increasing")
        return cls(o, ruleset, *thresholds)

    @staticmethod
    def _difficulty_range(od: float,
                          values: tuple[float, float, float]) -> float:
        """Match IBeatmapDifficultyInfo.DifficultyRange operation order."""
        low, middle, high = values
        if od > 5:
            return middle + (high - middle) * ((od - 5.0) / 5.0)
        if od < 5:
            return middle + (middle - low) * ((od - 5.0) / 5.0)
        return middle

    @property
    def expiry_offset_us(self) -> int:
        """First late offset that the ruleset will automatically expire."""
        if self.ruleset == "lazer":
            # HitWindows.CanBeHit() remains true through the largest
            # successful window (MEH); expiry occurs on the next microsecond.
            return int(Decimal(self.meh_ms) * 1000) + 1
        return self.ok_ms * 1000 + 500 + (1 if self.ok_ms % 2 == 0 else 0)

    def press_judgement(self, error_us: int) -> ManiaJudgement | None:
        """Classify one press relative to a candidate note.

        None means there is no press judgement: before the early MISS window
        or outside this profile's pressable timing range. An early MISS is a
        real note judgement.
        """
        require_time_us(error_us, "error_us")
        if self.ruleset == "lazer":
            error = abs(error_us)
            windows = (
                (self.max_ms, ManiaJudgement.MAX_320),
                (self.great_ms, ManiaJudgement.GREAT_300),
                (self.good_ms, ManiaJudgement.GOOD_200),
                (self.ok_ms, ManiaJudgement.OK_100),
                (self.meh_ms, ManiaJudgement.MEH_50),
            )
            for window_ms, judgement in windows:
                if error <= int(Decimal(window_ms) * 1000):
                    return judgement
            if error <= int(Decimal(self.miss_ms) * 1000):
                return ManiaJudgement.MISS
            return None

        rounded_ms = rounded_abs_error_ms(error_us)
        if error_us < 0 and rounded_ms > self.miss_ms:
            return None
        if error_us >= 0 and rounded_ms > self.ok_ms:
            return None
        if rounded_ms <= self.max_ms:
            return ManiaJudgement.MAX_320
        if rounded_ms <= self.great_ms:
            return ManiaJudgement.GREAT_300
        if rounded_ms <= self.good_ms:
            return ManiaJudgement.GOOD_200
        if rounded_ms <= self.ok_ms:
            return ManiaJudgement.OK_100
        if error_us < 0 and rounded_ms <= self.meh_ms:
            return ManiaJudgement.MEH_50
        if error_us < 0:
            return ManiaJudgement.MISS
        return None
