"""First-action identity and artificial PAM request state for MVP-C1.

This layer consumes emitted DOWNs and game dispositions; it never writes a
synapse. PAM requests are distinct from subsequent actual PAM spikes.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, replace

from project_b.osu.types import ActionDisposition
from project_b.utils.time import require_time_us


@dataclass(frozen=True, slots=True)
class NoteWindow:
    note_id: str
    visible_from_us: int
    hit_us: int

    def __post_init__(self) -> None:
        if not self.note_id or self.visible_from_us < 0 or self.hit_us <= self.visible_from_us:
            raise ValueError("invalid note window")
        require_time_us(self.visible_from_us)
        require_time_us(self.hit_us)


@dataclass(frozen=True, slots=True)
class FirstActionOutcome:
    note_id: str
    first_down_us: int | None
    signed_error_us: int | None
    category: str
    game_disposition: str | None
    extra_downs: int


@dataclass(frozen=True, slots=True)
class FeedbackDecision:
    time_us: int
    outcome: FirstActionOutcome
    utility: float
    expected_before: float
    rpe: float
    pam_request: float
    route: str


@dataclass(frozen=True, slots=True)
class PamPulse:
    origin_note_id: str
    start_us: int
    end_us: int
    amplitude: float
    route: str


class FirstActionTracker:
    """Assign the first emitted DOWN to the most recent visible isolated cue."""

    def __init__(self, notes: tuple[NoteWindow, ...], success_window_us: int = 73_000):
        if (not notes or len({n.note_id for n in notes}) != len(notes)
                or tuple(sorted(notes, key=lambda n: n.visible_from_us)) != notes
                or any(b.visible_from_us <= a.hit_us for a, b in zip(notes, notes[1:]))):
            raise ValueError("first-action notes must be unique, sorted and isolated")
        if require_time_us(success_window_us) <= 0:
            raise ValueError("success window must be positive")
        self.notes = notes
        self.success_window_us = success_window_us
        self.next_note_index = 0
        self.active_note_id: str | None = None
        self.first_down_us: int | None = None
        self.first_disposition: str | None = None
        self.first_outcome: FirstActionOutcome | None = None
        self.extra_downs = 0
        self.last_time_us = 0
        self.outcomes: list[FirstActionOutcome] = []
        self.background_downs: list[int] = []

    def _finish_active(self) -> FirstActionOutcome | None:
        if self.active_note_id is None:
            return None
        note = self.notes[self.next_note_index - 1]
        outcome = (FirstActionOutcome(note.note_id, None, None, "no_down", None, 0)
                   if self.first_outcome is None else
                   replace(self.first_outcome, extra_downs=self.extra_downs))
        self.outcomes.append(outcome)
        self.active_note_id = None
        self.first_down_us = None
        self.first_disposition = None
        self.first_outcome = None
        self.extra_downs = 0
        return outcome

    def on_visible_onset(self, note_id: str, time_us: int) -> FirstActionOutcome | None:
        require_time_us(time_us)
        if time_us < self.last_time_us or self.next_note_index >= len(self.notes):
            raise ValueError("cue onset is out of order")
        note = self.notes[self.next_note_index]
        if note.note_id != note_id or note.visible_from_us != time_us:
            raise ValueError("cue onset differs from immutable note schedule")
        previous = self._finish_active()
        self.active_note_id = note_id
        self.next_note_index += 1
        self.last_time_us = time_us
        return previous

    def on_down(self, time_us: int,
                disposition: ActionDisposition | None) -> FirstActionOutcome | None:
        require_time_us(time_us)
        if time_us < self.last_time_us:
            raise ValueError("DOWN is out of order")
        if disposition is not None and not isinstance(disposition, ActionDisposition):
            raise ValueError("invalid game disposition")
        self.last_time_us = time_us
        if self.active_note_id is None:
            self.background_downs.append(time_us)
            return None
        elif self.first_down_us is None:
            self.first_down_us = time_us
            self.first_disposition = None if disposition is None else disposition.value
            note = self.notes[self.next_note_index - 1]
            error = time_us - note.hit_us
            if abs(error) <= self.success_window_us:
                category = "success"
            elif error < 0:
                category = ("too_early_null" if disposition is ActionDisposition.NULL_PRESS
                            else "early_judged")
            else:
                category = "late"
            self.first_outcome = FirstActionOutcome(
                note.note_id, time_us, error, category, self.first_disposition, 0)
            return self.first_outcome
        else:
            self.extra_downs += 1
            return None

    def finish(self, time_us: int) -> FirstActionOutcome | None:
        require_time_us(time_us)
        if time_us < self.last_time_us:
            raise ValueError("finish is out of order")
        self.last_time_us = time_us
        return self._finish_active()

    def state(self) -> dict:
        return {"next_note_index": self.next_note_index,
                "active_note_id": self.active_note_id,
                "first_down_us": self.first_down_us,
                "first_disposition": self.first_disposition,
                "first_outcome": None if self.first_outcome is None else asdict(self.first_outcome),
                "extra_downs": self.extra_downs,
                "last_time_us": self.last_time_us,
                "outcomes": [asdict(o) for o in self.outcomes],
                "background_downs": list(self.background_downs)}

    def restore(self, state: dict) -> None:
        clone = FirstActionTracker(self.notes, self.success_window_us)
        clone.next_note_index = state["next_note_index"]
        clone.active_note_id = state["active_note_id"]
        clone.first_down_us = state["first_down_us"]
        clone.first_disposition = state["first_disposition"]
        clone.first_outcome = (None if state["first_outcome"] is None else
                               FirstActionOutcome(**state["first_outcome"]))
        clone.extra_downs = state["extra_downs"]
        clone.last_time_us = state["last_time_us"]
        clone.outcomes = [FirstActionOutcome(**o) for o in state["outcomes"]]
        clone.background_downs = list(state["background_downs"])
        if (not 0 <= clone.next_note_index <= len(self.notes)
                or clone.extra_downs < 0 or clone.last_time_us < 0
                or clone.active_note_id != (None if clone.next_note_index == 0
                                           or len(clone.outcomes) == clone.next_note_index
                                           else self.notes[clone.next_note_index - 1].note_id)
                or len(clone.outcomes) not in (clone.next_note_index - 1,
                                               clone.next_note_index)):
            raise ValueError("invalid first-action continuation state")
        self.__dict__.update(clone.__dict__)


class FeedbackScheduler:
    """B2 utility/RPE and early-flush versus next-visible-cue PAM requests."""

    def __init__(self, sensory_latency_us: int = 25_000,
                 pulse_duration_us: int = 20_000, alpha: float = 0.1,
                 *, enabled: bool = True):
        if (sensory_latency_us <= 0 or pulse_duration_us <= 0
                or not math.isfinite(alpha) or not 0 < alpha <= 1):
            raise ValueError("invalid feedback constants")
        self.sensory_latency_us = sensory_latency_us
        self.pulse_duration_us = pulse_duration_us
        self.alpha = alpha
        self.enabled = enabled
        self.expected_utility = 1.0
        self.pending_late: FeedbackDecision | None = None
        self.pending_early: tuple[int, FeedbackDecision] | None = None
        self.active_pulses: list[PamPulse] = []
        self.pulse_records: list[PamPulse] = []
        self.decisions: list[FeedbackDecision] = []
        self.last_time_us = 0
        self.discarded_late: list[str] = []

    def resolve(self, outcome: FirstActionOutcome, time_us: int) -> FeedbackDecision:
        require_time_us(time_us)
        if time_us < self.last_time_us or any(d.outcome.note_id == outcome.note_id
                                              for d in self.decisions):
            raise ValueError("feedback outcome is duplicate or out of order")
        utility = 1.0 if outcome.category == "success" else 0.0
        prior = self.expected_utility
        rpe = utility - prior
        request = min(1.0, max(0.0, -rpe)) if self.enabled else 0.0
        route = ("off_frozen" if not self.enabled else
                 "early_flush" if outcome.category == "early_judged" else
                 "next_visible_prime" if outcome.category in ("late", "no_down") else
                 "none")
        if request > 0 and route == "next_visible_prime" and self.pending_late is not None:
            raise ValueError("unconsumed late prime")
        if request > 0 and route == "early_flush" and self.pending_early is not None:
            raise ValueError("unconsumed early flush")
        decision = FeedbackDecision(time_us, outcome, utility, prior, rpe, request, route)
        if self.enabled:
            self.expected_utility = prior + self.alpha * rpe
        self.decisions.append(decision)
        if request > 0 and route == "early_flush":
            self.pending_early = (time_us + self.sensory_latency_us, decision)
        elif request > 0 and route == "next_visible_prime":
            self.pending_late = decision
        self.last_time_us = time_us
        return decision

    def on_visible_onset(self, time_us: int) -> PamPulse | None:
        require_time_us(time_us)
        if time_us < self.last_time_us:
            raise ValueError("visible onset is out of order")
        self.last_time_us = time_us
        decision = self.pending_late
        self.pending_late = None
        if decision is None:
            return None
        pulse = PamPulse(decision.outcome.note_id, time_us,
                         time_us + self.pulse_duration_us,
                         decision.pam_request, "next_visible_prime")
        self.active_pulses.append(pulse)
        self.pulse_records.append(pulse)
        return pulse

    def advance_to(self, time_us: int) -> tuple[PamPulse, ...]:
        require_time_us(time_us)
        if time_us < self.last_time_us:
            raise ValueError("feedback clock reversal")
        started = []
        if self.pending_early is not None and self.pending_early[0] <= time_us:
            due, decision = self.pending_early
            pulse = PamPulse(decision.outcome.note_id, due,
                             due + self.pulse_duration_us,
                             decision.pam_request, "early_flush")
            self.active_pulses.append(pulse)
            self.pulse_records.append(pulse)
            started.append(pulse)
            self.pending_early = None
        self.active_pulses = [p for p in self.active_pulses if p.end_us > time_us]
        self.last_time_us = time_us
        return tuple(started)

    def pam_current(self, time_us: int) -> float:
        return 2.0 * sum(p.amplitude for p in self.active_pulses
                         if p.start_us <= time_us < p.end_us)

    def discard_end_of_sequence(self) -> None:
        if self.pending_late is not None:
            self.discarded_late.append(self.pending_late.outcome.note_id)
            self.pending_late = None

    def state(self) -> dict:
        return {
            "expected_utility": self.expected_utility,
            "enabled": self.enabled,
            "pending_late": None if self.pending_late is None else asdict(self.pending_late),
            "pending_early": None if self.pending_early is None else
                             [self.pending_early[0], asdict(self.pending_early[1])],
            "active_pulses": [asdict(p) for p in self.active_pulses],
            "pulse_records": [asdict(p) for p in self.pulse_records],
            "decisions": [asdict(d) for d in self.decisions],
            "last_time_us": self.last_time_us,
            "discarded_late": list(self.discarded_late),
        }

    @staticmethod
    def _decision(data: dict) -> FeedbackDecision:
        return FeedbackDecision(data["time_us"], FirstActionOutcome(**data["outcome"]),
                                data["utility"], data["expected_before"],
                                data["rpe"], data["pam_request"], data["route"])

    def restore(self, state: dict) -> None:
        if type(state.get("enabled")) is not bool or state["enabled"] != self.enabled:
            raise ValueError("feedback mode differs")
        clone = FeedbackScheduler(self.sensory_latency_us,
                                  self.pulse_duration_us, self.alpha,
                                  enabled=self.enabled)
        clone.expected_utility = state["expected_utility"]
        clone.pending_late = (None if state["pending_late"] is None else
                              self._decision(state["pending_late"]))
        clone.pending_early = (None if state["pending_early"] is None else
                               (state["pending_early"][0],
                                self._decision(state["pending_early"][1])))
        clone.active_pulses = [PamPulse(**p) for p in state["active_pulses"]]
        clone.pulse_records = [PamPulse(**p) for p in state["pulse_records"]]
        clone.decisions = [self._decision(d) for d in state["decisions"]]
        clone.last_time_us = state["last_time_us"]
        clone.discarded_late = list(state["discarded_late"])
        if (not math.isfinite(clone.expected_utility)
                or not 0 <= clone.expected_utility <= 1
                or clone.last_time_us < 0
                or any(not math.isfinite(d.pam_request) or
                       not 0 <= d.pam_request <= 1 for d in clone.decisions)
                or any(not math.isfinite(p.amplitude) or
                       not 0 <= p.amplitude <= 1 or p.end_us <= p.start_us
                       for p in clone.active_pulses)):
            raise ValueError("invalid feedback continuation state")
        self.__dict__.update(clone.__dict__)
