"""MVP-C1 contact-masked KC/PAM temporal-order rule (engineering model)."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from project_b.utils.time import require_time_us


@dataclass(frozen=True, slots=True)
class Gamma4Parameters:
    kc_trace_tau_us: int = 1_000_000
    pam_trace_tau_us: int = 1_200_000
    eta: float = 0.001
    trace_cap: float = 1.0
    minimum_weight_factor: float = 0.5
    maximum_weight_factor: float = 1.5

    def __post_init__(self) -> None:
        if (require_time_us(self.kc_trace_tau_us, "kc_trace_tau_us") <= 0
                or require_time_us(self.pam_trace_tau_us, "pam_trace_tau_us") <= 0):
            raise ValueError("trace constants must be positive")
        values = (self.eta, self.trace_cap, self.minimum_weight_factor,
                  self.maximum_weight_factor)
        if not all(math.isfinite(v) and v > 0 for v in values):
            raise ValueError("rule parameters must be finite and positive")
        if not self.minimum_weight_factor <= 1 <= self.maximum_weight_factor:
            raise ValueError("weight bounds must contain the initial value")


@dataclass(frozen=True, slots=True)
class Gamma4PairMask:
    kc_source_id: int
    total_contacts: int
    plastic_contact_rows: tuple[int, ...]

    @property
    def plastic_contacts(self) -> int:
        return len(self.plastic_contact_rows)


class Gamma4ContactMask:
    """Pinned source partner rows and pair totals, including fixed-only KC pairs."""

    def __init__(self, data: dict):
        if data.get("candidate_id") != "MVP-C1" or data.get("compartment") != "g4(L)":
            raise ValueError("wrong candidate or compartment")
        self.mbon_source_id = data["mbon_source_id"]
        if type(self.mbon_source_id) is not int:
            raise ValueError("invalid MBON source ID")
        pairs = []
        all_rows = []
        for item in data["kc_pairs"]:
            kc, total = item["kc_source_id"], item["total_contacts"]
            rows = tuple(item["plastic_contact_rows"])
            if (type(kc) is not int or type(total) is not int or total <= 0
                    or len(rows) > total or any(type(r) is not int or r < 0 for r in rows)
                    or tuple(sorted(set(rows))) != rows):
                raise ValueError("invalid KC contact partition")
            pairs.append(Gamma4PairMask(kc, total, rows))
            all_rows.extend(rows)
        if (not pairs or len({p.kc_source_id for p in pairs}) != len(pairs)
                or len(set(all_rows)) != len(all_rows)):
            raise ValueError("duplicate or empty contact mask")
        self.pairs = tuple(sorted(pairs, key=lambda p: p.kc_source_id))
        self.by_kc = {p.kc_source_id: p for p in self.pairs}
        self.mask_sha256 = hashlib.sha256(json.dumps(
            [(p.kc_source_id, p.total_contacts, p.plastic_contact_rows) for p in self.pairs],
            separators=(",", ":")).encode()).hexdigest()
        self.source_partner_sha256 = data.get("source_partner_sha256")
        self.b2_audit_sha256 = data.get("b2_audit_sha256")

    @classmethod
    def load_b2(cls, path: Path, audit_path: Path) -> "Gamma4ContactMask":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        digest = hashlib.sha256(Path(audit_path).read_bytes()).hexdigest()
        if digest != data.get("b2_audit_sha256"):
            raise ValueError("B2 audit checksum differs from runtime mask")
        audit = json.loads(Path(audit_path).read_text(encoding="utf-8"))
        mask = cls(data)
        rows = sorted(r for p in mask.pairs for r in p.plastic_contact_rows)
        screen = audit["same_kc_screen"]
        if (rows != sorted(screen["candidate_source_partner_rows"])
                or [p.kc_source_id for p in mask.pairs if p.plastic_contacts]
                != screen["candidate_kc_ids"]
                or mask.source_partner_sha256 != audit["source_partner_sha256"]):
            raise ValueError("runtime mask differs from B2 source contact selection")
        return mask


@dataclass(frozen=True, slots=True)
class Gamma4WeightUpdate:
    time_us: int
    compartment: str
    mask_sha256: str
    kc_source_id: int
    edge_slot: int
    plastic_contacts: int
    branch: str
    kc_trace_pre: float
    pam_trace_pre: float
    pam_fraction: float
    previous_plastic_weight: float
    proposed_plastic_weight: float
    applied_plastic_weight: float
    clipped: bool


@dataclass(frozen=True, slots=True)
class Gamma4BatchRecord:
    time_us: int
    compartment: str
    mask_sha256: str
    kc_source_ids: tuple[int, ...]
    pam_source_ids: tuple[int, ...]
    pam_fraction: float
    pam_trace_pre: float
    updates: tuple[Gamma4WeightUpdate, ...]


class Gamma4Plasticity:
    """Updates only the selected positive KC contact contribution.

    The graph retains its initial pair weights and topology. The weight used
    at emission is fixed contribution plus mutable selected contribution.
    KC-before-PAM depresses; PAM-before-KC potentiates; coincidence depresses.
    """

    def __init__(self, graph, source_ids_by_index: Iterable[int],
                 mask: Gamma4ContactMask, pam_source_ids: Iterable[int],
                 parameters: Gamma4Parameters = Gamma4Parameters()):
        ids = tuple(source_ids_by_index)
        if (len(ids) != graph.neuron_count or any(type(x) is not int for x in ids)
                or len(set(ids)) != len(ids)):
            raise ValueError("source IDs must uniquely cover graph neurons")
        pam = tuple(sorted(set(pam_source_ids)))
        if not pam or any(type(x) is not int or x not in ids for x in pam):
            raise ValueError("PAM source IDs must be known graph neurons")
        if mask.mbon_source_id not in ids or any(k not in ids for k in mask.by_kc):
            raise ValueError("mask source IDs must be known graph neurons")
        self.graph = graph
        self.source_ids_by_index = ids
        self.mask = mask
        self.parameters = parameters
        self.pam_source_ids = pam
        self._pam_set = set(pam)
        self._index_by_source = {source_id: i for i, source_id in enumerate(ids)}
        mbon = self._index_by_source[mask.mbon_source_id]
        self._slot_by_kc: dict[int, int] = {}
        self._fixed_by_slot: dict[int, float] = {}
        self._initial_by_slot: dict[int, float] = {}
        self._plastic_by_slot: dict[int, float] = {}
        for pair in mask.pairs:
            if not pair.plastic_contacts:
                continue
            pre = self._index_by_source[pair.kc_source_id]
            slots = [s for s in graph.outgoing_slots(pre) if int(graph.post_indices[s]) == mbon]
            if len(slots) != 1:
                raise ValueError("each selected KC-to-MBON05 pair needs one graph edge")
            slot = slots[0]
            total = float(graph.weights_mv[slot])
            if not math.isfinite(total) or total <= 0:
                raise ValueError("selected KC output must have positive initial magnitude")
            initial = total * pair.plastic_contacts / pair.total_contacts
            self._slot_by_kc[pair.kc_source_id] = slot
            self._fixed_by_slot[slot] = total - initial
            self._initial_by_slot[slot] = initial
            self._plastic_by_slot[slot] = initial
        self._kc_trace = {kc: (0.0, 0) for kc in self._slot_by_kc}
        self._pam_trace = (0.0, 0)
        self._last_time_us = 0
        self._last_batch_time_us: int | None = None
        self.enabled = True

    @classmethod
    def from_b2_design(cls, graph, source_ids_by_index: Iterable[int],
                       project_root: Path) -> "Gamma4Plasticity":
        """Bind the exact B2 mask, 25 PAM cells and numerical rule to a graph."""
        root = Path(project_root)
        receipt = json.loads((root / "docs/figures/b2_candidate_design/artifact_receipt.json")
                             .read_text(encoding="utf-8"))
        config_path = root / "configs/b2_candidate1_design.json"
        config_sha = hashlib.sha256(config_path.read_bytes()).hexdigest()
        if config_sha != receipt["files"]["configs/b2_candidate1_design.json"]:
            raise ValueError("B2 design differs from its pinned receipt")
        config = json.loads(config_path.read_text(encoding="utf-8"))
        audit_path = root / config["plastic_contact_mask"]["audit"]
        if (hashlib.sha256(audit_path.read_bytes()).hexdigest()
                != receipt["files"]["docs/figures/b2_candidate_design/gamma4_contact_audit.json"]):
            raise ValueError("B2 contact audit differs from its pinned receipt")
        mask = Gamma4ContactMask.load_b2(
            root / "configs/b2_candidate1_runtime_mask.json",
            audit_path)
        if (config["candidate_id"] != "MVP-C1"
                or sum(p.plastic_contacts for p in mask.pairs)
                != config["plastic_contact_mask"]["contacts"]
                or sum(bool(p.plastic_contacts) for p in mask.pairs)
                != config["plastic_contact_mask"]["pairs"]):
            raise ValueError("B2 design and runtime mask disagree")
        ids = tuple(source_ids_by_index)
        index = {source_id: i for i, source_id in enumerate(ids)}
        if len(index) != len(ids) or any(k not in index for k in mask.by_kc):
            raise ValueError("B2 source ID mapping is incomplete")
        target = index.get(mask.mbon_source_id)
        if target is None:
            raise ValueError("B2 MBON05 is absent")
        gain = config["effective_weight_policy"]["class_gain"]["kc_to_mbon05"]
        total_contacts = sum(p.total_contacts for p in mask.pairs)
        for pair in mask.pairs:
            slots = [s for s in graph.outgoing_slots(index[pair.kc_source_id])
                     if int(graph.post_indices[s]) == target]
            expected = gain * pair.total_contacts / total_contacts
            if (len(slots) != 1 or not math.isclose(
                    float(graph.weights_mv[slots[0]]), expected,
                    rel_tol=0, abs_tol=1e-12)):
                raise ValueError("KC-to-MBON05 graph coupling differs from B2 transform")
        rule = config["plasticity"]
        if (rule["coincidence_rule"] != "DEPRESSION"
                or rule["potentiation_fraction"] != 1.0
                or rule["depression_fraction"] != 1.0
                or rule["trace_cap"] != 1.0):
            raise ValueError("unsupported B2 γ4 rule variant")
        parameters = Gamma4Parameters(
            kc_trace_tau_us=rule["kc_trace_tau_us"],
            pam_trace_tau_us=rule["pam_trace_tau_us"],
            eta=rule["normalized_update_per_event"],
            trace_cap=rule["trace_cap"],
            minimum_weight_factor=rule["minimum_weight_factor"],
            maximum_weight_factor=rule["maximum_weight_factor"])
        b1_path = root / "docs/figures/b1_mvp_pathway_rule_selection/selected_anatomy.json"
        mask_data = json.loads((root / "configs/b2_candidate1_runtime_mask.json")
                               .read_text(encoding="utf-8"))
        if hashlib.sha256(b1_path.read_bytes()).hexdigest() != mask_data["b1_anatomy_sha256"]:
            raise ValueError("B1 anatomy differs from the runtime mask source")
        b1 = json.loads(b1_path.read_text(encoding="utf-8"))
        pam = b1["dan_source_ids"]
        if len(pam) != config["roster"]["pam08_count"] or len(pam) != 25:
            raise ValueError("B2 PAM08 roster differs from B1")
        return cls(graph, source_ids_by_index, mask, pam, parameters)

    @staticmethod
    def _decay(state: tuple[float, int], time_us: int, tau_us: int) -> float:
        return state[0] * math.exp(-(time_us - state[1]) / tau_us)

    def effective_weight(self, edge_slot: int) -> float:
        if type(edge_slot) is not int or not 0 <= edge_slot < self.graph.edge_count:
            raise ValueError("edge slot outside graph")
        if edge_slot in self._plastic_by_slot:
            return self._fixed_by_slot[edge_slot] + self._plastic_by_slot[edge_slot]
        return float(self.graph.weights_mv[edge_slot])

    def state(self) -> dict:
        """Return causal γ4 state keyed by stable KC source ID."""
        return {
            "mask_sha256": self.mask.mask_sha256,
            "selected_plastic_weights_by_kc_source_id": {
                str(kc): self._plastic_by_slot[slot]
                for kc, slot in sorted(self._slot_by_kc.items())},
            "kc_trace_value_and_last_update_us": {
                str(kc): list(self._kc_trace[kc]) for kc in sorted(self._kc_trace)},
            "pam_trace_value_and_last_update_us": list(self._pam_trace),
            "last_event_time_us": self._last_time_us,
            "last_spike_batch_time_us": self._last_batch_time_us,
            "enabled": self.enabled,
        }

    def restore(self, state: dict) -> None:
        """Validate every selected value before mutating rule state."""
        required = {"mask_sha256", "selected_plastic_weights_by_kc_source_id",
                    "kc_trace_value_and_last_update_us",
                    "pam_trace_value_and_last_update_us", "last_event_time_us",
                    "last_spike_batch_time_us", "enabled"}
        if set(state) != required or state["mask_sha256"] != self.mask.mask_sha256:
            raise ValueError("γ4 state schema or mask differs")
        keyset = {str(kc) for kc in self._slot_by_kc}
        weights = state["selected_plastic_weights_by_kc_source_id"]
        traces = state["kc_trace_value_and_last_update_us"]
        if set(weights) != keyset or set(traces) != keyset:
            raise ValueError("γ4 selected KC membership differs")
        last = state["last_event_time_us"]
        batch = state["last_spike_batch_time_us"]
        if (type(last) is not int or last < 0 or
                (batch is not None and (type(batch) is not int or not 0 <= batch <= last))
                or type(state["enabled"]) is not bool):
            raise ValueError("invalid γ4 event clock or enabled flag")

        def checked_trace(value):
            if (not isinstance(value, list) or len(value) != 2
                    or type(value[0]) not in (int, float)
                    or not math.isfinite(value[0])
                    or not 0 <= value[0] <= self.parameters.trace_cap
                    or type(value[1]) is not int or not 0 <= value[1] <= last):
                raise ValueError("invalid γ4 trace")
            return (float(value[0]), value[1])

        next_weights = {}
        next_traces = {}
        for kc, slot in self._slot_by_kc.items():
            value = weights[str(kc)]
            initial = self._initial_by_slot[slot]
            if (type(value) not in (int, float) or not math.isfinite(value)
                    or not initial * self.parameters.minimum_weight_factor <= value
                    <= initial * self.parameters.maximum_weight_factor):
                raise ValueError("γ4 plastic weight outside B2 bounds")
            next_weights[slot] = float(value)
            next_traces[kc] = checked_trace(traces[str(kc)])
        next_pam = checked_trace(state["pam_trace_value_and_last_update_us"])
        self._plastic_by_slot = next_weights
        self._kc_trace = next_traces
        self._pam_trace = next_pam
        self._last_time_us = last
        self._last_batch_time_us = batch
        self.enabled = state["enabled"]

    def frozen_policy_state(self) -> dict:
        """Learned selected weights only; no trace or pending teaching state."""
        state = self.state()
        return {"mask_sha256": state["mask_sha256"],
                "selected_plastic_weights_by_kc_source_id":
                    state["selected_plastic_weights_by_kc_source_id"]}

    def load_frozen_policy(self, policy: dict) -> None:
        """Install learned weights into a fresh zero-trace rule and disable updates."""
        if (set(policy) != {"mask_sha256", "selected_plastic_weights_by_kc_source_id"}
                or self._last_time_us != 0 or self._last_batch_time_us is not None
                or any(value for value, _ in self._kc_trace.values())
                or self._pam_trace[0]):
            raise ValueError("frozen policy needs a fresh rule and exact schema")
        candidate = self.state()
        candidate["selected_plastic_weights_by_kc_source_id"] = policy[
            "selected_plastic_weights_by_kc_source_id"]
        candidate["mask_sha256"] = policy["mask_sha256"]
        candidate["enabled"] = False
        self.restore(candidate)

    def observe_spikes(self, time_us: int, neuron_indices: Iterable[int],
                       *, compartment: str = "g4(L)",
                       eligibility_enabled: bool = True) -> Gamma4BatchRecord:
        """Consume one complete simultaneous spike batch, atomically."""
        if compartment != "g4(L)":
            raise ValueError("PAM/KC event has the wrong compartment")
        if type(eligibility_enabled) is not bool:
            raise ValueError("eligibility_enabled must be boolean")
        require_time_us(time_us, "time_us")
        if time_us < self._last_time_us or time_us == self._last_batch_time_us:
            raise ValueError("spike batches must have unique chronological timestamps")
        indices = tuple(neuron_indices)
        if (len(indices) != len(set(indices)) or any(type(i) is not int
                or not 0 <= i < self.graph.neuron_count for i in indices)):
            raise ValueError("invalid or duplicate spike source")
        sources = {self.source_ids_by_index[i] for i in indices}
        kc_spikes = tuple(sorted(sources & self._slot_by_kc.keys()))
        pam_spikes = tuple(sorted(sources & self._pam_set))
        p = len(pam_spikes) / len(self.pam_source_ids)
        d_pre = self._decay(self._pam_trace, time_us, self.parameters.pam_trace_tau_us)
        if not eligibility_enabled:
            # Control arm: preserve observed KC/PAM events and event clocks, but
            # neither local traces nor selected contributions may change.
            self._last_time_us = time_us
            self._last_batch_time_us = time_us
            return Gamma4BatchRecord(time_us, "g4(L)", self.mask.mask_sha256,
                                     kc_spikes, pam_spikes, p, d_pre, ())
        updates: list[Gamma4WeightUpdate] = []
        proposed: dict[int, float] = {}
        if self.enabled:
            affected = sorted(self._slot_by_kc) if p else kc_spikes
            for kc in affected:
                slot = self._slot_by_kc[kc]
                x_pre = self._decay(self._kc_trace[kc], time_us,
                                    self.parameters.kc_trace_tau_us)
                if p and kc in kc_spikes:
                    branch = "coincident_depression"
                    delta = -self.parameters.eta * self._initial_by_slot[slot] * max(x_pre, 1.0) * p
                elif p:
                    branch = "kc_before_pam_depression"
                    delta = -self.parameters.eta * self._initial_by_slot[slot] * x_pre * p
                else:
                    branch = "pam_before_kc_potentiation"
                    delta = self.parameters.eta * self._initial_by_slot[slot] * d_pre
                previous = self._plastic_by_slot[slot]
                raw = previous + delta
                if not math.isfinite(raw):
                    raise ArithmeticError("non-finite γ4 weight proposal")
                initial = self._initial_by_slot[slot]
                applied = min(initial * self.parameters.maximum_weight_factor,
                              max(initial * self.parameters.minimum_weight_factor, raw))
                proposed[slot] = applied
                pair = self.mask.by_kc[kc]
                updates.append(Gamma4WeightUpdate(
                    time_us, "g4(L)", self.mask.mask_sha256, kc, slot,
                    pair.plastic_contacts, branch, x_pre, d_pre, p,
                    previous, raw, applied, applied != raw))
        # Validate every proposal before changing traces or weights.
        next_kc = {}
        for kc in kc_spikes:
            value = min(self.parameters.trace_cap,
                        self._decay(self._kc_trace[kc], time_us,
                                    self.parameters.kc_trace_tau_us) + 1.0)
            if not math.isfinite(value):
                raise ArithmeticError("non-finite KC trace")
            next_kc[kc] = (value, time_us)
        next_d = min(self.parameters.trace_cap, d_pre + p)
        if not math.isfinite(next_d):
            raise ArithmeticError("non-finite PAM trace")
        for slot, value in proposed.items():
            self._plastic_by_slot[slot] = value
        self._kc_trace.update(next_kc)
        if p:
            self._pam_trace = (next_d, time_us)
        self._last_time_us = time_us
        self._last_batch_time_us = time_us
        return Gamma4BatchRecord(time_us, "g4(L)", self.mask.mask_sha256,
                                 kc_spikes, pam_spikes, p, d_pre, tuple(updates))
