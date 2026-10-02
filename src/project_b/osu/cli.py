"""Run a generated tap-note scenario without graphics or neural code."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .config import load_config
from .environment import play
from .types import ActionRecord, HoldNote, JudgementRecord, KeyAction, KeyActionKind, TapNote


def _fields(data: Any, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(data, dict) or set(data) != expected:
        raise ValueError(f"{label} must contain exactly {sorted(expected)}")
    return data


def run_scenario(config_path: str | Path, scenario_path: str | Path) -> dict[str, Any]:
    """Load a simple generated scenario and return a deterministic event log."""
    config = load_config(config_path)
    with Path(scenario_path).open("r", encoding="utf-8") as stream:
        scenario = _fields(json.load(stream), {"notes", "actions"}, "scenario")
    if not isinstance(scenario["notes"], list) or not isinstance(scenario["actions"], list):
        raise ValueError("notes and actions must be arrays")
    notes = []
    for item in scenario["notes"]:
        if not isinstance(item, dict) or "kind" not in item:
            raise ValueError("each note needs an explicit kind")
        if item["kind"] == "tap":
            value = _fields(item, {"kind", "id", "lane", "time_us"}, "tap note")
            notes.append(TapNote(value["id"], value["lane"], value["time_us"]))
        elif item["kind"] == "hold":
            value = _fields(item, {"kind", "id", "lane", "time_us", "end_time_us"},
                            "hold note")
            notes.append(HoldNote(value["id"], value["lane"], value["time_us"],
                                  value["end_time_us"]))
        else:
            raise ValueError(f"unsupported note kind: {item['kind']}")
    actions = []
    for item in scenario["actions"]:
        value = _fields(item, {"time_us", "lane", "kind"}, "action")
        actions.append(KeyAction(value["time_us"], value["lane"],
                                 KeyActionKind(value["kind"])))
    result = play(notes, actions, config)
    events = []
    for event in result.events:
        if isinstance(event, JudgementRecord):
            events.append({"type": "judgement", "note_id": event.note_id,
                           "lane": event.lane, "note_time_us": event.note_time_us,
                           "event_time_us": event.event_time_us,
                           "judgement": event.judgement.name,
                           "hit_value": int(event.judgement),
                           "hit_error_us": event.hit_error_us})
        elif isinstance(event, ActionRecord):
            events.append({"type": "action", "time_us": event.action.time_us,
                           "lane": event.action.lane, "kind": event.action.kind.value,
                           "disposition": event.disposition.value, "note_id": event.note_id})
    return {"config": {"osu": config.as_dict()}, "events": events,
            "total_notes": result.total_notes, "null_presses": result.null_presses,
            "key_down": list(result.key_down)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", type=Path, help="JSON generated-note scenario")
    parser.add_argument("--config", type=Path, default=Path("configs/base.yaml"))
    args = parser.parse_args()
    print(json.dumps(run_scenario(args.config, args.scenario),
                     sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
