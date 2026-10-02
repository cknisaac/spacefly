"""Neutral-only Circuit V1 electrical runtime; no game, readout, or learning."""

from __future__ import annotations

import copy
import heapq
import math
from collections import Counter

import numpy as np

from .boundary import DNBoundary
from .source import CircuitDefinition, UnknownEdgePolicy, parameter


CONDITIONS = {"A", "B", "C", "D"}


class NeutralCircuit:
    """Spiking cells, local graded APL, inactive DAN, and autonomous DN drive.

    All source edges remain in CircuitDefinition. Only the named active class
    hypotheses enter the queue. UNKNOWN is never passed to this scheduler.
    """

    def __init__(self, circuit: CircuitDefinition, *, condition: str, level: str = "nominal",
                 seed: int = 31001, record_neurons: tuple[int, ...] = ()):
        if condition not in CONDITIONS or (condition in {"B", "D"} and level != "nominal"):
            raise ValueError("Only predeclared neutral conditions are accepted")
        self.circuit = circuit
        self.condition = condition
        self.level = level
        self.seed = seed
        c = circuit.config
        if c["boundary_contract_id"] != "dn-boundary-v1" or c["plasticity_enabled"] is not False:
            raise ValueError("Circuit V1 neutral model requires locked boundary and disabled plasticity")
        self.tick_us = int(parameter(c["timing"]["integration_tick_us"], positive=True))
        self.delay_us = int(parameter(c["timing"]["chemical_delay_us"], positive=True))
        self.tau_syn_us = int(parameter(c["timing"]["synaptic_decay_us"], positive=True))
        self.max_queued = int(parameter(c["timing"]["max_queued_events"], positive=True))
        if self.delay_us % self.tick_us or self.tick_us <= 0:
            raise ValueError("Chemical delay must be positive and tick aligned")
        if c["unknown_edge_policy"] != UnknownEdgePolicy.RETAIN_ANATOMY_INACTIVE:
            raise ValueError("Unknown-edge fallback is prohibited")
        b = c["boundary"]
        if (b["seed_ids"] != [31001, 31002, 31003]
                or b["strengths"] != {"low": 0.5, "nominal": 1.0, "high": 1.5}
                or (b["common_coefficient"], b["private_coefficient"], b["mean_flip_interval_us"]) !=
                   (0.2, 0.2, 100000)
                or b["provenance"]["evidence"] != "ENGINEERING ASSUMPTION"):
            raise ValueError("DN background settings differ from frozen dn-boundary-v1")
        self.spiking_local = tuple(i for i, n in enumerate(circuit.cells) if n.kind not in {"APL", "PPL103"})
        self.dynamic_of_local = {i: j for j, i in enumerate(self.spiking_local)}
        self.local_of_dynamic = self.spiking_local
        self.source_ids = tuple(circuit.cells[i].source_id for i in self.spiking_local)
        self.dynamic_of_source = {sid: i for i, sid in enumerate(self.source_ids)}
        n = len(self.spiking_local)
        expected_spiking = 115 if c["schema_version"] == 2 else 113
        if n != expected_spiking:
            raise ValueError("Selected circuit needs its versioned spiking cells, one graded APL and one DAN")
        self.kind = tuple(circuit.cells[i].kind for i in self.spiking_local)
        raw_params = [c["spiking_classes"][kind] for kind in self.kind]
        provenance = c["spiking_parameter_provenance"]
        if provenance["evidence"] != "ENGINEERING ASSUMPTION" or not provenance["source"]:
            raise ValueError("Missing class-parameter provenance")
        required = {"capacitance_pf", "leak_ns", "rest_mv", "onset_mv", "reset_mv", "refractory_us"}
        if any(set(p) != required for p in raw_params):
            raise ValueError("Incomplete cell-class electrical parameters")
        params = [{key: parameter(value, positive=key in {"capacitance_pf", "leak_ns"})
                   for key, value in p.items()} for p in raw_params]
        self.cap_pf = np.array([p["capacitance_pf"] for p in params], float)
        self.leak_ns = np.array([p["leak_ns"] for p in params], float)
        self.rest_mv = np.array([p["rest_mv"] for p in params], float)
        self.onset_mv = np.array([p["onset_mv"] for p in params], float)
        self.reset_mv = np.array([p["reset_mv"] for p in params], float)
        self.refractory_us = np.array([p["refractory_us"] for p in params], np.int64)
        if (not np.all(np.isfinite(self.cap_pf)) or not np.all(np.isfinite(self.leak_ns))
                or np.any(self.cap_pf <= 0) or np.any(self.leak_ns <= 0)
                or np.any(self.onset_mv <= self.rest_mv)
                or np.any(self.onset_mv <= self.reset_mv)
                or np.any(self.refractory_us < 0)):
            raise ValueError("Invalid independent neuron electrical scales")
        self.v_mv = self.rest_mv.copy()
        self.syn_pa = np.zeros(n)
        self.refractory_until_us = np.zeros(n, np.int64)
        self.spike_counts = np.zeros(n, np.int64)
        self.refractory_time_us = np.zeros(n, np.int64)
        self.dn_refractory_bins_us: dict[int, list[int]] = {}
        self.voltage_sample_count = 0
        self.voltage_outer_count = np.zeros(n, np.int64)
        self.voltage_extreme_count = np.zeros(n, np.int64)
        self.dn3 = self.dynamic_of_source[519624]
        self.dn2 = self.dynamic_of_source[523769]
        self.dn_refractory_bins_us = {519624: [], 523769: []}
        # For a passive subthreshold compartment, (V_onset - V_rest)/R_in
        # with R_in=1/g_leak equals g_leak * voltage margin in pA.
        self.dn_reference_pa = (float(self.leak_ns[self.dn3] * (self.onset_mv[self.dn3] - self.rest_mv[self.dn3])),
                                float(self.leak_ns[self.dn2] * (self.onset_mv[self.dn2] - self.rest_mv[self.dn2])))
        if not all(math.isfinite(x) and x > 0 for x in self.dn_reference_pa):
            raise ValueError("DN model lacks finite positive reference current")

        apl = c["graded_APL"]
        self.apl_tau_us = int(parameter(apl["local_decay_us"], positive=True))
        self.apl_calyx_tau_us = int(parameter(apl["calyx_decay_us"], positive=True))
        self.apl_input_per_contact = parameter(apl["kc_to_local_increment_per_contact"], positive=True)
        self.apl_output_pa_per_contact = parameter(apl["local_to_kc_current_pa_per_contact_per_unit"])
        if self.apl_output_pa_per_contact >= 0:
            raise ValueError("APL local output hypothesis must inhibit")
        self.apl_local = np.zeros(n)
        self.apl_calyx = 0.0
        self.apl_out_coefficient = np.zeros(n)
        self.dan_tau_us = int(parameter(c["dopamine_state"]["decay_us"], positive=True))
        self.dan_state = 0.0  # No teaching source in neutral mode.
        self.modulatory_pair_count = 0

        self.outgoing: list[list[tuple[int, float, int, str]]] = [[] for _ in range(n)]
        for edge in circuit.connections:
            pre_cell, post_cell = circuit.cells[edge.pre], circuit.cells[edge.post]
            if edge.effect_state == "UNKNOWN":
                UnknownEdgePolicy.electrical_weight(edge)
            if edge.effect_state == "ACTIVE_FAST":
                if edge.weight_pa is None or not math.isfinite(edge.weight_pa) or edge.weight_pa == 0:
                    raise ValueError("Active effect has no declared current")
                if condition == "C" and pre_cell.source_id == 519131 and post_cell.source_id in {519624, 523769}:
                    continue  # Explicit functional disconnection; source row retained.
                self.outgoing[self.dynamic_of_local[edge.pre]].append(
                    (self.dynamic_of_local[edge.post], edge.weight_pa, edge.source_row, "FAST"))
            elif edge.effect_state == "GRADED_INPUT":
                # One separately evolving local gamma2 APL microdomain per KC.
                # Anatomical subbranch location is not asserted from pair counts.
                self.outgoing[self.dynamic_of_local[edge.pre]].append(
                    (self.dynamic_of_local[edge.pre], edge.contacts * self.apl_input_per_contact,
                     edge.source_row, "APL_INPUT"))
            elif edge.effect_state == "GRADED_OUTPUT":
                self.apl_out_coefficient[self.dynamic_of_local[edge.post]] += (
                    edge.contacts * self.apl_output_pa_per_contact)
            elif edge.effect_state == "MODULATORY":
                self.modulatory_pair_count += 1
            elif edge.effect_state != "UNKNOWN":
                raise ValueError("Unrecognized source effect")
        for outgoing in self.outgoing:
            outgoing.sort(key=lambda x: (x[0], x[2], x[3]))
        if self.modulatory_pair_count != 108:
            raise ValueError("PPL103 modulatory source route drifted")
        bmode = "omitted" if condition == "B" else "independent" if condition == "D" else "shared"
        self.boundary = DNBoundary(seed=seed, level=level, control=bmode)
        self.current_time_us = 0
        # (time, post_dynamic, pre_dynamic, source_row, sequence, effect_kind, amplitude)
        self.queue: list[tuple[int, int, int, int, int, str, float]] = []
        self.sequence = 0
        self.delivered = 0
        self.peak_queued = 0
        self.record_indices = tuple(sorted({self.dynamic_of_source[s] for s in record_neurons}))
        self.samples: list[dict] = []
        self.spikes: list[tuple[int, int]] = []

    @property
    def plasticity_enabled(self) -> bool:
        return False

    def _integrate(self, dt_us: int) -> None:
        if dt_us <= 0:
            return
        refractory_duration = np.clip(np.minimum(self.current_time_us + dt_us, self.refractory_until_us)
                                      - self.current_time_us, 0, dt_us)
        self.refractory_time_us += refractory_duration.astype(np.int64)
        # Integration boundaries include each 500-us tick; a segment cannot
        # cross a whole-second boundary. Retain exact occupancy for the gate.
        bin_index = self.current_time_us // 1_000_000
        for source_id, index in ((519624, self.dn3), (523769, self.dn2)):
            bins = self.dn_refractory_bins_us[source_id]
            while len(bins) <= bin_index:
                bins.append(0)
            bins[bin_index] += int(refractory_duration[index])
        dt_ms = dt_us / 1000.0
        tau_m_ms = self.cap_pf / self.leak_ns
        a = np.exp(-dt_ms / tau_m_ms)
        syn_decay = math.exp(-dt_us / self.tau_syn_us)
        apl_decay = math.exp(-dt_us / self.apl_tau_us)

        def contribution(decay: float, tau_ms: float, current_pa: np.ndarray) -> np.ndarray:
            difference = 1 / tau_m_ms - 1 / tau_ms
            factor = np.empty_like(difference)
            equal = np.isclose(difference, 0, atol=1e-12)
            factor[equal] = dt_ms * a[equal] / self.cap_pf[equal]
            factor[~equal] = ((decay - a[~equal]) /
                              (self.cap_pf[~equal] * difference[~equal]))
            return current_pa * factor

        boundary3, boundary2 = self.boundary.currents_pa(*self.dn_reference_pa)
        constant_pa = np.zeros(len(self.v_mv))
        constant_pa[self.dn3] = boundary3
        constant_pa[self.dn2] = boundary2
        apl_pa = self.apl_local * self.apl_out_coefficient
        self.v_mv = (self.rest_mv + (self.v_mv - self.rest_mv) * a
                     + constant_pa / self.leak_ns * (1 - a)
                     + contribution(syn_decay, self.tau_syn_us / 1000, self.syn_pa)
                     + contribution(apl_decay, self.apl_tau_us / 1000, apl_pa))
        self.syn_pa *= syn_decay
        self.apl_local *= apl_decay
        self.apl_calyx *= math.exp(-dt_us / self.apl_calyx_tau_us)
        self.dan_state *= math.exp(-dt_us / self.dan_tau_us)
        refractory = self.current_time_us < self.refractory_until_us
        self.v_mv[refractory] = self.reset_mv[refractory]
        if not np.all(np.isfinite(self.v_mv)) or not np.all(np.isfinite(self.syn_pa)):
            raise ArithmeticError("Nonfinite electrical state")

    def _deliver_due(self, time_us: int) -> None:
        while self.queue and self.queue[0][0] == time_us:
            _, post, _, _, _, kind, amplitude = heapq.heappop(self.queue)
            if kind == "FAST":
                self.syn_pa[post] += amplitude
            elif kind == "APL_INPUT":
                self.apl_local[post] += amplitude
            else:
                raise AssertionError("Invalid queued event kind")
            self.delivered += 1
        if self.queue and self.queue[0][0] < time_us:
            raise AssertionError("Overdue synaptic event")

    def _step(self) -> None:
        tick_us = self.current_time_us + self.tick_us
        while self.current_time_us < tick_us:
            next_time = min(tick_us, self.boundary.next_event_us,
                            self.queue[0][0] if self.queue else tick_us)
            if next_time < self.current_time_us:
                raise AssertionError("Event time reversal")
            self._integrate(next_time - self.current_time_us)
            self.current_time_us = next_time
            if next_time < tick_us:
                # At an interior tie, boundary flips precede chemical arrivals.
                self.boundary.advance_to(next_time)
                self._deliver_due(next_time)
        # Thresholds are evaluated before events exactly on this tick.
        spike_indices = np.flatnonzero((self.v_mv >= self.onset_mv) &
                                      (tick_us >= self.refractory_until_us))
        for i in spike_indices:
            self.spike_counts[i] += 1
            self.v_mv[i] = self.reset_mv[i]
            self.refractory_until_us[i] = tick_us + self.refractory_us[i]
            self.spikes.append((tick_us, self.source_ids[i]))
            for post, amplitude, source_row, kind in self.outgoing[i]:
                heapq.heappush(self.queue, (tick_us + self.delay_us, post, int(i),
                                            source_row, self.sequence, kind, amplitude))
                self.sequence += 1
        if len(self.queue) > self.max_queued:
            raise RuntimeError("Queued-event safety limit exceeded")
        self.peak_queued = max(self.peak_queued, len(self.queue))
        self.boundary.advance_to(tick_us)
        self._deliver_due(tick_us)
        z = (self.v_mv - self.rest_mv) / (self.onset_mv - self.rest_mv)
        self.voltage_outer_count += (np.abs(z) > 2).astype(np.int64)
        self.voltage_extreme_count += (np.abs(z) > 4).astype(np.int64)
        self.voltage_sample_count += 1
        for i in self.record_indices:
            boundary3, boundary2 = self.boundary.currents_pa(*self.dn_reference_pa)
            self.samples.append({"time_us": tick_us, "source_id": self.source_ids[i],
                                 "voltage_mv": float(self.v_mv[i]), "synaptic_drive_pa": float(self.syn_pa[i]),
                                 "leak_drive_pa": float(-self.leak_ns[i] * (self.v_mv[i] - self.rest_mv[i])),
                                 "apl_drive_pa": float(self.apl_local[i] * self.apl_out_coefficient[i]),
                                 "boundary_drive_pa": (boundary3 if i == self.dn3 else
                                                        boundary2 if i == self.dn2 else 0.0),
                                 "apl_local_state": float(self.apl_local[i]),
                                 "refractory_until_us": int(self.refractory_until_us[i]),
                                 "spike_count": int(self.spike_counts[i])})

    def run_until(self, end_time_us: int) -> dict:
        if type(end_time_us) is not int or end_time_us < self.current_time_us or end_time_us % self.tick_us:
            raise ValueError("Run end must be a nondecreasing integration tick")
        while self.current_time_us < end_time_us:
            self._step()
        return self.summary()

    def summary(self) -> dict:
        by_kind = Counter()
        for i, count in enumerate(self.spike_counts):
            by_kind[self.kind[i]] += int(count)
        return {"time_us": self.current_time_us, "condition": self.condition, "level": self.level,
                "seed": self.seed, "spikes_by_class": dict(by_kind),
                "dn_spike_counts": {"519624": int(self.spike_counts[self.dn3]),
                                    "523769": int(self.spike_counts[self.dn2])},
                "scheduled_events": self.sequence, "delivered_events": self.delivered,
                "queued_events": len(self.queue), "peak_queued_events": self.peak_queued,
                "dn_refractory_time_us": {"519624": int(self.refractory_time_us[self.dn3]),
                                          "523769": int(self.refractory_time_us[self.dn2])},
                "dn_refractory_bins_us": {str(k): tuple(v) for k, v in self.dn_refractory_bins_us.items()},
                "voltage_sample_count": self.voltage_sample_count,
                "dn_voltage_outer_samples": {"519624": int(self.voltage_outer_count[self.dn3]),
                                             "523769": int(self.voltage_outer_count[self.dn2])},
                "dn_voltage_extreme_samples": {"519624": int(self.voltage_extreme_count[self.dn3]),
                                               "523769": int(self.voltage_extreme_count[self.dn2])},
                "apl_spikes": 0, "ppl103_spikes": 0, "dan_state": self.dan_state,
                "plasticity_enabled": False}

    def checkpoint(self) -> dict:
        return copy.deepcopy({"model_sha256": self.circuit.config_sha256, "condition": self.condition,
            "level": self.level, "seed": self.seed, "time_us": self.current_time_us,
            "voltage_mv": self.v_mv.tolist(), "synaptic_pa": self.syn_pa.tolist(),
            "refractory_until_us": self.refractory_until_us.tolist(),
            "spike_counts": self.spike_counts.tolist(), "apl_local": self.apl_local.tolist(),
            "refractory_time_us": self.refractory_time_us.tolist(),
            "dn_refractory_bins_us": copy.deepcopy(self.dn_refractory_bins_us),
            "voltage_sample_count": self.voltage_sample_count,
            "voltage_outer_count": self.voltage_outer_count.tolist(),
            "voltage_extreme_count": self.voltage_extreme_count.tolist(),
            "apl_calyx": self.apl_calyx, "dan_state": self.dan_state,
            "boundary": self.boundary.checkpoint(), "queue": self.queue,
            "sequence": self.sequence, "delivered": self.delivered,
            "peak_queued": self.peak_queued, "spikes": self.spikes, "samples": self.samples})

    def restore(self, state: dict) -> None:
        if (state.get("model_sha256") != self.circuit.config_sha256 or
                (state.get("condition"), state.get("level"), state.get("seed")) !=
                (self.condition, self.level, self.seed) or
                state.get("time_us", -1) % self.tick_us):
            raise ValueError("Checkpoint does not match locked circuit/condition/tick")
        for key, target in (("voltage_mv", "v_mv"), ("synaptic_pa", "syn_pa"),
                            ("refractory_until_us", "refractory_until_us"),
                            ("spike_counts", "spike_counts"), ("apl_local", "apl_local"),
                            ("refractory_time_us", "refractory_time_us"),
                            ("voltage_outer_count", "voltage_outer_count"),
                            ("voltage_extreme_count", "voltage_extreme_count")):
            values = state[key]
            if len(values) != len(self.v_mv):
                raise ValueError("Checkpoint neuron count differs")
            setattr(self, target, np.asarray(values, dtype=getattr(self, target).dtype).copy())
        self.apl_calyx = float(state["apl_calyx"])
        self.dn_refractory_bins_us = copy.deepcopy(state["dn_refractory_bins_us"])
        self.dan_state = float(state["dan_state"])
        self.voltage_sample_count = int(state["voltage_sample_count"])
        self.current_time_us = int(state["time_us"])
        self.boundary.restore(state["boundary"])
        if self.boundary.time_us != self.current_time_us:
            raise ValueError("Boundary checkpoint time differs from neural clock")
        self.queue = copy.deepcopy(state["queue"])
        heapq.heapify(self.queue)
        self.sequence = int(state["sequence"])
        self.delivered = int(state["delivered"])
        self.peak_queued = int(state["peak_queued"])
        self.spikes = copy.deepcopy(state["spikes"])
        self.samples = copy.deepcopy(state["samples"])
