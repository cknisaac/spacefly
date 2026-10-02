"""Fixed component interventions at the A3 seed-2002 outcome-373 update."""

from __future__ import annotations

import hashlib
import json
import math
import os
import pickle
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

from project_b.experiments import TinyLaneSession
from scripts.exploration_map_diagnostic import inspect_original_common, make_probe
from scripts.long_continuation import atomic_json, event_record, sha
from scripts.successive_update_interference_diagnostic import (
    LONG_LEDGER, LONG_META, LONG_PROTOCOL, ORIGINAL_LEDGER,
    make_config, replay_to, timing_summary,
)
from scripts.update_direction_magnitude_diagnostic import geometry
from scripts.weight_rollback_diagnostic import PERMITTED_REPLAY_SOURCE_DRIFT
from scripts.exploration_map_diagnostic import load_long_rows, load_rows


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/eligibility_timing_credit_diagnostic.json"
A3 = ROOT / "docs/figures/successive_update_interference"
OUTPUT = ROOT / "docs/figures/eligibility_timing_credit"
RESULT = OUTPUT / "result.json"
META = OUTPUT / "meta.json"
STATUS = OUTPUT / "status.json"
TARGET_SEED = 2002
TARGET_OUTCOME = 373


def digest_bytes(value: object) -> str:
    return hashlib.sha256(pickle.dumps(value, protocol=5)).hexdigest()


def eligibility_vector(session: TinyLaneSession, time_us: int) -> list[float]:
    return [session.plasticity.eligibility_at(slot, time_us)
            for slot in session.layout.plastic_slots]


def replay_and_capture(originals: dict, long_rows: dict,
                       long_protocol: dict, a3_point: dict) -> tuple[bytes, dict, dict]:
    source = long_rows[TARGET_SEED]
    target_us = source["update_diagnostics"][TARGET_OUTCOME - 1]["time_us"]
    cut450, cut150 = target_us - 450_000, target_us - 150_000
    session = replay_to(TARGET_SEED, TARGET_OUTCOME - 1,
                        originals, long_rows, long_protocol)
    assert session.simulator.current_time_us < cut450 < cut150 < target_us
    while session.simulator.current_time_us < cut450:
        session.step()
    assert session.simulator.current_time_us == cut450
    assert session.resolved_count == TARGET_OUTCOME - 1
    e450 = eligibility_vector(session, cut450)
    while session.simulator.current_time_us < cut150:
        session.step()
    assert session.simulator.current_time_us == cut150
    assert session.resolved_count == TARGET_OUTCOME - 1
    e150 = eligibility_vector(session, cut150)
    original_apply = session.simulator.apply_dopamine
    captured = {}

    def intercept(dopamine: float):
        assert session.resolved_count + 1 == TARGET_OUTCOME
        del session.simulator.apply_dopamine
        try:
            pre = session.checkpoint_bytes()
            geo = geometry(session, dopamine)
            changes = original_apply(dopamine)
        finally:
            session.simulator.apply_dopamine = intercept
        captured["pre"] = pre
        captured["geometry"] = geo
        captured["real_changed_edges"] = len(changes)
        captured["real_weights_after_mv"] = [
            session.plasticity.effective_weight(slot)
            for slot in session.layout.plastic_slots]
        return changes

    session.simulator.apply_dopamine = intercept
    while session.resolved_count < TARGET_OUTCOME:
        session.step()
    assert captured
    del session.simulator.apply_dopamine
    event = event_record(session, TARGET_OUTCOME - 1)
    assert event == source["training_events"][TARGET_OUTCOME - 1]
    assert event == a3_point["training_event"]
    geo = captured["geometry"]
    prior = a3_point["update"]
    for key in ("edge_slots", "time_us", "dopamine", "eta", "weight_bounds_mv",
                "weights_before_mv", "eligibility", "raw_proposed_update_mv",
                "proposed_below_min_slots", "proposed_above_max_slots"):
        assert geo[key] == prior[key], key
    assert captured["real_weights_after_mv"] == prior["weights_after_mv"]
    assert captured["real_changed_edges"] == prior["changed_edges"]
    tau = session.plasticity.parameters.tau_eligibility_us
    assert tau == 150_000
    factor150 = math.exp(-150_000 / tau)
    factor450 = math.exp(-450_000 / tau)
    old150 = [x * factor150 for x in e150]
    old450 = [x * factor450 for x in e450]
    recent = [all_e - old_e for all_e, old_e in zip(geo["eligibility"], old150)]
    age150_450 = [x - y for x, y in zip(old150, old450)]
    assert all(x >= -1e-10 for x in recent + age150_450 + old450)
    assert all(math.isclose(r + o, total, rel_tol=0, abs_tol=1e-11)
               for r, o, total in zip(recent, old150, geo["eligibility"]))
    age = {"tau_eligibility_us": tau,
           "cutoffs_us": {"t_minus_450ms": cut450, "t_minus_150ms": cut150,
                          "dopamine_time": target_us},
           "eligibility_at_t_minus_450ms": e450,
           "eligibility_at_t_minus_150ms": e150,
           "recent_0_to_150ms": recent,
           "older_than_150ms": old150,
           "age_150_to_450ms": age150_450,
           "older_than_450ms": old450,
           "semantics": "Age of postsynaptic eligibility additions under exact exponential decay; pre-post spike lag within each addition is not reconstructed."}
    pre_session = TinyLaneSession.from_trusted_checkpoint_bytes(captured["pre"])
    assert pre_session.plasticity is pre_session.simulator.plasticity
    state = {"pre_update_checkpoint_sha256": hashlib.sha256(captured["pre"]).hexdigest(),
             "simulator_snapshot": repr(pre_session.simulator.snapshot()),
             "queued_arrivals": pre_session.simulator.snapshot().queued_arrivals,
             "neural_state_pickle_sha256": digest_bytes((
                 pre_session.simulator.voltage_mv,
                 pre_session.simulator.synaptic_drive_mv,
                 pre_session.simulator.refractory_until_us,
                 pre_session.simulator._queue,
                 pre_session.simulator.spiked_this_tick)),
             "readout_state_pickle_sha256": digest_bytes(pre_session.readout),
             "reward_state_pickle_sha256": digest_bytes(pre_session.reward),
             "rng_state_sha256": digest_bytes(pre_session.rng.getstate()),
             "topology_sha256": digest_bytes(pre_session.layout.graph),
             "source_event": event,
             "predictor_expected_after_reward": pre_session.reward.predictor.expected_utility}
    return (
        captured["pre"],
        {**geo,
         "real_weights_after_mv": captured["real_weights_after_mv"],
         "real_applied_update_mv": [a - b for a, b in zip(
             captured["real_weights_after_mv"], geo["weights_before_mv"])],
         "real_changed_edges": captured["real_changed_edges"]},
        {"age": age, "state": state},
    )


def structural_groups(session: TinyLaneSession, geo: dict) -> dict:
    graph = session.layout.graph
    relay = session.layout.relay
    motor_set = set(session.layout.motor)
    sensory_count = session.encoder.neuron_count
    assert sensory_count == 40 and session.encoder.replicas == 4
    assert len(relay) == 40 and len(session.layout.motor) == 32
    groups = {"source_far_500_to_200ms": [],
              "source_mid_150_to_75ms": [],
              "source_near_50_to_0ms": [],
              "full_proposal_clipped_edges": [],
              "full_proposal_unclipped_edges": []}
    per_edge = []
    for i, slot in enumerate(geo["edge_slots"]):
        pre, post = graph.pre_indices[slot], graph.post_indices[slot]
        assert pre in relay and post in motor_set
        relay_index = relay.index(pre)
        sensory_index = min(sensory_count - 1, relay_index * sensory_count // len(relay))
        bin_index = sensory_index // session.encoder.replicas
        preferred_us = session.encoder.preferred_us[bin_index]
        source_name = ("source_far_500_to_200ms" if bin_index <= 3 else
                       "source_mid_150_to_75ms" if bin_index <= 6 else
                       "source_near_50_to_0ms")
        groups[source_name].append(slot)
        proposed = geo["weights_before_mv"][i] + geo["raw_proposed_update_mv"][i]
        lo, hi = geo["weight_bounds_mv"]
        clipped = proposed < lo or proposed > hi
        clip_name = "full_proposal_clipped_edges" if clipped else "full_proposal_unclipped_edges"
        groups[clip_name].append(slot)
        per_edge.append({"slot": slot, "pre_relay_id": pre, "post_motor_id": post,
                         "sensory_parent_id": sensory_index,
                         "cue_bin_index": bin_index,
                         "preferred_time_to_contact_us": preferred_us,
                         "source_group": source_name,
                         "real_full_proposal_clips": clipped,
                         "weight_at_upper_bound_before": geo["weights_before_mv"][i] == hi,
                         "weight_at_lower_bound_before": geo["weights_before_mv"][i] == lo})
    assert [len(groups[n]) for n in (
        "source_far_500_to_200ms", "source_mid_150_to_75ms",
        "source_near_50_to_0ms")] == [192, 144, 144]
    assert len(groups["full_proposal_clipped_edges"]) == 354
    assert len(groups["full_proposal_unclipped_edges"]) == 126
    return {"edge_metadata": per_edge, "group_slots": groups,
            "motor_target_ids": list(session.layout.motor),
            "relay_source_ids": list(session.layout.relay),
            "cue_preferred_us": list(session.encoder.preferred_us)}


def branch_weights(pre: bytes, name: str, geo: dict, structure: dict,
                   age: dict, zero_bytes: bytes) -> tuple[bytes, dict]:
    session = TinyLaneSession.from_trusted_checkpoint_bytes(pre)
    slots = session.layout.plastic_slots
    before = geo["weights_before_mv"]
    p = session.plasticity.parameters
    D = geo["dopamine"]
    if name == "real_full":
        changes = session.simulator.apply_dopamine(D)
        raw = geo["raw_proposed_update_mv"]
    elif name == "rpe_sign_reversed":
        changes = session.simulator.apply_dopamine(-D)
        raw = [-x for x in geo["raw_proposed_update_mv"]]
    else:
        session.simulator.apply_dopamine(0.0)
        if name == "no_update":
            raw = [0.0] * len(slots)
        elif name in structure["group_slots"]:
            selected = set(structure["group_slots"][name])
            raw = [d if slot in selected else 0.0
                   for slot, d in zip(slots, geo["raw_proposed_update_mv"])]
        elif name == "eligibility_recent_0_to_150ms":
            raw = [p.eta * e * D for e in age["recent_0_to_150ms"]]
        elif name == "eligibility_older_than_150ms":
            raw = [p.eta * e * D for e in age["older_than_150ms"]]
        else:
            raise ValueError(name)
        for slot, old, delta in zip(slots, before, raw):
            session.plasticity._weights[slot] = min(p.w_max_mv,
                                                   max(p.w_min_mv, old + delta))
        changes = ()  # Manual edge-mask interventions are diagnostic only.
    after = [session.plasticity.effective_weight(slot) for slot in slots]
    applied = [a - b for a, b in zip(after, before)]
    assert all(math.isclose(a, min(p.w_max_mv, max(p.w_min_mv, b + r)),
                            rel_tol=0, abs_tol=1e-12)
               for a, b, r in zip(after, before, raw))
    if name == "real_full":
        assert after == geo["real_weights_after_mv"]
        assert len(changes) == geo["real_changed_edges"]
    if name == "no_update":
        assert session.checkpoint_bytes() == zero_bytes
    branch_bytes = session.checkpoint_bytes()
    for slot, original in zip(slots, before):
        session.plasticity._weights[slot] = original
    assert session.checkpoint_bytes() == zero_bytes, name
    clipped = [slot for slot, r, a in zip(slots, raw, applied)
               if not math.isclose(r, a, rel_tol=0, abs_tol=1e-12)]
    return branch_bytes, {"raw_proposed_update_mv": raw,
                          "applied_update_mv": applied,
                          "weights_after_mv": after,
                          "raw_l1_mv": sum(abs(x) for x in raw),
                          "raw_l2_mv": math.sqrt(sum(x*x for x in raw)),
                          "applied_l1_mv": sum(abs(x) for x in applied),
                          "applied_l2_mv": math.sqrt(sum(x*x for x in applied)),
                          "changed_edge_count": sum(a != b for a, b in zip(after, before)),
                          "clipped_slots": clipped,
                          "clipped_edge_count": len(clipped),
                          "lower_bound_edges_after": sum(w == p.w_min_mv for w in after),
                          "upper_bound_edges_after": sum(w == p.w_max_mv for w in after)}


def paired_timing(current: dict, reference: dict) -> dict:
    pairs = [(a["hit_error_us"], b["hit_error_us"])
             for a, b in zip(current["events"], reference["events"])
             if a["hit_error_us"] is not None and b["hit_error_us"] is not None]
    differences = [(a - b) / 1000 for a, b in pairs]
    return {"paired_note_count": len(pairs),
            "paired_signed_error_delta_ms_by_note": [
                (a["hit_error_us"] - b["hit_error_us"]) / 1000
                if a["hit_error_us"] is not None and b["hit_error_us"] is not None else None
                for a, b in zip(current["events"], reference["events"])],
            "mean_paired_signed_error_delta_ms": statistics.mean(differences)
            if differences else None}


def main() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    names = protocol["branches"]
    assert len(names) == len(set(names)) == 10
    assert protocol["case"] == {"seed": 2002, "one_based_training_outcome": 373,
                               "source_condition": "on"}
    protocol_sha = sha(PROTOCOL)
    source_sha = sha(LONG_LEDGER)
    a3_sha = sha(A3 / "runs.jsonl")
    a3_counter_sha = sha(A3 / "counterfactual.json")
    long_meta = json.loads(LONG_META.read_text(encoding="utf-8"))
    assert long_meta["protocol_sha256"] == sha(LONG_PROTOCOL)
    assert long_meta["source_ledger_sha256"] == sha(ORIGINAL_LEDGER)
    model_hashes = {relative: sha(ROOT / relative)
                    for relative in long_meta["model_source_sha256"]}
    drift = {relative: {"saved": expected, "replay": model_hashes[relative]}
             for relative, expected in long_meta["model_source_sha256"].items()
             if model_hashes[relative] != expected}
    assert {k: v["replay"] for k, v in drift.items()} == PERMITTED_REPLAY_SOURCE_DRIFT
    source = load_long_rows()
    originals = load_rows(ORIGINAL_LEDGER)
    long_protocol = json.loads(LONG_PROTOCOL.read_text(encoding="utf-8"))
    a3_row = next(json.loads(line) for line in (A3 / "runs.jsonl").read_text(
        encoding="utf-8").splitlines() if json.loads(line)["seed"] == 2002)
    a3_point = a3_row["checkpoints"][373 - a3_row["start_after_outcomes"]]
    a3_counter = json.loads((A3 / "counterfactual.json").read_text(encoding="utf-8"))
    assert a3_counter["status"] == "complete" and a3_counter["target_outcome"] == 373
    common = (tuple(long_meta["probe_relative_note_offsets_us"]),
              tuple(long_meta["probe_cue_gains"]))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    atomic_json(STATUS, {"status": "running", "protocol_sha256": protocol_sha})
    pre, geo, extra = replay_and_capture(originals, source, long_protocol,
                                         a3_point)
    structure = structural_groups(TinyLaneSession.from_trusted_checkpoint_bytes(pre), geo)
    zero = TinyLaneSession.from_trusted_checkpoint_bytes(pre)
    zero.simulator.apply_dopamine(0.0)
    zero_bytes = zero.checkpoint_bytes()
    note_times = tuple(geo["time_us"] + offset for offset in common[0])
    branches = {}
    for name in names:
        snap, update = branch_weights(pre, name, geo, structure,
                                      extra["age"], zero_bytes)
        probe = make_probe(snap, note_times, common[1], False, None)
        branches[name] = {"update": update, "probe": probe,
                          "timing": timing_summary(probe)}
        if name == "no_update":
            assert probe == a3_counter["branches"]["skip_target_update"]["immediate_probe"]
        if name == "real_full":
            assert probe == a3_counter["branches"]["real_update"]["immediate_probe"]
            inspect_original_common(probe, a3_point["probe"])
        print(json.dumps({"branch": name,
                          "good": probe["metrics"]["good_or_better_count"],
                          "utility": probe["metrics"]["mean_utility"],
                          "attempt_error_ms": branches[name]["timing"]["mean_signed_attempt_error_ms"],
                          "applied_l1_mv": update["applied_l1_mv"]}), flush=True)
    baseline = branches["no_update"]["probe"]
    for name in names:
        branches[name]["paired_timing_vs_no"] = paired_timing(branches[name]["probe"], baseline)
    full = geo["real_applied_update_mv"]
    for i, (a, b) in enumerate(zip(
            branches["full_proposal_clipped_edges"]["update"]["applied_update_mv"],
            branches["full_proposal_unclipped_edges"]["update"]["applied_update_mv"])):
        assert math.isclose(a + b, full[i], rel_tol=0, abs_tol=1e-12)
    age = extra["age"]
    assert all(math.isclose(a+b, e, rel_tol=0, abs_tol=1e-11)
               for a, b, e in zip(age["recent_0_to_150ms"],
                                  age["older_than_150ms"], geo["eligibility"]))
    result = {"study_id": protocol["study_id"], "status": "complete",
              "protocol_sha256": protocol_sha,
              "source_long_ledger_sha256": source_sha,
              "a3_trajectory_ledger_sha256": a3_sha,
              "a3_counterfactual_sha256": a3_counter_sha,
              "seed": TARGET_SEED, "one_based_outcome": TARGET_OUTCOME,
              "pre_update_geometry": geo,
              "age_decomposition": age,
              "source_pathway_structure": structure,
              "pre_update_state": extra["state"],
              "branches": branches,
              "completed_utc": datetime.now(timezone.utc).isoformat()}
    atomic_json(RESULT, result)
    atomic_json(META, {"study_id": protocol["study_id"],
                       "completed_utc": result["completed_utc"],
                       "python": sys.version.split()[0],
                       "protocol_sha256": protocol_sha,
                       "source_long_ledger_sha256": source_sha,
                       "source_long_meta_sha256": sha(LONG_META),
                       "source_original_ledger_sha256": sha(ORIGINAL_LEDGER),
                       "a3_trajectory_ledger_sha256": a3_sha,
                       "a3_counterfactual_sha256": a3_counter_sha,
                       "saved_model_source_sha256": long_meta["model_source_sha256"],
                       "replay_model_source_sha256": model_hashes,
                       "source_hash_drift_requiring_exact_replay": drift,
                       "synthetic_topology": "build_tiny_brain; no imported connectome"})
    atomic_json(STATUS, {"status": "complete", "protocol_sha256": protocol_sha,
                         "result_sha256": sha(RESULT)})
    print(json.dumps({"status": "complete", "result_sha256": sha(RESULT)}), flush=True)


if __name__ == "__main__":
    main()
