"""Independent source, edge, age and branch audit of the outcome-373 study."""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from collections import Counter
from pathlib import Path

from project_b.experiments.tiny_brain import TinyBrainConfig, build_tiny_brain
from project_b.sensory import TimeToContactEncoder


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/figures/eligibility_timing_credit"
PROTOCOL = ROOT / "configs/eligibility_timing_credit_diagnostic.json"
A3 = ROOT / "docs/figures/successive_update_interference"
LONG = ROOT / "docs/figures/long_continuation"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def close(a: float, b: float, tol: float = 1e-9) -> bool:
    return math.isclose(a, b, rel_tol=0, abs_tol=tol)


def check_probe(probe: dict, timing: dict, offsets: list[int],
                gains: list[float]) -> tuple[int, int]:
    assert probe["exploration"] is False
    assert probe["exploration_pulses_us"] == []
    assert probe["uses_checkpoint_rng"] is True
    assert probe["relative_note_offsets_us"] == offsets
    assert probe["cue_gains"] == gains
    events = probe["events"]
    downs = probe["down_actions"]
    metrics = probe["metrics"]
    assert len(events) == 32
    assert all(e["weight_changes"] == 0 for e in events)
    assert all(e["note_time_us"] == probe["checkpoint_time_us"] + offsets[i]
               for i, e in enumerate(events))
    assert close(metrics["mean_utility"], statistics.mean(e["game_utility"] for e in events))
    assert metrics["good_or_better_count"] == sum(e["hit_value"] >= 200 for e in events)
    assert metrics["judgement_counts"] == dict(Counter(e["judgement"] for e in events))
    assert metrics["down_count"] == len(downs)
    assert metrics["null_down_count"] == sum(a["disposition"] == "null_press" for a in downs)
    assert timing["attempt_count_with_error"] == sum(e["hit_error_us"] is not None for e in events)
    errors = [e["hit_error_us"] for e in events if e["hit_error_us"] is not None]
    if errors:
        assert close(timing["mean_signed_attempt_error_ms"], statistics.mean(errors) / 1000)
    else:
        assert timing["mean_signed_attempt_error_ms"] is None
    hits = [e for e in events if e["judgement"] != "MISS"]
    if hits:
        assert close(metrics["hit_mean_absolute_error_ms"],
                     statistics.mean(abs(e["hit_error_us"]) for e in hits) / 1000)
    else:
        assert metrics["hit_mean_absolute_error_ms"] is None
    assert isinstance(probe["motor_spikes"], int) and probe["motor_spikes"] >= 0
    return len(events), len(downs)


def main() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    result = json.loads((OUT / "result.json").read_text(encoding="utf-8"))
    meta = json.loads((OUT / "meta.json").read_text(encoding="utf-8"))
    status = json.loads((OUT / "status.json").read_text(encoding="utf-8"))
    long_meta = json.loads((LONG / "meta.json").read_text(encoding="utf-8"))
    a3_row = next(json.loads(line) for line in (A3 / "runs.jsonl").read_text(
        encoding="utf-8").splitlines() if json.loads(line)["seed"] == 2002)
    a3_point = a3_row["checkpoints"][373 - a3_row["start_after_outcomes"]]
    a3_counter = json.loads((A3 / "counterfactual.json").read_text(encoding="utf-8"))
    assert status["status"] == result["status"] == "complete"
    assert status["result_sha256"] == sha(OUT / "result.json")
    assert meta["protocol_sha256"] == result["protocol_sha256"] == sha(PROTOCOL)
    assert meta["source_long_ledger_sha256"] == result["source_long_ledger_sha256"] == sha(LONG / "runs.jsonl")
    assert meta["a3_trajectory_ledger_sha256"] == result["a3_trajectory_ledger_sha256"] == sha(A3 / "runs.jsonl")
    assert meta["a3_counterfactual_sha256"] == result["a3_counterfactual_sha256"] == sha(A3 / "counterfactual.json")
    assert meta["saved_model_source_sha256"] == long_meta["model_source_sha256"]
    for relative, digest in meta["replay_model_source_sha256"].items():
        assert sha(ROOT / relative) == digest
    drift = {name: {"saved": meta["saved_model_source_sha256"][name], "replay": digest}
             for name, digest in meta["replay_model_source_sha256"].items()
             if digest != meta["saved_model_source_sha256"][name]}
    assert drift == meta["source_hash_drift_requiring_exact_replay"]
    assert set(drift) == {"src\\project_b\\simulation\\__init__.py",
                          "src\\project_b\\simulation\\spiking.py"}
    assert result["seed"] == 2002 and result["one_based_outcome"] == 373
    geo = result["pre_update_geometry"]
    prior = a3_point["update"]
    for field in ("edge_slots", "time_us", "dopamine", "eta", "weight_bounds_mv",
                  "weights_before_mv", "eligibility", "raw_proposed_update_mv",
                  "real_weights_after_mv", "applied_l1_mv"):
        actual_field = "weights_after_mv" if field == "real_weights_after_mv" else field
        if field == "applied_l1_mv":
            assert close(sum(abs(x) for x in geo["real_applied_update_mv"]), prior[field])
        else:
            assert geo[field] == prior[actual_field], field
    assert result["pre_update_state"]["source_event"] == a3_point["training_event"]
    assert result["pre_update_state"]["queued_arrivals"] >= 0
    assert len(result["pre_update_state"]["rng_state_sha256"]) == 64
    age = result["age_decomposition"]
    assert age["tau_eligibility_us"] == 150_000
    assert age["cutoffs_us"]["dopamine_time"] == geo["time_us"]
    assert age["cutoffs_us"]["t_minus_150ms"] == geo["time_us"] - 150_000
    assert age["cutoffs_us"]["t_minus_450ms"] == geo["time_us"] - 450_000
    e150 = age["eligibility_at_t_minus_150ms"]
    e450 = age["eligibility_at_t_minus_450ms"]
    recent = age["recent_0_to_150ms"]
    older = age["older_than_150ms"]
    age150_450 = age["age_150_to_450ms"]
    old450 = age["older_than_450ms"]
    assert all(len(x) == 480 for x in (e150, e450, recent, older, age150_450, old450))
    for a, b, c, d, e, f in zip(recent, older, age150_450, old450,
                                 e150, e450):
        assert close(b, e * math.exp(-1))
        assert close(d, f * math.exp(-3))
        assert close(c + d, b)
        assert a >= -1e-10 and b >= -1e-10 and c >= -1e-10 and d >= -1e-10
    assert all(close(a+b, full, 1e-11) for a, b, full in zip(recent, older, geo["eligibility"]))
    structure = result["source_pathway_structure"]
    edge_meta = structure["edge_metadata"]
    groups = structure["group_slots"]
    assert len(edge_meta) == 480
    assert len({e["slot"] for e in edge_meta}) == 480
    layout = build_tiny_brain(TinyBrainConfig(neuron_count=128), TimeToContactEncoder())
    assert list(layout.plastic_slots) == geo["edge_slots"]
    assert structure["motor_target_ids"] == list(layout.motor)
    assert structure["relay_source_ids"] == list(layout.relay)
    assert [len(groups[n]) for n in ("source_far_500_to_200ms",
                                    "source_mid_150_to_75ms",
                                    "source_near_50_to_0ms")] == [192, 144, 144]
    assert [len(groups[n]) for n in ("full_proposal_clipped_edges",
                                    "full_proposal_unclipped_edges")] == [354, 126]
    for i, item in enumerate(edge_meta):
        slot = geo["edge_slots"][i]
        assert item["slot"] == slot
        assert item["pre_relay_id"] == layout.graph.pre_indices[slot]
        assert item["post_motor_id"] == layout.graph.post_indices[slot]
        assert item["source_group"] in groups
        assert slot in groups[item["source_group"]]
        assert item["cue_bin_index"] == item["sensory_parent_id"] // 4
        assert item["preferred_time_to_contact_us"] == structure["cue_preferred_us"][item["cue_bin_index"]]
        w = geo["weights_before_mv"][i]
        raw = geo["raw_proposed_update_mv"][i]
        lo, hi = geo["weight_bounds_mv"]
        clipped = not lo <= w + raw <= hi
        assert item["real_full_proposal_clips"] == clipped
        assert slot in groups["full_proposal_clipped_edges" if clipped else "full_proposal_unclipped_edges"]
    assert set(result["branches"]) == set(protocol["branches"])
    offsets = long_meta["probe_relative_note_offsets_us"]
    gains = long_meta["probe_cue_gains"]
    events = actions = 0
    no_probe = result["branches"]["no_update"]["probe"]
    for name in protocol["branches"]:
        item = result["branches"][name]
        update = item["update"]
        raw = update["raw_proposed_update_mv"]
        applied = update["applied_update_mv"]
        before = geo["weights_before_mv"]
        after = update["weights_after_mv"]
        assert len(raw) == len(applied) == len(before) == len(after) == 480
        selected = set(groups[name]) if name in groups else None
        for i, (slot, w, r, a, new) in enumerate(zip(
                geo["edge_slots"], before, raw, applied, after)):
            expected_raw = (0.0 if name == "no_update" else
                            geo["raw_proposed_update_mv"][i] if name == "real_full" else
                            -geo["raw_proposed_update_mv"][i] if name == "rpe_sign_reversed" else
                            geo["raw_proposed_update_mv"][i] if selected is not None and slot in selected else
                            0.0 if selected is not None else
                            geo["eta"] * geo["dopamine"] * recent[i] if name == "eligibility_recent_0_to_150ms" else
                            geo["eta"] * geo["dopamine"] * older[i])
            assert close(r, expected_raw)
            assert close(new, min(geo["weight_bounds_mv"][1],
                                  max(geo["weight_bounds_mv"][0], w+r)))
            assert close(a, new-w)
        assert close(update["raw_l1_mv"], sum(abs(x) for x in raw))
        assert close(update["applied_l1_mv"], sum(abs(x) for x in applied))
        assert close(update["raw_l2_mv"], math.sqrt(sum(x*x for x in raw)))
        assert close(update["applied_l2_mv"], math.sqrt(sum(x*x for x in applied)))
        assert update["changed_edge_count"] == sum(a != b for a, b in zip(after, before))
        assert update["clipped_edge_count"] == len(update["clipped_slots"])
        n, a = check_probe(item["probe"], item["timing"], offsets, gains)
        events += n
        actions += a
        pairs = [(x["hit_error_us"], y["hit_error_us"])
                 for x, y in zip(item["probe"]["events"], no_probe["events"])
                 if x["hit_error_us"] is not None and y["hit_error_us"] is not None]
        assert item["paired_timing_vs_no"]["paired_note_count"] == len(pairs)
        if pairs:
            assert close(item["paired_timing_vs_no"]["mean_paired_signed_error_delta_ms"],
                         statistics.mean((x-y)/1000 for x, y in pairs))
    assert no_probe == a3_counter["branches"]["skip_target_update"]["immediate_probe"]
    assert result["branches"]["real_full"]["probe"] == a3_counter["branches"]["real_update"]["immediate_probe"]
    for i, actual in enumerate(geo["real_applied_update_mv"]):
        parts = (result["branches"]["full_proposal_clipped_edges"]["update"]["applied_update_mv"][i]
                 + result["branches"]["full_proposal_unclipped_edges"]["update"]["applied_update_mv"][i])
        assert close(actual, parts, 1e-12)
    receipt = {"status": "passed", "branches": len(protocol["branches"]),
               "frozen_note_outcomes": events, "down_actions": actions,
               "selected_edges": 480,
               "source_group_counts": {n: len(groups[n]) for n in groups},
               "protocol_sha256": sha(PROTOCOL),
               "result_sha256": sha(OUT / "result.json")}
    (OUT / "audit.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
