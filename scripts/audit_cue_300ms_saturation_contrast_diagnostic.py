"""Independent saved-state and readout audit for the two locked contrasts."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from project_b.experiments import TinyLaneSession
from scripts.audit_cue_300ms_threshold_cohort_diagnostic import (
    assert_same_nonweight_state, check_probe, sha, weights,
)
from scripts.exploration_map_diagnostic import load_long_rows


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/cue_300ms_saturation_contrast_diagnostic.json"
OUT = ROOT / "docs/figures/cue_300ms_saturation_contrast"
A3_LEDGER = ROOT / "docs/figures/successive_update_interference/runs.jsonl"
A5 = ROOT / "docs/figures/cue_300ms_necessity"
BRANCHES = ("no_update", "real_full", "real_except_300ms_targets_97_105")


def main() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    result = json.loads((OUT / "result.json").read_text(encoding="utf-8"))
    status = json.loads((OUT / "status.json").read_text(encoding="utf-8"))
    assert result["status"] == status["status"] == "complete"
    assert result["protocol_sha256"] == status["protocol_sha256"] == sha(PROTOCOL)
    assert status["result_sha256"] == sha(OUT / "result.json")
    assert result["source_a3_ledger_sha256"] == sha(A3_LEDGER)
    assert result["checkpoint_selection"] == protocol["checkpoint_selection"]
    a3 = next(json.loads(line) for line in A3_LEDGER.read_text(encoding="utf-8").splitlines()
              if json.loads(line)["seed"] == 2002)
    a5 = json.loads((A5 / "result.json").read_text(encoding="utf-8"))
    assert result["a5_result_sha256"] == sha(A5 / "result.json")
    edge_meta = a5["source_pathway_structure"]["edge_metadata"]
    selected = [i for i, e in enumerate(edge_meta)
                if e["preferred_time_to_contact_us"] == 300_000
                and 97 <= e["post_motor_id"] <= 105]
    assert len(selected) == 36
    assert {edge_meta[i]["pre_relay_id"] for i in selected} == {48, 49, 50, 51}
    source = load_long_rows()[2002]
    events = actions = rises = 0
    historical_pickle_mismatches = []
    for outcome in (372, 377):
        case = result["cases"][str(outcome)]
        prior = next(c for c in a3["checkpoints"] if c["after_outcomes"] == outcome)
        assert case["source_training_event"] == prior["training_event"] == source["training_events"][outcome-1]
        pre_bytes = (OUT / f"{outcome}_pre_update_checkpoint.pkl").read_bytes()
        assert sha(OUT / f"{outcome}_pre_update_checkpoint.pkl") == case["pre_update_checkpoint_sha256"]
        pre = TinyLaneSession.from_trusted_checkpoint_bytes(pre_bytes)
        geo = case["pre_update_geometry"]
        assert all(geo[k] == prior["update"][k] for k in geo)
        assert weights(pre) == geo["weights_before_mv"]
        assert pre.simulator.current_time_us == geo["time_us"]
        assert geo["dopamine"] == prior["training_event"]["rpe"]
        assert case["source_pre_update_canonical_sha256"] == prior["pre_update_canonical_sha256"]
        actual_pickle_match = hashlib.sha256(pre.checkpoint_bytes()).hexdigest() == prior["pre_update_canonical_sha256"]
        assert case["historical_pickle_match"] == actual_pickle_match
        if not actual_pickle_match:
            historical_pickle_mismatches.append(outcome)
        for i, slot in enumerate(geo["edge_slots"]):
            e = pre.plasticity.eligibility_at(slot, geo["time_us"])
            assert math.isclose(e, geo["eligibility"][i], abs_tol=1e-12)
            assert math.isclose(geo["raw_proposed_update_mv"][i],
                                geo["eta"] * e * geo["dopamine"], abs_tol=1e-12)
        slots = [geo["edge_slots"][i] for i in selected]
        assert slots == case["selected_edge_slots"] == result["selected_edge_slots"]
        zero = TinyLaneSession.from_trusted_checkpoint_bytes(pre_bytes)
        zero.simulator.apply_dopamine(0.0)
        full = TinyLaneSession.from_trusted_checkpoint_bytes(pre_bytes)
        full.simulator.apply_dopamine(geo["dopamine"])
        assert weights(zero) == geo["weights_before_mv"]
        assert weights(full) == prior["update"]["weights_after_mv"]
        checkpoints = {name: (OUT / f"{outcome}_{name}_checkpoint.pkl").read_bytes()
                       for name in BRANCHES}
        for name, checkpoint in checkpoints.items():
            assert hashlib.sha256(checkpoint).hexdigest() == case["branches"][name]["checkpoint_sha256"]
            saved = TinyLaneSession.from_trusted_checkpoint_bytes(checkpoint)
            assert saved.plasticity is saved.simulator.plasticity
            assert weights(saved) == case["branches"][name]["weights_after_mv"]
            assert_same_nonweight_state(saved, zero if name == "no_update" else full)
        cut = TinyLaneSession.from_trusted_checkpoint_bytes(checkpoints[BRANCHES[2]])
        cut_w, full_w, before = weights(cut), weights(full), geo["weights_before_mv"]
        assert all(cut_w[i] == (before[i] if i in selected else full_w[i])
                   for i in range(480))
        assert math.isclose(case["removed_applied_l1_mv"],
                            sum(abs(full_w[i]-before[i]) for i in selected))
        assert math.isclose(case["retained_applied_l1_mv"],
                            sum(abs(a-b) for a,b in zip(cut_w,before)))
        source_probe = prior["probe"]
        times = tuple(geo["time_us"] + x for x in source_probe["relative_note_offsets_us"])
        gains = tuple(source_probe["cue_gains"])
        for name in BRANCHES:
            item = case["branches"][name]
            if name == "real_full":
                assert item["probe"] == source_probe
            e, a, r = check_probe(item, checkpoints[name], times, gains)
            events += e
            actions += a
            rises += r
            assert case["first_crossing_us"][name] == item["first_note"]["first_on_threshold_rise_us"]
        f = case["first_crossing_us"]
        assert case["full_minus_no_us"] == f["real_full"] - f["no_update"]
        assert case["omit_minus_full_us"] == f[BRANCHES[2]] - f["real_full"]
    receipt = {"status": "passed", "cases": 2, "branches": 6,
               "frozen_note_outcomes": events, "down_actions": actions,
               "readout_on_threshold_rises": rises,
               "selected_300ms_edges_per_case": len(selected),
               "historical_pickle_mismatch_outcomes": historical_pickle_mismatches,
               "protocol_sha256": sha(PROTOCOL),
               "result_sha256": sha(OUT / "result.json")}
    (OUT / "audit.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
