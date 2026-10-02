"""Deterministic, headless osu!mania 4K game mechanics."""

from .config import OsuConfig, load_config
from .environment import GameEnvironment, play
from .types import (
    ActionDisposition,
    ActionRecord,
    GameResult,
    HoldNote,
    JudgementRecord,
    KeyAction,
    KeyActionKind,
    ManiaJudgement,
    TapNote,
)
from .windows import ManiaHitWindows

__all__ = [
    "ActionDisposition",
    "ActionRecord",
    "GameEnvironment",
    "GameResult",
    "HoldNote",
    "JudgementRecord",
    "KeyAction",
    "KeyActionKind",
    "ManiaHitWindows",
    "ManiaJudgement",
    "OsuConfig",
    "TapNote",
    "load_config",
    "play",
]
