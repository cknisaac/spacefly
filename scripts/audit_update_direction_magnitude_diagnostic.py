"""Independent arithmetic and provenance audit of the saved A2 raw ledger."""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/figures/update_direction_magnitude_diagnostic"
LONG = ROOT / "docs/figures/long_continuation"
PROTOCOL = ROOT / "configs/update_direction_magnitude_diagnostic.json"
BRANCHES = ("no_update", "small_positive", "full_actual", "small_negative")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def close(actual: float, expected: float) -> bool:
    return math.isclose(actual, expected, rel_tol=0, abs_tol=1e-9)


def main() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    meta = json.loads((OUT / "meta.json").read_text(encoding="utf-8"))
    status = json.loads((OUT / "status.json").read_text(encoding="utf-8"))
    source_meta = json.loads((LONG / "meta.json").read_text(encoding="utf-8"))
    source_rows = {r["seed"]: r for r in (json.loads(line) for line in
                   (LONG / "runs.jsonl").read_text(encoding="utf-8").splitlines())
                   if r["condition"] == "on"}
    raw = [json.loads(line) for line in (OUT / "runs.jsonl").read_text(encoding="utf-8").splitlines()]
    rows = {r["key"]: r for r in raw}
    assert len(raw) == len(rows) == 4
    assert status["status"] == "complete"
    assert meta["protocol_sha256"] == sha(PROTOCOL)
    assert meta["source_long_ledger_sha256"] == sha(LONG / "runs.jsonl")
    assert meta["source_long_meta_sha256"] == sha(LONG / "meta.json")
    assert status["ledger_sha256"] == sha(OUT / "runs.jsonl")
    assert status["completed_keys"] == meta["planned_keys"]
    assert set(rows) == set(meta["planned_keys"])
    for relative, digest in meta["replay_model_source_sha256"].items():
        assert sha(ROOT / relative) == digest
    assert meta["saved_model_source_sha256"] == source_meta["model_source_sha256"]
    drift = {name: {"saved": meta["saved_model_source_sha256"][name], "replay": digest}
             for name, digest in meta["replay_model_source_sha256"].items()
             if digest != meta["saved_model_source_sha256"][name]}
    assert drift == meta["source_hash_drift_requiring_exact_replay"]
    assert set(drift) == {"src\\project_b\\simulation\\__init__.py",
                          "src\\project_b\\simulation\\spiking.py"}

    total_actions = total_events = total_clipped_full = 0
    case_receipts = {}
    for seed in protocol["seeds"]:
        source = source_rows[seed]
        eligible = [u for u in source["update_diagnostics"]
                    if 193 <= u["note_index"] + 1 <= 288
                    and u["raw_l1_mv"] >= 20
                    and u["proposed_below_min_edges"] == 0
                    and u["proposed_above_max_edges"] == 0]
        assert eligible
        selected = [eligible[0]["note_index"] + 1, 384]
        assert selected == protocol["selected_outcomes"][str(seed)]
        for outcome in selected:
            key = f"{seed}:{outcome}"
            row = rows[key]
            geo = row["pre_update_geometry"]
            saved = source["update_diagnostics"][outcome - 1]
            assert row["source_training_event"] == source["training_events"][outcome - 1]
            assert row["source_update_diagnostic"] == saved
            assert row["checkpoint_time_us"] == saved["time_us"] == geo["time_us"]
            assert row["protocol_sha256"] == meta["protocol_sha256"]
            assert row["source_long_ledger_sha256"] == meta["source_long_ledger_sha256"]
            assert len(geo["edge_slots"]) == len(set(geo["edge_slots"])) == 480
            assert len(geo["weights_before_mv"]) == len(geo["eligibility"]) == 480
            assert len(geo["raw_proposed_update_mv"]) == 480
            assert close(geo["raw_l1_mv"], saved["raw_l1_mv"])
            assert close(geo["raw_l2_mv"], saved["raw_l2_mv"])
            assert len(geo["proposed_below_min_slots"]) == saved["proposed_below_min_edges"]
            assert len(geo["proposed_above_max_slots"]) == saved["proposed_above_max_edges"]
            assert close(geo["eligibility_mean"], statistics.mean(geo["eligibility"]))
            for e, raw_delta in zip(geo["eligibility"], geo["raw_proposed_update_mv"]):
                assert close(raw_delta, geo["eta"] * e * geo["dopamine"])
            assert set(row["branches"]) == set(BRANCHES)
            reference = row["branches"]["no_update"]["probe"]
            panel = (reference["relative_note_offsets_us"], reference["cue_gains"])
            assert panel == (source_meta["probe_relative_note_offsets_us"],
                             source_meta["probe_cue_gains"])
            for name, scale in (("no_update", 0.0),
                                ("small_positive", protocol["small_raw_fraction"]),
                                ("full_actual", 1.0),
                                ("small_negative", -protocol["small_raw_fraction"])):
                branch = row["branches"][name]
                update = branch["update"]
                probe = branch["probe"]
                assert update["scale_of_real_dopamine"] == scale
                assert (probe["relative_note_offsets_us"], probe["cue_gains"]) == panel
                assert probe["checkpoint_time_us"] == geo["time_us"]
                assert probe["exploration"] is False
                assert probe["exploration_pulses_us"] == []
                assert probe["uses_checkpoint_rng"] is True
                assert len(probe["events"]) == 32
                assert all(e["weight_changes"] == 0 for e in probe["events"])
                before = geo["weights_before_mv"]
                raw_delta = update["raw_proposed_update_mv"]
                applied = update["applied_update_mv"]
                after = update["weights_after_mv"]
                assert len(before) == len(raw_delta) == len(applied) == len(after) == 480
                bounds = geo["weight_bounds_mv"]
                clipped = []
                for slot, w, original_raw, raw, real, new in zip(
                        geo["edge_slots"], before, geo["raw_proposed_update_mv"],
                        raw_delta, applied, after):
                    assert close(raw, scale * original_raw)
                    assert close(real, new - w)
                    assert close(new, min(bounds[1], max(bounds[0], w + raw)))
                    if not math.isclose(raw, real, rel_tol=0, abs_tol=1e-12):
                        clipped.append(slot)
                assert clipped == update["clipped_slots"]
                assert len(clipped) == update["clipped_edge_count"]
                assert close(sum(abs(x) for x in raw_delta), update["raw_l1_mv"])
                assert close(sum(abs(x) for x in applied), update["applied_l1_mv"])
                assert close(math.sqrt(sum(x*x for x in raw_delta)), update["raw_l2_mv"])
                assert close(math.sqrt(sum(x*x for x in applied)), update["applied_l2_mv"])
                assert sum(w == bounds[0] for w in after) == update["lower_bound_edges_after"]
                assert sum(w == bounds[1] for w in after) == update["upper_bound_edges_after"]
                if name == "full_actual":
                    assert close(update["applied_l1_mv"], saved["applied_l1_mv"])
                    assert update["changed_edges"] == saved["changed_edges"]
                    total_clipped_full += len(clipped)
                metrics = probe["metrics"]
                events = probe["events"]
                downs = probe["down_actions"]
                assert close(metrics["mean_utility"], statistics.mean(e["game_utility"] for e in events))
                assert close(metrics["mean_expected_utility_before"],
                             statistics.mean(e["expected_utility_before"] for e in events))
                assert close(metrics["mean_signed_rpe"], statistics.mean(e["rpe"] for e in events))
                assert metrics["good_or_better_count"] == sum(e["hit_value"] >= 200 for e in events)
                assert metrics["judgement_counts"] == dict(Counter(e["judgement"] for e in events))
                assert metrics["down_count"] == len(downs)
                assert metrics["null_down_count"] == sum(a["disposition"] == "null_press" for a in downs)
                assert all(e["note_time_us"] == geo["time_us"] + panel[0][i]
                           for i, e in enumerate(events))
                assert all(e["rpe"] == e["learning_utility"] - e["expected_utility_before"]
                           for e in events)
                hits = [e for e in events if e["judgement"] != "MISS"]
                if hits:
                    assert close(metrics["hit_mean_absolute_error_ms"],
                                 statistics.mean(abs(e["hit_error_us"]) for e in hits) / 1000)
                    assert close(metrics["hit_mean_signed_error_ms"],
                                 statistics.mean(e["hit_error_us"] for e in hits) / 1000)
                else:
                    assert metrics["hit_mean_absolute_error_ms"] is None
                total_events += len(events)
                total_actions += len(downs)
            if outcome == 384:
                full = row["branches"]["full_actual"]["probe"]
                old = source["checkpoints"][2]["probe"]
                for field in ("relative_note_offsets_us", "cue_gains", "events", "down_actions", "metrics"):
                    assert full[field] == old[field]
            no_util = reference["metrics"]["mean_utility"]
            case_receipts[key] = {"branch_mean_utility": {
                name: row["branches"][name]["probe"]["metrics"]["mean_utility"]
                for name in BRANCHES},
                "full_clipped_edges": row["branches"]["full_actual"]["update"]["clipped_edge_count"],
                "full_applied_over_raw_l1": (
                    row["branches"]["full_actual"]["update"]["applied_l1_mv"] / geo["raw_l1_mv"]),
                "delta_utility_vs_no": {
                    name: row["branches"][name]["probe"]["metrics"]["mean_utility"] - no_util
                    for name in BRANCHES[1:]}}
    receipt = {"status": "passed", "cases": len(rows), "branches": len(rows)*len(BRANCHES),
               "probe_events": total_events, "down_actions": total_actions,
               "full_update_clipped_edge_events": total_clipped_full,
               "protocol_sha256": sha(PROTOCOL),
               "ledger_sha256": sha(OUT / "runs.jsonl"),
               "case_receipts": case_receipts}
    (OUT / "audit.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
