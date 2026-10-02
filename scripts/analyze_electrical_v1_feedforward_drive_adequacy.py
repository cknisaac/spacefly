"""Summarize the locked B5.1 reconstruction without selecting parameters."""

from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/figures/electrical_v1_feedforward_drive_adequacy"


def dist(rows, key):
    vals = [r[key] for r in rows if r[key] is not None]
    return {"n": len(vals), "min": min(vals) if vals else None,
            "p25": float(np.percentile(vals, 25)) if vals else None,
            "median": float(np.median(vals)) if vals else None,
            "p75": float(np.percentile(vals, 75)) if vals else None,
            "max": max(vals) if vals else None}


def main():
    d = json.loads((OUT / "result.json").read_text())
    grouped = defaultdict(list)
    for trial in d["trials"]:
        grouped[(trial["stage"], trial["level"])].append(trial)
    result = {"source_result_sha256": __import__("hashlib").sha256((OUT / "result.json").read_bytes()).hexdigest(),
              "protocol_sha256": d["protocol_sha256"], "groups": {}}
    fields = ("anatomical_contact_count", "anatomical_pair_count", "event_count",
              "event_impulse_pa", "peak_fast_current_pa", "fast_charge_fc",
              "peak_voltage_mv", "peak_depolarization_mv", "minimum_threshold_distance_mv",
              "leak_charge_fc", "arrival_span_us", "distinct_arrival_ticks",
              "best_5ms_impulse_fraction", "critical_multiplier_linear")
    for (stage, level), trials in grouped.items():
        first = trials[0]
        observed = first["results_by_timing"]["observed"]
        contacted = [r for r in observed if r["anatomical_contact_count"]]
        active = [r for r in observed if r["event_count"]]
        summary = {"trial_count": len(trials), "target_count": len(observed),
                   "contacted_count": len(contacted), "receiving_events_count": len(active),
                   "meaningful_count": sum(r["meaningful_drive"] for r in observed),
                   "events_per_trial": sum(r["event_count"] for r in observed),
                   "impulse_pa_per_trial": sum(r["event_impulse_pa"] for r in observed),
                   "total_fast_charge_fc_per_trial": sum(r["fast_charge_fc"] for r in observed),
                   "all_targets": {field: dist(observed, field) for field in fields},
                   "contacted_targets": {field: dist(contacted, field) for field in fields},
                   "receiving_targets": {field: dist(active, field) for field in fields},
                   "threshold_bands": {"critical_at_most_2": sum(r["critical_multiplier_linear"] is not None and r["critical_multiplier_linear"] <= 2 for r in observed),
                                       "critical_2_to_10": sum(r["critical_multiplier_linear"] is not None and 2 < r["critical_multiplier_linear"] < 10 for r in observed),
                                       "critical_at_least_10": sum(r["critical_multiplier_linear"] is not None and r["critical_multiplier_linear"] >= 10 for r in observed),
                                       "no_finite_critical": sum(r["critical_multiplier_linear"] is None for r in observed)},
                   "first_panel_multiplier_count": {str(k): v for k, v in Counter(r["first_tested_spiking_multiplier"] for r in observed).items()},
                   "timing": {}, "variation_across_seed_pulses": {}}
        for timing in ("observed", "bin20ms_midpoint", "single_volley_100ms"):
            rr = first["results_by_timing"][timing]
            ratios = [o["critical_multiplier_linear"] / t["critical_multiplier_linear"]
                      for o, t in zip(observed, rr) if o["critical_multiplier_linear"] and t["critical_multiplier_linear"]]
            summary["timing"][timing] = {"critical_multiplier": dist(rr, "critical_multiplier_linear"),
                                          "observed_to_timing_critical_ratio": dist([{"ratio": r} for r in ratios], "ratio"),
                                          "first_panel_multiplier_count": {str(k): v for k, v in Counter(r["first_tested_spiking_multiplier"] for r in rr).items()}}
        for field in ("event_count", "peak_fast_current_pa", "fast_charge_fc", "peak_voltage_mv", "minimum_threshold_distance_mv"):
            signatures = {tuple(r[field] for r in trial["results_by_timing"]["observed"]) for trial in trials}
            summary["variation_across_seed_pulses"][field] = len(signatures)
        result["groups"][f"{stage}/{level}"] = summary
    (OUT / "analysis.json").write_text(json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n")
    for key, group in result["groups"].items():
        print(key, "contacted", group["contacted_count"], "meaningful", group["meaningful_count"],
              "events", group["events_per_trial"], "peak-V", group["all_targets"]["peak_voltage_mv"],
              "critical", group["threshold_bands"])


if __name__ == "__main__":
    main()
