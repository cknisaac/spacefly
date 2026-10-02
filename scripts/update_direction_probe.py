"""Predeclared matched-checkpoint update-direction experiment C.

Diagnostic interventions only: production model code and training protocol stay
unchanged. Run from project root with PYTHONPATH=src, as a module.
"""

from __future__ import annotations

import bisect
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
from scripts.checkpoint_controls import summarize
from scripts.diagnose_mechanisms import config_from_record


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/update_direction_probe.json"
LEDGER = ROOT / "docs/figures/overnight_synthetic/runs.jsonl"
ORIGINAL_META = ROOT / "docs/figures/overnight_synthetic/meta.json"
OUTPUT = ROOT / "docs/figures/update_direction_probe.json"
INITIAL_WEIGHT_MV = 0.04
SMALL_LIMIT_MV = 0.1 * INITIAL_WEIGHT_MV
PROBE_START_NOTE = 24


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replay_training(row: dict) -> TinyLaneSession:
    session = TinyLaneSession(config_from_record(row))
    assert session.training_notes == 24
    while session.resolved_count < session.training_notes:
        session.step()
    assert session.simulator.current_time_us == session.feedback[-1].delivered_time_us
    for index, (saved, actual) in enumerate(zip(row["summary"]["events"][:24],
                                                session.feedback)):
        j = actual.reinforcement.judgement_record
        assert saved["note_index"] == index
        assert saved["judgement"] == j.judgement.name
        assert saved["hit_error_us"] == j.hit_error_us
        assert math.isclose(saved["rpe"], actual.reinforcement.prediction.rpe,
                            rel_tol=0, abs_tol=1e-12)
    return session


def last_update_geometry(session: TinyLaneSession) -> tuple[dict, dict[int, float], dict[int, float]]:
    slots = session.layout.plastic_slots
    final = {slot: session.plasticity.effective_weight(slot) for slot in slots}
    changes = {change.edge_slot: change for change in session.feedback[-1].weight_changes}
    before = {slot: changes[slot].previous_weight_mv if slot in changes else final[slot]
              for slot in slots}
    delta = {slot: final[slot] - before[slot] for slot in slots}
    p = session.plasticity.parameters
    t = session.simulator.current_time_us
    dopamine = session.feedback[-1].reinforcement.modulation.amplitude
    eligibility = {slot: session.plasticity.eligibility_at(slot, t) for slot in slots}
    raw = {slot: p.eta * eligibility[slot] * dopamine for slot in slots}
    proposed = {slot: before[slot] + raw[slot] for slot in slots}
    for slot in slots:
        expected = min(p.w_max_mv, max(p.w_min_mv, proposed[slot]))
        assert math.isclose(expected, final[slot], rel_tol=0, abs_tol=1e-12)
    max_applied = max(abs(v) for v in delta.values())
    assert max_applied > 0
    epsilon = min(1.0, SMALL_LIMIT_MV / max_applied)
    assert max(abs(epsilon * v) for v in delta.values()) <= SMALL_LIMIT_MV + 1e-12
    geometry = {
        "last_training_judgement": session.feedback[-1].reinforcement.judgement_record.judgement.name,
        "last_dopamine": dopamine,
        "changed_edges": len(changes),
        "max_abs_applied_delta_mv": max_applied,
        "max_abs_raw_delta_mv": max(abs(v) for v in raw.values()),
        "raw_delta_l1_mv": sum(abs(v) for v in raw.values()),
        "applied_delta_l1_mv": sum(abs(v) for v in delta.values()),
        "raw_proposed_below_min_edges": sum(v < p.w_min_mv for v in proposed.values()),
        "raw_proposed_above_max_edges": sum(v > p.w_max_mv for v in proposed.values()),
        "small_epsilon": epsilon,
        "max_abs_small_delta_mv": max(abs(epsilon * v) for v in delta.values()),
    }
    return geometry, before, delta


def collect(session: TinyLaneSession, action_start: int, pulse_start: int) -> dict:
    result = session.run()
    train = PROBE_START_NOTE
    events = []
    for index in range(train, session.config.note_count):
        j = result.judgements[index]
        r = result.feedback[index].reinforcement
        assert not result.feedback[index].weight_changes
        events.append({
            "note_index": index,
            "note_time_us": j.note_time_us,
            "judgement_time_us": j.event_time_us,
            "judgement": j.judgement.name,
            "utility": r.utility.utility,
            "hit_value": int(j.judgement),
            "hit_error_us": j.hit_error_us,
        })
    downs = []
    note_times = result.note_times_us
    for record in session.game.result().actions[action_start:]:
        if record.action.kind.value != "down":
            continue
        time_us = record.action.time_us
        position = bisect.bisect_left(note_times, time_us)
        choices = [i for i in (position - 1, position) if train <= i < len(note_times)]
        nearest = min(choices, key=lambda i: abs(note_times[i] - time_us)) if choices else None
        downs.append({
            "time_us": time_us,
            "disposition": record.disposition.value,
            "scored_note_id": record.note_id,
            "nearest_probe_note_index": nearest,
            "relative_nearest_note_us": time_us - note_times[nearest] if nearest is not None else None,
        })
    hits = [e for e in events if e["judgement"] != "MISS"]
    p = session.plasticity.parameters
    weights = [session.plasticity.effective_weight(slot) for slot in session.layout.plastic_slots]
    return {
        "mean_utility": statistics.mean(e["utility"] for e in events),
        "good_or_better": sum(e["hit_value"] >= 200 for e in events),
        "non_miss": len(hits),
        "judgement_counts": dict(Counter(e["judgement"] for e in events)),
        "hit_mean_signed_error_ms": statistics.mean(e["hit_error_us"] for e in hits) / 1000
        if hits else None,
        "hit_mean_absolute_error_ms": statistics.mean(abs(e["hit_error_us"]) for e in hits) / 1000
        if hits else None,
        "attempted_early_miss_count": sum(e["judgement"] == "MISS" and
                                         e["hit_error_us"] is not None and
                                         e["hit_error_us"] < 0 for e in events),
        "down_count": len(downs),
        "null_down_count": sum(a["disposition"] == "null_press" for a in downs),
        "exploration_pulses": len(session.exploration_pulses) - pulse_start,
        "lower_bound_edges": sum(w == p.w_min_mv for w in weights),
        "upper_bound_edges": sum(w == p.w_max_mv for w in weights),
        "weight_sum_mv": sum(weights),
        "events": events,
        "down_actions": downs,
        "complete_summary": summarize(result, train),
    }


def branch(checkpoint: bytes, before: dict[int, float], delta: dict[int, float],
           epsilon: float, name: str, mode: str, stream_seed: int | None) -> dict:
    session = TinyLaneSession.from_trusted_checkpoint_bytes(checkpoint)
    if name == "no_update":
        scale = 0.0
    elif name == "small_update":
        scale = epsilon
    elif name == "full_update":
        scale = 1.0
    else:
        raise ValueError(name)
    for slot in session.layout.plastic_slots:
        session.plasticity._weights[slot] = before[slot] + scale * delta[slot]
    if mode == "noise_off":
        assert session.training_notes == 24  # ordinary frozen-phase rule
    elif mode == "noise_on":
        session.training_notes = session.config.note_count
        session.config = replace(session.config, training_notes=session.config.note_count,
                                 plasticity_enabled=False)
        if stream_seed is not None:
            session.rng.setstate(random.Random(stream_seed).getstate())
    else:
        raise ValueError(mode)
    action_start = len(session.game.result().actions)
    pulse_start = len(session.exploration_pulses)
    output = collect(session, action_start, pulse_start)
    output.pop("complete_summary") if (mode != "noise_off" or name != "full_update") else None
    return output


def main() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert protocol["source_seeds"] == [2000, 2009, 2013]
    assert protocol["noise_stream_xor_constants"] == [324508639, 610839776]
    assert "0.004 mV/max_abs(d)" in protocol["small_rule"]
    original_hashes = json.loads(ORIGINAL_META.read_text(encoding="utf-8"))["model_source_sha256"]
    for relative_path, original_hash in original_hashes.items():
        assert digest(ROOT / relative_path) == original_hash, (
            f"model source changed since overnight study: {relative_path}")
    rows = [json.loads(line) for line in LEDGER.read_text(encoding="utf-8").splitlines()]
    result = {
        "study_id": protocol["study_id"],
        "protocol_sha256": digest(PROTOCOL),
        "original_ledger_sha256": digest(LEDGER),
        "python": sys.version.split()[0],
        "source_sha256": {str(p.relative_to(ROOT)): digest(p)
                          for p in sorted((ROOT / "src/project_b").rglob("*.py"))},
        "notes": "Selected cases from prior diagnosis; exploratory mechanism evidence, no held-out confirmation. Identical original map and time-indexed RNG draws within each mode/stream; endogenous cue after a resolved note can diverge.",
        "cases": [],
    }
    for seed in protocol["source_seeds"]:
        row = next(r for r in rows if r["stage"] == protocol["source_stage"]
                   and r["condition"] == protocol["source_condition"] and r["seed"] == seed)
        trained = replay_training(row)
        geometry, before, delta = last_update_geometry(trained)
        checkpoint = trained.checkpoint_bytes()
        cases = {"seed": seed, "checkpoint_time_us": trained.simulator.current_time_us,
                 "last_update_geometry": geometry, "probes": []}
        plans = [("noise_off", "inherited", None), ("noise_on", "inherited", None)]
        plans += [("noise_on", f"seed_xor_{constant}", seed ^ constant)
                  for constant in protocol["noise_stream_xor_constants"]]
        for mode, label, stream_seed in plans:
            variants = {}
            for name in protocol["branches"]:
                variants[name] = branch(checkpoint, before, delta, geometry["small_epsilon"],
                                        name, mode, stream_seed)
            if mode == "noise_off":
                assert variants["full_update"].pop("complete_summary") == row["summary"]
                for name in ("no_update", "small_update"):
                    assert "complete_summary" not in variants[name]
            reference = variants["no_update"]
            contrasts = {}
            for name in ("small_update", "full_update"):
                current = variants[name]
                contrasts[name] = {
                    "delta_mean_utility": current["mean_utility"] - reference["mean_utility"],
                    "delta_good_or_better": current["good_or_better"] - reference["good_or_better"],
                    "delta_non_miss": current["non_miss"] - reference["non_miss"],
                    "delta_null_down_count": current["null_down_count"] - reference["null_down_count"],
                    "delta_utility_by_note": [a["utility"] - b["utility"]
                                              for a, b in zip(current["events"], reference["events"])],
                    "delta_hit_error_us_by_note_where_both_attempted": [
                        (a["hit_error_us"] - b["hit_error_us"]
                         if a["hit_error_us"] is not None and b["hit_error_us"] is not None
                         else None)
                        for a, b in zip(current["events"], reference["events"])],
                }
            cases["probes"].append({"mode": mode, "stream": label,
                                    "variants": variants, "contrasts_vs_no": contrasts})
            print(json.dumps({"seed": seed, "mode": mode, "stream": label,
                              "epsilon": geometry["small_epsilon"],
                              "utility": {name: round(variants[name]["mean_utility"], 5)
                                          for name in protocol["branches"]},
                              "good_plus": {name: variants[name]["good_or_better"]
                                            for name in protocol["branches"]}}), flush=True)
        result["cases"].append(cases)
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT}", flush=True)


if __name__ == "__main__":
    main()
