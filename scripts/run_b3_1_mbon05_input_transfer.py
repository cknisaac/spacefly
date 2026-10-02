"""One matched B3.1 APL→MBON05 omission with selective current balance."""

from __future__ import annotations

import hashlib
import json
import math
from copy import deepcopy
from pathlib import Path

from project_b.checkpoint.codec import _canonical, _encode
from project_b.checkpoint.frozen import FrozenPolicySnapshot
from project_b.mvp_c1.feedback import NoteWindow
from project_b.mvp_c1.first_action_audit import (
    compare_owner_outcomes, game_events_from_mvp_ledger, reconstruct_first_actions)
from project_b.mvp_c1.runtime import MvpSession
from project_b.mvp_c1.source import load_mvp_circuit


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/b3_1_mbon05_input_transfer.json"
OUT = ROOT / "docs/figures/b3_1_mbon05_input_transfer"


def digest(value) -> str:
    return hashlib.sha256(_canonical(_encode(value))).hexdigest()


def save(path: Path, value) -> str:
    payload = _canonical(_encode(value))
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


class TraceSession(MvpSession):
    """Leave production integration intact; correct only MBON05's APL term."""

    def __init__(self, *args, apl_to_mbon05_off: bool = False, **kwargs):
        self.apl_to_mbon05_off = apl_to_mbon05_off
        self.target_source_id = 10495
        self.selective_trace: list[dict] = []
        self.max_balance_error = 0.0
        self.max_cue_voltage = float("-inf")
        self.apl_current_integral = 0.0
        self.apl_membrane_term_sum = 0.0
        self.external_membrane_term_sum = 0.0
        self.chemical_membrane_term_sum = 0.0
        self.interval_count = 0
        super().__init__(*args, **kwargs)
        self.target_index = self.index[self.target_source_id]
        if self.target_index not in self.apl_indices:
            raise ValueError("B3.1 target lacks declared APL output")

    def _integrate(self, end_us: int) -> None:
        start = self.time_us
        if end_us <= start:
            return
        i = self.target_index
        dt = end_us - start
        active_start = max(start, min(end_us, int(self.refractory_until_us[i])))
        clamp = active_start - start
        active_dt = end_us - active_start
        v_before = float(self.voltage[i])
        syn_before = float(self.synaptic[i])
        apl_before = float(self.apl_state)
        external = float(self.external[i])
        em = math.exp(-active_dt / self.TAU_M_US)
        base_term = (0.0 if clamp else v_before) * em
        external_term = external * (1 - em)
        phi_syn = self.TAU_S_US / (self.TAU_S_US - self.TAU_M_US) * (
            math.exp(-active_dt / self.TAU_S_US) - em)
        synaptic_term = syn_before * math.exp(-clamp / self.TAU_S_US) * phi_syn
        phi_apl = active_dt / self.TAU_M_US * em
        apl_term = -0.2 * apl_before * math.exp(-clamp / self.TAU_APL_US) * phi_apl
        expected = base_term + external_term + synaptic_term + (
            0.0 if self.apl_to_mbon05_off else apl_term)

        super()._integrate(end_us)
        if self.apl_to_mbon05_off:
            # The production vector integration applied the one target's APL
            # term. Undo exactly that term, leaving all other cells unchanged.
            self.voltage[i] -= apl_term
        actual = float(self.voltage[i])
        self.max_balance_error = max(self.max_balance_error, abs(actual - expected))
        self.interval_count += 1
        self.external_membrane_term_sum += external_term
        self.chemical_membrane_term_sum += synaptic_term
        if not self.apl_to_mbon05_off:
            self.apl_membrane_term_sum += apl_term
            self.apl_current_integral += -0.2 * apl_before * self.TAU_APL_US * (
                1 - math.exp(-dt / self.TAU_APL_US))
        if 100_000 <= end_us <= 900_000:
            self.max_cue_voltage = max(self.max_cue_voltage, actual)
        if end_us <= 900_000 and end_us % self.DT_US == 0:
            self.selective_trace.append({
                "time_us": end_us,
                "mbon05_voltage_before_arrivals_and_threshold": actual,
                "mbon05_external_current": external,
                "mbon05_synaptic_state": float(self.synaptic[i]),
                "apl_graded_state": float(self.apl_state),
                "declared_apl_current": (0.0 if self.apl_to_mbon05_off else
                                         -0.2 * float(self.apl_state)),
                "mbon05_refractory_until_us": int(self.refractory_until_us[i]),
                "cumulative_apl_current_integral": self.apl_current_integral,
                "cumulative_apl_membrane_term_sum": self.apl_membrane_term_sum,
                "cumulative_external_membrane_term_sum": self.external_membrane_term_sum,
                "cumulative_chemical_membrane_term_sum": self.chemical_membrane_term_sum,
                "max_abs_interval_balance_error": self.max_balance_error,
            })


def run_arm(circuit, notes, policy, checkpoint: Path, arm: str,
            expected_start_sha: str) -> dict:
    off = arm == "apl_to_mbon05_off"
    session = TraceSession(circuit, ROOT, notes, seed=31001, level="nominal",
                           frozen_policy=policy, apl_to_mbon05_off=off)
    session.load(checkpoint)
    start_sha = digest(session.state())
    if start_sha != expected_start_sha:
        raise AssertionError("B3.1 arms did not load the identical committed state")
    session.run_until(1_100_000)
    ledger_sha = save(OUT / f"{arm}_ledger.json", session.ledger)
    trace_sha = save(OUT / f"{arm}_selective_trace.json", session.selective_trace)
    arrivals = [row for row in session.ledger
                if row[0] == "output_chemical_arrival" and row[2] == 10495]
    arrival_sha = save(OUT / f"{arm}_mbon05_source_arrivals.json", arrivals)
    audit = reconstruct_first_actions(notes, game_events_from_mvp_ledger(session.ledger),
                                      1_100_000)
    closed = deepcopy(session.task.first_action)
    closed.finish(1_100_000)
    compare_owner_outcomes(audit, closed.outcomes)
    audit_sha = save(OUT / f"{arm}_first_action.json", audit.as_dict())
    cue_spikes = [row[1] for row in session.ledger if row[0] == "spike" and
                  row[2] == 10495 and 100_000 <= row[1] <= 900_000]
    return {"arm": arm, "start_state_sha256": start_sha,
            "ledger_sha256": ledger_sha, "selective_trace_sha256": trace_sha,
            "source_arrivals_sha256": arrival_sha,
            "first_action_audit_sha256": audit_sha,
            "selective_trace_ticks": len(session.selective_trace),
            "integration_intervals": session.interval_count,
            "max_abs_interval_balance_error": session.max_balance_error,
            "max_cue_mbon05_voltage": session.max_cue_voltage,
            "cue_mbon05_spike_times_us": cue_spikes,
            "first_down_us": audit.rows[0].first_down_us,
            "first_action_category": audit.rows[0].category,
            "apl_current_integral": session.apl_current_integral,
            "apl_membrane_term_sum": session.apl_membrane_term_sum,
            "external_membrane_term_sum": session.external_membrane_term_sum,
            "chemical_membrane_term_sum": session.chemical_membrane_term_sum,
            "source_arrivals": len(arrivals),
            "cue_arrival_amplitude_sum": sum(row[7] for row in arrivals
                                             if 100_000 <= row[1] <= 900_000),
            "final_boundary_rng_sha256": digest(session.boundary.state()["rng_states"]),
            "final_selected_weight_sha256": digest(
                session.rule.state()["selected_plastic_weights_by_kc_source_id"]),
            "pam_task_pulses": len(session.task.feedback.pulse_records),
            "peak_queue": session.peak_queue}


def main() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if OUT.exists():
        raise FileExistsError("B3.1 evidence already exists")
    if (protocol["seed"] != 31001 or protocol["boundary_level"] != "nominal" or
            protocol["arms"] != ["baseline", "apl_to_mbon05_off"] or
            protocol["note"] != {"note_id": "b3-isolated", "visible_from_us": 100000,
                                  "hit_us": 900000}):
        raise ValueError("B3.1 protocol differs from the B3.1 proposal")
    OUT.mkdir(parents=True)
    circuit = load_mvp_circuit(ROOT)
    notes = (NoteWindow(**protocol["note"]),)
    donor = MvpSession(circuit, ROOT, notes, seed=31001)
    policy = FrozenPolicySnapshot.capture(donor.rule)
    parent = MvpSession(circuit, ROOT, notes, seed=31001, level="nominal",
                        frozen_policy=policy)
    parent.run_until(protocol["parent_committed_cut_us"])
    checkpoint = OUT / "parent_cut_1000"
    checkpoint_sha = parent.save(checkpoint)
    start_sha = digest(parent.state())
    rows = []
    for arm in protocol["arms"]:
        row = run_arm(circuit, notes, policy, checkpoint, arm, start_sha)
        rows.append(row)
        print(json.dumps({k: row[k] for k in ("arm", "max_cue_mbon05_voltage",
                                            "cue_mbon05_spike_times_us", "first_down_us")}),
              flush=True)
    b3_rows = json.loads((ROOT / "docs/figures/b3_controllability_v2/arm_results.json")
                         .read_text(encoding="utf-8"))
    b3_baseline = next(r for r in b3_rows if (r["seed"], r["level"], r["arm"]) ==
                       (31001, "nominal", "weight_1.0"))
    baseline_reproduced = rows[0]["ledger_sha256"] == b3_baseline["ledger_sha256"]
    matched = rows[0]["start_state_sha256"] == rows[1]["start_state_sha256"] == start_sha
    balanced = all(math.isfinite(r["max_abs_interval_balance_error"]) and
                   r["max_abs_interval_balance_error"] <= 1e-12 for r in rows)
    isolated = (rows[1]["apl_current_integral"] == 0 and
                rows[1]["apl_membrane_term_sum"] == 0 and
                all(r["pam_task_pulses"] == 0 for r in rows) and
                rows[0]["final_selected_weight_sha256"] ==
                rows[1]["final_selected_weight_sha256"])
    if not (matched and balanced and isolated and baseline_reproduced):
        status = "INCONCLUSIVE"
    elif not rows[0]["cue_mbon05_spike_times_us"] and rows[1]["cue_mbon05_spike_times_us"]:
        status = "PASS"
    elif not rows[0]["cue_mbon05_spike_times_us"] and not rows[1]["cue_mbon05_spike_times_us"]:
        status = "FAIL"
    else:
        status = "INCONCLUSIVE"
    receipt = {"stage_id": "MVP-B3.1", "status": status,
               "protocol_sha256": hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
               "parent_checkpoint_sha256": checkpoint_sha,
               "parent_state_sha256": start_sha,
               "source_identity": parent.identity,
               "resolved_config_sha256": circuit.resolved_sha256,
               "baseline_b3_ledger_reproduced": baseline_reproduced,
               "matched_start": matched, "selective_balance_verified": balanced,
               "one_target_intervention_and_frozen_weights": isolated,
               "arms": rows}
    save(OUT / "receipt.json", receipt)
    print(json.dumps({"status": status, "baseline_b3_reproduced": baseline_reproduced,
                      "matched_start": matched, "balance_verified": balanced}), flush=True)


if __name__ == "__main__":
    main()
