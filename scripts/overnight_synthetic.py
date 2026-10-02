"""Bounded synthetic training study; dry-run unless --start-training is explicit.

Each completed run is durably logged. The study resumes at run boundaries and
never exposes heldout outcomes during candidate selection.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
import time
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path

from project_b.experiments import TinyBrainConfig, run_tiny_lane_one
from scripts.checkpoint_controls import shuffled_utilities, summarize

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs" / "overnight_synthetic.json"
DEFAULT_OUTPUT = ROOT / "docs" / "figures" / "overnight_synthetic"


def seed_range(spec: dict) -> tuple[int, ...]:
    return tuple(range(spec["start"], spec["start"] + spec["count"]))


def map_for_seed(seed: int, count: int, spec: dict) -> tuple[tuple[int, ...], tuple[float, ...]]:
    """Separate map RNG from neural exploration; no condition sees another map."""
    rng = random.Random(seed ^ 0x6D6170)
    times = [800_000]
    for _ in range(1, count):
        times.append(times[-1] + rng.choice(spec["note_interval_ms_choices"]) * 1_000)
    gains = tuple(rng.choice(spec["cue_gain_choices"]) for _ in range(count))
    return tuple(times), gains


def frozen_metric(row: dict, metric: str) -> float:
    return float(row["summary"][metric])


def choose_candidate(rows: dict, spec: dict) -> int:
    dev = seed_range(spec["development_seeds"])
    choices = spec["candidate_readout_thresholds"]
    def score(threshold: int) -> tuple[float, float, int]:
        values = [rows[f"dev:{threshold}:{seed}:on"]["summary"] for seed in dev]
        return (sum(v["frozen_good_or_better_percent"] for v in values) / len(values),
                sum(v["frozen_non_miss_percent"] for v in values) / len(values),
                -threshold)
    return max(choices, key=score)


def atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def load_rows(path: Path, config_sha256: str) -> dict:
    rows = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row["config_sha256"] != config_sha256:
                raise ValueError("ledger configuration hash differs; use a new output directory")
            if row["key"] in rows:
                raise ValueError("duplicate completed run in ledger")
            rows[row["key"]] = row
    return rows


def append_row(path: Path, row: dict) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, separators=(",", ":")) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def evaluate_gate(rows: dict, threshold: int, spec: dict) -> dict:
    seeds = seed_range(spec["heldout_seeds"])
    metric = spec["primary_metric"]
    limits = spec["heldout_gate"]
    on = [rows[f"heldout:{threshold}:{seed}:on"]["summary"] for seed in seeds]
    good_mean = sum(v[metric] for v in on) / len(on)
    abs_errors = [abs(event["hit_error_us"]) / 1000
                  for seed in seeds
                  for event in rows[f"heldout:{threshold}:{seed}:on"]["summary"]["events"]
                  if event["phase"] == "frozen" and event["judgement"] != "MISS"
                  and event["hit_error_us"] is not None]
    mean_abs_error = sum(abs_errors)/len(abs_errors) if abs_errors else None
    comparisons = {}
    for control in ("off", "shuffled"):
        diff = [rows[f"heldout:{threshold}:{seed}:on"]["summary"][metric]
                - rows[f"heldout:{threshold}:{seed}:{control}"]["summary"][metric]
                for seed in seeds]
        comparisons[control] = {
            "mean_paired_advantage_percentage_points": sum(diff)/len(diff),
            "strict_win_seeds": sum(value > 0 for value in diff),
            "tie_seeds": sum(value == 0 for value in diff),
            "strict_loss_seeds": sum(value < 0 for value in diff),
            "passes": (sum(diff)/len(diff) >=
                       limits["minimum_mean_paired_advantage_percentage_points_vs_each_control"]
                       and sum(value > 0 for value in diff) >=
                       limits["minimum_strict_win_seeds_vs_each_control"]),
        }
    return {
        "selected_threshold": threshold,
        "on_good_or_better_percent": good_mean,
        "on_hit_mean_absolute_error_ms": mean_abs_error,
        "comparisons": comparisons,
        "passes": (all(x["passes"] for x in comparisons.values())
                   and good_mean >= limits["minimum_on_good_or_better_percent"]
                   and mean_abs_error is not None
                   and mean_abs_error <= limits["maximum_on_hit_mean_absolute_error_ms"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--start-training", action="store_true",
                        help="required to execute training; otherwise only print the plan")
    args = parser.parse_args()
    raw_config = args.config.read_bytes()
    spec = json.loads(raw_config)
    config_sha = hashlib.sha256(raw_config).hexdigest()
    dev = seed_range(spec["development_seeds"])
    holdout = seed_range(spec["heldout_seeds"])
    if set(dev) & set(holdout):
        parser.error("development and heldout seeds must be disjoint")
    if (not spec["candidate_readout_thresholds"] or spec["wall_budget_seconds"] <= 0
            or spec["training_notes"] <= 0 or spec["frozen_notes"] <= 0):
        parser.error("invalid candidate, note or budget values")
    planned = (len(dev) * len(spec["candidate_readout_thresholds"])
               + len(holdout) * 3)
    plan = {"status": "dry_run", "study_id": spec["study_id"],
            "config_sha256": config_sha, "development_runs": len(dev)*len(spec["candidate_readout_thresholds"]),
            "heldout_runs": len(holdout)*3, "total_runs": planned,
            "wall_budget_hours": spec["wall_budget_seconds"]/3600,
            "output": str(args.output.resolve())}
    if not args.start_training:
        print(json.dumps(plan, indent=2))
        return
    args.output.mkdir(parents=True, exist_ok=True)
    ledger = args.output / "runs.jsonl"
    meta_path = args.output / "meta.json"
    status_path = args.output / "status.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta["config_sha256"] != config_sha:
            raise ValueError("existing run has a different configuration")
    else:
        meta = {**plan, "status": "running", "python": sys.version.split()[0],
                "started_unix": time.time(),
                "started_utc": datetime.now(timezone.utc).isoformat(),
                "model_source_sha256": {
                    str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in (ROOT/"src/project_b/experiments/tiny_brain.py",
                                 ROOT/"src/project_b/neuromodulation/reward.py",
                                 ROOT/"src/project_b/plasticity/eligibility.py")}}
        atomic_json(meta_path, meta)
    deadline = meta["started_unix"] + spec["wall_budget_seconds"]
    rows = load_rows(ledger, config_sha)
    train = spec["training_notes"]
    count = train + spec["frozen_notes"]

    def execute(stage: str, threshold: int, seed: int, condition: str) -> bool:
        key = f"{stage}:{threshold}:{seed}:{condition}"
        if key in rows:
            return True
        if time.time() >= deadline:
            atomic_json(status_path, {"status": "budget_exhausted", "completed_runs": len(rows),
                                      "planned_runs": planned, "last_key": key})
            return False
        times, gains = map_for_seed(seed, count, spec)
        base = TinyBrainConfig(
            note_count=count, training_notes=train, seed=seed,
            explicit_note_times_us=times, cue_gain_by_note=gains,
            readout_on_threshold=threshold)
        if condition == "off":
            config = replace(base, plasticity_enabled=False)
        elif condition == "shuffled":
            reference = rows[f"heldout:{threshold}:{seed}:on"]["summary"]
            utilities = tuple(event["game_utility"] for event in reference["events"][:train])
            config = replace(base, reward_utility_schedule=shuffled_utilities(utilities, seed))
        else:
            config = base
        result = run_tiny_lane_one(config)
        row = {"key": key, "stage": stage, "threshold": threshold,
               "seed": seed, "condition": condition, "config_sha256": config_sha,
               "resolved_config": asdict(config), "summary": summarize(result, train),
               "completed_utc": datetime.now(timezone.utc).isoformat()}
        append_row(ledger, row)
        rows[key] = row
        atomic_json(status_path, {"status": "running", "completed_runs": len(rows),
                                  "planned_runs": planned, "last_key": key,
                                  "deadline_unix": deadline})
        print(f"{len(rows)}/{planned} {key}", flush=True)
        return True

    for threshold in spec["candidate_readout_thresholds"]:
        for seed in dev:
            if not execute("dev", threshold, seed, "on"):
                return
    selected = choose_candidate(rows, spec)
    atomic_json(args.output/"selection.json", {
        "selected_threshold": selected,
        "selection_rule": spec["candidate_selection"],
        "development_seeds": dev})
    for seed in holdout:
        for condition in ("on", "off", "shuffled"):
            if not execute("heldout", selected, seed, condition):
                return
    gate = evaluate_gate(rows, selected, spec)
    atomic_json(args.output/"result.json", {
        "status": "complete", "study_id": spec["study_id"],
        "config_sha256": config_sha, "gate": gate,
        "completed_runs": len(rows), "planned_runs": planned,
        "finished_utc": datetime.now(timezone.utc).isoformat()})
    atomic_json(status_path, {"status": "complete", "completed_runs": len(rows),
                              "planned_runs": planned, "gate_passes": gate["passes"]})
    print(json.dumps(gate, indent=2), flush=True)


if __name__ == "__main__":
    main()
