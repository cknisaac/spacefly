"""Sparse event propagation with exact between-event LIF state integration."""

from __future__ import annotations

import heapq
import hashlib
import json
import math
from dataclasses import asdict, dataclass
from typing import Iterable, Sequence

from project_b.neurons import LIFParameters, advance_lif
from project_b.plasticity import (Gamma4BatchRecord, Gamma4Plasticity,
                                 ThreeFactorPlasticity, WeightChange)
from project_b.synapses import SparseGraph
from project_b.utils.time import require_time_us


@dataclass(frozen=True, slots=True)
class SpikeEvent:
    time_us: int
    neuron_index: int
    voltage_before_reset_mv: float


@dataclass(frozen=True, slots=True)
class SynapticArrival:
    time_us: int
    pre: int
    post: int
    edge_slot: int
    weight_mv: float


@dataclass(frozen=True, slots=True)
class VoltageSample:
    time_us: int
    neuron_index: int
    voltage_before_reset_mv: float
    voltage_after_reset_mv: float
    synaptic_drive_mv: float
    refractory_until_us: int
    spiked: bool


@dataclass(frozen=True, slots=True)
class SimulationSnapshot:
    time_us: int
    voltage_mv: tuple[float, ...]
    synaptic_drive_mv: tuple[float, ...]
    refractory_until_us: tuple[int, ...]
    spike_counts: tuple[int, ...]
    spikes: tuple[SpikeEvent, ...]
    arrivals: tuple[SynapticArrival, ...]
    voltage_trace: tuple[VoltageSample, ...]
    queued_arrivals: int


@dataclass(frozen=True, slots=True)
class SimulationDiagnostics:
    """Counters that avoid recording every spike or arrival at scale."""

    scheduled_events: int
    delivered_events: int
    peak_queued_events: int
    unique_active_synapses: int | None
    spike_counts_by_tick: tuple[int, ...]


class SpikingSimulator:
    """Deterministic CPU reference model with O(N+E+queued events) state.

    Neurons are sampled for threshold at fixed integer-µs ticks. Synaptic
    arrivals retain their exact integer timestamp and split the subthreshold
    integration interval. Positive delays forbid zero-time causal loops.
    """

    def __init__(
        self,
        parameters: Sequence[LIFParameters],
        graph: SparseGraph,
        external_drive_mv: Sequence[float],
        *,
        dt_us: int = 1_000,
        record_neurons: Iterable[int] = (),
        record_spikes: bool = False,
        record_arrivals: bool = False,
        track_active_synapses: bool = False,
        max_queued_events: int | None = None,
        max_scheduled_events: int | None = None,
        plasticity: ThreeFactorPlasticity | Gamma4Plasticity | None = None,
    ) -> None:
        if require_time_us(dt_us, "dt_us") <= 0:
            raise ValueError("dt_us must be positive")
        if len(parameters) != graph.neuron_count:
            raise ValueError("one LIF parameter set is required per neuron")
        if len(external_drive_mv) != graph.neuron_count:
            raise ValueError("one external drive is required per neuron")
        if not all(isinstance(p, LIFParameters) for p in parameters):
            raise TypeError("parameters must contain LIFParameters records")
        if not all(math.isfinite(value) for value in external_drive_mv):
            raise ValueError("external drives must be finite")
        if plasticity is not None and plasticity.graph is not graph:
            raise ValueError("plasticity must refer to the simulator's graph")
        recorded = sorted(set(record_neurons))
        if any(type(i) is not int or not 0 <= i < graph.neuron_count for i in recorded):
            raise ValueError("record_neurons contains an invalid neuron index")
        self.parameters = tuple(parameters)
        self.graph = graph
        self.external_drive_mv = tuple(float(value) for value in external_drive_mv)
        self.dt_us = dt_us
        self.plasticity = plasticity
        self.last_plasticity_record: Gamma4BatchRecord | None = None
        self.current_time_us = 0
        self.voltage_mv = [p.v_rest_mv for p in parameters]
        self.synaptic_drive_mv = [0.0] * graph.neuron_count
        self.refractory_until_us = [0] * graph.neuron_count
        self.spiked_this_tick = [False] * graph.neuron_count
        self.spike_counts = [0] * graph.neuron_count
        self._record_neurons = tuple(recorded)
        self._record_spikes = record_spikes
        self._record_arrivals = record_arrivals
        self._spikes: list[SpikeEvent] = []
        self._arrivals: list[SynapticArrival] = []
        self._voltage_trace = [
            VoltageSample(0, i, self.voltage_mv[i], self.voltage_mv[i], 0.0, 0, False)
            for i in recorded
        ]
        # Weight is captured at spike emission, so a later dopamine event
        # cannot retroactively change an already scheduled arrival.
        # (arrival time, post, pre, canonical edge slot, sequence, weight)
        self._queue: list[tuple[int, int, int, int, int, float]] = []
        self._sequence = 0
        self._delivered_events = 0
        self._peak_queued_events = 0
        self._active_edge_slots: set[int] | None = set() if track_active_synapses else None
        self._spike_counts_by_tick: list[int] = []
        if max_queued_events is not None and max_queued_events <= 0:
            raise ValueError("max_queued_events must be positive")
        if max_scheduled_events is not None and max_scheduled_events <= 0:
            raise ValueError("max_scheduled_events must be positive")
        self.max_queued_events = max_queued_events
        self.max_scheduled_events = max_scheduled_events

    def _advance_neuron(self, i: int, start_us: int, end_us: int) -> None:
        """Update one neuron between exact event times, without a spike."""
        if end_us < start_us:
            raise AssertionError("internal time reversal")
        if start_us == end_us:
            return
        parameters = self.parameters[i]
        cursor_us = start_us
        refractory_end_us = self.refractory_until_us[i]
        if cursor_us < refractory_end_us:
            clamp_end_us = min(end_us, refractory_end_us)
            elapsed_us = clamp_end_us - cursor_us
            self.synaptic_drive_mv[i] *= math.exp(-elapsed_us / parameters.tau_syn_us)
            self.voltage_mv[i] = parameters.v_reset_mv
            cursor_us = clamp_end_us
        if cursor_us < end_us:
            voltage, synaptic = advance_lif(
                self.voltage_mv[i], self.synaptic_drive_mv[i],
                self.external_drive_mv[i], end_us - cursor_us, parameters)
            self.voltage_mv[i] = voltage
            self.synaptic_drive_mv[i] = synaptic

    def _schedule_outgoing(self, pre: int, spike_time_us: int) -> None:
        for slot in self.graph.outgoing_slots(pre):
            arrival_us = require_time_us(
                spike_time_us + int(self.graph.delays_us[slot]), "arrival_time_us")
            weight_mv = (self.plasticity.effective_weight(slot)
                         if self.plasticity is not None
                         else float(self.graph.weights_mv[slot]))
            heapq.heappush(self._queue, (
                arrival_us, int(self.graph.post_indices[slot]), pre, slot,
                self._sequence, weight_mv))
            self._sequence += 1
            if self._active_edge_slots is not None:
                self._active_edge_slots.add(slot)
        self._peak_queued_events = max(self._peak_queued_events, len(self._queue))

    def _step(self, tick_us: int) -> None:
        arrivals_by_post: dict[int, list[tuple[int, float]]] = {}
        while self._queue and self._queue[0][0] <= tick_us:
            arrival_us, post, pre, slot, _, weight_mv = heapq.heappop(self._queue)
            self._delivered_events += 1
            arrivals_by_post.setdefault(post, []).append(
                (arrival_us, weight_mv))
            if self._record_arrivals:
                self._arrivals.append(SynapticArrival(
                    arrival_us, pre, post, slot, weight_mv))
        for i in range(self.graph.neuron_count):
            cursor_us = self.current_time_us
            for arrival_us, weight_mv in arrivals_by_post.get(i, ()):
                self._advance_neuron(i, cursor_us, arrival_us)
                cursor_us = arrival_us
                self.synaptic_drive_mv[i] += weight_mv
                if not math.isfinite(self.synaptic_drive_mv[i]):
                    raise ArithmeticError("non-finite synaptic drive")
            self._advance_neuron(i, cursor_us, tick_us)
        self.current_time_us = tick_us
        pre_reset = {i: self.voltage_mv[i] for i in self._record_neurons}
        spiking_indices: list[int] = []
        for i, parameters in enumerate(self.parameters):
            spiked = (tick_us >= self.refractory_until_us[i]
                      and self.voltage_mv[i] >= parameters.v_threshold_mv)
            self.spiked_this_tick[i] = spiked
            if spiked:
                spiking_indices.append(i)
                before_reset = self.voltage_mv[i]
                self.voltage_mv[i] = parameters.v_reset_mv
                self.refractory_until_us[i] = require_time_us(
                    tick_us + parameters.refractory_us, "refractory_until_us")
                self.spike_counts[i] += 1
                if self._record_spikes:
                    self._spikes.append(SpikeEvent(tick_us, i, before_reset))
        self._spike_counts_by_tick.append(len(spiking_indices))
        # Check the entire spike batch before placing any arrivals. A safety
        # stop therefore leaves complete per-tick spike counts and no partial
        # batch of outgoing events.
        proposed_events = sum(len(self.graph.outgoing_slots(i)) for i in spiking_indices)
        if (self.max_scheduled_events is not None
                and self._sequence + proposed_events > self.max_scheduled_events):
            raise RuntimeError("scheduled event safety limit would be exceeded")
        if (self.max_queued_events is not None
                and len(self._queue) + proposed_events > self.max_queued_events):
            raise RuntimeError("queued event safety limit would be exceeded")
        for i in spiking_indices:
            self._schedule_outgoing(i, tick_us)
        self.last_plasticity_record = None
        if self.plasticity is not None and spiking_indices:
            record = self.plasticity.observe_spikes(tick_us, spiking_indices)
            if isinstance(record, Gamma4BatchRecord):
                self.last_plasticity_record = record
        for i in self._record_neurons:
            self._voltage_trace.append(VoltageSample(
                tick_us, i, pre_reset[i], self.voltage_mv[i],
                self.synaptic_drive_mv[i], self.refractory_until_us[i],
                self.spiked_this_tick[i]))

    def run_until(self, end_time_us: int) -> SimulationSnapshot:
        """Advance on the fixed grid; repeated or chunked calls are identical."""
        require_time_us(end_time_us, "end_time_us")
        if end_time_us < self.current_time_us or end_time_us % self.dt_us:
            raise ValueError("end_time_us must be a nondecreasing multiple of dt_us")
        while self.current_time_us < end_time_us:
            self._step(self.current_time_us + self.dt_us)
        return self.snapshot()

    def set_external_drive_mv(self, drive_mv: Sequence[float]) -> None:
        """Replace drive at the current tick boundary for the next interval."""
        if len(drive_mv) != self.graph.neuron_count:
            raise ValueError("one external drive is required per neuron")
        if not all(type(value) in (int, float) and math.isfinite(value)
                   for value in drive_mv):
            raise ValueError("external drives must be finite numbers")
        self.external_drive_mv = tuple(float(value) for value in drive_mv)

    def apply_dopamine(self, dopamine: float) -> tuple[WeightChange, ...]:
        """Apply a modulatory event after the current tick's spike batch."""
        if not isinstance(self.plasticity, ThreeFactorPlasticity):
            raise RuntimeError("signed scalar dopamine is only for the legacy fixture")
        return self.plasticity.apply_dopamine(self.current_time_us, dopamine)

    def snapshot(self) -> SimulationSnapshot:
        """Return immutable state and only the traces explicitly requested."""
        return SimulationSnapshot(
            self.current_time_us, tuple(self.voltage_mv),
            tuple(self.synaptic_drive_mv), tuple(self.refractory_until_us),
            tuple(self.spike_counts), tuple(self._spikes), tuple(self._arrivals),
            tuple(self._voltage_trace), len(self._queue))

    def diagnostics(self) -> SimulationDiagnostics:
        """Return bounded aggregate event and spike counters."""
        return SimulationDiagnostics(
            self._sequence,
            self._delivered_events,
            self._peak_queued_events,
            None if self._active_edge_slots is None else len(self._active_edge_slots),
            tuple(self._spike_counts_by_tick),
        )

    def _state_identity(self) -> str:
        """Digest source graph ordering and the fixed simulator contract."""
        data = {
            "dt_us": self.dt_us,
            "parameters": [asdict(p) for p in self.parameters],
            "graph": [[int(self.graph.pre_indices[s]), int(self.graph.post_indices[s]),
                       float(self.graph.weights_mv[s]).hex(),
                       int(self.graph.delays_us[s])]
                      for s in range(self.graph.edge_count)],
            "record_neurons": self._record_neurons,
            "record_spikes": self._record_spikes,
            "record_arrivals": self._record_arrivals,
            "track_active_synapses": self._active_edge_slots is not None,
            "max_queued_events": self.max_queued_events,
            "max_scheduled_events": self.max_scheduled_events,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True,
                                         separators=(",", ":")).encode()).hexdigest()

    def state(self) -> dict:
        """Capture the exact committed-tick simulator state, including arrivals."""
        return {
            "identity_sha256": self._state_identity(),
            "time_us": self.current_time_us,
            "voltage_mv": list(self.voltage_mv),
            "synaptic_drive_mv": list(self.synaptic_drive_mv),
            "refractory_until_us": list(self.refractory_until_us),
            "spiked_this_tick": list(self.spiked_this_tick),
            "spike_counts": list(self.spike_counts),
            "external_drive_mv": list(self.external_drive_mv),
            "queue": [list(row) for row in sorted(self._queue)],
            "sequence": self._sequence,
            "delivered_events": self._delivered_events,
            "peak_queued_events": self._peak_queued_events,
            "active_edge_slots": (None if self._active_edge_slots is None else
                                  sorted(self._active_edge_slots)),
            "spike_counts_by_tick": list(self._spike_counts_by_tick),
            "spikes": [asdict(s) for s in self._spikes],
            "arrivals": [asdict(a) for a in self._arrivals],
            "voltage_trace": [asdict(v) for v in self._voltage_trace],
            "last_plasticity_record": (None if self.last_plasticity_record is None else
                                       asdict(self.last_plasticity_record)),
        }

    def restore(self, state: dict) -> None:
        """Reject an incompatible/corrupt state before changing any live value."""
        if set(state) != set(self.state()) or state["identity_sha256"] != self._state_identity():
            raise ValueError("simulator checkpoint schema or identity differs")
        n = self.graph.neuron_count
        tick = state["time_us"]
        if type(tick) is not int or tick < 0 or tick % self.dt_us:
            raise ValueError("checkpoint is not at a committed tick")
        vectors = ("voltage_mv", "synaptic_drive_mv", "refractory_until_us",
                   "spiked_this_tick", "spike_counts", "external_drive_mv")
        if any(not isinstance(state[key], list) or len(state[key]) != n for key in vectors):
            raise ValueError("simulator vector dimension differs")
        if any(type(v) not in (int, float) or not math.isfinite(v)
               for key in ("voltage_mv", "synaptic_drive_mv", "external_drive_mv")
               for v in state[key]):
            raise ValueError("non-finite simulator state")
        if any(type(v) is not int or v < 0 for key in ("refractory_until_us", "spike_counts")
               for v in state[key]) or any(type(v) is not bool for v in state["spiked_this_tick"]):
            raise ValueError("invalid simulator counters")
        queue = [tuple(row) for row in state["queue"]]
        if any(len(row) != 6 or type(row[0]) is not int or row[0] <= tick
               or type(row[3]) is not int or not 0 <= row[3] < self.graph.edge_count
               or int(self.graph.pre_indices[row[3]]) != row[2]
               or int(self.graph.post_indices[row[3]]) != row[1]
               or type(row[4]) is not int or row[4] < 0
               or type(row[5]) not in (int, float) or not math.isfinite(row[5])
               for row in queue):
            raise ValueError("invalid captured-weight arrival queue")
        if (len({row[4] for row in queue}) != len(queue)
                or any(type(state[key]) is not int or state[key] < 0
                       for key in ("sequence", "delivered_events", "peak_queued_events"))
                or (queue and state["sequence"] <= max(row[4] for row in queue))
                or state["peak_queued_events"] < len(queue)
                or len(state["spike_counts_by_tick"]) != tick // self.dt_us):
            raise ValueError("invalid simulator event counters")
        active = state["active_edge_slots"]
        if ((active is None) != (self._active_edge_slots is None)
                or (active is not None and (active != sorted(set(active))
                    or any(type(s) is not int or not 0 <= s < self.graph.edge_count
                           for s in active)))):
            raise ValueError("active-edge tracking differs")
        spikes = [SpikeEvent(**row) for row in state["spikes"]]
        arrivals = [SynapticArrival(**row) for row in state["arrivals"]]
        trace = [VoltageSample(**row) for row in state["voltage_trace"]]
        local = state["last_plasticity_record"]
        if local is not None:
            from project_b.plasticity import Gamma4WeightUpdate
            local = Gamma4BatchRecord(
                local["time_us"], local["compartment"], local["mask_sha256"],
                tuple(local["kc_source_ids"]), tuple(local["pam_source_ids"]),
                local["pam_fraction"], local["pam_trace_pre"],
                tuple(Gamma4WeightUpdate(**u) for u in local["updates"]))
        self.current_time_us = tick
        self.voltage_mv = list(state["voltage_mv"])
        self.synaptic_drive_mv = list(state["synaptic_drive_mv"])
        self.refractory_until_us = list(state["refractory_until_us"])
        self.spiked_this_tick = list(state["spiked_this_tick"])
        self.spike_counts = list(state["spike_counts"])
        self.external_drive_mv = tuple(state["external_drive_mv"])
        self._queue = queue
        heapq.heapify(self._queue)
        self._sequence = state["sequence"]
        self._delivered_events = state["delivered_events"]
        self._peak_queued_events = state["peak_queued_events"]
        self._active_edge_slots = None if active is None else set(active)
        self._spike_counts_by_tick = list(state["spike_counts_by_tick"])
        self._spikes = spikes
        self._arrivals = arrivals
        self._voltage_trace = trace
        self.last_plasticity_record = local
