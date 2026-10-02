"""One target-cohort omission at the exact synthetic 2002:373 update."""

from __future__ import annotations

import hashlib
import json
import math
import pickle
from datetime import datetime, timezone
from pathlib import Path

from project_b.experiments import TinyLaneSession
from scripts.cue_300ms_necessity_diagnostic import probe_with_readout_trace
from scripts.long_continuation import atomic_json, sha
from scripts.successive_update_interference_diagnostic import timing_summary


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/cue_300ms_threshold_cohort_diagnostic.json"
A5 = ROOT / "docs/figures/cue_300ms_necessity"
OUTPUT = ROOT / "docs/figures/cue_300ms_threshold_cohort"
BRANCHES = ("no_update", "real_full", "real_except_300ms_targets_94_96")
SELECTED_SLOTS = (136, 137, 138, 148, 149, 150, 160, 161, 162, 172, 173, 174)


def digest(value: object) -> str:
    return hashlib.sha256(pickle.dumps(value, protocol=5)).hexdigest()


def weights(session: TinyLaneSession) -> list[float]:
    return [session.plasticity.effective_weight(slot)
            for slot in session.layout.plastic_slots]


def assert_same_state_except_weights(a: TinyLaneSession,
                                     b: TinyLaneSession) -> None:
    assert a.plasticity is a.simulator.plasticity
    assert b.plasticity is b.simulator.plasticity
    for name in vars(a):
        if name == "game":
            assert vars(a.game).keys() == vars(b.game).keys()
            for game_field in vars(a.game):
                if game_field == "_resolved":
                    assert a.game._resolved == b.game._resolved
                else:
                    assert digest(getattr(a.game, game_field)) == digest(
                        getattr(b.game, game_field)), game_field
        elif name == "population_sets":
            assert a.population_sets == b.population_sets
        elif name not in ("plasticity", "simulator"):
            assert digest(getattr(a, name)) == digest(getattr(b, name)), name
    a_w, b_w = weights(a), weights(b)
    for slot, w in zip(a.layout.plastic_slots, a_w):
        a.plasticity._weights[slot] = b_w[a.layout.plastic_slots.index(slot)]
    assert digest(a.plasticity) == digest(b.plasticity)
    assert digest(a.simulator) == digest(b.simulator)
    for slot, w in zip(a.layout.plastic_slots, a_w):
        a.plasticity._weights[slot] = w


def first_rise(trace: dict) -> dict:
    return next(item for item in trace["threshold_crossings"]
                if item["threshold"] == "on" and item["direction"] == "rise")


def window_count(trace: dict, time_us: int) -> int:
    low = time_us - trace["initial"]["window_us"]
    count = sum(low < t <= time_us for t in trace["initial"]["spike_times_us"])
    for batch in trace["motor_spike_batches"]:
        if batch["time_us"] > time_us:
            break
        if batch["time_us"] > low:
            count += len(batch["motor_neuron_indices"])
    return count


def first_note(probe: dict, trace: dict) -> dict:
    crossing = first_rise(trace)
    t = crossing["time_us"]
    dt = trace["initial"]["dt_us"]
    downs = probe["down_actions"]
    return {
        "first_on_threshold_rise_us": t,
        "readout_window_count_previous_tick": window_count(trace, t - dt),
        "readout_window_count_at_crossing": window_count(trace, t),
        "on_threshold": trace["initial"]["on_threshold"],
        "first_down_us": downs[0]["time_us"] if downs else None,
        "first_down_disposition": downs[0]["disposition"] if downs else None,
        "first_scored_down_us": next((a["time_us"] for a in downs
                                       if a["note_id"] == "probe-0"), None),
        "first_judgement": probe["events"][0]["judgement"],
        "first_scored_error_us": probe["events"][0]["hit_error_us"],
    }


def main() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert protocol["branches"] == list(BRANCHES)
    a5 = json.loads((A5 / "result.json").read_text(encoding="utf-8"))
    assert sha(A5 / "result.json") == json.loads((A5 / "status.json").read_text(
        encoding="utf-8"))["result_sha256"]
    assert json.loads((A5 / "audit.json").read_text(encoding="utf-8"))["status"] == "passed"
    pre_bytes = (A5 / "pre_update_checkpoint.pkl").read_bytes()
    assert hashlib.sha256(pre_bytes).hexdigest() == a5["checkpoint_files_sha256"]["pre_update"]
    pre = TinyLaneSession.from_trusted_checkpoint_bytes(pre_bytes)
    geo = a5["pre_update_geometry"]
    state = a5["pre_update_state"]
    assert pre.simulator.current_time_us == geo["time_us"] == 371_725_000
    assert weights(pre) == geo["weights_before_mv"]
    assert digest((pre.simulator.voltage_mv, pre.simulator.synaptic_drive_mv,
                   pre.simulator.refractory_until_us, pre.simulator._queue,
                   pre.simulator.spiked_this_tick)) == state["neural_state_pickle_sha256"]
    assert pre.simulator.snapshot().queued_arrivals == state["queued_arrivals"]
    assert digest(pre.readout) == state["readout_state_pickle_sha256"]
    assert digest(pre.reward) == state["reward_state_pickle_sha256"]
    assert digest(pre.rng.getstate()) == state["rng_state_sha256"]
    assert digest(pre.layout.graph) == state["topology_sha256"]
    assert geo["dopamine"] == state["source_event"]["rpe"]
    for i, slot in enumerate(geo["edge_slots"]):
        e = pre.plasticity.eligibility_at(slot, geo["time_us"])
        assert math.isclose(e, geo["eligibility"][i], abs_tol=1e-12)
        assert math.isclose(geo["raw_proposed_update_mv"][i],
                            geo["eta"] * geo["dopamine"] * e, abs_tol=1e-12)
    selected = [i for i, edge in enumerate(a5["source_pathway_structure"]["edge_metadata"])
                if edge["preferred_time_to_contact_us"] == 300_000
                and edge["post_motor_id"] in (94, 95, 96)]
    assert tuple(geo["edge_slots"][i] for i in selected) == SELECTED_SLOTS
    assert len(selected) == 12
    assert {a5["source_pathway_structure"]["edge_metadata"][i]["pre_relay_id"]
            for i in selected} == {48, 49, 50, 51}
    zero = TinyLaneSession.from_trusted_checkpoint_bytes(pre_bytes)
    zero.simulator.apply_dopamine(0.0)
    full = TinyLaneSession.from_trusted_checkpoint_bytes(pre_bytes)
    full.simulator.apply_dopamine(geo["dopamine"])
    assert weights(zero) == a5["branches"]["no_update"]["update"]["weights_after_mv"]
    assert weights(full) == geo["real_weights_after_mv"]
    omission = TinyLaneSession.from_trusted_checkpoint_bytes(full.checkpoint_bytes())
    for i in selected:
        omission.plasticity._weights[geo["edge_slots"][i]] = geo["weights_before_mv"][i]
    assert_same_state_except_weights(omission, full)
    after = weights(omission)
    full_w = weights(full)
    before = geo["weights_before_mv"]
    assert all(after[i] == (before[i] if i in selected else full_w[i])
               for i in range(480))
    removed_l1 = sum(abs(full_w[i] - before[i]) for i in selected)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    atomic_json(OUTPUT / "status.json", {"status": "running", "protocol_sha256": sha(PROTOCOL)})
    sessions = {"no_update": zero, "real_full": full,
                "real_except_300ms_targets_94_96": omission}
    checkpoint_bytes = {name: session.checkpoint_bytes()
                        for name, session in sessions.items()}
    for name, value in checkpoint_bytes.items():
        (OUTPUT / f"{name}_checkpoint.pkl").write_bytes(value)
    no_ref = a5["branches"]["no_update"]["probe"]
    offsets = tuple(no_ref["relative_note_offsets_us"])
    gains = tuple(no_ref["cue_gains"])
    note_times = tuple(geo["time_us"] + x for x in offsets)
    records = {}
    for name in BRANCHES:
        probe, trace = probe_with_readout_trace(checkpoint_bytes[name], note_times, gains)
        if name in ("no_update", "real_full"):
            assert probe == a5["branches"][name]["probe"], name
        records[name] = {"checkpoint_sha256": hashlib.sha256(
            checkpoint_bytes[name]).hexdigest(),
            "weights_after_mv": weights(sessions[name]),
            "probe": probe, "readout_trace": trace,
            "first_note": first_note(probe, trace),
            "timing": timing_summary(probe)}
        print(json.dumps({"branch": name,
                          "first_note": records[name]["first_note"],
                          "good": probe["metrics"]["good_or_better_count"],
                          "utility": probe["metrics"]["mean_utility"]}), flush=True)
    no_t = records["no_update"]["first_note"]["first_on_threshold_rise_us"]
    full_t = records["real_full"]["first_note"]["first_on_threshold_rise_us"]
    omit_t = records["real_except_300ms_targets_94_96"]["first_note"]["first_on_threshold_rise_us"]
    assert no_t == 372_456_000 and full_t == 372_383_000
    if omit_t > full_t:
        classification = "causal_upstream_timing_contributor"
    elif omit_t == full_t:
        classification = "no_detected_first_threshold_timing_contribution"
    else:
        classification = "nonlinear_or_opposing_effect"
    result = {
        "study_id": protocol["study_id"], "status": "complete",
        "protocol_sha256": sha(PROTOCOL),
        "a5_result_sha256": sha(A5 / "result.json"),
        "a5_pre_checkpoint_sha256": hashlib.sha256(pre_bytes).hexdigest(),
        "pre_update_geometry": geo,
        "selected_300ms_target_cohort": {
            "relay_source_ids": [48, 49, 50, 51],
            "motor_target_ids": [94, 95, 96],
            "edge_slots": list(SELECTED_SLOTS),
            "raw_proposal_l1_mv": sum(abs(geo["raw_proposed_update_mv"][i])
                                      for i in selected),
            "removed_applied_l1_mv": removed_l1,
            "retained_applied_l1_mv": sum(abs(a-b) for a,b in zip(after,before)),
        },
        "checkpoint_sha256": {name: hashlib.sha256(value).hexdigest()
                              for name, value in checkpoint_bytes.items()},
        "branches": records,
        "primary_comparison": {
            "no_update_first_rise_us": no_t,
            "real_full_first_rise_us": full_t,
            "omission_first_rise_us": omit_t,
            "movement_from_full_toward_no_us": omit_t - full_t,
            "fraction_of_73000us_separation": (omit_t - full_t) / (no_t - full_t),
            "classification": classification,
        },
        "completed_utc": datetime.now(timezone.utc).isoformat(),
    }
    atomic_json(OUTPUT / "result.json", result)
    atomic_json(OUTPUT / "meta.json", {
        "study_id": protocol["study_id"],
        "protocol_sha256": sha(PROTOCOL),
        "a5_result_sha256": sha(A5 / "result.json"),
        "a5_audit_sha256": sha(A5 / "audit.json"),
        "a5_pre_checkpoint_sha256": result["a5_pre_checkpoint_sha256"],
        "checkpoint_sha256": result["checkpoint_sha256"],
        "synthetic_topology": "build_tiny_brain; no imported connectome",
    })
    atomic_json(OUTPUT / "status.json", {
        "status": "complete", "protocol_sha256": sha(PROTOCOL),
        "result_sha256": sha(OUTPUT / "result.json")})
    print(json.dumps(result["primary_comparison"], indent=2))


if __name__ == "__main__":
    main()
