"""Independent ledger checks for the completed longitudinal study."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "docs/figures/long_continuation"
PROTOCOL = ROOT / "configs/long_continuation.json"
SOURCE = ROOT / "docs/figures/overnight_synthetic/runs.jsonl"


def main() -> None:
    protocol_raw = PROTOCOL.read_bytes()
    protocol = json.loads(protocol_raw)
    meta = json.loads((DIRECTORY / "meta.json").read_text())
    summary = json.loads((DIRECTORY / "result.json").read_text())
    rows = [json.loads(line) for line in (DIRECTORY / "runs.jsonl").read_text().splitlines()]
    originals = {(row["seed"], row["condition"]): row
                 for line in SOURCE.read_text().splitlines()
                 if (row := json.loads(line))["stage"] == "heldout"}
    assert meta["protocol_sha256"] == hashlib.sha256(protocol_raw).hexdigest()
    assert meta["source_ledger_sha256"] == hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    for name, expected in meta["model_source_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected
    assert len(rows) == len(protocol["seeds"]) * len(protocol["conditions"]) == 24
    by_key = {(row["seed"], row["condition"]): row for row in rows}
    assert len(by_key) == len(rows)
    assert summary["status"] == "complete"
    assert meta["probe_relative_note_offsets_us"] == rows[0]["checkpoints"][0]["probe"]["relative_note_offsets_us"]
    assert meta["probe_cue_gains"] == rows[0]["checkpoints"][0]["probe"]["cue_gains"]

    outcome_count = 0
    probe_count = 0
    for seed in protocol["seeds"]:
        seed_rows = {condition: by_key[(seed, condition)] for condition in protocol["conditions"]}
        maps = [row["resolved_config"] for row in seed_rows.values()]
        assert all(item["training_note_times_us"] == maps[0]["training_note_times_us"] for item in maps)
        assert all(item["training_cue_gains"] == maps[0]["training_cue_gains"] for item in maps)
        on_utility = [event["game_utility"] for event in seed_rows["on"]["training_events"]]
        shuffled = [event["learning_utility"] for event in seed_rows["shuffled"]["training_events"]]
        for start, stop in ((0, 24), (24, 96), (96, 384)):
            assert sorted(on_utility[start:stop]) == sorted(shuffled[start:stop])
        for condition, row in seed_rows.items():
            assert row["protocol_sha256"] == meta["protocol_sha256"]
            assert row["original_source_ledger_sha256"] == meta["source_ledger_sha256"]
            assert len(row["training_events"]) == 384
            assert len(row["checkpoints"]) == 3
            assert len(row["update_diagnostics"]) == (0 if condition == "off" else 384)
            outcome_count += len(row["training_events"])
            original = originals[(seed, condition)]["summary"]["events"]
            for current, saved in zip(row["training_events"][:24], original[:24]):
                for field in ("judgement", "hit_error_us", "game_utility",
                              "learning_utility", "rpe", "weight_changes"):
                    assert current[field] == saved[field], (seed, condition, field)
            for checkpoint, expected in zip(row["checkpoints"], (24, 96, 384)):
                assert checkpoint["after_training_outcomes"] == expected
                probe = checkpoint["probe"]
                assert probe["relative_note_offsets_us"] == meta["probe_relative_note_offsets_us"]
                assert probe["cue_gains"] == meta["probe_cue_gains"]
                assert len(probe["events"]) == protocol["probe_panel"]["note_count"]
                assert all(event["weight_changes"] == 0 for event in probe["events"])
                assert probe["metrics"]["note_count"] == protocol["probe_panel"]["note_count"]
                probe_count += len(probe["events"])
            if condition == "off":
                assert all(event["weight_changes"] == 0 for event in row["training_events"])
            if condition == "shuffled":
                assert [event["learning_utility"] for event in row["training_events"]] == shuffled
    print(json.dumps({"status": "audit_passed", "seeds": protocol["seeds"],
                      "condition_runs": len(rows), "training_outcomes": outcome_count,
                      "frozen_probe_outcomes": probe_count,
                      "checkpoints_per_run": [24, 96, 384]}))


if __name__ == "__main__":
    main()
