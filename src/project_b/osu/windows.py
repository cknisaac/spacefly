"""Versioned stable mania timing windows in exact integer microseconds."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

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
    max_ms: int
    great_ms: int
    good_ms: int
    ok_ms: int
    meh_ms: int
    miss_ms: int

    @classmethod
    def from_od(cls, od: Decimal | int | str, ruleset: str = "stable_native") -> ManiaHitWindows:
        config = OsuConfig(od=od, ruleset=ruleset)
        o = config.od
        if ruleset == "stable_native":
            thresholds = (16, int(64 - 3 * o), int(97 - 3 * o),
                          int(127 - 3 * o), int(151 - 3 * o), int(188 - 3 * o))
        else:
            if o > 4:
                thresholds = (16, 34, 67, 97, 121, 158)
            else:
                thresholds = (16, 47, 77, 97, 121, 158)
        if not all(a < b for a, b in zip(thresholds, thresholds[1:])):
            raise ValueError("judgement thresholds must be strictly increasing")
        return cls(o, ruleset, *thresholds)

    @property
    def expiry_offset_us(self) -> int:
        """First positive offset that rounds beyond OK; expiry precedes input."""
        return self.ok_ms * 1000 + 500 + (1 if self.ok_ms % 2 == 0 else 0)

    def press_judgement(self, error_us: int) -> ManiaJudgement | None:
        """Classify one press relative to a candidate note.

        None means there is no press judgement: before the early MISS window
        or after late OK expiry. An early MISS is a real note judgement.
        """
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
