"""Isolated, resumable long-horizon synthetic experiment; no parameter search.

Run from the project root with PYTHONPATH=src:
    python -m scripts.long_continuation

Training sessions retain all state and weights across 384 outcomes. Each
checkpoint is cloned onto one fixed, disjoint 32-note probe map and frozen.
Only finished condition runs enter the durable JSONL ledger.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import statistics
import sys
import time
from collections import Counter
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from project_b.experiments import TinyBrainConfig, TinyLaneSession
from project_b.osu import GameEnvironment, TapNote
from scripts.checkpoint_controls import shuffled_utilities
from scripts.diagnose_mechanisms import config_from_record


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/long_continuation.json"
SOURCE_LEDGER = ROOT / "docs/figures/overnight_synthetic/runs.jsonl"
SOURCE_META = ROOT / "docs/figures/overnight_synthetic/meta.json"
OUTPUT = ROOT / "docs/figures/long_continuation"
LEDGER = OUTPUT / "runs.jsonl"
META = OUTPUT / "meta.json"
STATUS = OUTPUT / "status.json"
RESULT = OUTPUT / "result.json"
CONDITIONS = ("on", "off", "shuffled")
CHECKPOINTS = (24, 96, 384)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def load_source_rows() -> dict[tuple[int, str], dict]:
    result = {}
    for line in SOURCE_LEDGER.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row["stage"] == "heldout":
            key = (row["seed"], row["condition"])
            assert key not in result
            result[key] = row
    return result


def make_extended_map(original: TinyBrainConfig, seed: int, protocol: dict) -> tuple[tuple[int, ...], tuple[float, ...]]:
    assert original.explicit_note_times_us is not None
    assert original.cue_gain_by_note is not None
    assert len(original.explicit_note_times_us) == len(original.cue_gain_by_note) == 40
    settings = protocol["training_map"]
    rng = random.Random(seed ^ settings["extension_seed_xor"])
    times = list(original.explicit_note_times_us)
    gains = list(original.cue_gain_by_note)
    for _ in range(40, protocol["training_outcomes"]):
        times.append(times[-1] + rng.choice(settings["note_interval_ms_choices"]) * 1000)
        gains.append(rng.choice(settings["cue_gain_choices"]))
    assert tuple(times[:40]) == original.explicit_note_times_us
    assert tuple(gains[:40]) == original.cue_gain_by_note
    return tuple(times), tuple(gains)


def make_probe_panel(protocol: dict) -> tuple[tuple[int, ...], tuple[float, ...]]:
    p = protocol["probe_panel"]
    settings = protocol["training_map"]
    rng = random.Random(p["seed"])
    offsets = [p["first_note_after_checkpoint_us"]]
    for _ in range(p["note_count"] - 1):
        offsets.append(offsets[-1] + rng.choice(settings["note_interval_ms_choices"]) * 1000)
    gains = tuple(rng.choice(settings["cue_gain_choices"]) for _ in offsets)
    return tuple(offsets), gains


def make_schedule(on_utilities: tuple[float, ...], seed: int) -> tuple[float, ...]:
    assert len(on_utilities) == CHECKPOINTS[-1]
    schedule = []
    for start, stop in zip((0,) + CHECKPOINTS[:-1], CHECKPOINTS):
        block = on_utilities[start:stop]
        schedule.extend(shuffled_utilities(block, seed ^ start))
        assert sorted(schedule[start:stop]) == sorted(block)
    return tuple(schedule)


def event_record(session: TinyLaneSession, index: int) -> dict:
    feedback = session.feedback[index]
    reinforcement = feedback.reinforcement
    judgement = reinforcement.judgement_record
    return {"note_index": index, "note_time_us": judgement.note_time_us,
            "judgement_time_us": judgement.event_time_us,
            "delivered_time_us": feedback.delivered_time_us,
            "judgement": judgement.judgement.name,
            "hit_error_us": judgement.hit_error_us,
            "hit_value": int(judgement.judgement),
            "game_utility": reinforcement.utility.utility,
            "learning_utility": reinforcement.learning_utility,
            "expected_utility_before": reinforcement.prediction.expected_before,
            "rpe": reinforcement.prediction.rpe,
            "actual_minus_expected": (reinforcement.utility.utility
                                      - reinforcement.prediction.expected_before),
            "dopamine_like_amplitude": reinforcement.modulation.amplitude,
            "weight_changes": len(feedback.weight_changes)}


def update_capture(session: TinyLaneSession, records: dict[int, dict]):
    original = session.simulator.apply_dopamine
    slots = session.layout.plastic_slots
    p = session.plasticity.parameters

    def capture(dopamine: float):
        index = session.resolved_count
        t = session.simulator.current_time_us
        before = [session.plasticity.effective_weight(slot) for slot in slots]
        eligibility = [session.plasticity.eligibility_at(slot, t) for slot in slots]
        raw = [p.eta * e * dopamine for e in eligibility]
        proposed = [w + d for w, d in zip(before, raw)]
        expected = [min(p.w_max_mv, max(p.w_min_mv, w)) for w in proposed]
        changes = original(dopamine)
        after = [session.plasticity.effective_weight(slot) for slot in slots]
        assert max(abs(a-b) for a, b in zip(after, expected)) < 1e-12
        applied = [a-b for a, b in zip(after, before)]
        assert index not in records
        records[index] = {
            "note_index": index, "time_us": t, "dopamine": dopamine,
            "raw_l1_mv": sum(abs(v) for v in raw),
            "raw_l2_mv": math.sqrt(sum(v*v for v in raw)),
            "raw_max_abs_mv": max(abs(v) for v in raw),
            "applied_l1_mv": sum(abs(v) for v in applied),
            "applied_l2_mv": math.sqrt(sum(v*v for v in applied)),
            "applied_max_abs_mv": max(abs(v) for v in applied),
            "proposed_below_min_edges": sum(v < p.w_min_mv for v in proposed),
            "proposed_above_max_edges": sum(v > p.w_max_mv for v in proposed),
            "lower_bound_edges_after": sum(v == p.w_min_mv for v in after),
            "upper_bound_edges_after": sum(v == p.w_max_mv for v in after),
            "changed_edges": len(changes),
        }
        return changes

    session.simulator.apply_dopamine = capture
    return capture


def checkpoint_bytes(session: TinyLaneSession, capture) -> bytes:
    if capture is not None:
        del session.simulator.apply_dopamine
    data = session.checkpoint_bytes()
    if capture is not None:
        session.simulator.apply_dopamine = capture
    return data


def action_counts(actions) -> dict:
    downs = [record for record in actions if record.action.kind.value == "down"]
    counts = Counter(record.disposition.value for record in downs)
    return {"down_count": len(downs), "null_down_count": counts["null_press"],
            "hit_down_count": counts["hit"],
            "early_miss_down_count": counts["early_miss"],
            "dispositions": dict(counts)}


def game_metrics(events: list[dict], actions) -> dict:
    assert events
    hits = [e for e in events if e["judgement"] != "MISS"]
    return {
        "note_count": len(events),
        "good_or_better_count": sum(e["hit_value"] >= 200 for e in events),
        "good_or_better_percent": 100 * sum(e["hit_value"] >= 200 for e in events) / len(events),
        "non_miss_count": len(hits),
        "mean_utility": statistics.mean(e["game_utility"] for e in events),
        "mean_learning_utility": statistics.mean(e["learning_utility"] for e in events),
        "mean_expected_utility_before": statistics.mean(e["expected_utility_before"] for e in events),
        "mean_signed_rpe": statistics.mean(e["rpe"] for e in events),
        "mean_abs_rpe": statistics.mean(abs(e["rpe"]) for e in events),
        "mean_actual_minus_expected": statistics.mean(e["actual_minus_expected"] for e in events),
        "mean_abs_actual_minus_expected": statistics.mean(abs(e["actual_minus_expected"]) for e in events),
        "hit_mean_signed_error_ms": (statistics.mean(e["hit_error_us"] for e in hits) / 1000
                                     if hits else None),
        "hit_mean_absolute_error_ms": (statistics.mean(abs(e["hit_error_us"]) for e in hits) / 1000
                                       if hits else None),
        "attempted_early_miss_count": sum(e["judgement"] == "MISS"
                                          and e["hit_error_us"] is not None
                                          and e["hit_error_us"] < 0 for e in events),
        "judgement_counts": dict(Counter(e["judgement"] for e in events)),
        **action_counts(actions),
    }


def frozen_probe(checkpoint: bytes, offsets: tuple[int, ...],
                 gains: tuple[float, ...]) -> dict:
    session = TinyLaneSession.from_trusted_checkpoint_bytes(checkpoint)
    t = session.simulator.current_time_us
    dt = session.config.dt_us
    note_times = tuple(t + offset for offset in offsets)
    session.config = replace(session.config, note_count=len(note_times),
                             explicit_note_times_us=note_times,
                             cue_gain_by_note=gains, training_notes=0,
                             plasticity_enabled=False,
                             reward_utility_schedule=None)
    session.training_notes = 0
    session.note_times_us = note_times
    session.notes = tuple(TapNote(f"probe-{i}", 0, note_time)
                          for i, note_time in enumerate(note_times))
    game = GameEnvironment(session.notes)
    game.current_time_us = t
    game._key_down[0] = session.readout.key_down
    session.game = game
    session.resolved_count = 0
    session.next_note = 0
    session.feedback = []
    session.decisions = []
    session.exploration_pulses = []
    session.spike_counts = [0, 0, 0, 0]
    session.peak_queue = 0
    session.initial_weights = tuple(session.plasticity.effective_weight(slot)
                                    for slot in session.layout.plastic_slots)
    last_expiry = note_times[-1] + game.windows.expiry_offset_us
    session.end_us = ((last_expiry + dt - 1) // dt) * dt
    frozen_start = session.initial_weights
    result = session.run()
    assert result.final_plastic_weights_mv == frozen_start
    assert len(result.exploration_pulses) == 0
    assert all(not feedback.weight_changes for feedback in result.feedback)
    events = [event_record(session, i) for i in range(len(note_times))]
    actions = session.game.result().actions
    return {"checkpoint_time_us": t,
            "relative_note_offsets_us": list(offsets),
            "cue_gains": list(gains),
            "events": events,
            "down_actions": [{"time_us": record.action.time_us,
                              "relative_time_us": record.action.time_us - t,
                              "disposition": record.disposition.value,
                              "note_id": record.note_id}
                             for record in actions if record.action.kind.value == "down"],
            "metrics": game_metrics(events, actions),
            "initial_upper_bound_edges": sum(w == session.plasticity.parameters.w_max_mv
                                              for w in frozen_start)}


def inspect_prefix(session: TinyLaneSession, original_row: dict, n: int) -> None:
    saved = original_row["summary"]["events"][:n]
    assert len(saved) == n
    for index, item in enumerate(saved):
        actual = event_record(session, index)
        for key in ("judgement", "hit_error_us", "game_utility", "learning_utility", "rpe", "weight_changes"):
            assert actual[key] == item[key], (session.config.seed, index, key,
                                               actual[key], item[key])


def run_condition(config: TinyBrainConfig, source_row: dict, panel: tuple,
                  condition: str, protocol_sha: str, source_sha: str,
                  expected_schedule: tuple[float, ...] | None) -> dict:
    session = TinyLaneSession(config)
    diagnostics: dict[int, dict] = {}
    capture = update_capture(session, diagnostics) if config.plasticity_enabled else None
    checkpoints = []
    action_start = 0
    feedback_start = 0
    pulse_start = 0
    for milestone in CHECKPOINTS:
        while session.resolved_count < milestone:
            session.step()
        assert session.resolved_count == milestone
        if milestone == 24:
            inspect_prefix(session, source_row, 24)
        checkpoint = checkpoint_bytes(session, capture)
        current_actions = session.game.result().actions
        block_events = [event_record(session, index)
                        for index in range(feedback_start, milestone)]
        block_updates = [diagnostics[index] for index in range(feedback_start, milestone)] if capture is not None else []
        weights = [session.plasticity.effective_weight(slot)
                   for slot in session.layout.plastic_slots]
        p = session.plasticity.parameters
        probe = frozen_probe(checkpoint, panel[0], panel[1])
        checkpoints.append({
            "after_training_outcomes": milestone,
            "checkpoint_time_us": session.simulator.current_time_us,
            "training_block_start_index": feedback_start,
            "training_block_events": block_events,
            "training_block_metrics": game_metrics(block_events, current_actions[action_start:]),
            "training_block_update_raw_l1_mv": sum(u["raw_l1_mv"] for u in block_updates),
            "training_block_update_applied_l1_mv": sum(u["applied_l1_mv"] for u in block_updates),
            "training_block_clipped_low_edge_events": sum(u["proposed_below_min_edges"] for u in block_updates),
            "training_block_clipped_high_edge_events": sum(u["proposed_above_max_edges"] for u in block_updates),
            "training_block_exploration_pulses": len(session.exploration_pulses) - pulse_start,
            "expected_utility_at_checkpoint": session.reward.predictor.expected_utility,
            "plastic_weight_sum_mv": sum(weights),
            "plastic_weight_min_mv": min(weights),
            "plastic_weight_max_mv": max(weights),
            "lower_bound_edges": sum(w == p.w_min_mv for w in weights),
            "upper_bound_edges": sum(w == p.w_max_mv for w in weights),
            "probe": probe,
        })
        action_start = len(current_actions)
        feedback_start = milestone
        pulse_start = len(session.exploration_pulses)
        print(json.dumps({"seed": config.seed, "condition": condition,
                          "checkpoint": milestone,
                          "probe_good_percent": probe["metrics"]["good_or_better_percent"],
                          "probe_mean_utility": probe["metrics"]["mean_utility"],
                          "upper_bound_edges": checkpoints[-1]["upper_bound_edges"]}),
              flush=True)
    if capture is not None:
        del session.simulator.apply_dopamine
    assert len(session.feedback) == CHECKPOINTS[-1]
    all_events = [event_record(session, i) for i in range(CHECKPOINTS[-1])]
    if expected_schedule is not None:
        assert tuple(e["learning_utility"] for e in all_events) == expected_schedule
    if condition == "off":
        assert not diagnostics
        assert all(not feedback.weight_changes for feedback in session.feedback)
    else:
        assert len(diagnostics) == CHECKPOINTS[-1]
    return {"key": f"{config.seed}:{condition}", "seed": config.seed,
            "condition": condition, "protocol_sha256": protocol_sha,
            "original_source_ledger_sha256": source_sha,
            "resolved_config": {
                "note_count": config.note_count,
                "training_notes": config.training_notes,
                "readout_on_threshold": config.readout_on_threshold,
                "plasticity_eta": config.plasticity_eta,
                "exploration_probability": config.exploration_probability,
                "dt_us": config.dt_us,
                "plasticity_enabled": config.plasticity_enabled,
                "training_note_times_us": list(config.explicit_note_times_us),
                "training_cue_gains": list(config.cue_gain_by_note),
                "reward_utility_schedule": list(config.reward_utility_schedule)
                if config.reward_utility_schedule is not None else None},
            "training_events": all_events,
            "update_diagnostics": [diagnostics[i] for i in range(CHECKPOINTS[-1])]
            if diagnostics else [],
            "checkpoints": checkpoints,
            "completed_utc": datetime.now(timezone.utc).isoformat()}


def aggregate(rows: dict[str, dict], protocol: dict) -> dict:
    seeds = protocol["seeds"]
    by_checkpoint = {}
    for milestone in CHECKPOINTS:
        summaries = {}
        for condition in CONDITIONS:
            values = [rows[f"{seed}:{condition}"]["checkpoints"][CHECKPOINTS.index(milestone)]
                      for seed in seeds]
            metrics = [item["probe"]["metrics"] for item in values]
            summaries[condition] = {
                "mean_good_or_better_percent": statistics.mean(m["good_or_better_percent"] for m in metrics),
                "mean_non_miss_percent": statistics.mean(100*m["non_miss_count"]/m["note_count"] for m in metrics),
                "mean_utility": statistics.mean(m["mean_utility"] for m in metrics),
                "mean_null_downs_per_probe": statistics.mean(m["null_down_count"] for m in metrics),
                "mean_upper_bound_edges": statistics.mean(item["upper_bound_edges"] for item in values),
                "per_seed": {str(seed): {"good_or_better_percent": metric["good_or_better_percent"],
                                        "mean_utility": metric["mean_utility"],
                                        "non_miss_count": metric["non_miss_count"],
                                        "hit_mean_absolute_error_ms": metric["hit_mean_absolute_error_ms"],
                                        "null_down_count": metric["null_down_count"],
                                        "upper_bound_edges": value["upper_bound_edges"]}
                             for seed, metric, value in zip(seeds, metrics, values)},
            }
        paired = {}
        for control in ("off", "shuffled"):
            good_deltas = [summaries["on"]["per_seed"][str(seed)]["good_or_better_percent"]
                           - summaries[control]["per_seed"][str(seed)]["good_or_better_percent"]
                           for seed in seeds]
            utility_deltas = [summaries["on"]["per_seed"][str(seed)]["mean_utility"]
                              - summaries[control]["per_seed"][str(seed)]["mean_utility"]
                              for seed in seeds]
            paired[control] = {"mean_good_advantage_percentage_points": statistics.mean(good_deltas),
                               "strict_good_win_seeds": sum(v > 0 for v in good_deltas),
                               "tie_seeds": sum(v == 0 for v in good_deltas),
                               "loss_seeds": sum(v < 0 for v in good_deltas),
                               "mean_utility_advantage": statistics.mean(utility_deltas),
                               "per_seed_good_advantage_percentage_points":
                               {str(seed): diff for seed, diff in zip(seeds, good_deltas)}}
        by_checkpoint[str(milestone)] = {"conditions": summaries, "paired": paired}
    trends = {str(seed): {
        condition: [by_checkpoint[str(milestone)]["conditions"][condition]["per_seed"][str(seed)]
                    for milestone in CHECKPOINTS]
        for condition in CONDITIONS} for seed in seeds}
    return {"study_id": protocol["study_id"], "status": "complete",
            "seed_count": len(seeds), "seeds": seeds,
            "probe_note_count": protocol["probe_panel"]["note_count"],
            "training_outcomes_per_condition": CHECKPOINTS[-1],
            "checkpoints": by_checkpoint,
            "seed_trajectories": trends,
            "limitations": "Diagnostic selected seeds from prior held-out data; 24 independent condition runs, not a 32-seed confirmatory M2 gate. Frozen clones never affect training."}


def main() -> None:
    protocol_raw = PROTOCOL.read_bytes()
    protocol = json.loads(protocol_raw)
    assert protocol["seeds"] == list(range(2000, 2008))
    assert protocol["conditions"] == list(CONDITIONS)
    assert protocol["checkpoints"] == list(CHECKPOINTS)
    assert protocol["training_outcomes"] == CHECKPOINTS[-1]
    protocol_sha = hashlib.sha256(protocol_raw).hexdigest()
    source_sha = sha(SOURCE_LEDGER)
    source_meta = json.loads(SOURCE_META.read_text(encoding="utf-8"))
    for relative, expected in source_meta["model_source_sha256"].items():
        assert sha(ROOT / relative) == expected, f"source changed since original: {relative}"
    model_hashes = {str(path.relative_to(ROOT)): sha(path)
                    for path in sorted((ROOT / "src/project_b").rglob("*.py"))}
    panel = make_probe_panel(protocol)
    source_rows = load_source_rows()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if META.exists():
        meta = json.loads(META.read_text(encoding="utf-8"))
        assert meta["protocol_sha256"] == protocol_sha
        assert meta["source_ledger_sha256"] == source_sha
        assert meta["model_source_sha256"] == model_hashes
    else:
        meta = {"study_id": protocol["study_id"], "status": "running",
                "started_utc": datetime.now(timezone.utc).isoformat(),
                "started_unix": time.time(), "python": sys.version.split()[0],
                "protocol_sha256": protocol_sha,
                "source_ledger_sha256": source_sha,
                "model_source_sha256": model_hashes,
                "probe_relative_note_offsets_us": list(panel[0]),
                "probe_cue_gains": list(panel[1]),
                "synthetic_topology": "build_tiny_brain, no imported connectome"}
        atomic_json(META, meta)
    rows = {}
    if LEDGER.exists():
        for line in LEDGER.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            assert row["protocol_sha256"] == protocol_sha
            assert row["original_source_ledger_sha256"] == source_sha
            assert row["key"] not in rows
            rows[row["key"]] = row
    planned = len(protocol["seeds"]) * len(CONDITIONS)
    deadline = meta["started_unix"] + 21600
    for seed in protocol["seeds"]:
        original = config_from_record(source_rows[(seed, "on")])
        times, gains = make_extended_map(original, seed, protocol)
        base = replace(original, note_count=CHECKPOINTS[-1],
                       training_notes=CHECKPOINTS[-1],
                       explicit_note_times_us=times, cue_gain_by_note=gains)
        assert base.readout_on_threshold == 10
        for condition in CONDITIONS:
            key = f"{seed}:{condition}"
            if key in rows:
                continue
            if time.time() >= deadline:
                atomic_json(STATUS, {"status": "budget_exhausted", "completed": len(rows),
                                     "planned": planned, "next_key": key})
                return
            schedule = None
            if condition == "on":
                config = base
            elif condition == "off":
                config = replace(base, plasticity_enabled=False)
            else:
                on_row = rows[f"{seed}:on"]
                on_utilities = tuple(e["game_utility"] for e in on_row["training_events"])
                schedule = make_schedule(on_utilities, seed)
                assert tuple(schedule[:24]) == tuple(
                    source_rows[(seed, "shuffled")]["resolved_config"]["reward_utility_schedule"])
                config = replace(base, reward_utility_schedule=schedule)
            atomic_json(STATUS, {"status": "running", "completed": len(rows),
                                 "planned": planned, "current_key": key,
                                 "started_condition_utc": datetime.now(timezone.utc).isoformat()})
            row = run_condition(config, source_rows[(seed, condition)], panel,
                                condition, protocol_sha, source_sha, schedule)
            with LEDGER.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(row, separators=(",", ":")) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            rows[key] = row
            atomic_json(STATUS, {"status": "running", "completed": len(rows),
                                 "planned": planned, "last_key": key})
            print(json.dumps({"condition_complete": key,
                              "completed": len(rows), "planned": planned}), flush=True)
    summary = aggregate(rows, protocol)
    atomic_json(RESULT, summary)
    atomic_json(STATUS, {"status": "complete", "completed": len(rows),
                         "planned": planned, "finished_utc": datetime.now(timezone.utc).isoformat()})
    print(json.dumps({"status": "complete", "completed": len(rows),
                      "planned": planned}), flush=True)


if __name__ == "__main__":
    main()
