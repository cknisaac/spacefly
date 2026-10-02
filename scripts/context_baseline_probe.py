"""Fixed-weight context baseline and eligibility audit for Project B.

Run with PYTHONPATH=src as ``python -m scripts.context_baseline_probe``.
All learning after the restored checkpoint is disabled. Private weight state is
used only for cloned diagnostic interventions, never for production training.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import statistics
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path

from project_b.experiments import TinyLaneSession
from scripts.update_direction_probe import collect, digest, replay_training


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/context_baseline_probe.json"
LEDGER = ROOT / "docs/figures/overnight_synthetic/runs.jsonl"
ORIGINAL_META = ROOT / "docs/figures/overnight_synthetic/meta.json"
OUTPUT = ROOT / "docs/figures/context_baseline_probe.json"
EDGE_LIMIT_MV = 0.004


def stream_seed(study_id: str, split: str, gain: float, repeat: int) -> int:
    label = f"{study_id}|{split}|{repr(gain)}|{repeat}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(label).digest()[:8], "big")


def mean_vectors(vectors: list[list[float]]) -> list[float]:
    n = len(vectors)
    assert n > 0 and all(len(v) == len(vectors[0]) for v in vectors)
    return [sum(row[i] for row in vectors) / n for i in range(len(vectors[0]))]


def norm(values: list[float]) -> dict:
    return {"l1": sum(abs(v) for v in values),
            "l2": math.sqrt(sum(v*v for v in values)),
            "max_abs": max((abs(v) for v in values), default=0.0),
            "signed_sum": sum(values)}


def sample_once(checkpoint: bytes, gain: float, seed: int,
                target_index: int, slots: tuple[int, ...]) -> dict:
    session = TinyLaneSession.from_trusted_checkpoint_bytes(checkpoint)
    gains = list(session.config.cue_gain_by_note)
    gains[target_index] = gain
    session.config = replace(session.config, cue_gain_by_note=tuple(gains),
                             training_notes=session.config.note_count,
                             plasticity_enabled=False)
    session.training_notes = session.config.note_count
    session.rng.setstate(random.Random(seed).getstate())
    first_action = len(session.game.result().actions)
    first_pulse = len(session.exploration_pulses)
    target_resolved = target_index + 1
    while session.resolved_count < target_resolved:
        session.step()
    assert session.resolved_count == target_resolved
    feedback = session.feedback[target_index]
    j = feedback.reinforcement.judgement_record
    assert j.note_time_us == session.note_times_us[target_index]
    assert feedback.weight_changes == ()
    t = feedback.delivered_time_us
    assert t == session.simulator.current_time_us
    e = [session.plasticity.eligibility_at(slot, t) for slot in slots]
    u = feedback.reinforcement.utility.utility
    assert math.isclose(feedback.reinforcement.prediction.rpe,
                        u - feedback.reinforcement.prediction.expected_before,
                        rel_tol=0, abs_tol=1e-12)
    down_actions = [
        {"time_us": action.action.time_us, "disposition": action.disposition.value}
        for action in session.game.result().actions[first_action:]
        if action.action.kind.value == "down"
    ]
    return {"stream_seed": seed, "gain": gain,
            "judgement": j.judgement.name, "hit_error_us": j.hit_error_us,
            "utility": u, "judgement_time_us": j.event_time_us,
            "delivered_time_us": t, "eligibility_by_plastic_slot": e,
            "exploration_pulses": len(session.exploration_pulses) - first_pulse,
            "down_actions": down_actions}


def context_moments(estimation: list[dict], evaluation: list[dict],
                    global_baseline: float, eta: float) -> dict:
    baseline = statistics.mean(row["utility"] for row in estimation)
    utility_eval = statistics.mean(row["utility"] for row in evaluation)
    mean_e = mean_vectors([row["eligibility_by_plastic_slot"] for row in evaluation])
    mean_eu = mean_vectors([[e * row["utility"]
                            for e in row["eligibility_by_plastic_slot"]]
                           for row in evaluation])
    covariance = [eta * (eu - e * utility_eval)
                  for e, eu in zip(mean_e, mean_eu)]
    drift_global = [eta * e * (utility_eval - global_baseline) for e in mean_e]
    drift_context = [eta * e * (utility_eval - baseline) for e in mean_e]
    update_global = [eta * (eu - e * global_baseline)
                     for e, eu in zip(mean_e, mean_eu)]
    update_context = [eta * (eu - e * baseline)
                      for e, eu in zip(mean_e, mean_eu)]
    assert max(abs(a-b-c) for a, b, c in zip(update_global, covariance, drift_global)) < 1e-12
    assert max(abs(a-b-c) for a, b, c in zip(update_context, covariance, drift_context)) < 1e-12
    return {
        "estimate_mean_utility": baseline,
        "evaluate_mean_utility": utility_eval,
        "estimate_utility_counts": dict(Counter(row["judgement"] for row in estimation)),
        "evaluate_utility_counts": dict(Counter(row["judgement"] for row in evaluation)),
        "estimate_utility_standard_error": (
            statistics.stdev(row["utility"] for row in estimation) / math.sqrt(len(estimation))
            if len(estimation) > 1 else None),
        "mean_eligibility": mean_e,
        "covariance_term_mv": covariance,
        "global_drift_term_mv": drift_global,
        "context_drift_term_mv": drift_context,
        "global_proposed_update_mv": update_global,
        "context_proposed_update_mv": update_context,
        "covariance_norm": norm(covariance),
        "global_drift_norm": norm(drift_global),
        "context_drift_norm": norm(drift_context),
        "global_proposed_norm": norm(update_global),
        "context_proposed_norm": norm(update_context),
    }


def weighted_context_mean(contexts: list[dict], key: str) -> list[float]:
    return mean_vectors([item["moments"][key] for item in contexts])


def clipped_direction(raw: list[float], weights: list[float],
                      minimum: float, maximum: float) -> tuple[list[float], dict]:
    applied = [min(maximum, max(minimum, w + d)) - w
               for w, d in zip(weights, raw)]
    upper = sum(w + d > maximum for w, d in zip(weights, raw))
    lower = sum(w + d < minimum for w, d in zip(weights, raw))
    max_abs = max(abs(d) for d in applied)
    epsilon = min(1.0, EDGE_LIMIT_MV / max_abs) if max_abs else 0.0
    small = [epsilon * d for d in applied]
    assert max(abs(d) for d in small) <= EDGE_LIMIT_MV + 1e-12
    return small, {"raw_norm": norm(raw), "clipped_applied_norm": norm(applied),
                   "raw_below_min_edges": lower, "raw_above_max_edges": upper,
                   "small_epsilon": epsilon, "small_norm": norm(small),
                   "raw_update_mv": raw,
                   "clipped_applied_update_mv": applied,
                   "tested_small_update_mv": small}


def compare_directions(a: list[float], b: list[float]) -> dict:
    dot = sum(x*y for x, y in zip(a, b))
    na, nb = norm(a)["l2"], norm(b)["l2"]
    both_nonzero = [(x, y) for x, y in zip(a, b) if x != 0 and y != 0]
    return {"cosine_raw": dot / (na*nb) if na and nb else None,
            "opposite_sign_edges": sum(x*y < 0 for x, y in both_nonzero),
            "both_nonzero_edges": len(both_nonzero),
            "difference_norm": norm([x-y for x, y in zip(a, b)])}


def direction_probe(checkpoint: bytes, base_weights: list[float],
                    slots: tuple[int, ...], directions: dict[str, list[float]],
                    mode: str, stream_label: str, stream_seed_value: int | None) -> dict:
    variants = {}
    for name, delta in directions.items():
        session = TinyLaneSession.from_trusted_checkpoint_bytes(checkpoint)
        for slot, weight, shift in zip(slots, base_weights, delta):
            session.plasticity._weights[slot] = weight + shift
        if mode == "noise_on":
            session.training_notes = session.config.note_count
            session.config = replace(session.config, training_notes=session.config.note_count,
                                     plasticity_enabled=False)
            if stream_seed_value is not None:
                session.rng.setstate(random.Random(stream_seed_value).getstate())
        else:
            assert mode == "noise_off" and session.training_notes == 24
        action_start = len(session.game.result().actions)
        pulse_start = len(session.exploration_pulses)
        record = collect(session, action_start, pulse_start)
        record.pop("complete_summary")
        variants[name] = record
    reference = variants["no_update"]
    contrasts = {}
    for name in ("small_global", "small_context"):
        current = variants[name]
        contrasts[name] = {
            "delta_mean_utility": current["mean_utility"] - reference["mean_utility"],
            "delta_good_or_better": current["good_or_better"] - reference["good_or_better"],
            "delta_non_miss": current["non_miss"] - reference["non_miss"],
            "delta_utility_by_note": [a["utility"] - b["utility"]
                                      for a, b in zip(current["events"], reference["events"])],
        }
    return {"mode": mode, "stream": stream_label,
            "variants": variants, "contrasts_vs_no": contrasts}


def main() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert protocol["cue_gains"] == [0.75, 0.9, 1.0, 1.1, 1.25]
    assert protocol["sampling"]["estimation_repeats_per_gain"] == 32
    assert protocol["sampling"]["evaluation_repeats_per_gain"] == 32
    original_hashes = json.loads(ORIGINAL_META.read_text(encoding="utf-8"))["model_source_sha256"]
    for path, expected in original_hashes.items():
        assert digest(ROOT / path) == expected, f"model source changed: {path}"
    rows = [json.loads(line) for line in LEDGER.read_text(encoding="utf-8").splitlines()]
    row = next(r for r in rows if r["stage"] == "heldout"
               and r["condition"] == "on" and r["seed"] == 2013)
    session = replay_training(row)
    target = protocol["probe_note_index_zero_based"]
    assert target == session.resolved_count == 24
    assert session.config.cue_gain_by_note is not None
    checkpoint = session.checkpoint_bytes()
    slots = session.layout.plastic_slots
    weights = [session.plasticity.effective_weight(slot) for slot in slots]
    p = session.plasticity.parameters
    baseline = session.reward.predictor.expected_utility
    result = {
        "study_id": protocol["study_id"], "protocol_sha256": digest(PROTOCOL),
        "original_ledger_sha256": digest(LEDGER),
        "python": sys.version.split()[0],
        "source_sha256": {str(path.relative_to(ROOT)): digest(path)
                          for path in sorted((ROOT / "src/project_b").rglob("*.py"))},
        "checkpoint": {"seed": 2013, "note_index": target,
                       "time_us": session.simulator.current_time_us,
                       "next_note_time_us": session.note_times_us[target],
                       "original_next_gain": session.config.cue_gain_by_note[target],
                       "global_baseline": baseline, "eta": p.eta,
                       "weight_min_mv": p.w_min_mv, "weight_max_mv": p.w_max_mv,
                       "weight_by_plastic_slot_mv": weights,
                       "upper_bound_edges": sum(w == p.w_max_mv for w in weights)},
        "plastic_slots": list(slots),
        "contexts": [], "aggregate": {}, "direction_probes": [],
    }
    for gain in protocol["cue_gains"]:
        context = {"gain": gain, "estimation": [], "evaluation": []}
        for split, repeats in (("estimation", 32), ("evaluation", 32)):
            for repeat in range(repeats):
                seed = stream_seed(protocol["study_id"], "estimate" if split == "estimation"
                                   else "evaluate", gain, repeat)
                record = sample_once(checkpoint, gain, seed, target, slots)
                record["repeat"] = repeat
                context[split].append(record)
        context["moments"] = context_moments(
            context["estimation"], context["evaluation"], baseline, p.eta)
        result["contexts"].append(context)
        print(json.dumps({"gain": gain,
                          "estimate_mean_u": context["moments"]["estimate_mean_utility"],
                          "evaluate_mean_u": context["moments"]["evaluate_mean_utility"],
                          "evaluate_judgements": context["moments"]["evaluate_utility_counts"]}),
              flush=True)
    keys = ("covariance_term_mv", "global_drift_term_mv", "context_drift_term_mv",
            "global_proposed_update_mv", "context_proposed_update_mv")
    aggregate = {key: weighted_context_mean(result["contexts"], key) for key in keys}
    for key in keys:
        aggregate[key + "_norm"] = norm(aggregate[key])
    for context_name in ("global", "context"):
        raw = aggregate[context_name + "_proposed_update_mv"]
        small, geometry = clipped_direction(raw, weights, p.w_min_mv, p.w_max_mv)
        aggregate[context_name + "_direction_geometry"] = geometry
        aggregate["small_" + context_name + "_direction_mv"] = small
    aggregate["global_vs_context"] = compare_directions(
        aggregate["global_proposed_update_mv"],
        aggregate["context_proposed_update_mv"])
    for label, actual, covariance, drift in (
            ("global", "global_proposed_update_mv", "covariance_term_mv", "global_drift_term_mv"),
            ("context", "context_proposed_update_mv", "covariance_term_mv", "context_drift_term_mv")):
        error = max(abs(a-b-c) for a, b, c in zip(aggregate[actual],
                                                  aggregate[covariance], aggregate[drift]))
        assert error < 1e-12, label
    result["aggregate"] = aggregate
    directions = {"no_update": [0.0]*len(slots),
                  "small_global": aggregate["small_global_direction_mv"],
                  "small_context": aggregate["small_context_direction_mv"]}
    plans = [("noise_off", "inherited", None), ("noise_on", "inherited", None),
             ("noise_on", "seed_xor_324508639", 2013 ^ 324508639),
             ("noise_on", "seed_xor_610839776", 2013 ^ 610839776)]
    for mode, label, probe_seed in plans:
        probe = direction_probe(checkpoint, weights, slots, directions,
                                mode, label, probe_seed)
        result["direction_probes"].append(probe)
        print(json.dumps({"direction_probe": mode + "/" + label,
                          "utility": {name: value["mean_utility"]
                                      for name, value in probe["variants"].items()},
                          "good_plus": {name: value["good_or_better"]
                                        for name, value in probe["variants"].items()}}), flush=True)
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT}", flush=True)


if __name__ == "__main__":
    main()
