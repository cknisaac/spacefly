"""Source-derived MVP-C1 coupled CPU runner and committed-tick continuation."""

from __future__ import annotations

import hashlib
import heapq
import json
import math
import platform
from dataclasses import asdict
from enum import Enum
from pathlib import Path

import numpy as np

from project_b.checkpoint.codec import BOUNDARY, load_checkpoint, save_checkpoint
from project_b.checkpoint.frozen import FrozenPolicySnapshot
from project_b.motor.fixed_readout import FixedMotorReadout
from project_b.plasticity.gamma4 import Gamma4Plasticity

from .boundary import AutonomousBoundary, TARGETS
from .controls import ControlPolicy, PamControlRouter
from .feedback import NoteWindow
from .sensory import CurrentPositionKCEncoder
from .source import MvpCircuit
from .task_session import MvpTaskSession


def _hash_json(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     default=str).encode()).hexdigest()


def _plain(value):
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return value


def _source_tree_sha(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted((root / "src/project_b").rglob("*.py")):
        digest.update(str(path.relative_to(root)).replace("\\", "/").encode())
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


class MvpSession:
    """One 717-LIF plus graded-APL task session with no implicit candidate search."""

    DT_US = 1_000
    TAU_M_US = 20_000
    TAU_S_US = 5_000
    TAU_APL_US = 20_000
    MAX_QUEUED = 2_000_000

    def __init__(self, circuit: MvpCircuit, root: Path, notes: tuple[NoteWindow, ...],
                 *, seed: int, level: str = "nominal",
                 frozen_policy: FrozenPolicySnapshot | None = None,
                 controls: ControlPolicy = ControlPolicy()):
        if any(n.visible_from_us % self.DT_US or n.hit_us % self.DT_US for n in notes):
            raise ValueError("MVP renderer cue and hit times must use the 1-ms grid")
        if not isinstance(controls, ControlPolicy) or (frozen_policy is not None and
                                                       controls != ControlPolicy()):
            raise ValueError("A4 controls require a plastic session")
        self.circuit, self.root, self.notes = circuit, Path(root), notes
        self.seed, self.level = seed, level
        self.mode = "frozen" if frozen_policy is not None else "plastic"
        self.frozen_policy = frozen_policy
        self.controls = controls
        self.pam_router = PamControlRouter(controls.teaching)
        self.index = {source: i for i, source in enumerate(circuit.source_ids)}
        self.kc_indices = np.asarray([self.index[s] for s in circuit.kc_ids], dtype=np.int64)
        self.pam_indices = np.asarray([self.index[s] for s in circuit.pam_ids], dtype=np.int64)
        self.apl_indices = np.asarray(circuit.apl_target_indices, dtype=np.int64)
        self.boundary = AutonomousBoundary(seed, level)
        self.encoder = CurrentPositionKCEncoder(circuit.kc_ids)
        self.task = MvpTaskSession(notes, teaching_enabled=self.mode == "plastic")
        self.motor = FixedMotorReadout((self.index[10713],), lane=0, window_us=20_000,
                                      on_threshold=2, off_threshold=0, min_hold_us=10_000,
                                      max_hold_us=30_000, cooldown_us=200_000)
        self.rule = Gamma4Plasticity.from_b2_design(circuit.graph, circuit.source_ids, self.root)
        if frozen_policy is not None:
            frozen_policy.install_into_fresh_rule(self.rule)
        elif controls.plasticity == "off":
            self.rule.enabled = False
        self.time_us = 0
        self.voltage = np.zeros(len(circuit.source_ids), dtype=np.float64)
        self.synaptic = np.zeros_like(self.voltage)
        self.refractory_until_us = np.zeros(len(circuit.source_ids), dtype=np.int64)
        self.spike_counts = np.zeros(len(circuit.source_ids), dtype=np.int64)
        self.apl_state = 0.0
        self.external = np.zeros_like(self.voltage)
        self.chemical_queue: list[tuple[int, int, int, int, int, int, float]] = []
        self.apl_queue: list[tuple[int, int, int, int, float]] = []
        self.sequence = 0
        self.delivered_chemical = 0
        self.delivered_apl = 0
        self.chemical_hash_head = "0" * 64
        self.peak_queue = 0
        self.ledger: list[list] = []
        self._last_game_events = 0
        self._last_decisions = 0
        self._last_pulses = 0
        self.task.advance_to(0)
        self.pam_router.advance_to(0, self.task.feedback.pulse_records)
        self._sync_sensory(0)
        self._refresh_external()
        self.identity = self._identity()

    def _identity(self) -> dict:
        resolved = json.loads((self.root / "configs/b2_1_candidate1_resolved.json").read_text())
        pins = resolved["identity"]
        g = self.circuit.graph
        graph_digest = hashlib.sha256()
        for array in (g.offsets, g.pre_indices, g.post_indices, g.weights_mv,
                      g.delays_us, g.source_rows):
            graph_digest.update(array.tobytes())
        identity = {
            "candidate": "MVP-C1", "schema": "MVP-C1-checkpoint-v1",
            "source_release": "MaleCNS v1.0 traced-only",
            "source_neurons_sha256": pins["source_neurons_sha256"],
            "source_connections_sha256": pins["source_connections_sha256"],
            "source_partner_sha256": pins["source_partner_sha256"],
            "B1_anatomy_sha256": pins["B1_anatomy_sha256"],
            "B2_design_sha256": pins["B2_design_sha256"],
            "B2_contact_audit_sha256": pins["B2_contact_audit_sha256"],
            "B2_runtime_mask_sha256": pins["B2_runtime_mask_sha256"],
            "ordered_source_ids_sha256": _hash_json(self.circuit.source_ids),
            "ordered_CSR_graph_sha256": graph_digest.hexdigest(),
            "effect_and_boundary_overlay_sha256": pins["B2_1_addendum_sha256"],
            "resolved_config_sha256": self.circuit.resolved_sha256,
            "renderer_and_note_schedule_sha256": _hash_json([asdict(n) for n in self.notes]),
            "ruleset_and_metric_sha256": _hash_json(self.task.game.config.as_dict()),
            "code_revision_or_source_tree_sha256": _source_tree_sha(self.root),
            "runtime_backend_and_numeric_version": ["numpy-cpu", np.__version__,
                                                     platform.python_version()],
            "master_seed": self.seed, "boundary_level": self.level, "mode": self.mode,
            "control_policy": asdict(self.controls),
            "frozen_policy_sha256": (None if self.frozen_policy is None else
                                     _hash_json(asdict(self.frozen_policy))),
        }
        return identity

    def apply_controls(self, controls: ControlPolicy) -> None:
        """Activate one declared arm after restoring an identical parent cut."""
        if (self.mode != "plastic" or self.controls != ControlPolicy() or
                not isinstance(controls, ControlPolicy) or
                self.task.feedback.pulse_records or self.task.feedback.pending_early or
                self.task.feedback.pending_late or self.task.feedback.active_pulses):
            raise ValueError("control activation needs an unassigned plastic parent cut")
        self.controls = controls
        self.pam_router = PamControlRouter(controls.teaching)
        self.pam_router.time_us = self.time_us
        self.rule.enabled = controls.plasticity == "on"
        self._refresh_external()
        self.identity = self._identity()

    def _log(self, kind: str, *parts) -> None:
        self.ledger.append([kind, *(_plain(p) for p in parts)])

    def _sync_sensory(self, time_us: int, *, observe: bool = True) -> None:
        active = next((n for n in self.notes if n.visible_from_us <= time_us
                       and n.note_id not in self.task.game._resolved
                       and time_us <= n.hit_us + self.task.game.windows.expiry_offset_us), None)
        old = self.encoder._active_note_id
        if old is not None and (active is None or old != active.note_id):
            self.encoder.cancel(time_us, old)
            self._log("cue_remove", time_us, old)
        if active is not None and observe:
            position = min(1.0, max(0.0, (time_us - active.visible_from_us) /
                                      (active.hit_us - active.visible_from_us)))
            self.encoder.observe(time_us, active.note_id, position)
        prior = tuple(self.encoder.current_drive)
        current = self.encoder.due_drive(time_us)
        if current != prior:
            self._log("sensory_current", time_us, self.encoder._active_note_id,
                      self.encoder.observation_cursor, _hash_json(current),
                      max(current), sum(current))

    def _refresh_external(self) -> None:
        self.external.fill(0.0)
        self.external[self.kc_indices] = self.encoder.current_drive
        self.external[self.pam_indices] = (self.pam_router.current(self.time_us)
                                           if self.controls.dan == "on" else 0.0)
        for source in TARGETS:
            self.external[self.index[source]] += self.boundary.current(source)

    @staticmethod
    def _phi(dt: np.ndarray, tau_x: int) -> np.ndarray:
        if tau_x == 20_000:
            return (dt / 20_000) * np.exp(-dt / 20_000)
        return tau_x / (tau_x - 20_000) * (np.exp(-dt / tau_x) - np.exp(-dt / 20_000))

    def _integrate(self, end_us: int) -> None:
        start = self.time_us
        if end_us <= start:
            return
        dt = end_us - start
        active_start = np.maximum(start, np.minimum(end_us, self.refractory_until_us))
        clamp = active_start - start
        active_dt = end_us - active_start
        s_active = self.synaptic * np.exp(-clamp / self.TAU_S_US)
        l_active = self.apl_state * np.exp(-clamp / self.TAU_APL_US)
        em = np.exp(-active_dt / self.TAU_M_US)
        base_v = np.where(clamp > 0, 0.0, self.voltage)
        apl_coeff = np.zeros_like(self.voltage)
        apl_coeff[self.apl_indices] = -0.2
        self.voltage = (base_v * em + self.external * (1 - em)
                        + s_active * self._phi(active_dt, self.TAU_S_US)
                        + apl_coeff * l_active * self._phi(active_dt, self.TAU_APL_US))
        self.synaptic *= math.exp(-dt / self.TAU_S_US)
        self.apl_state *= math.exp(-dt / self.TAU_APL_US)
        self.time_us = end_us
        if not np.all(np.isfinite(self.voltage)) or not np.all(np.isfinite(self.synaptic)):
            raise ArithmeticError("non-finite MVP neural state")

    def _process_due(self, at: int) -> None:
        for time_us, source, sign in self.boundary.advance_to(at):
            self._log("boundary_flip", time_us, source, sign)
        self._refresh_external()
        while self.chemical_queue and self.chemical_queue[0][0] <= at:
            due, post_source, pre_source, row, seq, slot, captured = heapq.heappop(
                self.chemical_queue)
            self.synaptic[self.index[post_source]] += captured
            self.delivered_chemical += 1
            self.chemical_hash_head = hashlib.sha256((self.chemical_hash_head + "|" +
                repr((due, post_source, pre_source, row, seq, slot, captured.hex()))
                ).encode()).hexdigest()
            if post_source in (10495, 11145, 10713):
                self._log("output_chemical_arrival", due, post_source, pre_source,
                          row, seq, slot, captured)
        while self.apl_queue and self.apl_queue[0][0] <= at:
            due, row, seq, source, increment = heapq.heappop(self.apl_queue)
            self.apl_state = min(1.0, self.apl_state + increment)
            self.delivered_apl += 1
            self._log("apl_arrival", due, source, row, seq, increment, self.apl_state)

    def _advance_to_tick(self, tick: int) -> None:
        while self.time_us < tick:
            expiry = (self.task.game._expiry_heap[0][0]
                      if self.task.game._expiry_heap else tick)
            next_event = min(tick, self.boundary.next_time(),
                             expiry,
                             self.chemical_queue[0][0] if self.chemical_queue else tick,
                             self.apl_queue[0][0] if self.apl_queue else tick)
            self._integrate(next_event)
            if next_event < tick:
                if expiry == next_event:
                    self.task.advance_to(next_event)
                    self._sync_sensory(next_event, observe=False)
                self._process_due(next_event)

    def _flush_task_events(self) -> None:
        events = self.task.game.state()["events"]
        for event in events[self._last_game_events:]:
            self._log("game_event", event)
        self._last_game_events = len(events)
        for decision in self.task.feedback.decisions[self._last_decisions:]:
            self._log("feedback_decision", asdict(decision))
        self._last_decisions = len(self.task.feedback.decisions)
        for pulse in self.task.feedback.pulse_records[self._last_pulses:]:
            self._log("pam_pulse", asdict(pulse))
        self._last_pulses = len(self.task.feedback.pulse_records)

    def _tick(self, tick: int) -> None:
        self._advance_to_tick(tick)
        prior_onset_cursor = self.task.next_onset_index
        self.task.advance_to(tick)
        self._flush_task_events()
        onset_note = (self.notes[prior_onset_cursor].note_id
                      if self.task.next_onset_index > prior_onset_cursor else None)
        for pulse in self.pam_router.advance_to(
                tick, self.task.feedback.pulse_records, onset_note):
            self._log("pam_delivery" if self.controls.dan == "on" else
                      "pam_delivery_suppressed", asdict(pulse))
        self._sync_sensory(tick)
        self._process_due(tick)
        self._refresh_external()
        spikes = np.flatnonzero((self.voltage >= 1.0) &
                                (self.refractory_until_us <= tick)).tolist()
        if self.controls.dan == "disabled":
            pam_set = set(self.pam_indices.tolist())
            spikes = [i for i in spikes if i not in pam_set]
        proposed = sum(len(self.circuit.graph.outgoing_slots(i)) for i in spikes)
        proposed += sum(self.circuit.source_ids[i] in self.circuit.apl_input_by_kc
                        for i in spikes)
        if len(self.chemical_queue) + len(self.apl_queue) + proposed > self.MAX_QUEUED:
            raise RuntimeError("MVP event queue safety limit exceeded")
        graph = self.circuit.graph
        for i in spikes:
            source = self.circuit.source_ids[i]
            self._log("spike", tick, source, float(self.voltage[i]))
            self.voltage[i] = 0.0
            self.refractory_until_us[i] = tick + 2_000
            self.spike_counts[i] += 1
            for slot in graph.outgoing_slots(i):
                post = self.circuit.source_ids[int(graph.post_indices[slot])]
                weight = self.rule.effective_weight(slot)
                heapq.heappush(self.chemical_queue,
                               (tick + int(graph.delays_us[slot]), post, source,
                                int(graph.source_rows[slot]), self.sequence, slot, weight))
                self.sequence += 1
            if source in self.circuit.apl_input_by_kc:
                row, count = self.circuit.apl_input_by_kc[source]
                heapq.heappush(self.apl_queue, (tick + 2_000, row, self.sequence,
                                                source, count / 37_593))
                self.sequence += 1
        self.peak_queue = max(self.peak_queue,
                              len(self.chemical_queue) + len(self.apl_queue))
        if spikes:
            record = self.rule.observe_spikes(
                tick, spikes, eligibility_enabled=self.controls.eligibility == "on")
            if record.kc_source_ids or record.pam_source_ids:
                self._log("gamma4_batch", asdict(record))
            if record.pam_source_ids:
                self._log("pam_actual_spikes", tick, list(record.pam_source_ids),
                          record.pam_fraction)
        motor = self.motor.observe(tick, spikes)
        if motor is not None:
            self._log("motor", asdict(motor))
            self.task.apply_action(motor.action)
            if self.encoder._active_note_id in self.task.game._resolved:
                old = self.encoder._active_note_id
                self.encoder.cancel(tick, old)
                self._log("cue_remove", tick, old)
        self._flush_task_events()
        self._refresh_external()

    def run_until(self, end_us: int) -> None:
        if type(end_us) is not int or end_us < self.time_us or end_us % self.DT_US:
            raise ValueError("end must be a nondecreasing committed tick")
        for tick in range(self.time_us + self.DT_US, end_us + 1, self.DT_US):
            self._tick(tick)

    def state(self) -> dict:
        return {"phase": BOUNDARY, "time_us": self.time_us,
                "next_tick_us": self.time_us + self.DT_US,
                "voltage": self.voltage.tolist(), "synaptic_drive": self.synaptic.tolist(),
                "refractory_until_us": self.refractory_until_us.tolist(),
                "spike_counts": self.spike_counts.tolist(),
                "external_drive": self.external.tolist(), "apl_graded_state": self.apl_state,
                "chemical_queue": [list(x) for x in sorted(self.chemical_queue)],
                "apl_queue": [list(x) for x in sorted(self.apl_queue)],
                "global_event_sequence": self.sequence,
                "neural_diagnostic_counters": [self.delivered_chemical, self.delivered_apl,
                                                self.peak_queue],
                "chemical_hash_chain_head": self.chemical_hash_head,
                "boundary": self.boundary.state(), "encoder": self.encoder.state(),
                "task": self.task.state(), "motor": self.motor.state(),
                "control_policy": asdict(self.controls),
                "pam_router": self.pam_router.state(),
                "plasticity": self.rule.state(), "ledger": self.ledger,
                "ledger_offsets": [self._last_game_events, self._last_decisions,
                                   self._last_pulses],
                "ledger_hash_chain_head": _hash_json(self.ledger)}

    def restore(self, state: dict) -> None:
        """Validate into a new owner set before swapping live continuation state."""
        if set(state) != set(self.state()) or state["phase"] != BOUNDARY:
            raise ValueError("MVP state schema differs")
        clone = MvpSession(self.circuit, self.root, self.notes, seed=self.seed,
                           level=self.level, frozen_policy=self.frozen_policy,
                           controls=self.controls)
        t = state["time_us"]
        n = len(self.circuit.source_ids)
        if (type(t) is not int or t < 0 or t % self.DT_US or
                state["next_tick_us"] != t + self.DT_US or
                any(len(state[k]) != n for k in ("voltage", "synaptic_drive",
                                                "refractory_until_us", "spike_counts",
                                                "external_drive")) or
                not all(math.isfinite(v) for k in ("voltage", "synaptic_drive",
                                                 "external_drive") for v in state[k]) or
                not math.isfinite(state["apl_graded_state"]) or
                not 0 <= state["apl_graded_state"] <= 1 or
                (type(state["chemical_hash_chain_head"]) is not str or
                 len(state["chemical_hash_chain_head"]) != 64) or
                state["ledger_hash_chain_head"] != _hash_json(state["ledger"])):
            raise ValueError("invalid MVP neural or ledger state")
        clone.boundary.restore(state["boundary"])
        clone.encoder.restore(state["encoder"])
        clone.task.restore(state["task"])
        clone.motor.restore(state["motor"])
        clone.rule.restore(state["plasticity"])
        if state["control_policy"] != asdict(self.controls):
            raise ValueError("control policy differs")
        clone.pam_router.restore(state["pam_router"], clone.task.feedback.pulse_records)
        if (clone.boundary.time_us != t or clone.encoder.last_time_us != t or
                clone.task.time_us != t or
                clone.motor._last_time_us != (None if t == 0 else t) or
                clone.pam_router.time_us != t or
                clone.rule.enabled != (self.mode == "plastic" and
                                       self.controls.plasticity == "on")):
            raise ValueError("MVP owner clocks or mode differ")
        chemical = [tuple(row) for row in state["chemical_queue"]]
        apl = [tuple(row) for row in state["apl_queue"]]
        if (any(len(row) != 7 or row[0] <= t or not 0 <= row[5] <
                self.circuit.graph.edge_count or not math.isfinite(row[6]) or
                self.circuit.source_ids[int(self.circuit.graph.pre_indices[row[5]])] != row[2] or
                self.circuit.source_ids[int(self.circuit.graph.post_indices[row[5]])] != row[1]
                for row in chemical) or
                any(len(row) != 5 or row[0] <= t or row[3] not in
                    self.circuit.apl_input_by_kc or not math.isfinite(row[4])
                    for row in apl) or
                any(type(v) is not int or v < 0 for v in
                    state["neural_diagnostic_counters"] + state["ledger_offsets"] +
                    [state["global_event_sequence"]])):
            raise ValueError("invalid MVP event continuation")
        clone.time_us = t
        clone.voltage = np.asarray(state["voltage"], dtype=np.float64)
        clone.synaptic = np.asarray(state["synaptic_drive"], dtype=np.float64)
        clone.refractory_until_us = np.asarray(state["refractory_until_us"], dtype=np.int64)
        clone.spike_counts = np.asarray(state["spike_counts"], dtype=np.int64)
        clone.external = np.asarray(state["external_drive"], dtype=np.float64)
        clone.apl_state = state["apl_graded_state"]
        clone.chemical_queue, clone.apl_queue = chemical, apl
        heapq.heapify(clone.chemical_queue)
        heapq.heapify(clone.apl_queue)
        clone.sequence = state["global_event_sequence"]
        clone.delivered_chemical, clone.delivered_apl, clone.peak_queue = state[
            "neural_diagnostic_counters"]
        clone.chemical_hash_head = state["chemical_hash_chain_head"]
        clone.ledger = state["ledger"]
        (clone._last_game_events, clone._last_decisions,
         clone._last_pulses) = state["ledger_offsets"]
        expected_external = clone.external.copy()
        clone._refresh_external()
        if not np.array_equal(clone.external, expected_external):
            raise ValueError("MVP external current differs from owners")
        self.__dict__.update(clone.__dict__)

    def save(self, path: Path) -> str:
        return save_checkpoint(path, self.identity, self.state(),
                               schema_id="MVP-C1-checkpoint-v1")

    def load(self, path: Path) -> None:
        state = load_checkpoint(path, self.identity, schema_id="MVP-C1-checkpoint-v1")
        self.restore(state)

    def ledger_bytes(self) -> bytes:
        from project_b.checkpoint.codec import _canonical, _encode
        return _canonical(_encode({"ledger": self.ledger}))
