"""Summarize all complete seed triplets after the user-directed early stop."""

from __future__ import annotations

import json
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "docs/figures/exploration_map_diagnostic"


def avg(values) -> float:
    return statistics.mean(values)


def main() -> None:
    protocol = json.loads((ROOT / "configs/exploration_map_diagnostic.json").read_text())
    stop = json.loads((DIRECTORY / "stop.json").read_text())
    rows = [json.loads(s) for s in (DIRECTORY / "runs.jsonl").read_text().splitlines()]
    by_key = {row["key"]: row for row in rows}
    seeds = stop["completed_seeds"]
    assert len(rows) == len(by_key) == 15
    assert seeds == protocol["seeds"][:5]
    assert all(f"{seed}:{checkpoint}" in by_key for seed in seeds
               for checkpoint in (24, 96, 384))
    output = {"study_id": protocol["study_id"],
              "status": "user_stopped_early",
              "original_planned_seeds": protocol["seeds"],
              "completed_seeds": seeds,
              "unrun_seeds": stop["unrun_seeds"],
              "checkpoints": {},
              "per_seed": {}}
    for checkpoint in (24, 96, 384):
        group = {}
        for map_name in ("common", "continuation"):
            off = [by_key[f"{seed}:{checkpoint}"]["branches"][map_name]["off"]
                   for seed in seeds]
            on = [by_key[f"{seed}:{checkpoint}"]["branches"][map_name]["on"]
                  for seed in seeds]
            off_good = [b["metrics"]["good_or_better_percent"] for b in off]
            on_good = [avg(b["metrics"]["good_or_better_percent"] for b in branches)
                       for branches in on]
            off_utility = [b["metrics"]["mean_utility"] for b in off]
            on_utility = [avg(b["metrics"]["mean_utility"] for b in branches)
                          for branches in on]
            group[map_name] = {
                "off_mean_good_percent": avg(off_good),
                "on_mean_good_percent": avg(on_good),
                "on_minus_off_mean_good_points": avg(a-b for a, b in zip(on_good, off_good)),
                "off_mean_utility": avg(off_utility),
                "on_mean_utility": avg(on_utility),
                "on_minus_off_mean_utility": avg(a-b for a, b in zip(on_utility, off_utility)),
                "off_mean_early_attempted_misses": avg(b["metrics"]["attempted_early_miss_count"] for b in off),
                "on_mean_early_attempted_misses": avg(avg(b["metrics"]["attempted_early_miss_count"] for b in branches) for branches in on),
                "off_mean_down_actions": avg(b["metrics"]["down_count"] for b in off),
                "on_mean_down_actions": avg(avg(b["metrics"]["down_count"] for b in branches) for branches in on),
                "off_mean_null_downs": avg(b["metrics"]["null_down_count"] for b in off),
                "on_mean_null_downs": avg(avg(b["metrics"]["null_down_count"] for b in branches) for branches in on),
                "on_mean_exploration_pulses": avg(avg(len(b["exploration_pulses_us"]) for b in branches) for branches in on),
                "per_seed": {str(seed): {
                    "off_good_percent": off_value,
                    "on_good_percent_by_stream": [b["metrics"]["good_or_better_percent"] for b in branches],
                    "on_mean_good_percent": on_value,
                    "on_minus_off_good_points": on_value - off_value,
                } for seed, off_value, on_value, branches in zip(seeds, off_good, on_good, on)},
            }
        group["map_effect_off_points"] = (group["continuation"]["off_mean_good_percent"] -
                                          group["common"]["off_mean_good_percent"])
        group["map_effect_on_points"] = (group["continuation"]["on_mean_good_percent"] -
                                         group["common"]["on_mean_good_percent"])
        output["checkpoints"][str(checkpoint)] = group
    for seed in seeds:
        output["per_seed"][str(seed)] = {str(checkpoint): {
            map_name: {
                "off_good_percent": by_key[f"{seed}:{checkpoint}"]["branches"][map_name]["off"]["metrics"]["good_or_better_percent"],
                "on_good_percent_by_stream": [b["metrics"]["good_or_better_percent"]
                                              for b in by_key[f"{seed}:{checkpoint}"]["branches"][map_name]["on"]],
            } for map_name in ("common", "continuation")}
            for checkpoint in (24, 96, 384)}
    target = DIRECTORY / "result_partial.json"
    target.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(target)


if __name__ == "__main__":
    main()
