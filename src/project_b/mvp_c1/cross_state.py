"""Outcome-blind cross-state checkpoint selection for Branch A infrastructure."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Selection:
    run_id: str
    seed: int
    phase: str
    checkpoint_us: int
    reason: str


def select_checkpoints(contract: dict, *, horizon_us: int,
                       runs: tuple[tuple[str, int], ...]) -> tuple[Selection, ...]:
    """Select all declared run/phase cuts without consulting any run state."""
    selection = contract["selection"]
    tick = selection["tick_us"]
    if (type(tick) is not int or tick <= 0 or type(horizon_us) is not int or
            horizon_us <= tick or horizon_us % tick):
        raise ValueError("invalid committed-tick horizon")
    if not runs or any(type(run_id) is not str or not run_id or
                       type(seed) is not int or seed < 0 for run_id, seed in runs):
        raise ValueError("run IDs and nonnegative seeds must be predeclared")
    if len({run_id for run_id, _ in runs}) != len(runs):
        raise ValueError("duplicate run ID")
    fractions = selection["fractions"]
    if tuple(fractions) != ("early", "middle", "late"):
        raise ValueError("expected ordered early/middle/late fractions")
    cuts = []
    for phase, pair in fractions.items():
        if (type(pair) is not list or len(pair) != 2 or
                any(type(value) is not int for value in pair)):
            raise ValueError("fractions must be exact integer pairs")
        numerator, denominator = pair
        if not 0 < numerator < denominator:
            raise ValueError("fraction must be strictly internal")
        checkpoint_us = (horizon_us * numerator // denominator // tick) * tick
        if not 0 < checkpoint_us < horizon_us:
            raise ValueError("horizon cannot resolve all internal checkpoints")
        cuts.append((phase, checkpoint_us, numerator, denominator))
    if len({cut for _, cut, _, _ in cuts}) != len(cuts) or [x[1] for x in cuts] != sorted(x[1] for x in cuts):
        raise ValueError("checkpoint cuts collide or are not ordered")
    return tuple(Selection(run_id, seed, phase, cut,
                           f"predeclared {numerator}/{denominator} of {horizon_us} us; floor to {tick}-us tick")
                 for run_id, seed in runs
                 for phase, cut, numerator, denominator in cuts)
