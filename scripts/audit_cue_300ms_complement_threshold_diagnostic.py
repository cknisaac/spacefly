"""Independent checkpoint, edge-selection, frozen-probe and readout audit."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from project_b.experiments import TinyLaneSession
from scripts.audit_cue_300ms_threshold_cohort_diagnostic import (
    assert_same_nonweight_state, check_probe, digest, sha, weights,
)


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/cue_300ms_complement_threshold_diagnostic.json"
A5 = ROOT / "docs/figures/cue_300ms_necessity"
A7 = ROOT / "docs/figures/cue_300ms_threshold_cohort"
OUT = ROOT / "docs/figures/cue_300ms_complement_threshold"
BRANCHES = ("no_update", "real_full", "real_except_300ms_targets_97_105")


def main() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    result = json.loads((OUT / "result.json").read_text(encoding="utf-8"))
    meta = json.loads((OUT / "meta.json").read_text(encoding="utf-8"))
    status = json.loads((OUT / "status.json").read_text(encoding="utf-8"))
    a5 = json.loads((A5 / "result.json").read_text(encoding="utf-8"))
    a7 = json.loads((A7 / "result.json").read_text(encoding="utf-8"))
    assert protocol["branches"] == list(BRANCHES)
    assert result["status"] == status["status"] == "complete"
    assert result["protocol_sha256"] == meta["protocol_sha256"] == status["protocol_sha256"] == sha(PROTOCOL)
    assert result["a5_result_sha256"] == meta["a5_result_sha256"] == sha(A5 / "result.json")
    assert result["a7_result_sha256"] == meta["a7_result_sha256"] == sha(A7 / "result.json")
    assert status["result_sha256"] == sha(OUT / "result.json")
    pre_bytes = (A5 / "pre_update_checkpoint.pkl").read_bytes()
    assert result["a5_pre_checkpoint_sha256"] == meta["a5_pre_checkpoint_sha256"] == sha(A5 / "pre_update_checkpoint.pkl")
    assert result["a5_pre_checkpoint_sha256"] == a5["checkpoint_files_sha256"]["pre_update"]
    geo = a5["pre_update_geometry"]
    assert result["pre_update_geometry"] == geo == a7["pre_update_geometry"]
    pre = TinyLaneSession.from_trusted_checkpoint_bytes(pre_bytes)
    assert weights(pre) == geo["weights_before_mv"]
    assert pre.simulator.current_time_us == geo["time_us"] == 371_725_000
    state = a5["pre_update_state"]
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
                            geo["eta"] * e * geo["dopamine"], abs_tol=1e-12)
    edge_meta = a5["source_pathway_structure"]["edge_metadata"]
    selected = [i for i, edge in enumerate(edge_meta)
                if edge["preferred_time_to_contact_us"] == 300_000
                and edge["post_motor_id"] in protocol["selected_motor_target_ids"]]
    slots = [geo["edge_slots"][i] for i in selected]
    assert slots == protocol["selected_edge_slots"] == result["selected_300ms_complement"]["edge_slots"]
    assert len(selected) == 36
    assert {edge_meta[i]["pre_relay_id"] for i in selected} == set(protocol["selected_relay_source_ids"])
    assert {edge_meta[i]["post_motor_id"] for i in selected} == set(protocol["selected_motor_target_ids"])
    assert set(slots).isdisjoint(a7["selected_300ms_target_cohort"]["edge_slots"])
    assert len(slots) + len(a7["selected_300ms_target_cohort"]["edge_slots"]) == 48
    zero = TinyLaneSession.from_trusted_checkpoint_bytes(pre_bytes)
    zero.simulator.apply_dopamine(0.0)
    full = TinyLaneSession.from_trusted_checkpoint_bytes(pre_bytes)
    full.simulator.apply_dopamine(geo["dopamine"])
    assert weights(zero) == a5["branches"]["no_update"]["update"]["weights_after_mv"]
    assert weights(full) == geo["real_weights_after_mv"]
    checkpoints = {name: (OUT / f"{name}_checkpoint.pkl").read_bytes()
                   for name in BRANCHES}
    for name, checkpoint in checkpoints.items():
        assert hashlib.sha256(checkpoint).hexdigest() == result["checkpoint_sha256"][name]
        assert meta["checkpoint_sha256"][name] == result["checkpoint_sha256"][name]
        saved = TinyLaneSession.from_trusted_checkpoint_bytes(checkpoint)
        assert saved.plasticity is saved.simulator.plasticity
        assert weights(saved) == result["branches"][name]["weights_after_mv"]
        assert_same_nonweight_state(saved, zero if name == "no_update" else full)
    cut = TinyLaneSession.from_trusted_checkpoint_bytes(checkpoints[BRANCHES[2]])
    cut_w, full_w, before = weights(cut), weights(full), geo["weights_before_mv"]
    assert all(cut_w[i] == (before[i] if i in selected else full_w[i]) for i in range(480))
    assert math.isclose(result["selected_300ms_complement"]["removed_applied_l1_mv"],
                        sum(abs(full_w[i] - before[i]) for i in selected))
    assert math.isclose(result["selected_300ms_complement"]["raw_proposal_l1_mv"],
                        sum(abs(geo["raw_proposed_update_mv"][i]) for i in selected))
    assert math.isclose(result["selected_300ms_complement"]["retained_applied_l1_mv"],
                        sum(abs(a-b) for a, b in zip(cut_w, before)))
    source_probe = a5["branches"]["no_update"]["probe"]
    times = tuple(geo["time_us"] + x for x in source_probe["relative_note_offsets_us"])
    gains = tuple(source_probe["cue_gains"])
    events = actions = rises = 0
    for name in BRANCHES:
        item = result["branches"][name]
        if name in ("no_update", "real_full"):
            assert item["probe"] == a5["branches"][name]["probe"]
        e, a, r = check_probe(item, checkpoints[name], times, gains)
        events += e
        actions += a
        rises += r
    first = {name: result["branches"][name]["first_note"]["first_on_threshold_rise_us"]
             for name in BRANCHES}
    primary = result["primary_comparison"]
    assert primary["no_update_first_rise_us"] == first["no_update"] == 372_456_000
    assert primary["real_full_first_rise_us"] == first["real_full"] == 372_383_000
    assert primary["omission_first_rise_us"] == first[BRANCHES[2]]
    assert primary["movement_from_full_toward_no_us"] == first[BRANCHES[2]] - first["real_full"]
    assert primary["fraction_of_73000us_separation"] == ((first[BRANCHES[2]] - first["real_full"])
                                                      / (first["no_update"] - first["real_full"]))
    expected_class = ("toward_no_update" if first[BRANCHES[2]] > first["real_full"]
                      else "unchanged" if first[BRANCHES[2]] == first["real_full"]
                      else "earlier_or_nonlinear")
    assert primary["classification"] == expected_class
    receipt = {"status": "passed", "branches": 3, "frozen_note_outcomes": events,
               "down_actions": actions, "readout_on_threshold_rises": rises,
               "selected_300ms_edges": len(selected),
               "protocol_sha256": sha(PROTOCOL),
               "result_sha256": sha(OUT / "result.json")}
    (OUT / "audit.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
