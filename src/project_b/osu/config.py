"""Validated M0 configuration. Configuration is separate from beatmap objects."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

import yaml


@dataclass(frozen=True, slots=True)
class OsuConfig:
    keys: int = 4
    od: Decimal = Decimal("8")
    ruleset: str = "stable_native"

    def __post_init__(self) -> None:
        if type(self.keys) is not int or self.keys != 4:
            raise ValueError("M0 supports exactly four keys")
        try:
            od = Decimal(str(self.od))
        except InvalidOperation as exc:
            raise ValueError("od must be a decimal number") from exc
        if not od.is_finite() or not Decimal("0") <= od <= Decimal("10"):
            raise ValueError("od must be finite and in 0..10")
        object.__setattr__(self, "od", od)
        if self.ruleset not in {"stable_native", "stable_convert", "lazer"}:
            raise ValueError("ruleset must be stable_native, stable_convert, or lazer")

    def as_dict(self) -> dict[str, object]:
        return {"keys": self.keys, "od": str(self.od), "ruleset": self.ruleset}


def load_config(path: str | Path) -> OsuConfig:
    """Load a YAML file containing only the supported M0 `osu` settings."""
    with Path(path).open("r", encoding="utf-8") as stream:
        document = yaml.safe_load(stream)
    if not isinstance(document, dict) or set(document) != {"osu"}:
        raise ValueError("config must contain only an 'osu' mapping")
    settings = document["osu"]
    if not isinstance(settings, dict) or set(settings) != {"keys", "od", "ruleset"}:
        raise ValueError("osu config must contain keys, od, and ruleset")
    return OsuConfig(**settings)
