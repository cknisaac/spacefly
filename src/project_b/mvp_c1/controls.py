"""Declared A4 control switches and causal artificial-PAM routing."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .feedback import PamPulse


@dataclass(frozen=True, slots=True)
class ControlPolicy:
    plasticity: str = "on"
    teaching: str = "aligned"
    dan: str = "on"
    eligibility: str = "on"

    def __post_init__(self) -> None:
        if (self.plasticity not in ("on", "off") or
                self.teaching not in ("aligned", "wrong_note") or
                self.dan not in ("on", "disabled") or
                self.eligibility not in ("on", "disabled")):
            raise ValueError("unsupported MVP control policy")

    def active_switches(self) -> tuple[str, ...]:
        baseline = ControlPolicy()
        return tuple(key for key, value in asdict(self).items()
                     if value != getattr(baseline, key))


@dataclass(frozen=True, slots=True)
class RoutedPamPulse:
    origin_note_id: str
    source_start_us: int
    actual_start_us: int
    end_us: int
    amplitude: float
    route: str
    recipient_note_id: str | None


class PamControlRouter:
    """Use aligned B2 pulses or shift each pulse to the next actual cue.

    The wrong-note arm waits for an observed later onset; it never reads a
    future note timestamp to choose delivery. One queued pulse is assigned per
    later onset in FIFO source order.
    """

    def __init__(self, teaching: str = "aligned"):
        if teaching not in ("aligned", "wrong_note"):
            raise ValueError("invalid PAM route")
        self.teaching = teaching
        self.source_cursor = 0
        self.pending: list[PamPulse] = []
        self.deliveries: list[RoutedPamPulse] = []
        self.time_us = 0

    def advance_to(self, time_us: int, source_pulses: list[PamPulse],
                   visible_onset_note_id: str | None = None) -> tuple[RoutedPamPulse, ...]:
        if type(time_us) is not int or time_us < self.time_us or self.source_cursor > len(source_pulses):
            raise ValueError("PAM router clock or source cursor differs")
        new = source_pulses[self.source_cursor:]
        if any(p.start_us > time_us for p in new):
            raise ValueError("PAM source pulse is from the future")
        self.source_cursor = len(source_pulses)
        delivered = []
        if self.teaching == "aligned":
            for pulse in new:
                routed = RoutedPamPulse(pulse.origin_note_id, pulse.start_us,
                                        pulse.start_us, pulse.end_us, pulse.amplitude,
                                        "aligned", None)
                self.deliveries.append(routed)
                delivered.append(routed)
        else:
            self.pending.extend(new)
            if (visible_onset_note_id is not None and self.pending and
                    self.pending[0].start_us < time_us and
                    visible_onset_note_id != self.pending[0].origin_note_id):
                pulse = self.pending.pop(0)
                routed = RoutedPamPulse(pulse.origin_note_id, pulse.start_us,
                                        time_us, time_us + pulse.end_us - pulse.start_us,
                                        pulse.amplitude, "wrong_note", visible_onset_note_id)
                self.deliveries.append(routed)
                delivered.append(routed)
        self.time_us = time_us
        return tuple(delivered)

    def current(self, time_us: int) -> float:
        return 2.0 * sum(p.amplitude for p in self.deliveries
                         if p.actual_start_us <= time_us < p.end_us)

    def state(self) -> dict:
        return {"teaching": self.teaching, "time_us": self.time_us,
                "source_cursor": self.source_cursor,
                "pending": [asdict(p) for p in self.pending],
                "deliveries": [asdict(p) for p in self.deliveries]}

    def restore(self, state: dict, source_pulses: list[PamPulse]) -> None:
        if set(state) != set(self.state()) or state["teaching"] != self.teaching:
            raise ValueError("PAM router schema or identity differs")
        clone = PamControlRouter(self.teaching)
        t, cursor = state["time_us"], state["source_cursor"]
        if (type(t) is not int or t < 0 or type(cursor) is not int or
                not 0 <= cursor <= len(source_pulses)):
            raise ValueError("invalid PAM router clock or source cursor")
        clone.pending = [PamPulse(**row) for row in state["pending"]]
        clone.deliveries = [RoutedPamPulse(**row) for row in state["deliveries"]]
        if (any(p.start_us > t for p in clone.pending) or
                any(p.actual_start_us > t or p.end_us <= p.actual_start_us or
                    not 0 <= p.amplitude <= 1 for p in clone.deliveries) or
                (self.teaching == "aligned" and clone.pending) or
                (self.teaching == "wrong_note" and any(
                    p.route != "wrong_note" or p.recipient_note_id in (None, p.origin_note_id)
                    for p in clone.deliveries))):
            raise ValueError("invalid PAM routed pulse state")
        clone.source_cursor = cursor
        clone.time_us = t
        self.__dict__.update(clone.__dict__)
