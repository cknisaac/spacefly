"""Derive compact diagnostics from the immutable longitudinal event ledger."""

from __future__ import annotations

import json
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "docs/figures/long_continuation"


def mean(items) -> float:
    return statistics.mean(items)


def main() -> None:
    rows = [json.loads(line) for line in (DIRECTORY / "runs.jsonl").read_text().splitlines()]
    assert len(rows) == 24
    result = {"diagnostics_by_checkpoint": {}, "per_seed_probe": {}}
    for index, checkpoint in enumerate((24, 96, 384)):
        result["diagnostics_by_checkpoint"][str(checkpoint)] = {}
        for condition in ("on", "off", "shuffled"):
            chosen = [row["checkpoints"][index] for row in rows if row["condition"] == condition]
            assert len(chosen) == 8
            block_lengths = [checkpoint - (0, 24, 96)[index] for _ in chosen]
            metrics = [item["training_block_metrics"] for item in chosen]
            probes = [item["probe"]["metrics"] for item in chosen]
            result["diagnostics_by_checkpoint"][str(checkpoint)][condition] = {
                "mean_training_good_percent": mean(item["good_or_better_percent"] for item in metrics),
                "mean_training_game_utility": mean(item["mean_utility"] for item in metrics),
                "mean_training_abs_game_prediction_error": mean(item["mean_abs_actual_minus_expected"] for item in metrics),
                "mean_training_signed_game_prediction_error": mean(item["mean_actual_minus_expected"] for item in metrics),
                "mean_training_abs_learning_rpe": mean(item["mean_abs_rpe"] for item in metrics),
                "mean_training_downs_per_note": mean(item["down_count"] / n for item, n in zip(metrics, block_lengths)),
                "mean_training_null_downs_per_note": mean(item["null_down_count"] / n for item, n in zip(metrics, block_lengths)),
                "mean_training_exploration_pulses_per_note": mean(item["training_block_exploration_pulses"] / n for item, n in zip(chosen, block_lengths)),
                "mean_raw_update_l1_mv_per_outcome": mean(item["training_block_update_raw_l1_mv"] / n for item, n in zip(chosen, block_lengths)),
                "mean_applied_update_l1_mv_per_outcome": mean(item["training_block_update_applied_l1_mv"] / n for item, n in zip(chosen, block_lengths)),
                "mean_upper_clipped_edge_proposals_per_outcome": mean(item["training_block_clipped_high_edge_events"] / n for item, n in zip(chosen, block_lengths)),
                "mean_lower_clipped_edge_proposals_per_outcome": mean(item["training_block_clipped_low_edge_events"] / n for item, n in zip(chosen, block_lengths)),
                "mean_upper_bound_edges": mean(item["upper_bound_edges"] for item in chosen),
                "mean_probe_good_percent": mean(item["good_or_better_percent"] for item in probes),
                "mean_probe_game_utility": mean(item["mean_utility"] for item in probes),
                "mean_probe_null_downs": mean(item["null_down_count"] for item in probes),
                "mean_probe_early_attempted_misses": mean(item["attempted_early_miss_count"] for item in probes),
                "mean_probe_hit_absolute_error_ms_among_seeds_with_hits": (
                    mean(item["hit_mean_absolute_error_ms"] for item in probes
                         if item["hit_mean_absolute_error_ms"] is not None)
                    if any(item["hit_mean_absolute_error_ms"] is not None for item in probes)
                    else None),
            }
    for seed in range(2000, 2008):
        result["per_seed_probe"][str(seed)] = {}
        for condition in ("on", "off", "shuffled"):
            row = next(row for row in rows if row["seed"] == seed and row["condition"] == condition)
            result["per_seed_probe"][str(seed)][condition] = [
                {"after": item["after_training_outcomes"],
                 "good_percent": item["probe"]["metrics"]["good_or_better_percent"],
                 "mean_utility": item["probe"]["metrics"]["mean_utility"],
                 "null_downs": item["probe"]["metrics"]["null_down_count"],
                 "upper_bound_edges": item["upper_bound_edges"]}
                for item in row["checkpoints"]]
    path = DIRECTORY / "diagnostics.json"
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
