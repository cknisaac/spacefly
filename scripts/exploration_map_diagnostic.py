"""Fixed-weight 2x2 exploration/map diagnostic at exact longitudinal checkpoints.

Run from the project root with PYTHONPATH=src:
    python -m scripts.exploration_map_diagnostic

No model source or trained weights are modified. One durable row is saved per
seed/checkpoint after all its branches complete; reruns skip completed rows.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import statistics
import sys
import time
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from project_b.experiments import TinyLaneSession
from project_b.osu import GameEnvironment, TapNote
from scripts.diagnose_mechanisms import config_from_record
from scripts.long_continuation import (
    SOURCE_LEDGER as ORIGINAL_LEDGER,
    atomic_json,
    event_record,
    game_metrics,
    make_extended_map,
    sha,
)


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/exploration_map_diagnostic.json"
LONG_PROTOCOL = ROOT / "configs/long_continuation.json"
LONG_DIRECTORY = ROOT / "docs/figures/long_continuation"
LONG_LEDGER = LONG_DIRECTORY / "runs.jsonl"
LONG_META = LONG_DIRECTORY / "meta.json"
OUTPUT = ROOT / "docs/figures/exploration_map_diagnostic"
META = OUTPUT / "meta.json"
LEDGER = OUTPUT / "runs.jsonl"
STATUS = OUTPUT / "status.json"
RESULT = OUTPUT / "result.json"
CHECKPOINTS = (24, 96, 384)
MAPS = ("common", "continuation")
ON_REPEATS = (0, 1, 2)


def stream_seed(study_id: str, seed: int, checkpoint: int, repeat: int) -> int:
    assert repeat in (1, 2)
    value = f"{study_id}|{seed}|{checkpoint}|{repeat}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(value).digest()[:8], "big")


def load_rows(path: Path) -> dict[int, dict]:
    rows = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("stage") == "heldout" and row["condition"] == "on":
            assert row["seed"] not in rows
            rows[row["seed"]] = row
    return rows


def load_long_rows() -> dict[int, dict]:
    rows = {}
    for line in LONG_LEDGER.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row["condition"] == "on":
            assert row["seed"] not in rows
            rows[row["seed"]] = row
    return rows


def continuation_map(original_config, seed: int, long_protocol: dict,
                     long_row: dict) -> tuple[tuple[int, ...], tuple[float, ...]]:
    extended_protocol = dict(long_protocol)
    extended_protocol["training_outcomes"] = 416
    times, gains = make_extended_map(original_config, seed, extended_protocol)
    assert list(times[:384]) == long_row["resolved_config"]["training_note_times_us"]
    assert list(gains[:384]) == long_row["resolved_config"]["training_cue_gains"]
    return times, gains


def make_probe(checkpoint: bytes, note_times: tuple[int, ...],
               gains: tuple[float, ...], exploration: bool,
               rng_seed: int | None) -> dict:
    session = TinyLaneSession.from_trusted_checkpoint_bytes(checkpoint)
    now = session.simulator.current_time_us
    assert len(note_times) == len(gains) == 32
    assert note_times[0] > now
    if rng_seed is not None:
        assert exploration
        session.rng = random.Random(rng_seed)
    training_notes = 32 if exploration else 0
    session.config = replace(session.config, note_count=32,
                             explicit_note_times_us=note_times,
                             cue_gain_by_note=gains,
                             training_notes=training_notes,
                             plasticity_enabled=False,
                             reward_utility_schedule=None)
    session.training_notes = training_notes
    session.note_times_us = note_times
    session.notes = tuple(TapNote(f"probe-{i}", 0, t)
                          for i, t in enumerate(note_times))
    game = GameEnvironment(session.notes)
    game.current_time_us = now
    game._key_down[0] = session.readout.key_down
    session.game = game
    session.resolved_count = 0
    session.next_note = 0
    session.feedback = []
    session.decisions = []
    session.exploration_pulses = []
    session.spike_counts = [0, 0, 0, 0]
    session.peak_queue = 0
    start_weights = tuple(session.plasticity.effective_weight(slot)
                          for slot in session.layout.plastic_slots)
    session.initial_weights = start_weights
    expiry = note_times[-1] + game.windows.expiry_offset_us
    dt = session.config.dt_us
    session.end_us = ((expiry + dt - 1) // dt) * dt
    completed = session.run()
    assert completed.final_plastic_weights_mv == start_weights
    assert all(not event.weight_changes for event in completed.feedback)
    if not exploration:
        assert not completed.exploration_pulses
    events = [event_record(session, i) for i in range(32)]
    actions = session.game.result().actions
    downs = [action for action in actions if action.action.kind.value == "down"]
    return {
        "exploration": exploration,
        "rng_seed": rng_seed,
        "uses_checkpoint_rng": rng_seed is None,
        "checkpoint_time_us": now,
        "relative_note_offsets_us": [t - now for t in note_times],
        "cue_gains": list(gains),
        "events": events,
        "down_actions": [{"time_us": a.action.time_us,
                          "relative_time_us": a.action.time_us - now,
                          "disposition": a.disposition.value,
                          "note_id": a.note_id}
                         for a in downs],
        "exploration_pulses_us": list(completed.exploration_pulses),
        "motor_spikes": completed.motor_spikes,
        "peak_queued_arrivals": completed.peak_queued_arrivals,
        "metrics": game_metrics(events, actions),
        "frozen_weight_sum_mv": sum(start_weights),
        "frozen_weight_upper_bound_edges": sum(
            w == session.plasticity.parameters.w_max_mv for w in start_weights),
    }


def assert_replay(session: TinyLaneSession, long_row: dict,
                  start: int, stop: int) -> None:
    expected_events = long_row["training_events"]
    for index in range(start, stop):
        actual = event_record(session, index)
        assert actual == expected_events[index], (session.config.seed, index)
    expected_checkpoint = long_row["checkpoints"][CHECKPOINTS.index(stop)]
    assert session.simulator.current_time_us == expected_checkpoint["checkpoint_time_us"]
    weights = [session.plasticity.effective_weight(slot)
               for slot in session.layout.plastic_slots]
    assert abs(sum(weights) - expected_checkpoint["plastic_weight_sum_mv"]) < 1e-9
    assert sum(w == session.plasticity.parameters.w_max_mv for w in weights) == expected_checkpoint["upper_bound_edges"]


def inspect_original_common(branch: dict, original: dict) -> None:
    assert branch["relative_note_offsets_us"] == original["relative_note_offsets_us"]
    assert branch["cue_gains"] == original["cue_gains"]
    assert branch["events"] == original["events"]
    assert branch["down_actions"] == original["down_actions"]
    assert branch["metrics"] == original["metrics"]


def run_checkpoint(session: TinyLaneSession, long_row: dict, checkpoint: int,
                   all_times: tuple[int, ...], all_gains: tuple[float, ...],
                   common: tuple[tuple[int, ...], tuple[float, ...]],
                   protocol: dict, protocol_sha: str, long_sha: str) -> dict:
    now = session.simulator.current_time_us
    source_index = CHECKPOINTS.index(checkpoint)
    common_times = tuple(now + offset for offset in common[0])
    continued_times = all_times[checkpoint:checkpoint + 32]
    continued_gains = all_gains[checkpoint:checkpoint + 32]
    assert len(continued_times) == len(continued_gains) == 32
    panels = {"common": (common_times, common[1]),
              "continuation": (continued_times, continued_gains)}
    snapshot = session.checkpoint_bytes()
    weight_sum = long_row["checkpoints"][source_index]["plastic_weight_sum_mv"]
    branches = {}
    rng_seeds = {str(repeat): (None if repeat == 0 else stream_seed(
        protocol["study_id"], session.config.seed, checkpoint, repeat))
        for repeat in ON_REPEATS}
    for map_name in MAPS:
        times, gains = panels[map_name]
        off = make_probe(snapshot, times, gains, False, None)
        if map_name == "common":
            inspect_original_common(off,
                long_row["checkpoints"][source_index]["probe"])
        on = []
        for repeat in ON_REPEATS:
            value = make_probe(snapshot, times, gains, True, rng_seeds[str(repeat)])
            value["repeat"] = repeat
            on.append(value)
        branches[map_name] = {"absolute_note_times_us": list(times),
                              "cue_gains": list(gains),
                              "off": off, "on": on}
    return {
        "key": f"{session.config.seed}:{checkpoint}",
        "seed": session.config.seed,
        "checkpoint": checkpoint,
        "checkpoint_time_us": now,
        "training_prefix_good_percent": 100 * sum(
            e["hit_value"] >= 200 for e in long_row["training_events"][:checkpoint]
        ) / checkpoint,
        "preceding_training_block_good_percent": long_row["checkpoints"][source_index]["training_block_metrics"]["good_or_better_percent"],
        "frozen_weight_sum_mv": weight_sum,
        "source_long_ledger_sha256": long_sha,
        "protocol_sha256": protocol_sha,
        "exploration_rng_seeds": rng_seeds,
        "branches": branches,
        "completed_utc": datetime.now(timezone.utc).isoformat(),
    }


def aggregate(rows: dict[str, dict], protocol: dict) -> dict:
    results = {}
    for checkpoint in CHECKPOINTS:
        item = {}
        for map_name in MAPS:
            off_values = []
            on_seed_means = []
            on_repeat_values = []
            paired_seed_differences = {}
            pulses = []
            for seed in protocol["seeds"]:
                branch = rows[f"{seed}:{checkpoint}"]["branches"][map_name]
                off = branch["off"]["metrics"]["good_or_better_percent"]
                on_values = [v["metrics"]["good_or_better_percent"]
                             for v in branch["on"]]
                off_values.append(off)
                on_seed_means.append(statistics.mean(on_values))
                on_repeat_values.extend(on_values)
                paired_seed_differences[str(seed)] = statistics.mean(on_values) - off
                pulses.extend(len(v["exploration_pulses_us"]) for v in branch["on"])
            item[map_name] = {
                "off_mean_good_percent": statistics.mean(off_values),
                "on_mean_good_percent_seed_then_stream": statistics.mean(on_seed_means),
                "on_all_stream_good_percent": on_repeat_values,
                "on_minus_off_mean_good_percentage_points": statistics.mean(on_seed_means) - statistics.mean(off_values),
                "on_minus_off_per_seed_percentage_points": paired_seed_differences,
                "mean_on_exploration_pulses_per_32_notes": statistics.mean(pulses),
            }
        item["continuation_minus_common_off_percentage_points"] = (
            item["continuation"]["off_mean_good_percent"] -
            item["common"]["off_mean_good_percent"])
        item["continuation_minus_common_on_percentage_points"] = (
            item["continuation"]["on_mean_good_percent_seed_then_stream"] -
            item["common"]["on_mean_good_percent_seed_then_stream"])
        results[str(checkpoint)] = item
    return {"study_id": protocol["study_id"], "status": "complete",
            "seeds": protocol["seeds"], "checkpoints": results,
            "branch_count": len(protocol["seeds"]) * len(CHECKPOINTS) *
                            len(MAPS) * (1 + len(ON_REPEATS)),
            "note_outcomes": len(protocol["seeds"]) * len(CHECKPOINTS) *
                             len(MAPS) * (1 + len(ON_REPEATS)) * 32}


def main() -> None:
    protocol_raw = PROTOCOL.read_bytes()
    protocol = json.loads(protocol_raw)
    assert protocol["seeds"] == list(range(2000, 2008))
    assert protocol["checkpoints_after_training_outcomes"] == list(CHECKPOINTS)
    assert protocol["notes_per_branch"] == 32
    protocol_sha = hashlib.sha256(protocol_raw).hexdigest()
    long_sha = sha(LONG_LEDGER)
    long_meta = json.loads(LONG_META.read_text(encoding="utf-8"))
    long_protocol = json.loads(LONG_PROTOCOL.read_text(encoding="utf-8"))
    assert long_meta["protocol_sha256"] == sha(LONG_PROTOCOL)
    for relative, expected in long_meta["model_source_sha256"].items():
        assert sha(ROOT / relative) == expected, relative
    original_rows = load_rows(ORIGINAL_LEDGER)
    long_rows = load_long_rows()
    assert set(protocol["seeds"]) <= original_rows.keys() & long_rows.keys()
    common = (tuple(long_meta["probe_relative_note_offsets_us"]),
              tuple(long_meta["probe_cue_gains"]))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if META.exists():
        meta = json.loads(META.read_text(encoding="utf-8"))
        assert meta["protocol_sha256"] == protocol_sha
        assert meta["source_long_ledger_sha256"] == long_sha
    else:
        meta = {"study_id": protocol["study_id"],
                "started_utc": datetime.now(timezone.utc).isoformat(),
                "started_unix": time.time(),
                "python": sys.version.split()[0],
                "protocol_sha256": protocol_sha,
                "source_long_ledger_sha256": long_sha,
                "source_long_meta_sha256": sha(LONG_META),
                "source_original_ledger_sha256": sha(ORIGINAL_LEDGER),
                "model_source_sha256": long_meta["model_source_sha256"],
                "common_relative_note_offsets_us": list(common[0]),
                "common_cue_gains": list(common[1]),
                "synthetic_topology": "build_tiny_brain; no imported connectome"}
        atomic_json(META, meta)
    rows = {}
    if LEDGER.exists():
        for line in LEDGER.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            assert row["protocol_sha256"] == protocol_sha
            assert row["source_long_ledger_sha256"] == long_sha
            assert row["key"] not in rows
            rows[row["key"]] = row
    planned = len(protocol["seeds"]) * len(CHECKPOINTS)
    for seed in protocol["seeds"]:
        if all(f"{seed}:{c}" in rows for c in CHECKPOINTS):
            continue
        original = config_from_record(original_rows[seed])
        long_row = long_rows[seed]
        times, gains = continuation_map(original, seed, long_protocol, long_row)
        config = replace(original, note_count=384, training_notes=384,
                         explicit_note_times_us=times[:384],
                         cue_gain_by_note=gains[:384])
        assert config.readout_on_threshold == long_row["resolved_config"]["readout_on_threshold"]
        assert config.plasticity_eta == long_row["resolved_config"]["plasticity_eta"]
        assert config.exploration_probability == long_row["resolved_config"]["exploration_probability"]
        session = TinyLaneSession(config)
        previous = 0
        for checkpoint in CHECKPOINTS:
            while session.resolved_count < checkpoint:
                session.step()
            assert session.resolved_count == checkpoint
            assert_replay(session, long_row, previous, checkpoint)
            previous = checkpoint
            key = f"{seed}:{checkpoint}"
            if key in rows:
                continue
            if time.time() - meta["started_unix"] >= protocol["runtime_cap_seconds"]:
                atomic_json(STATUS, {"status": "budget_exhausted", "completed": len(rows),
                                     "planned": planned, "next_key": key})
                return
            atomic_json(STATUS, {"status": "running", "completed": len(rows),
                                 "planned": planned, "current_key": key})
            row = run_checkpoint(session, long_row, checkpoint, times, gains,
                                 common, protocol, protocol_sha, long_sha)
            with LEDGER.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(row, separators=(",", ":")) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            rows[key] = row
            atomic_json(STATUS, {"status": "running", "completed": len(rows),
                                 "planned": planned, "last_key": key})
            print(json.dumps({"completed": len(rows), "planned": planned,
                              "key": key,
                              "common_off_good": row["branches"]["common"]["off"]["metrics"]["good_or_better_percent"],
                              "common_on_good": [v["metrics"]["good_or_better_percent"] for v in row["branches"]["common"]["on"]],
                              "continuation_off_good": row["branches"]["continuation"]["off"]["metrics"]["good_or_better_percent"],
                              "continuation_on_good": [v["metrics"]["good_or_better_percent"] for v in row["branches"]["continuation"]["on"]]}),
                  flush=True)
    result = aggregate(rows, protocol)
    atomic_json(RESULT, result)
    atomic_json(STATUS, {"status": "complete", "completed": len(rows),
                         "planned": planned,
                         "finished_utc": datetime.now(timezone.utc).isoformat()})
    print(json.dumps({"status": "complete", "completed": len(rows),
                      "planned": planned}), flush=True)


if __name__ == "__main__":
    main()
