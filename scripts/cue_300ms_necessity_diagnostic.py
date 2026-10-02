"""Exact three-branch necessity test at synthetic seed 2002, outcome 373."""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path

from project_b.experiments import TinyLaneSession
from project_b.motor.fixed_readout import FixedMotorReadout
from scripts import eligibility_timing_credit_diagnostic as a4
from scripts.exploration_map_diagnostic import load_long_rows, load_rows, make_probe
from scripts.long_continuation import atomic_json, sha
from scripts.successive_update_interference_diagnostic import timing_summary


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/cue_300ms_necessity_diagnostic.json"
A4 = ROOT / "docs/figures/eligibility_timing_credit"
OUTPUT = ROOT / "docs/figures/cue_300ms_necessity"
CHECKPOINT_NAMES = {
    "pre_update": "pre_update_checkpoint.pkl",
    "no_update": "no_update_checkpoint.pkl",
    "real_full": "real_full_checkpoint.pkl",
    "real_except_300ms": "real_except_300ms_checkpoint.pkl",
}


def checkpoint_digest(checkpoint: bytes) -> str:
    return hashlib.sha256(checkpoint).hexdigest()


def readout_initial_state(checkpoint: bytes) -> dict:
    session = TinyLaneSession.from_trusted_checkpoint_bytes(checkpoint)
    r = session.readout
    return {
        "key_down": r.key_down,
        "last_down_us": r._last_down_us,
        "last_time_us": r._last_time_us,
        "spike_times_us": list(r._spike_times),
        "motor_neuron_indices": list(r.neuron_indices),
        "window_us": r.window_us,
        "on_threshold": r.on_threshold,
        "off_threshold": r.off_threshold,
        "min_hold_us": r.min_hold_us,
        "max_hold_us": r.max_hold_us,
        "cooldown_us": r.cooldown_us,
        "dt_us": session.config.dt_us,
    }


def probe_with_readout_trace(checkpoint: bytes, note_times: tuple[int, ...],
                             gains: tuple[float, ...]) -> tuple[dict, dict]:
    """Observe one existing frozen probe without changing its decisions."""
    initial = readout_initial_state(checkpoint)
    motor_set = set(initial["motor_neuron_indices"])
    trace = {"initial": initial, "motor_spike_batches": [],
             "threshold_crossings": [], "readout_decisions": [],
             "first_observe_us": None, "last_observe_us": None,
             "observe_tick_count": 0}
    previous_on = len(initial["spike_times_us"]) >= initial["on_threshold"]
    previous_off = len(initial["spike_times_us"]) <= initial["off_threshold"]
    original_observe = FixedMotorReadout.observe

    def traced_observe(self: FixedMotorReadout, time_us: int, spiking_indices):
        nonlocal previous_on, previous_off
        spikes = tuple(spiking_indices)
        key_down_before = self.key_down
        decision = original_observe(self, time_us, spikes)
        motor_spikes = [i for i in spikes if i in motor_set]
        if motor_spikes:
            trace["motor_spike_batches"].append({"time_us": time_us,
                                                  "motor_neuron_indices": motor_spikes})
        count = len(self._spike_times)
        now_on = count >= self.on_threshold
        now_off = count <= self.off_threshold
        for name, before, after in (("on", previous_on, now_on),
                                    ("off", previous_off, now_off)):
            if before != after:
                trace["threshold_crossings"].append({
                    "time_us": time_us, "threshold": name,
                    "direction": "rise" if after else "fall",
                    "spike_count_in_window": count,
                    "key_down_before": key_down_before,
                    "key_down_after": self.key_down,
                })
        previous_on, previous_off = now_on, now_off
        if decision is not None:
            trace["readout_decisions"].append({
                "time_us": decision.time_us,
                "kind": decision.action.kind.value,
                "lane": decision.action.lane,
                "spike_count_in_window": decision.spike_count_in_window,
                "threshold": decision.threshold,
            })
        if trace["first_observe_us"] is None:
            trace["first_observe_us"] = time_us
        trace["last_observe_us"] = time_us
        trace["observe_tick_count"] += 1
        return decision

    FixedMotorReadout.observe = traced_observe
    try:
        probe = make_probe(checkpoint, note_times, gains, False, None)
    finally:
        FixedMotorReadout.observe = original_observe
    assert trace["observe_tick_count"] > 0
    assert sum(len(batch["motor_neuron_indices"])
               for batch in trace["motor_spike_batches"]) == probe["motor_spikes"]
    assert sum(d["kind"] == "down" for d in trace["readout_decisions"]) == len(probe["down_actions"])
    return probe, trace


def make_omission(full_checkpoint: bytes, zero_checkpoint: bytes,
                  geo: dict, structure: dict) -> tuple[bytes, dict]:
    session = TinyLaneSession.from_trusted_checkpoint_bytes(full_checkpoint)
    slots = geo["edge_slots"]
    before = geo["weights_before_mv"]
    full = geo["real_weights_after_mv"]
    omitted = [i for i, edge in enumerate(structure["edge_metadata"])
               if edge["preferred_time_to_contact_us"] == 300_000]
    assert len(omitted) == 48
    assert len({structure["edge_metadata"][i]["pre_relay_id"] for i in omitted}) == 4
    assert len({structure["edge_metadata"][i]["post_motor_id"] for i in omitted}) == 12
    assert all(before[i] != full[i] for i in omitted)
    for i in omitted:
        session.plasticity._weights[slots[i]] = before[i]
    after = [session.plasticity.effective_weight(slot) for slot in slots]
    assert all(after[i] == (before[i] if i in omitted else full[i])
               for i in range(480))
    checkpoint = session.checkpoint_bytes()
    for i in omitted:
        session.plasticity._weights[slots[i]] = full[i]
    assert session.checkpoint_bytes() == full_checkpoint
    for i, slot in enumerate(slots):
        session.plasticity._weights[slot] = before[i]
    assert session.checkpoint_bytes() == zero_checkpoint
    applied = [new - old for new, old in zip(after, before)]
    removed = [b - c for b, c in zip(full, after)]
    assert all(removed[i] == 0.0 for i in range(480) if i not in omitted)
    return checkpoint, {
        "omitted_edge_slots": [slots[i] for i in omitted],
        "weights_after_mv": after,
        "applied_update_mv": applied,
        "removed_applied_update_mv": removed,
        "applied_l1_mv": sum(abs(x) for x in applied),
        "removed_applied_l1_mv": sum(abs(x) for x in removed),
        "changed_edge_count": sum(x != 0.0 for x in applied),
        "clipped_retained_edges_identical_to_full": True,
    }


def main() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert protocol["branches"] == ["no_update", "real_full", "real_except_300ms"]
    a4_result = json.loads((A4 / "result.json").read_text(encoding="utf-8"))
    a4_meta = json.loads((A4 / "meta.json").read_text(encoding="utf-8"))
    assert a4_result["status"] == "complete"
    assert a4_meta["protocol_sha256"] == a4_result["protocol_sha256"]
    assert sha(A4 / "result.json") == json.loads((A4 / "status.json").read_text(
        encoding="utf-8"))["result_sha256"]
    a3_row = next(json.loads(line) for line in (a4.A3 / "runs.jsonl").read_text(
        encoding="utf-8").splitlines() if json.loads(line)["seed"] == 2002)
    a3_point = a3_row["checkpoints"][373 - a3_row["start_after_outcomes"]]
    originals = load_rows(a4.ORIGINAL_LEDGER)
    long_rows = load_long_rows()
    long_protocol = json.loads(a4.LONG_PROTOCOL.read_text(encoding="utf-8"))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    atomic_json(OUTPUT / "status.json", {"status": "running", "protocol_sha256": sha(PROTOCOL)})
    pre, geo, extra = a4.replay_and_capture(originals, long_rows, long_protocol,
                                            a3_point)
    structure = a4.structural_groups(TinyLaneSession.from_trusted_checkpoint_bytes(pre), geo)
    # Whole-session pickle bytes are not canonical across independent
    # processes. Compare the separately hashed coupled state and exact
    # A3/A4 geometry instead; retain both serialization hashes in the result.
    (OUTPUT / CHECKPOINT_NAMES["pre_update"]).write_bytes(pre)
    assert geo == a4_result["pre_update_geometry"]
    for key, value in extra["state"].items():
        if key != "pre_update_checkpoint_sha256":
            assert value == a4_result["pre_update_state"][key], key
    assert structure == a4_result["source_pathway_structure"]
    zero_session = TinyLaneSession.from_trusted_checkpoint_bytes(pre)
    zero_session.simulator.apply_dopamine(0.0)
    zero_checkpoint = zero_session.checkpoint_bytes()
    checkpoints = {"pre_update": pre}
    records = {}
    for name in ("no_update", "real_full"):
        checkpoint, update = a4.branch_weights(pre, name, geo, structure,
                                                extra["age"], zero_checkpoint)
        assert update == a4_result["branches"][name]["update"]
        checkpoints[name] = checkpoint
        records[name] = {"update": update}
    assert checkpoints["no_update"] == zero_checkpoint
    intervention_checkpoint, intervention_update = make_omission(
        checkpoints["real_full"], zero_checkpoint, geo, structure)
    checkpoints["real_except_300ms"] = intervention_checkpoint
    records["real_except_300ms"] = {"update": intervention_update}
    for name, filename in CHECKPOINT_NAMES.items():
        (OUTPUT / filename).write_bytes(checkpoints[name])
    long_meta = json.loads(a4.LONG_META.read_text(encoding="utf-8"))
    offsets = tuple(long_meta["probe_relative_note_offsets_us"])
    gains = tuple(long_meta["probe_cue_gains"])
    note_times = tuple(geo["time_us"] + offset for offset in offsets)
    for name in protocol["branches"]:
        probe, trace = probe_with_readout_trace(checkpoints[name], note_times, gains)
        if name in ("no_update", "real_full"):
            assert probe == a4_result["branches"][name]["probe"]
        timing = timing_summary(probe)
        signed_down = [x["signed_nearest_note_error_us"]
                       for x in timing["down_actions_with_nearest_note"]]
        timing["mean_signed_all_down_ms"] = (
            statistics.mean(signed_down) / 1000 if signed_down else None)
        records[name].update({"probe": probe, "timing": timing,
                              "readout_trace": trace,
                              "checkpoint_sha256": checkpoint_digest(checkpoints[name])})
        print(json.dumps({"branch": name,
                          "good": probe["metrics"]["good_or_better_count"],
                          "utility": probe["metrics"]["mean_utility"],
                          "attempt_error_ms": timing["mean_signed_attempt_error_ms"],
                          "down_count": probe["metrics"]["down_count"]}), flush=True)
    no_probe = records["no_update"]["probe"]
    for name in protocol["branches"]:
        records[name]["paired_timing_vs_no"] = a4.paired_timing(records[name]["probe"], no_probe)
    full_shift = records["real_full"]["paired_timing_vs_no"]["mean_paired_signed_error_delta_ms"]
    cut_shift = records["real_except_300ms"]["paired_timing_vs_no"]["mean_paired_signed_error_delta_ms"]
    assert full_shift == -61.71875
    cut_probe = records["real_except_300ms"]["probe"]
    cut_metrics = cut_probe["metrics"]
    comparable = (records["real_except_300ms"]["paired_timing_vs_no"]["paired_note_count"] == 32
                  and cut_metrics["down_count"] == 64
                  and cut_metrics["null_down_count"] == 32)
    if not comparable or cut_shift is None:
        interpretation = "nonlinear_mechanistically_ambiguous"
    elif cut_shift >= 0 or abs(cut_shift) <= 0.50 * abs(full_shift):
        interpretation = "major_necessary_contributor_at_this_state"
    elif cut_shift < 0 and abs(cut_shift) >= 0.75 * abs(full_shift):
        interpretation = "not_necessary_other_far_cue_components_suffice"
    else:
        interpretation = "contributory_necessity_not_established"
    result = {
        "study_id": protocol["study_id"], "status": "complete",
        "protocol_sha256": sha(PROTOCOL),
        "a4_result_sha256": sha(A4 / "result.json"),
        "seed": 2002, "one_based_outcome": 373,
        "pre_update_geometry": geo,
        "pre_update_state": extra["state"],
        "a4_reference_pre_checkpoint_sha256": a4_result["pre_update_state"]["pre_update_checkpoint_sha256"],
        "source_pathway_structure": structure,
        "checkpoint_files_sha256": {name: checkpoint_digest(value)
                                    for name, value in checkpoints.items()},
        "branches": records,
        "interpretation": {"full_shift_ms": full_shift,
                           "omission_shift_ms": cut_shift,
                           "full_minus_omission_ms": (full_shift - cut_shift
                                                      if cut_shift is not None else None),
                           "comparable_attempt_pattern": comparable,
                           "classification": interpretation},
        "completed_utc": datetime.now(timezone.utc).isoformat(),
    }
    atomic_json(OUTPUT / "result.json", result)
    atomic_json(OUTPUT / "meta.json", {
        "study_id": protocol["study_id"],
        "protocol_sha256": sha(PROTOCOL),
        "a4_result_sha256": sha(A4 / "result.json"),
        "a4_audit_sha256": sha(A4 / "audit.json"),
        "a3_counterfactual_sha256": sha(a4.A3 / "counterfactual.json"),
        "checkpoint_files_sha256": result["checkpoint_files_sha256"],
        "reference_model_source_sha256": a4_meta["replay_model_source_sha256"],
        "synthetic_topology": "build_tiny_brain; no imported connectome",
    })
    atomic_json(OUTPUT / "status.json", {
        "status": "complete", "protocol_sha256": sha(PROTOCOL),
        "result_sha256": sha(OUTPUT / "result.json")})
    print(json.dumps(result["interpretation"], indent=2))


if __name__ == "__main__":
    main()
