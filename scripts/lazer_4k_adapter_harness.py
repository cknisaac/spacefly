"""Build deterministic current-position episodes for the 4K adapter parity gate."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from project_b.osu import KeyActionKind, TapNote, load_config
from project_b.osu.adapter import (
    HeadlessMania4KTapAdapter,
    PolicyKeyTransition,
    PositionFrameObservation,
    VisibleNotePosition,
)
from project_b.osu.feedback import NoteCue
from project_b.osu.windows import ManiaHitWindows


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "lazer_mvp_4k_adapter_scenarios.json"
CONFIG_PATH = ROOT / "configs" / "lazer_mvp.yaml"


class PositionThresholdPolicy:
    """Deterministic seam fixture; outputs keys only from visible positions."""

    def __init__(self, *, dt_us: int, threshold: float, key_hold_us: int):
        self.dt_us = dt_us
        self.threshold = threshold
        self.key_hold_us = key_hold_us
        self.time_us = 0
        self.armed_lanes: set[int] = set()
        self.pending_releases: list[PolicyKeyTransition] = []
        self.started = False
        self.finished = False

    def begin(self, observation: PositionFrameObservation) -> None:
        if self.started or type(observation) is not PositionFrameObservation:
            raise RuntimeError("begin requires one initial position frame")
        self.started = True
        self._observe(observation)

    def step(self, observation: PositionFrameObservation) -> tuple[PolicyKeyTransition, ...]:
        if not self.started or self.finished:
            raise RuntimeError("begin() must precede step(), before finish()")
        if type(observation) is not PositionFrameObservation:
            raise TypeError("policy input must be a PositionFrameObservation")
        self.time_us += self.dt_us
        return self._observe(observation)

    def _observe(self, observation: PositionFrameObservation) -> tuple[PolicyKeyTransition, ...]:
        below = {
            note.lane for note in observation.visible_notes
            if note.position <= self.threshold + 1e-12
        }
        due = [action for action in self.pending_releases
               if action.episode_time_us <= self.time_us]
        self.pending_releases = [action for action in self.pending_releases
                                 if action.episode_time_us > self.time_us]
        fresh = sorted(below - self.armed_lanes)
        self.armed_lanes.intersection_update(below)
        self.armed_lanes.update(fresh)
        downs = [PolicyKeyTransition(self.time_us, lane, KeyActionKind.DOWN)
                 for lane in fresh]
        self.pending_releases.extend(
            PolicyKeyTransition(self.time_us + self.key_hold_us, lane, KeyActionKind.UP)
            for lane in fresh
        )
        return tuple(due + downs)

    def finish(self) -> tuple[PolicyKeyTransition, ...]:
        if not self.started or self.finished:
            raise RuntimeError("finish() requires one active episode")
        self.finished = True
        releases = tuple(sorted(self.pending_releases,
                                key=lambda row: (row.episode_time_us, row.lane)))
        self.pending_releases.clear()
        return releases

    def reproducibility_metadata(self) -> dict[str, Any]:
        return {
            "policy_class": type(self).__qualname__,
            "stochastic": False,
            "threshold": self.threshold,
            "key_hold_us": self.key_hold_us,
        }


def load_fixture() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def build_episode(scenario: dict[str, Any]):
    fixture = load_fixture()
    settings = fixture["adapter"]
    config = load_config(CONFIG_PATH)
    windows = ManiaHitWindows.from_od(config.od, config.ruleset)
    notes = tuple(TapNote(row["id"], row["lane"], row["time_us"])
                  for row in scenario["notes"])
    cues = tuple(sorted((
        NoteCue(
            note.note_id, note.lane,
            note.time_us - settings["visible_lead_us"],
            note.time_us,
            note.time_us + windows.expiry_offset_us,
        )
        for note in notes
    ), key=lambda cue: (cue.lane, cue.visible_from_us, cue.note_id)))
    adapter = HeadlessMania4KTapAdapter(
        notes, cues, config,
        episode_start_time_us=settings["episode_start_time_us"],
        observation_dt_us=settings["observation_dt_us"],
        good_window_us=int(windows.good_ms * 1000),
    )
    policy = PositionThresholdPolicy(
        dt_us=settings["observation_dt_us"],
        threshold=settings["scripted_policy_threshold"],
        key_hold_us=settings["scripted_key_hold_us"],
    )
    expiry_us = max(cue.visible_until_us for cue in cues)
    tick_count = math.ceil(
        (expiry_us - settings["episode_start_time_us"]) / settings["observation_dt_us"]
    )
    observations = []
    for tick in range(tick_count + 1):
        time_us = settings["episode_start_time_us"] + tick * settings["observation_dt_us"]
        visible = []
        for cue in cues:
            if cue.visible_from_us <= time_us <= cue.visible_until_us:
                note = next(row for row in notes if row.note_id == cue.note_id)
                position = min(
                    1.0,
                    max(0.0, (note.time_us - time_us) / settings["visible_lead_us"]),
                )
                visible.append(VisibleNotePosition(note.lane, position))
        observations.append(PositionFrameObservation(tuple(sorted(
            visible, key=lambda row: (row.lane, row.position)))))
    episode = adapter.run(policy, observations)
    return episode
