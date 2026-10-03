"""Deterministic headless 4K tap-note state machine."""

from __future__ import annotations

import heapq
from dataclasses import asdict
from collections.abc import Iterable, Sequence

from .config import OsuConfig
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
    require_time_us,
)
from .windows import ManiaHitWindows


class GameEnvironment:
    """Judge independent lanes on a monotonic integer-µs timeline.

    At a timestamp, unresolved note expiries are processed before actions.
    Actions with equal timestamps retain caller order. Only a DOWN transition
    judges a note. The lazer profile follows its ordered note lock: an older
    note is hittable only before the next note's start time; a successful hit
    force-misses any earlier unresolved tap notes. Stable profiles retain the
    M0 oldest-unresolved-note approximation.
    """

    def __init__(self, notes: Sequence[TapNote | HoldNote], config: OsuConfig | None = None):
        self.config = config if config is not None else OsuConfig()
        self.windows = ManiaHitWindows.from_od(self.config.od, self.config.ruleset)
        lanes: list[list[TapNote]] = [[], [], [], []]
        seen_ids: set[str] = set()
        seen_positions: set[tuple[int, int]] = set()
        for note in notes:
            if isinstance(note, HoldNote):
                raise ValueError("M0 rejects hold notes; long-note judgement is not implemented")
            if not isinstance(note, TapNote):
                raise TypeError("notes must contain TapNote or HoldNote records")
            if note.note_id in seen_ids:
                raise ValueError(f"duplicate note_id: {note.note_id}")
            if (note.lane, note.time_us) in seen_positions:
                raise ValueError("duplicate tap notes in one lane at one timestamp are unsupported")
            seen_ids.add(note.note_id)
            seen_positions.add((note.lane, note.time_us))
            lanes[note.lane].append(note)
        self._lanes = tuple(tuple(sorted(items, key=lambda n: (n.time_us, n.note_id)))
                            for items in lanes)
        self._total_notes = len(seen_ids)
        self._positions = [0, 0, 0, 0]
        self._key_down = [False, False, False, False]
        self._resolved: set[str] = set()
        self._expiry_heap: list[tuple[int, int, str, TapNote]] = []
        for lane_notes in self._lanes:
            for note in lane_notes:
                expiry_us = require_time_us(note.time_us + self.windows.expiry_offset_us,
                                            "expiry_time_us")
                heapq.heappush(self._expiry_heap,
                               (expiry_us, note.lane, note.note_id, note))
        self.current_time_us: int | None = None
        self._judgements: list[JudgementRecord] = []
        self._actions: list[ActionRecord] = []
        self._events: list[JudgementRecord | ActionRecord] = []

    def _record_judgement(self, note: TapNote, logical_event_time_us: int,
                          judgement: ManiaJudgement, hit_error_us: int | None) -> None:
        self._resolved.add(note.note_id)
        record = JudgementRecord(note.note_id, note.lane, note.time_us,
                                 logical_event_time_us, judgement, hit_error_us,
                                 self.config.ruleset, observed_game_time_us=None)
        self._judgements.append(record)
        self._events.append(record)

    def advance_to(self, time_us: int) -> None:
        """Advance time and emit automatic misses at the first invalid µs."""
        require_time_us(time_us)
        if self.current_time_us is not None and time_us < self.current_time_us:
            raise ValueError("time cannot move backwards")
        while self._expiry_heap and self._expiry_heap[0][0] <= time_us:
            expiry_us, _, _, note = heapq.heappop(self._expiry_heap)
            if note.note_id not in self._resolved:
                self._record_judgement(note, expiry_us, ManiaJudgement.MISS, None)
        self.current_time_us = time_us

    def _advance_lane_cursor(self, lane: int) -> None:
        position = self._positions[lane]
        notes = self._lanes[lane]
        while position < len(notes) and notes[position].note_id in self._resolved:
            position += 1
        self._positions[lane] = position

    def _candidate_note(self, lane: int, time_us: int) -> tuple[int, TapNote, ManiaJudgement] | None:
        """Return the first ordered, hittable note that judges this press."""
        notes = self._lanes[lane]
        self._advance_lane_cursor(lane)
        for index in range(self._positions[lane], len(notes)):
            note = notes[index]
            if note.note_id in self._resolved:
                continue
            next_note = notes[index + 1] if index + 1 < len(notes) else None
            if (self.config.ruleset == "lazer" and next_note is not None
                    and time_us >= next_note.time_us):
                # Mirrors OrderedHitPolicy.IsHittable(): an old note cannot
                # hold input past the next note's start time.
                continue
            judgement = self.windows.press_judgement(time_us - note.time_us)
            if judgement is not None:
                return index, note, judgement
        return None

    def _force_miss_earlier_notes(self, lane: int, target_index: int,
                                  event_time_us: int) -> None:
        """Mirror OrderedHitPolicy.HandleHit for earlier tap notes."""
        notes = self._lanes[lane]
        target_time_us = notes[target_index].time_us
        for note in notes[:target_index]:
            if note.time_us >= target_time_us:
                break
            if note.note_id not in self._resolved:
                self._record_judgement(note, event_time_us, ManiaJudgement.MISS, None)
        self._advance_lane_cursor(lane)

    def apply_action(self, action: KeyAction) -> ActionRecord:
        """Apply one key transition and return its non-reward action record."""
        if not isinstance(action, KeyAction):
            raise TypeError("action must be a KeyAction")
        self.advance_to(action.time_us)
        lane = action.lane
        if action.kind is KeyActionKind.UP:
            if self._key_down[lane]:
                self._key_down[lane] = False
                disposition = ActionDisposition.RELEASE
            else:
                disposition = ActionDisposition.REPEAT_UP
            note_id = None
        elif self._key_down[lane]:
            disposition = ActionDisposition.REPEAT_DOWN
            note_id = None
        else:
            self._key_down[lane] = True
            candidate = self._candidate_note(lane, action.time_us)
            if candidate is None:
                disposition = ActionDisposition.NULL_PRESS
                note_id = None
            else:
                note_index, note, judgement = candidate
                self._record_judgement(
                    note, action.time_us, judgement, action.time_us - note.time_us)
                if (self.config.ruleset == "lazer"
                        and judgement is not ManiaJudgement.MISS):
                    # Lazer's column listener receives the new note result,
                    # then OrderedHitPolicy force-misses older unresolved notes.
                    self._force_miss_earlier_notes(lane, note_index, action.time_us)
                disposition = (ActionDisposition.EARLY_MISS if judgement is ManiaJudgement.MISS
                               else ActionDisposition.HIT)
                note_id = note.note_id
        record = ActionRecord(action, disposition, note_id)
        self._actions.append(record)
        self._events.append(record)
        return record

    def result(self) -> GameResult:
        """Return an immutable snapshot without forcing unplayed notes to miss."""
        key_down = (self._key_down[0], self._key_down[1],
                    self._key_down[2], self._key_down[3])
        return GameResult(tuple(self._judgements), tuple(self._actions),
                          tuple(self._events), key_down, self._total_notes)

    def finish(self) -> GameResult:
        """Advance through all remaining expiries and return the complete run."""
        if self._expiry_heap:
            last_expiry_us = max(item[0] for item in self._expiry_heap)
            self.advance_to(max(last_expiry_us, self.current_time_us)
                            if self.current_time_us is not None else last_expiry_us)
        return self.result()

    def state(self) -> dict:
        """Save exact game continuation without executable object serialization."""
        notes = [note for lane in self._lanes for note in lane]
        events = []
        for event in self._events:
            if isinstance(event, JudgementRecord):
                events.append({"kind": "judgement", "record": asdict(event)})
            else:
                events.append({"kind": "action", "record": asdict(event)})
        return {
            "identity": {"config": self.config.as_dict(),
                         "notes": [asdict(note) for note in notes]},
            "current_time_us": self.current_time_us,
            "positions": list(self._positions),
            "key_down": list(self._key_down),
            "resolved_note_ids": sorted(self._resolved),
            "expiry_heap": [[t, lane, note_id] for t, lane, note_id, _ in
                            sorted(self._expiry_heap)],
            "events": events,
        }

    def restore(self, state: dict) -> None:
        """Validate a game continuation before changing live state."""
        if set(state) != set(self.state()) or state["identity"] != self.state()["identity"]:
            raise ValueError("game checkpoint identity differs")
        now = state["current_time_us"]
        if now is not None and (type(now) is not int or now < 0):
            raise ValueError("invalid game clock")
        positions, key_down = state["positions"], state["key_down"]
        if (len(positions) != 4 or len(key_down) != 4
                or any(type(p) is not int or not 0 <= p <= len(self._lanes[i])
                       for i, p in enumerate(positions))
                or any(type(v) is not bool for v in key_down)):
            raise ValueError("invalid game lane state")
        note_by_id = {n.note_id: n for lane in self._lanes for n in lane}
        resolved = set(state["resolved_note_ids"])
        if len(resolved) != len(state["resolved_note_ids"]) or not resolved <= note_by_id.keys():
            raise ValueError("invalid resolved note IDs")
        expiry = []
        for row in state["expiry_heap"]:
            if (len(row) != 3 or row[2] not in note_by_id or
                    (row[0], row[1]) !=
                    (note_by_id[row[2]].time_us + self.windows.expiry_offset_us,
                     note_by_id[row[2]].lane) or
                    (now is not None and row[0] <= now)):
                raise ValueError("invalid game expiry event")
            expiry.append((row[0], row[1], row[2], note_by_id[row[2]]))
        if len({row[2] for row in expiry}) != len(expiry):
            raise ValueError("duplicate game expiry event")
        expected_expiry = {note_id for note_id, note in note_by_id.items()
                           if now is None or note.time_us + self.windows.expiry_offset_us > now}
        if {row[2] for row in expiry} != expected_expiry:
            raise ValueError("game expiry queue is incomplete")
        for lane, position in enumerate(positions):
            if any(note.note_id not in resolved for note in self._lanes[lane][:position]):
                raise ValueError("game cursor skipped an unresolved note")
        events = []
        for item in state["events"]:
            if item["kind"] == "judgement":
                row = item["record"]
                if ("logical_event_time_us" in row and "event_time_us" in row
                        and row["logical_event_time_us"] != row["event_time_us"]):
                    raise ValueError("conflicting logical judgement times in checkpoint")
                event = JudgementRecord(row["note_id"], row["lane"],
                                        row["note_time_us"],
                                        row.get("logical_event_time_us", row.get("event_time_us")),
                                        ManiaJudgement(row["judgement"]),
                                        row["hit_error_us"],
                                        row.get("ruleset", "stable_native"),
                                        row.get("observed_game_time_us"))
            elif item["kind"] == "action":
                row = item["record"]
                action = row["action"]
                event = ActionRecord(
                    KeyAction(action["time_us"], action["lane"],
                              KeyActionKind(action["kind"])),
                    ActionDisposition(row["disposition"]), row["note_id"])
            else:
                raise ValueError("unknown game event kind")
            events.append(event)
        judgements = [e for e in events if isinstance(e, JudgementRecord)]
        actions = [e for e in events if isinstance(e, ActionRecord)]
        if ({j.note_id for j in judgements} != resolved or
                len(judgements) != len(resolved) or
                (now is None and events) or
                any((e.logical_event_time_us if isinstance(e, JudgementRecord)
                     else e.action.time_us) > now for e in events)):
            raise ValueError("game ledger and resolved notes disagree")
        self.current_time_us = now
        self._positions = list(positions)
        self._key_down = list(key_down)
        self._resolved = resolved
        self._expiry_heap = expiry
        heapq.heapify(self._expiry_heap)
        self._events = events
        self._judgements = judgements
        self._actions = actions


def play(notes: Sequence[TapNote | HoldNote], actions: Iterable[KeyAction],
         config: OsuConfig | None = None) -> GameResult:
    """Replay actions by timestamp, preserving given order for exact ties."""
    environment = GameEnvironment(notes, config)
    indexed_actions = list(enumerate(actions))
    for _, action in indexed_actions:
        if not isinstance(action, KeyAction):
            raise TypeError("actions must contain KeyAction records")
    for _, action in sorted(indexed_actions, key=lambda item: (item[1].time_us, item[0])):
        environment.apply_action(action)
    return environment.finish()
