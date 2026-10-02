"""Independent saved-ledger audit for the five-seed weight rollback diagnostic."""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/figures/weight_rollback_diagnostic"
LONG = ROOT / "docs/figures/long_continuation"
EXPLORE = ROOT / "docs/figures/exploration_map_diagnostic"
PROTOCOL = ROOT / "configs/weight_rollback_diagnostic.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path: Path, key: str) -> dict[str, dict]:
    result = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        assert row[key] not in result
        result[row[key]] = row
    return result


def same_probe(actual: dict, prior: dict) -> None:
    for field in ("relative_note_offsets_us", "cue_gains", "events", "down_actions", "metrics"):
        assert actual[field] == prior[field], field


def main() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    meta = json.loads((OUT / "meta.json").read_text(encoding="utf-8"))
    status = json.loads((OUT / "status.json").read_text(encoding="utf-8"))
    summary = json.loads((OUT / "result.json").read_text(encoding="utf-8"))
    assert status["status"] == summary["status"] == "complete"
    assert meta["protocol_sha256"] == sha(PROTOCOL)
    assert meta["source_long_ledger_sha256"] == sha(LONG / "runs.jsonl")
    assert meta["source_long_meta_sha256"] == sha(LONG / "meta.json")
    for relative, digest in meta["replay_model_source_sha256"].items():
        assert sha(ROOT / relative) == digest
    drift = {name: {"saved": meta["model_source_sha256"][name], "replay": digest}
             for name, digest in meta["replay_model_source_sha256"].items()
             if digest != meta["model_source_sha256"][name]}
    assert drift == meta["source_hash_drift_requiring_exact_replay"]
    assert set(drift) == {"src\\project_b\\simulation\\__init__.py",
                          "src\\project_b\\simulation\\spiking.py"}

    ledger = rows(OUT / "runs.jsonl", "key")
    long_rows = {str(row["seed"]): row for row in rows(LONG / "runs.jsonl", "key").values()
                 if row["condition"] == "on"}
    explore_rows = rows(EXPLORE / "runs.jsonl", "key")
    seeds = [2000, 2001, 2002, 2003, 2004]
    assert protocol["seeds"] == summary["seeds"] == seeds
    assert set(ledger) == set(map(str, seeds))
    assert status["completed"] == status["planned"] == len(seeds)
    assert summary["branch_count"] == 30 and summary["frozen_outcomes"] == 960
    branch_count = outcome_count = action_count = 0
    per_seed = {}
    panel_definitions = {}
    for seed in seeds:
        key = str(seed)
        row = ledger[key]
        source = long_rows[key]
        assert row["seed"] == seed and row["protocol_sha256"] == meta["protocol_sha256"]
        assert row["source_long_ledger_sha256"] == meta["source_long_ledger_sha256"]
        assert row["checkpoint_time_us"] == source["checkpoints"][2]["checkpoint_time_us"]
        assert row["donor_checkpoints"] == [384, 96, 24]
        assert set(row["branches"]) == {"384", "96", "24"}
        per_seed[key] = {}
        for source_at in (384, 96, 24):
            branch = row["branches"][str(source_at)]
            displacement = branch["displacement_from_384"]
            assert 0 <= displacement["changed_edges"] <= 480
            assert 0 <= displacement["lower_bound_edges"] + displacement["upper_bound_edges"] <= 480
            saved_sum = source["checkpoints"][[24, 96, 384].index(source_at)]["plastic_weight_sum_mv"]
            assert math.isclose(displacement["weight_sum_mv"], saved_sum, abs_tol=1e-9)
            if source_at == 384:
                assert displacement["changed_edges"] == 0
                assert displacement["l1_weight_displacement_mv"] == 0
                assert displacement["l2_weight_displacement_mv"] == 0
            else:
                assert displacement["l1_weight_displacement_mv"] > 0
            assert set(branch["maps"]) == {"common", "continuation"}
            per_seed[key][str(source_at)] = {}
            for panel in ("common", "continuation"):
                probe = branch["maps"][panel]
                events = probe["events"]
                actions = probe["down_actions"]
                metrics = probe["metrics"]
                assert probe["exploration"] is False and probe["rng_seed"] is None
                assert probe["exploration_pulses_us"] == []
                assert probe["checkpoint_time_us"] == row["checkpoint_time_us"]
                assert len(events) == metrics["note_count"] == 32
                assert len(actions) == metrics["down_count"]
                panel_key = (seed, panel)
                definition = (probe["relative_note_offsets_us"], probe["cue_gains"])
                if panel_key in panel_definitions:
                    assert panel_definitions[panel_key] == definition
                else:
                    panel_definitions[panel_key] = definition
                for event in events:
                    if event["hit_error_us"] is not None:
                        assert event["hit_error_us"] == event["judgement_time_us"] - event["note_time_us"]
                for disposition in ("null_press", "hit", "early_miss"):
                    assert metrics["dispositions"].get(disposition, 0) == sum(
                        action["disposition"] == disposition for action in actions)
                assert metrics["good_or_better_count"] == sum(e["hit_value"] >= 200 for e in events)
                assert metrics["good_or_better_percent"] == 100 * metrics["good_or_better_count"] / 32
                assert math.isclose(metrics["mean_utility"],
                                    statistics.mean(e["game_utility"] for e in events), abs_tol=1e-12)
                assert metrics["attempted_early_miss_count"] == sum(
                    e["judgement"] == "MISS" and e["hit_error_us"] is not None
                    and e["hit_error_us"] < 0 for e in events)
                assert all(not e["weight_changes"] for e in events)
                assert math.isclose(probe["frozen_weight_sum_mv"], saved_sum, abs_tol=1e-9)
                if source_at == 384 and panel == "common":
                    same_probe(probe, source["checkpoints"][2]["probe"])
                if source_at == 384 and panel == "continuation":
                    same_probe(probe, explore_rows[f"{seed}:384"]["branches"]["continuation"]["off"])
                saved_summary = summary["maps"][panel][str(source_at)]["per_seed"][key]
                assert saved_summary["good_percent"] == metrics["good_or_better_percent"]
                assert saved_summary["mean_utility"] == metrics["mean_utility"]
                assert saved_summary["weight_displacement_l1_mv"] == displacement["l1_weight_displacement_mv"]
                per_seed[key][str(source_at)][panel] = {
                    "good_percent": metrics["good_or_better_percent"],
                    "mean_utility": metrics["mean_utility"],
                    "down_actions": len(actions),
                }
                branch_count += 1
                outcome_count += len(events)
                action_count += len(actions)
    for panel in ("common", "continuation"):
        for source_at in (384, 96, 24):
            probes = [ledger[str(seed)]["branches"][str(source_at)]["maps"][panel]
                      for seed in seeds]
            aggregate = summary["maps"][panel][str(source_at)]
            assert aggregate["mean_good_percent"] == statistics.mean(
                probe["metrics"]["good_or_better_percent"] for probe in probes)
            assert aggregate["mean_utility"] == statistics.mean(
                probe["metrics"]["mean_utility"] for probe in probes)
            assert aggregate["mean_down_actions"] == statistics.mean(
                probe["metrics"]["down_count"] for probe in probes)
            assert aggregate["mean_early_attempted_misses"] == statistics.mean(
                probe["metrics"]["attempted_early_miss_count"] for probe in probes)
    assert branch_count == 30 and outcome_count == 960
    receipt = {"status": "passed", "seeds": seeds, "branches": branch_count,
               "frozen_outcomes": outcome_count, "down_actions": action_count,
               "reference_common_exact_matches": 5,
               "reference_continuation_exact_matches": 5,
               "protocol_sha256": meta["protocol_sha256"],
               "ledger_sha256": sha(OUT / "runs.jsonl"), "per_seed": per_seed}
    (OUT / "audit.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in receipt.items() if key != "per_seed"}))


if __name__ == "__main__":
    main()
