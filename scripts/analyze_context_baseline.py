"""Post hoc pooled-baseline arithmetic from the saved context probe.

No new simulation trials, weight interventions, or parameter selection.
"""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/figures/context_baseline_probe.json"
OUTPUT = ROOT / "docs/figures/context_baseline_posthoc.json"


def vector_mean(rows: list[list[float]]) -> list[float]:
    return [statistics.mean(row[i] for row in rows) for i in range(len(rows[0]))]


def l1(values: list[float]) -> float:
    return sum(abs(value) for value in values)


def cosine(a: list[float], b: list[float]) -> float | None:
    aa, bb = sum(x*x for x in a), sum(y*y for y in b)
    return sum(x*y for x, y in zip(a, b)) / math.sqrt(aa*bb) if aa and bb else None


def main() -> None:
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    eta = data["checkpoint"]["eta"]
    contexts = data["contexts"]
    pooled_estimate = statistics.mean(c["moments"]["estimate_mean_utility"] for c in contexts)
    pooled_evaluation = statistics.mean(c["moments"]["evaluate_mean_utility"] for c in contexts)
    per_gain = []
    for c in contexts:
        m = c["moments"]
        drift = [eta * e * (m["evaluate_mean_utility"] - pooled_estimate)
                 for e in m["mean_eligibility"]]
        per_gain.append({"gain": c["gain"], "pooled_drift_mv": drift,
                         "pooled_drift_l1_mv": l1(drift),
                         "pooled_drift_signed_sum_mv": sum(drift)})
    pooled_drift = vector_mean([row["pooled_drift_mv"] for row in per_gain])
    covariance = data["aggregate"]["covariance_term_mv"]
    pooled_update = [a+b for a, b in zip(covariance, pooled_drift)]
    assert max(abs(a-b-c) for a,b,c in zip(pooled_update,covariance,pooled_drift)) < 1e-12
    saved_global = data["aggregate"]["global_proposed_update_mv"]
    context = data["aggregate"]["context_proposed_update_mv"]
    result = {
        "classification": "post_hoc_arithmetic_comparator_not_preregistered",
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "method": "Estimate one current-policy global utility mean by equally pooling the five disjoint estimation-split context means. Evaluate its update only on the evaluation split. No new streams or simulation.",
        "pooled_estimation_mean_utility": pooled_estimate,
        "pooled_evaluation_mean_utility": pooled_evaluation,
        "per_gain": per_gain,
        "mean_per_gain_pooled_drift_l1_mv": statistics.mean(row["pooled_drift_l1_mv"] for row in per_gain),
        "mean_per_gain_saved_global_drift_l1_mv": statistics.mean(c["moments"]["global_drift_norm"]["l1"] for c in contexts),
        "mean_per_gain_context_drift_l1_mv": statistics.mean(c["moments"]["context_drift_norm"]["l1"] for c in contexts),
        "aggregate_pooled_drift_mv": pooled_drift,
        "aggregate_pooled_update_mv": pooled_update,
        "aggregate_pooled_drift_l1_mv": l1(pooled_drift),
        "aggregate_pooled_update_l1_mv": l1(pooled_update),
        "aggregate_pooled_update_signed_sum_mv": sum(pooled_update),
        "cosine_pooled_vs_saved_global": cosine(pooled_update, saved_global),
        "cosine_pooled_vs_context": cosine(pooled_update, context),
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"pooled_estimate": pooled_estimate,
                      "saved_global_estimate": data["checkpoint"]["global_baseline"],
                      "mean_per_gain_drift_l1": [
                          result["mean_per_gain_saved_global_drift_l1_mv"],
                          result["mean_per_gain_pooled_drift_l1_mv"],
                          result["mean_per_gain_context_drift_l1_mv"]],
                      "cosine_pooled_vs_context": result["cosine_pooled_vs_context"]}),
          flush=True)
    print(f"wrote {OUTPUT}", flush=True)


if __name__ == "__main__":
    main()
