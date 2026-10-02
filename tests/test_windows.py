"""Reference-value and exhaustive OD8 boundary tests."""

import unittest
from decimal import Decimal, ROUND_HALF_EVEN

from project_b.osu import ManiaHitWindows, ManiaJudgement, OsuConfig
from project_b.osu.windows import rounded_abs_error_ms


class WindowTests(unittest.TestCase):
    def test_od8_canonical_windows(self) -> None:
        w = ManiaHitWindows.from_od(8, "stable_native")
        self.assertEqual((w.max_ms, w.great_ms, w.good_ms, w.ok_ms,
                          w.meh_ms, w.miss_ms), (16, 40, 73, 103, 127, 164))
        self.assertEqual(w.expiry_offset_us, 103_500)

    def test_native_od_parameterization(self) -> None:
        for od in range(11):
            with self.subTest(od=od):
                w = ManiaHitWindows.from_od(od)
                self.assertEqual((w.max_ms, w.great_ms, w.good_ms, w.ok_ms,
                                  w.meh_ms, w.miss_ms),
                                 (16, 64 - 3*od, 97 - 3*od, 127 - 3*od,
                                  151 - 3*od, 188 - 3*od))
        w = ManiaHitWindows.from_od(Decimal("8.25"))
        self.assertEqual((w.great_ms, w.good_ms, w.ok_ms, w.meh_ms, w.miss_ms),
                         (39, 72, 102, 126, 163))

    def test_convert_is_separate_profile(self) -> None:
        self.assertEqual((ManiaHitWindows.from_od(4, "stable_convert").great_ms,
                          ManiaHitWindows.from_od("4.01", "stable_convert").great_ms),
                         (47, 34))
        w = ManiaHitWindows.from_od(8, "stable_convert")
        self.assertEqual((w.max_ms, w.great_ms, w.good_ms, w.ok_ms,
                          w.meh_ms, w.miss_ms), (16, 34, 67, 97, 121, 158))

    def test_invalid_profiles_and_od(self) -> None:
        for od in (-1, 11, "NaN", "Infinity", "text"):
            with self.subTest(od=od), self.assertRaises(ValueError):
                ManiaHitWindows.from_od(od)
        for ruleset in ("lazer", "stable_scorev2", "unknown"):
            with self.subTest(ruleset=ruleset), self.assertRaises(ValueError):
                ManiaHitWindows.from_od(8, ruleset)
        with self.assertRaises(ValueError):
            OsuConfig(keys=7)

    def test_all_integer_millisecond_errors_od8(self) -> None:
        w = ManiaHitWindows.from_od(8)
        for error_ms in range(-170, 171):
            absolute = abs(error_ms)
            if error_ms < -164 or error_ms > 103:
                expected = None
            elif absolute <= 16:
                expected = ManiaJudgement.MAX_320
            elif absolute <= 40:
                expected = ManiaJudgement.GREAT_300
            elif absolute <= 73:
                expected = ManiaJudgement.GOOD_200
            elif absolute <= 103:
                expected = ManiaJudgement.OK_100
            elif error_ms < 0 and absolute <= 127:
                expected = ManiaJudgement.MEH_50
            else:
                expected = ManiaJudgement.MISS
            with self.subTest(error_ms=error_ms):
                self.assertEqual(w.press_judgement(error_ms * 1000), expected)

    def test_positive_negative_boundaries_microseconds(self) -> None:
        w = ManiaHitWindows.from_od(8)
        transitions = [
            (16, ManiaJudgement.MAX_320, ManiaJudgement.GREAT_300),
            (40, ManiaJudgement.GREAT_300, ManiaJudgement.GOOD_200),
            (73, ManiaJudgement.GOOD_200, ManiaJudgement.OK_100),
            (103, ManiaJudgement.OK_100, None),
        ]
        for threshold, inside, late_outside in transitions:
            first_outside_us = threshold * 1000 + 500 + (threshold % 2 == 0)
            for sign in (-1, 1):
                expected_outside = (ManiaJudgement.MEH_50 if threshold == 103 and sign < 0
                                    else late_outside)
                for magnitude, expected in ((first_outside_us - 1, inside),
                                            (first_outside_us, expected_outside)):
                    with self.subTest(threshold=threshold, sign=sign, magnitude=magnitude):
                        self.assertEqual(w.press_judgement(sign * magnitude), expected)

    def test_early_meh_and_miss_boundaries_microseconds(self) -> None:
        w = ManiaHitWindows.from_od(8)
        # Odd 127 rounds upward at 127.500 ms; even 164 rounds down at 164.500 ms.
        self.assertEqual(w.press_judgement(-127_499), ManiaJudgement.MEH_50)
        self.assertEqual(w.press_judgement(-127_500), ManiaJudgement.MISS)
        self.assertEqual(w.press_judgement(-164_500), ManiaJudgement.MISS)
        self.assertIsNone(w.press_judgement(-164_501))
        self.assertIsNone(w.press_judgement(127_000))  # No late 50.

    def test_rounding_is_symmetric_and_ties_even(self) -> None:
        cases = {16_499: 16, 16_500: 16, 16_501: 17,
                 73_499: 73, 73_500: 74, 103_499: 103, 103_500: 104}
        for magnitude, expected in cases.items():
            for sign in (-1, 1):
                with self.subTest(magnitude=magnitude, sign=sign):
                    self.assertEqual(rounded_abs_error_ms(sign * magnitude), expected)
        with self.assertRaises(ValueError):
            rounded_abs_error_ms(1.2)  # type: ignore[arg-type]

    def test_all_window_edges_for_each_integer_od_and_profile(self) -> None:
        for ruleset in ("stable_native", "stable_convert"):
            for od in range(11):
                w = ManiaHitWindows.from_od(od, ruleset)
                threshold_pairs = (
                    (w.max_ms, ManiaJudgement.MAX_320, ManiaJudgement.GREAT_300),
                    (w.great_ms, ManiaJudgement.GREAT_300, ManiaJudgement.GOOD_200),
                    (w.good_ms, ManiaJudgement.GOOD_200, ManiaJudgement.OK_100),
                    (w.ok_ms, ManiaJudgement.OK_100, ManiaJudgement.MEH_50),
                )
                for threshold, inside, next_early in threshold_pairs:
                    first_outside = threshold * 1000 + 500 + (threshold % 2 == 0)
                    for sign in (-1, 1):
                        next_judgement = (None if sign > 0 and threshold == w.ok_ms
                                          else next_early)
                        for magnitude, expected in ((first_outside - 1, inside),
                                                    (first_outside, next_judgement)):
                            with self.subTest(ruleset=ruleset, od=od, threshold=threshold,
                                              sign=sign, magnitude=magnitude):
                                self.assertEqual(w.press_judgement(sign * magnitude), expected)
                for threshold, inside, outside in (
                    (w.meh_ms, ManiaJudgement.MEH_50, ManiaJudgement.MISS),
                    (w.miss_ms, ManiaJudgement.MISS, None),
                ):
                    first_outside = threshold * 1000 + 500 + (threshold % 2 == 0)
                    with self.subTest(ruleset=ruleset, od=od, threshold=threshold):
                        self.assertEqual(w.press_judgement(-(first_outside - 1)), inside)
                        self.assertEqual(w.press_judgement(-first_outside), outside)
                self.assertLessEqual(rounded_abs_error_ms(w.expiry_offset_us - 1), w.ok_ms)
                self.assertGreater(rounded_abs_error_ms(w.expiry_offset_us), w.ok_ms)

    def test_rounding_against_independent_decimal_oracle_at_every_microsecond(self) -> None:
        w = ManiaHitWindows.from_od(8)
        for threshold in (w.max_ms, w.great_ms, w.good_ms, w.ok_ms,
                          w.meh_ms, w.miss_ms):
            for error_us in range(threshold * 1000 - 750, threshold * 1000 + 751):
                expected = int((Decimal(error_us) / Decimal(1000)).quantize(
                    Decimal(1), rounding=ROUND_HALF_EVEN))
                with self.subTest(threshold=threshold, error_us=error_us):
                    self.assertEqual(rounded_abs_error_ms(error_us), expected)
                    self.assertEqual(rounded_abs_error_ms(-error_us), expected)


if __name__ == "__main__":
    unittest.main()
