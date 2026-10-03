"""Independent A3 first-action reconstruction from raw game events.

This module does not call FirstActionTracker or use judged note IDs to assign
actions. The immutable renderer schedule sets causal cue scopes; raw emitted
key transitions set first-action identity. Game judgement is secondary only.
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import asdict, dataclass
from enum import Enum
from statistics import median
from typing import Sequence

from project_b.osu.types import ActionDisposition, KeyActionKind, ManiaJudgement
from project_b.osu.windows import ManiaHitWindows

from .feedback import FirstActionOutcome, NoteWindow


WINDOW_US = 73_000


def _value(value):
    return value.value if isinstance(value, Enum) else value


@dataclass(frozen=True, slots=True)
class ScopedAction:
    raw_event_index: int
    time_us: int
    kind: str
    disposition: str
    game_note_id: str | None


@dataclass(frozen=True, slots=True)
class FirstActionRow:
    note_id: str
    visible_from_us: int
    hit_us: int
    scope_end_us: int
    first_down_us: int | None
    signed_error_us: int | None
    category: str
    first_disposition: str | None
    extra_downs: int
    primary_success: bool
    scoped_actions: tuple[ScopedAction, ...]
    later_actions: tuple[ScopedAction, ...]
    game_judgements: tuple[dict, ...]


@dataclass(frozen=True, slots=True)
class FirstActionAudit:
    contract_id: str
    audit_end_us: int
    rows: tuple[FirstActionRow, ...]
    background_actions: tuple[ScopedAction, ...]
    other_lane_actions: tuple[ScopedAction, ...]
    summary: dict

    def as_dict(self) -> dict:
        return asdict(self)


def game_events_from_mvp_ledger(ledger: Sequence[list]) -> list[dict]:
    """Extract raw game records, preserving ledger order and original fields."""
    events = []
    for row in ledger:
        if not isinstance(row, (list, tuple)) or not row:
            raise ValueError("malformed MVP ledger row")
        if row[0] == "game_event":
            if len(row) != 2 or not isinstance(row[1], dict):
                raise ValueError("malformed raw game event")
            events.append(row[1])
    return events


def reconstruct_first_actions(notes: tuple[NoteWindow, ...], raw_game_events: Sequence[dict],
                              audit_end_us: int, *, success_window_us: int = WINDOW_US
                              ) -> FirstActionAudit:
    """One row per visible isolated note, independent of the task state owner."""
    if (type(audit_end_us) is not int or audit_end_us < 0 or
            type(success_window_us) is not int or success_window_us <= 0):
        raise ValueError("invalid A3 audit time or primary window")
    if (not notes or len({n.note_id for n in notes}) != len(notes) or
            tuple(sorted(notes, key=lambda n: n.visible_from_us)) != notes or
            any(b.visible_from_us <= a.hit_us for a, b in zip(notes, notes[1:]))):
        raise ValueError("A3 requires unique isolated cue onsets; chords are unsupported")
    visible = tuple(n for n in notes if n.visible_from_us <= audit_end_us)
    if not visible:
        raise ValueError("no visible note can enter the primary denominator")
    onsets = [n.visible_from_us for n in visible]
    by_id = {n.note_id: n for n in notes}
    actions: dict[str, list[ScopedAction]] = {n.note_id: [] for n in visible}
    judgements: dict[str, list[dict]] = {n.note_id: [] for n in visible}
    background: list[ScopedAction] = []
    other_lane: list[ScopedAction] = []
    seen_judgement_ids: set[str] = set()
    judgement_before_action: set[tuple[int, str]] = set()
    previous_time = -1
    for event_index, event in enumerate(raw_game_events):
        if not isinstance(event, dict) or set(event) != {"kind", "record"}:
            raise ValueError("invalid raw game event schema")
        kind, record = event["kind"], event["record"]
        if not isinstance(record, dict):
            raise ValueError("invalid game record")
        if kind == "judgement":
            required = {"note_id", "lane", "note_time_us", "judgement", "hit_error_us"}
            time_keys = {"logical_event_time_us", "event_time_us"}
            allowed = required | time_keys | {"observed_game_time_us", "ruleset"}
            if (not required <= set(record) or set(record) - allowed
                    or not (time_keys & set(record))
                    or (time_keys <= set(record)
                        and record["logical_event_time_us"] != record["event_time_us"])
                    or (record.get("observed_game_time_us") is not None
                        and type(record["observed_game_time_us"]) is not int)
                    or record["note_id"] not in by_id):
                raise ValueError("invalid judgement record")
            at = record.get("logical_event_time_us", record.get("event_time_us"))
            note_id = record["note_id"]
            note = by_id[note_id]
            judgement = _value(record["judgement"])
            if (type(at) is not int or not previous_time <= at <= audit_end_us or
                    record["lane"] != 0 or record["note_time_us"] != note.hit_us or
                    note_id in seen_judgement_ids or
                    type(judgement) is not int or
                    judgement not in {int(x) for x in ManiaJudgement} or
                    (record["hit_error_us"] is not None and
                     (type(record["hit_error_us"]) is not int or
                      record["hit_error_us"] != at - note.hit_us))):
                raise ValueError("judgement contradicts immutable note or event order")
            previous_time = at
            seen_judgement_ids.add(note_id)
            judgement_before_action.add((at, note_id))
            if note_id in judgements:
                judgements[note_id].append({
                    "raw_event_index": event_index, "event_time_us": at,
                    "judgement": judgement,
                    "hit_error_us": record["hit_error_us"]})
        elif kind == "action":
            if set(record) != {"action", "disposition", "note_id"} or not isinstance(
                    record["action"], dict) or set(record["action"]) != {
                        "time_us", "lane", "kind"}:
                raise ValueError("invalid action record")
            action = record["action"]
            at, lane = action["time_us"], action["lane"]
            key_kind, disposition = _value(action["kind"]), _value(record["disposition"])
            if (type(at) is not int or not previous_time <= at <= audit_end_us or
                    type(lane) is not int or not 0 <= lane < 4 or
                    key_kind not in {x.value for x in KeyActionKind} or
                    disposition not in {x.value for x in ActionDisposition} or
                    (record["note_id"] is not None and record["note_id"] not in by_id)):
                raise ValueError("action contradicts event order or domain")
            if disposition in ("hit", "early_miss"):
                if (key_kind != "down" or record["note_id"] is None or
                        (at, record["note_id"]) not in judgement_before_action):
                    raise ValueError("judged DOWN lacks preceding raw judgement")
            elif record["note_id"] is not None:
                raise ValueError("nonjudged action cannot name a judged note")
            previous_time = at
            scoped = ScopedAction(event_index, at, key_kind, disposition, record["note_id"])
            if lane != 0:
                other_lane.append(scoped)
            else:
                slot = bisect_right(onsets, at) - 1
                if slot < 0:
                    background.append(scoped)
                else:
                    actions[visible[slot].note_id].append(scoped)
        else:
            raise ValueError("unknown raw game event kind")

    rows: list[FirstActionRow] = []
    for i, note in enumerate(visible):
        scoped = tuple(actions[note.note_id])
        new_downs = [a for a in scoped if a.kind == "down" and
                     a.disposition != "repeat_down"]
        first = new_downs[0] if new_downs else None
        error = None if first is None else first.time_us - note.hit_us
        if first is None:
            category = "no_down"
        elif abs(error) <= success_window_us:
            category = "success"
        elif error < 0:
            category = "too_early_null" if first.disposition == "null_press" else "early_judged"
        else:
            category = "late"
        later = tuple(a for a in scoped if first is not None and
                      a.raw_event_index > first.raw_event_index)
        rows.append(FirstActionRow(
            note.note_id, note.visible_from_us, note.hit_us,
            visible[i + 1].visible_from_us if i + 1 < len(visible) else audit_end_us + 1,
            None if first is None else first.time_us, error, category,
            None if first is None else first.disposition, max(0, len(new_downs) - 1),
            category == "success", scoped, later, tuple(judgements[note.note_id])))

    if (rows[-1].category == "no_down" and
            audit_end_us < visible[-1].hit_us +
            ManiaHitWindows.from_od(8, "stable_native").expiry_offset_us):
        raise ValueError("last note is incomplete; no_down needs a final audit horizon")

    errors = [row.signed_error_us for row in rows if row.signed_error_us is not None]
    category_counts = {category: sum(r.category == category for r in rows)
                       for category in ("success", "too_early_null", "early_judged",
                                        "late", "no_down")}
    judged = [j["judgement"] for row in rows for j in row.game_judgements]
    histogram = {grade.name: sum(j == int(grade) for j in judged)
                 for grade in ManiaJudgement}
    summary = {
        "eligible_note_denominator": len(rows),
        "first_down_success_count": category_counts["success"],
        "first_down_success_rate": category_counts["success"] / len(rows),
        "missing_action_count": category_counts["no_down"],
        "first_action_category_counts": category_counts,
        "signed_errors_us_in_note_order": errors,
        "signed_errors_us_sorted": sorted(errors),
        "median_signed_error_us": None if not errors else median(errors),
        "extra_down_count": sum(row.extra_downs for row in rows),
        "secondary_judgement_histogram": histogram,
        "secondary_positive_judgement_notes": sum(
            any(j["judgement"] > 0 for j in row.game_judgements) for row in rows),
        "background_action_count": len(background),
        "other_lane_action_count": len(other_lane),
    }
    return FirstActionAudit("MVP-C1-first-action-v1", audit_end_us, tuple(rows),
                            tuple(background), tuple(other_lane), summary)


def compare_owner_outcomes(audit: FirstActionAudit,
                           owner_outcomes: Sequence[FirstActionOutcome]) -> None:
    """Audit an owner only after independent reconstruction has finished."""
    expected = [(r.note_id, r.first_down_us, r.signed_error_us, r.category,
                 r.first_disposition, r.extra_downs) for r in audit.rows]
    observed = [(o.note_id, o.first_down_us, o.signed_error_us, o.category,
                 o.game_disposition, o.extra_downs) for o in owner_outcomes]
    if expected != observed:
        raise AssertionError(f"A3 first-action owner differs: expected {expected}, got {observed}")
