"""Verify the completed fixed-weight exploration/map diagnostic ledger."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.exploration_map_diagnostic import stream_seed


ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "docs/figures/exploration_map_diagnostic"
PROTOCOL = ROOT / "configs/exploration_map_diagnostic.json"
LONG_DIRECTORY = ROOT / "docs/figures/long_continuation"


def main() -> None:
    protocol_raw = PROTOCOL.read_bytes()
    protocol = json.loads(protocol_raw)
    meta = json.loads((DIRECTORY / "meta.json").read_text())
    stopped = (DIRECTORY / "stop.json").exists()
    summary_path = DIRECTORY / ("result_partial.json" if stopped else "result.json")
    summary = json.loads(summary_path.read_text())
    selected_seeds = (json.loads((DIRECTORY / "stop.json").read_text())["completed_seeds"]
                      if stopped else protocol["seeds"])
    rows = [json.loads(s) for s in (DIRECTORY / "runs.jsonl").read_text().splitlines()]
    source = {r["seed"]: r for s in (LONG_DIRECTORY / "runs.jsonl").read_text().splitlines()
              if (r := json.loads(s))["condition"] == "on"}
    assert meta["protocol_sha256"] == hashlib.sha256(protocol_raw).hexdigest()
    assert meta["source_long_ledger_sha256"] == hashlib.sha256(
        (LONG_DIRECTORY / "runs.jsonl").read_bytes()).hexdigest()
    for name, expected in meta["model_source_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected
    assert len(rows) == len(selected_seeds) * 3
    assert len({row["key"] for row in rows}) == len(rows)
    assert summary["status"] == ("user_stopped_early" if stopped else "complete")
    count = 0
    for row in rows:
        seed, checkpoint = row["seed"], row["checkpoint"]
        assert seed in selected_seeds
        assert checkpoint in protocol["checkpoints_after_training_outcomes"]
        assert row["key"] == f"{seed}:{checkpoint}"
        assert row["protocol_sha256"] == meta["protocol_sha256"]
        assert row["source_long_ledger_sha256"] == meta["source_long_ledger_sha256"]
        checkpoint_index = protocol["checkpoints_after_training_outcomes"].index(checkpoint)
        saved = source[seed]["checkpoints"][checkpoint_index]
        assert row["checkpoint_time_us"] == saved["checkpoint_time_us"]
        for map_name in ("common", "continuation"):
            map_row = row["branches"][map_name]
            assert len(map_row["absolute_note_times_us"]) == 32
            assert len(map_row["cue_gains"]) == 32
            assert len(map_row["on"]) == 3
            all_branches = [map_row["off"], *map_row["on"]]
            for branch in all_branches:
                assert len(branch["events"]) == branch["metrics"]["note_count"] == 32
                assert all(event["weight_changes"] == 0 for event in branch["events"])
                assert branch["checkpoint_time_us"] == row["checkpoint_time_us"]
                assert branch["cue_gains"] == map_row["cue_gains"]
                assert [row["checkpoint_time_us"] + v for v in branch["relative_note_offsets_us"]] == map_row["absolute_note_times_us"]
                assert abs(branch["frozen_weight_sum_mv"] - row["frozen_weight_sum_mv"]) < 1e-9
                count += 32
            off = map_row["off"]
            assert off["exploration"] is False
            assert not off["exploration_pulses_us"]
            assert off["rng_seed"] is None
            for repeat, branch in enumerate(map_row["on"]):
                assert branch["exploration"] is True
                assert branch["repeat"] == repeat
                expected_seed = None if repeat == 0 else stream_seed(
                    protocol["study_id"], seed, checkpoint, repeat)
                assert branch["rng_seed"] == expected_seed
                assert row["exploration_rng_seeds"][str(repeat)] == expected_seed
            if map_name == "common":
                original = saved["probe"]
                assert off["relative_note_offsets_us"] == original["relative_note_offsets_us"] == meta["common_relative_note_offsets_us"]
                assert off["cue_gains"] == original["cue_gains"] == meta["common_cue_gains"]
                assert off["events"] == original["events"]
                assert off["down_actions"] == original["down_actions"]
                assert off["metrics"] == original["metrics"]
            else:
                note_times = source[seed]["resolved_config"]["training_note_times_us"]
                note_gains = source[seed]["resolved_config"]["training_cue_gains"]
                if checkpoint < 384:
                    assert map_row["absolute_note_times_us"] == note_times[checkpoint:checkpoint + 32]
                    assert map_row["cue_gains"] == note_gains[checkpoint:checkpoint + 32]
                else:
                    assert map_row["absolute_note_times_us"][0] > note_times[-1]
    expected_branches = len(selected_seeds) * 3 * 2 * 4
    assert count == expected_branches * 32
    if not stopped:
        assert count == summary["note_outcomes"]
        assert summary["branch_count"] == expected_branches
    print(json.dumps({"status": "audit_passed", "seeds": selected_seeds,
                      "checkpoints": len(rows), "branches": expected_branches,
                      "frozen_probe_outcomes": count}))


if __name__ == "__main__":
    main()
