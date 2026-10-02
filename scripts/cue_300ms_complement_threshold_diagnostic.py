"""One locked complement-cohort omission at synthetic seed 2002 outcome 373."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from project_b.experiments import TinyLaneSession
from scripts.cue_300ms_necessity_diagnostic import probe_with_readout_trace
from scripts.cue_300ms_threshold_cohort_diagnostic import (
    assert_same_state_except_weights, digest, first_note, weights,
)
from scripts.long_continuation import atomic_json, sha
from scripts.successive_update_interference_diagnostic import timing_summary


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/cue_300ms_complement_threshold_diagnostic.json"
A5 = ROOT / "docs/figures/cue_300ms_necessity"
A7 = ROOT / "docs/figures/cue_300ms_threshold_cohort"
OUTPUT = ROOT / "docs/figures/cue_300ms_complement_threshold"
BRANCHES = ("no_update", "real_full", "real_except_300ms_targets_97_105")


def main() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert protocol["branches"] == list(BRANCHES)
    a5 = json.loads((A5 / "result.json").read_text(encoding="utf-8"))
    a7 = json.loads((A7 / "result.json").read_text(encoding="utf-8"))
    assert sha(A5 / "result.json") == json.loads((A5 / "status.json").read_text())["result_sha256"]
    assert sha(A7 / "result.json") == json.loads((A7 / "status.json").read_text())["result_sha256"]
    assert json.loads((A5 / "audit.json").read_text())["status"] == "passed"
    assert json.loads((A7 / "audit.json").read_text())["status"] == "passed"
    pre_bytes = (A5 / "pre_update_checkpoint.pkl").read_bytes()
    assert hashlib.sha256(pre_bytes).hexdigest() == a5["checkpoint_files_sha256"]["pre_update"]
    pre = TinyLaneSession.from_trusted_checkpoint_bytes(pre_bytes)
    geo = a5["pre_update_geometry"]
    state = a5["pre_update_state"]
    assert geo == a7["pre_update_geometry"]
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
    edge_meta = a5["source_pathway_structure"]["edge_metadata"]
    selected = [i for i, edge in enumerate(edge_meta)
                if edge["preferred_time_to_contact_us"] == 300_000
                and edge["post_motor_id"] in protocol["selected_motor_target_ids"]]
    selected_slots = [geo["edge_slots"][i] for i in selected]
    assert selected_slots == protocol["selected_edge_slots"] and len(selected) == 36
    assert {edge_meta[i]["pre_relay_id"] for i in selected} == set(
        protocol["selected_relay_source_ids"])
    assert {edge_meta[i]["post_motor_id"] for i in selected} == set(
        protocol["selected_motor_target_ids"])
    assert set(selected_slots).isdisjoint(a7["selected_300ms_target_cohort"]["edge_slots"])
    assert len(selected_slots) + len(a7["selected_300ms_target_cohort"]["edge_slots"]) == 48

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
    before, full_w, cut_w = geo["weights_before_mv"], weights(full), weights(omission)
    assert all(cut_w[i] == (before[i] if i in selected else full_w[i])
               for i in range(480))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    atomic_json(OUTPUT / "status.json", {"status": "running", "protocol_sha256": sha(PROTOCOL)})
    sessions = dict(zip(BRANCHES, (zero, full, omission)))
    checkpoints = {name: session.checkpoint_bytes() for name, session in sessions.items()}
    for name, value in checkpoints.items():
        (OUTPUT / f"{name}_checkpoint.pkl").write_bytes(value)
    source_probe = a5["branches"]["no_update"]["probe"]
    offsets = tuple(source_probe["relative_note_offsets_us"])
    gains = tuple(source_probe["cue_gains"])
    note_times = tuple(geo["time_us"] + x for x in offsets)
    records = {}
    for name in BRANCHES:
        probe, trace = probe_with_readout_trace(checkpoints[name], note_times, gains)
        if name in ("no_update", "real_full"):
            assert probe == a5["branches"][name]["probe"]
        records[name] = {
            "checkpoint_sha256": hashlib.sha256(checkpoints[name]).hexdigest(),
            "weights_after_mv": weights(sessions[name]),
            "probe": probe,
            "readout_trace": trace,
            "first_note": first_note(probe, trace),
            "timing": timing_summary(probe),
        }
        print(json.dumps({"branch": name, "first_note": records[name]["first_note"],
                          "good": probe["metrics"]["good_or_better_count"],
                          "utility": probe["metrics"]["mean_utility"]}), flush=True)
    no_t = records["no_update"]["first_note"]["first_on_threshold_rise_us"]
    full_t = records["real_full"]["first_note"]["first_on_threshold_rise_us"]
    cut_t = records[BRANCHES[2]]["first_note"]["first_on_threshold_rise_us"]
    assert no_t == 372_456_000 and full_t == 372_383_000
    classification = ("toward_no_update" if cut_t > full_t
                      else "unchanged" if cut_t == full_t else "earlier_or_nonlinear")
    result = {
        "study_id": protocol["study_id"], "status": "complete",
        "protocol_sha256": sha(PROTOCOL),
        "a5_result_sha256": sha(A5 / "result.json"),
        "a7_result_sha256": sha(A7 / "result.json"),
        "a5_pre_checkpoint_sha256": hashlib.sha256(pre_bytes).hexdigest(),
        "pre_update_geometry": geo,
        "selected_300ms_complement": {
            "relay_source_ids": protocol["selected_relay_source_ids"],
            "motor_target_ids": protocol["selected_motor_target_ids"],
            "edge_slots": selected_slots,
            "raw_proposal_l1_mv": sum(abs(geo["raw_proposed_update_mv"][i]) for i in selected),
            "removed_applied_l1_mv": sum(abs(full_w[i] - before[i]) for i in selected),
            "retained_applied_l1_mv": sum(abs(a-b) for a, b in zip(cut_w, before)),
        },
        "checkpoint_sha256": {name: hashlib.sha256(value).hexdigest()
                              for name, value in checkpoints.items()},
        "branches": records,
        "primary_comparison": {
            "no_update_first_rise_us": no_t,
            "real_full_first_rise_us": full_t,
            "omission_first_rise_us": cut_t,
            "movement_from_full_toward_no_us": cut_t - full_t,
            "fraction_of_73000us_separation": (cut_t-full_t)/(no_t-full_t),
            "classification": classification,
        },
        "completed_utc": datetime.now(timezone.utc).isoformat(),
    }
    atomic_json(OUTPUT / "result.json", result)
    atomic_json(OUTPUT / "meta.json", {
        "study_id": protocol["study_id"],
        "protocol_sha256": sha(PROTOCOL),
        "a5_result_sha256": sha(A5 / "result.json"),
        "a7_result_sha256": sha(A7 / "result.json"),
        "a5_pre_checkpoint_sha256": result["a5_pre_checkpoint_sha256"],
        "checkpoint_sha256": result["checkpoint_sha256"],
        "synthetic_topology": "build_tiny_brain; no imported connectome",
    })
    atomic_json(OUTPUT / "status.json", {
        "status": "complete", "protocol_sha256": sha(PROTOCOL),
        "result_sha256": sha(OUTPUT / "result.json"),
    })
    print(json.dumps(result["primary_comparison"], indent=2), flush=True)


if __name__ == "__main__":
    main()
