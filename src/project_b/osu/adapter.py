"""Position-only policy seam and deterministic headless mania adapter."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, fields
import math
from typing import Any, Protocol

from project_b.utils.time import require_time_us

from .config import OsuConfig
from .environment import play
from .feedback import (
    FirstActionAuditOutcome,
    NoteCue,
    reconstruct_first_actions,
)
from .types import (
    GameResult,
    HoldNote,
    KeyAction,
    KeyActionKind,
    TapNote,
    require_lane,
)
from .scoring import ManiaTapScore, calculate_tap_score


@dataclass(frozen=True, slots=True)
class PositionObservation:
    """One rendered sample. Scheduled time, judgement, and score are absent."""

    visible: bool
    lane: int
    position: float | None

    def __post_init__(self) -> None:
        if type(self.visible) is not bool:
            raise ValueError("visible must be a bool")
        require_lane(self.lane)
        if self.visible:
            if (type(self.position) not in (int, float)
                    or not math.isfinite(self.position)
                    or not 0.0 <= self.position <= 1.0):
                raise ValueError("a visible note needs a finite position in [0, 1]")
        elif self.position is not None:
            raise ValueError("an invisible note must not expose a position")


@dataclass(frozen=True, slots=True)
class VisibleNotePosition:
    """One visible object in the current frame, with no note identity or time."""

    lane: int
    position: float

    def __post_init__(self) -> None:
        require_lane(self.lane)
        if (type(self.position) not in (int, float)
                or not math.isfinite(self.position)
                or not 0.0 <= self.position <= 1.0):
            raise ValueError("position must be finite and in [0, 1]")


@dataclass(frozen=True, slots=True)
class PositionFrameObservation:
    """Current visible note positions across all lanes; empty means none visible."""

    visible_notes: tuple[VisibleNotePosition, ...]

    def __post_init__(self) -> None:
        if type(self.visible_notes) is not tuple:
            raise TypeError("visible_notes must be a tuple")
        if any(type(note) is not VisibleNotePosition for note in self.visible_notes):
            raise TypeError("visible_notes must contain VisibleNotePosition records")
        if tuple(sorted(self.visible_notes, key=lambda row: (row.lane, row.position))) != self.visible_notes:
            raise ValueError("visible notes must be ordered by lane and current position")


@dataclass(frozen=True, slots=True)
class PolicyKeyTransition:
    """Episode-relative key output, translated by the game adapter."""

    episode_time_us: int
    lane: int
    kind: KeyActionKind

    def __post_init__(self) -> None:
        require_time_us(self.episode_time_us, "episode_time_us")
        if self.episode_time_us < 0:
            raise ValueError("episode_time_us must be nonnegative")
        require_lane(self.lane)
        if not isinstance(self.kind, KeyActionKind):
            raise ValueError("kind must be KeyActionKind.DOWN or KeyActionKind.UP")


class PositionOnlyPolicy(Protocol):
    """Policy input/output contract shared by the headless and live adapters."""

    def begin(self, observation: PositionObservation) -> None: ...

    def step(self, observation: PositionObservation) -> Sequence[PolicyKeyTransition]: ...

    def finish(self) -> Sequence[PolicyKeyTransition]: ...


class PositionFramePolicy(Protocol):
    """A policy that consumes one simultaneous current-position frame per tick."""

    def begin(self, observation: PositionFrameObservation) -> None: ...

    def step(self, observation: PositionFrameObservation) -> Sequence[PolicyKeyTransition]: ...

    def finish(self) -> Sequence[PolicyKeyTransition]: ...


@dataclass(frozen=True, slots=True)
class HeadlessMvpEpisode:
    """Post-run trace. This record is returned only after policy execution ends."""

    game_config: OsuConfig
    episode_start_time_us: int
    observation_dt_us: int
    observations: tuple[PositionObservation | PositionFrameObservation, ...]
    policy_actions: tuple[PolicyKeyTransition, ...]
    game_actions: tuple[KeyAction, ...]
    game_result: GameResult
    score: ManiaTapScore
    first_action_audit: tuple[FirstActionAuditOutcome, ...]
    policy_metadata: dict[str, Any]
    beatmap_notes: tuple[TapNote, ...]
    note_cues: tuple[NoteCue, ...]
    adapter_name: str = "headless_osu_mania_tap"

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-ready replay artifact with policy and evaluator data split."""
        events = []
        for event in self.game_result.events:
            if hasattr(event, "judgement"):
                events.append({
                    "kind": "judgement",
                    "logical_event_time_us": event.logical_event_time_us,
                    "observed_game_time_us": event.observed_game_time_us,
                    "note_id": event.note_id,
                    "lane": event.lane,
                    "note_time_us": event.note_time_us,
                    "result": event.result_name,
                    "hit_error_us": event.hit_error_us,
                })
            else:
                events.append({
                    "kind": "action",
                    "event_time_us": event.action.time_us,
                    "lane": event.action.lane,
                    "action": event.action.kind.value,
                    "disposition": event.disposition.value,
                    "note_id": event.note_id,
                })
        observation_type = type(self.observations[0]) if self.observations else None
        if observation_type is PositionObservation:
            policy_input_fields = [field.name for field in fields(PositionObservation)]
            policy_observations = [
                {"tick": tick, "visible": row.visible, "lane": row.lane,
                 "position": row.position}
                for tick, row in enumerate(self.observations)
            ]
        elif observation_type is PositionFrameObservation:
            policy_input_fields = [field.name for field in fields(PositionFrameObservation)]
            policy_observations = [
                {"tick": tick, "visible_notes": [
                    {"lane": note.lane, "position": note.position}
                    for note in row.visible_notes
                ]}
                for tick, row in enumerate(self.observations)
            ]
        else:
            policy_input_fields = []
            policy_observations = []
        return {
            "schema_version": 1,
            "adapter": self.adapter_name,
            "game_config": self.game_config.as_dict(),
            "episode_start_time_us": self.episode_start_time_us,
            "observation_dt_us": self.observation_dt_us,
            "policy_input_fields": policy_input_fields,
            "policy_observations": policy_observations,
            "policy_metadata": self.policy_metadata,
            "policy_actions": [
                {"episode_time_us": row.episode_time_us, "lane": row.lane,
                 "kind": row.kind.value}
                for row in self.policy_actions
            ],
            "game_actions": [
                {"time_us": row.time_us, "lane": row.lane, "kind": row.kind.value}
                for row in self.game_actions
            ],
            "beatmap_notes": [
                {"id": row.note_id, "lane": row.lane, "time_us": row.time_us}
                for row in self.beatmap_notes
            ],
            "evaluator_note_cues": [
                {"note_id": row.note_id, "lane": row.lane,
                 "visible_from_us": row.visible_from_us,
                 "note_time_us": row.note_time_us,
                 "visible_until_us": row.visible_until_us}
                for row in self.note_cues
            ],
            "events": events,
            "score": self.score.as_dict(),
            "first_action_audit": [
                {"note_id": row.note_id, "lane": row.lane,
                 "note_time_us": row.note_time_us,
                 "first_down_us": row.first_down_us,
                 "signed_error_us": row.signed_error_us,
                 "first_disposition": row.first_disposition,
                 "category": row.category.value,
                 "extra_down_count": row.extra_down_count,
                 "final_judgement": row.final_judgement,
                 "judgement_time_us": row.judgement_time_us}
                for row in self.first_action_audit
            ],
        }


class HeadlessManiaTapAdapter:
    """Translate episode-relative policy transitions into the game-owned clock.

    This adapter runs a single tap-note MVP episode. It feeds one observation
    at a time to the policy and withholds beatmap schedule, game results,
    feedback, score, and evaluator cues until policy execution has ended.
    """

    def __init__(
        self,
        notes: Sequence[TapNote | HoldNote],
        cues: Sequence[NoteCue],
        game_config: OsuConfig,
        *,
        episode_start_time_us: int,
        observation_dt_us: int,
        good_window_us: int,
    ) -> None:
        if (len(notes) != 1 or not isinstance(notes[0], TapNote)
                or isinstance(notes[0], HoldNote)):
            raise ValueError("the L0.9b adapter supports exactly one tap note")
        if len(cues) != 1:
            raise ValueError("the L0.9b adapter requires one evaluator cue")
        if not isinstance(game_config, OsuConfig):
            raise TypeError("game_config must be OsuConfig")
        if game_config.ruleset != "lazer":
            raise ValueError("the L0.9b adapter requires the lazer ruleset")
        require_time_us(episode_start_time_us, "episode_start_time_us")
        if type(observation_dt_us) is not int or observation_dt_us <= 0:
            raise ValueError("observation_dt_us must be a positive integer")
        if type(good_window_us) is not int or good_window_us <= 0:
            raise ValueError("good_window_us must be a positive integer")
        note, cue = notes[0], cues[0]
        if (cue.note_id, cue.lane, cue.note_time_us) != (
                note.note_id, note.lane, note.time_us):
            raise ValueError("evaluator cue must identify the single beatmap tap note")
        if cue.visible_from_us != episode_start_time_us:
            raise ValueError("the note cue must begin at the policy episode clock origin")
        self.notes = (note,)
        self.cues = tuple(cues)
        self.game_config = game_config
        self.episode_start_time_us = episode_start_time_us
        self.observation_dt_us = observation_dt_us
        self.good_window_us = good_window_us

    def run(
        self,
        policy: PositionOnlyPolicy,
        observations: Iterable[PositionObservation],
    ) -> HeadlessMvpEpisode:
        """Execute a causal observation stream, then score/audit its actions."""
        policy_dt_us = getattr(policy, "dt_us", self.observation_dt_us)
        if policy_dt_us != self.observation_dt_us:
            raise ValueError("policy integration step differs from observation cadence")
        iterator = iter(observations)
        try:
            first = next(iterator)
        except StopIteration as exc:
            raise ValueError("an episode needs at least one visible observation") from exc
        if type(first) is not PositionObservation or not first.visible:
            raise ValueError("the first episode observation must be visible")
        if first.lane != self.notes[0].lane:
            raise ValueError("observation lane differs from the one-note beatmap")

        observed = [first]
        policy_actions: list[PolicyKeyTransition] = []
        last_action_time_us = -1
        policy.begin(first)

        def collect(actions: Sequence[PolicyKeyTransition]) -> None:
            nonlocal last_action_time_us
            for action in actions:
                if not isinstance(action, PolicyKeyTransition):
                    raise TypeError("policy outputs must be PolicyKeyTransition records")
                if action.lane != self.notes[0].lane:
                    raise ValueError("policy action lane differs from the one-note beatmap")
                if action.episode_time_us < last_action_time_us:
                    raise ValueError("policy transition times must be nondecreasing")
                policy_actions.append(action)
                last_action_time_us = action.episode_time_us

        for observation in iterator:
            if type(observation) is not PositionObservation:
                raise TypeError("observation stream must contain PositionObservation records")
            if observation.lane != self.notes[0].lane:
                raise ValueError("observation lane differs from the one-note beatmap")
            observed.append(observation)
            collect(policy.step(observation))
        collect(policy.finish())

        game_actions = tuple(
            KeyAction(self.episode_start_time_us + action.episode_time_us,
                      action.lane, action.kind)
            for action in policy_actions
        )
        game_result = play(self.notes, game_actions, self.game_config)
        score = calculate_tap_score(self.notes, game_result, self.game_config)
        audit = reconstruct_first_actions(
            self.cues, game_result, good_window_us=self.good_window_us)
        metadata = getattr(policy, "reproducibility_metadata", None)
        policy_metadata = metadata() if callable(metadata) else {
            "policy_class": type(policy).__qualname__,
            "stochastic": None,
        }
        if not isinstance(policy_metadata, dict):
            raise TypeError("policy reproducibility_metadata() must return a dict")
        return HeadlessMvpEpisode(
            self.game_config, self.episode_start_time_us, self.observation_dt_us,
            tuple(observed), tuple(policy_actions), game_actions, game_result,
            score, audit, policy_metadata, self.notes, self.cues,
        )


class HeadlessMania4KTapAdapter:
    """Run a multi-lane current-position policy against the headless tap game.

    Each policy tick receives only currently visible note positions and lanes.
    Beatmap timing, score, judgements, and evaluator cues remain withheld until
    the policy has finished. Multiple visible objects may share a lane.
    """

    def __init__(
        self,
        notes: Sequence[TapNote | HoldNote],
        cues: Sequence[NoteCue],
        game_config: OsuConfig,
        *,
        episode_start_time_us: int,
        observation_dt_us: int,
        good_window_us: int,
    ) -> None:
        if not notes or any(not isinstance(note, TapNote) or isinstance(note, HoldNote)
                            for note in notes):
            raise ValueError("the 4K adapter requires one or more tap notes")
        if not isinstance(game_config, OsuConfig):
            raise TypeError("game_config must be OsuConfig")
        if game_config.ruleset != "lazer":
            raise ValueError("the 4K adapter requires the lazer ruleset")
        require_time_us(episode_start_time_us, "episode_start_time_us")
        if type(observation_dt_us) is not int or observation_dt_us <= 0:
            raise ValueError("observation_dt_us must be a positive integer")
        if type(good_window_us) is not int or good_window_us <= 0:
            raise ValueError("good_window_us must be a positive integer")

        note_by_id = {note.note_id: note for note in notes}
        if len(note_by_id) != len(notes):
            raise ValueError("beatmap note IDs must be unique")
        if not cues or len(cues) != len(notes):
            raise ValueError("the 4K adapter requires one evaluator cue per tap note")
        ordered_cues = tuple(sorted(
            cues, key=lambda cue: (cue.lane, cue.visible_from_us, cue.note_id)))
        if ordered_cues != tuple(cues):
            raise ValueError("note cues must be ordered by lane and visibility onset")
        cue_by_id = {cue.note_id: cue for cue in cues}
        if set(cue_by_id) != set(note_by_id):
            raise ValueError("evaluator cues must identify every beatmap tap note")
        for note_id, note in note_by_id.items():
            cue = cue_by_id[note_id]
            if (cue.lane, cue.note_time_us) != (note.lane, note.time_us):
                raise ValueError("evaluator cue does not match its beatmap tap note")
            if cue.visible_from_us < episode_start_time_us:
                raise ValueError("evaluator cue begins before the policy episode")
        if any(note.time_us < episode_start_time_us for note in notes):
            raise ValueError("tap note begins before the policy episode")

        self.notes = tuple(notes)
        self.cues = tuple(cues)
        self.game_config = game_config
        self.episode_start_time_us = episode_start_time_us
        self.observation_dt_us = observation_dt_us
        self.good_window_us = good_window_us

    def run(
        self,
        policy: PositionFramePolicy,
        observations: Iterable[PositionFrameObservation],
    ) -> HeadlessMvpEpisode:
        """Execute simultaneous position frames, then judge and score outputs."""
        policy_dt_us = getattr(policy, "dt_us", self.observation_dt_us)
        if policy_dt_us != self.observation_dt_us:
            raise ValueError("policy integration step differs from observation cadence")
        iterator = iter(observations)
        try:
            first = next(iterator)
        except StopIteration as exc:
            raise ValueError("an episode needs at least one observation frame") from exc
        if type(first) is not PositionFrameObservation:
            raise TypeError("frame stream must contain PositionFrameObservation records")

        observed = [first]
        policy_actions: list[PolicyKeyTransition] = []
        last_action_time_us = -1
        policy.begin(first)

        def collect(actions: Sequence[PolicyKeyTransition]) -> None:
            nonlocal last_action_time_us
            for action in actions:
                if not isinstance(action, PolicyKeyTransition):
                    raise TypeError("policy outputs must be PolicyKeyTransition records")
                if action.episode_time_us < last_action_time_us:
                    raise ValueError("policy transition times must be nondecreasing")
                policy_actions.append(action)
                last_action_time_us = action.episode_time_us

        for observation in iterator:
            if type(observation) is not PositionFrameObservation:
                raise TypeError("frame stream must contain PositionFrameObservation records")
            observed.append(observation)
            collect(policy.step(observation))
        collect(policy.finish())

        game_actions = tuple(
            KeyAction(self.episode_start_time_us + action.episode_time_us,
                      action.lane, action.kind)
            for action in policy_actions
        )
        game_result = play(self.notes, game_actions, self.game_config)
        score = calculate_tap_score(self.notes, game_result, self.game_config)
        audit = reconstruct_first_actions(
            self.cues, game_result, good_window_us=self.good_window_us)
        metadata = getattr(policy, "reproducibility_metadata", None)
        policy_metadata = metadata() if callable(metadata) else {
            "policy_class": type(policy).__qualname__,
            "stochastic": None,
        }
        if not isinstance(policy_metadata, dict):
            raise TypeError("policy reproducibility_metadata() must return a dict")
        return HeadlessMvpEpisode(
            self.game_config, self.episode_start_time_us, self.observation_dt_us,
            tuple(observed), tuple(policy_actions), game_actions, game_result,
            score, audit, policy_metadata, self.notes, self.cues,
            adapter_name="headless_osu_mania_4k_tap",
        )
