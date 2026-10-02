"""Predeclared short-window synthetic update-interference diagnostic.

Replays unchanged production training, probes cloned states, and optionally
skips one qualifying update in a matched counterfactual. No model edits.
"""

from __future__ import annotations

import bisect
import hashlib
import json
import math
import os
import statistics
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from project_b.experiments import TinyLaneSession
from scripts.diagnose_mechanisms import config_from_record
from scripts.exploration_map_diagnostic import (
    assert_replay, continuation_map, inspect_original_common,
    load_long_rows, load_rows, make_probe,
)
from scripts.long_continuation import atomic_json, event_record, sha
from scripts.update_direction_magnitude_diagnostic import geometry
from scripts.weight_rollback_diagnostic import PERMITTED_REPLAY_SOURCE_DRIFT


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/successive_update_interference_diagnostic.json"
LONG_PROTOCOL = ROOT / "configs/long_continuation.json"
LONG_LEDGER = ROOT / "docs/figures/long_continuation/runs.jsonl"
LONG_META = ROOT / "docs/figures/long_continuation/meta.json"
ORIGINAL_LEDGER = ROOT / "docs/figures/overnight_synthetic/runs.jsonl"
OUT = ROOT / "docs/figures/successive_update_interference"
LEDGER = OUT / "runs.jsonl"
META = OUT / "meta.json"
STATUS = OUT / "status.json"
COUNTERFACTUAL = OUT / "counterfactual.json"


def canonical_hash(data: bytes) -> str:
    loaded = TinyLaneSession.from_trusted_checkpoint_bytes(data)
    return hashlib.sha256(loaded.checkpoint_bytes()).hexdigest()


def make_config(seed: int, originals: dict, long_rows: dict,
                long_protocol: dict):
    original = config_from_record(originals[seed])
    times, gains = continuation_map(original, seed, long_protocol, long_rows[seed])
    return replace(original, note_count=384, training_notes=384,
                   explicit_note_times_us=times[:384],
                   cue_gain_by_note=gains[:384])


def weights(session: TinyLaneSession) -> list[float]:
    return [session.plasticity.effective_weight(slot)
            for slot in session.layout.plastic_slots]


def update_record(session: TinyLaneSession, dopamine: float, changes,
                  before: dict, after: list[float], saved: dict) -> dict:
    prior = before["weights_before_mv"]
    raw = before["raw_proposed_update_mv"]
    applied = [new - old for new, old in zip(after, prior)]
    p = session.plasticity.parameters
    assert len(raw) == len(applied) == len(prior) == 480
    assert before["time_us"] == saved["time_us"]
    assert dopamine == saved["dopamine"]
    assert len(changes) == saved["changed_edges"]
    assert len(before["proposed_below_min_slots"]) == saved["proposed_below_min_edges"]
    assert len(before["proposed_above_max_slots"]) == saved["proposed_above_max_edges"]
    scalars = {"raw_l1_mv": sum(abs(x) for x in raw),
               "raw_l2_mv": math.sqrt(sum(x*x for x in raw)),
               "raw_max_abs_mv": max(abs(x) for x in raw),
               "applied_l1_mv": sum(abs(x) for x in applied),
               "applied_l2_mv": math.sqrt(sum(x*x for x in applied)),
               "applied_max_abs_mv": max(abs(x) for x in applied)}
    for name, value in scalars.items():
        assert math.isclose(value, saved[name], rel_tol=0, abs_tol=1e-9), name
    clipped_slots = [slot for slot, r, a in zip(before["edge_slots"], raw, applied)
                     if not math.isclose(r, a, rel_tol=0, abs_tol=1e-12)]
    assert all(math.isclose(new, min(p.w_max_mv, max(p.w_min_mv, old + r)),
                            rel_tol=0, abs_tol=1e-12)
               for new, old, r in zip(after, prior, raw))
    return {**before,
            "applied_update_mv": applied,
            "weights_after_mv": after,
            "applied_l1_mv": scalars["applied_l1_mv"],
            "applied_l2_mv": scalars["applied_l2_mv"],
            "applied_max_abs_mv": scalars["applied_max_abs_mv"],
            "changed_edges": len(changes),
            "clipped_slots": clipped_slots,
            "clipped_edge_count": len(clipped_slots),
            "lower_bound_edges_after": sum(w == p.w_min_mv for w in after),
            "upper_bound_edges_after": sum(w == p.w_max_mv for w in after),
            "saved_training_update": saved}


def timing_summary(probe: dict) -> dict:
    times = [probe["checkpoint_time_us"] + offset
             for offset in probe["relative_note_offsets_us"]]
    downs = []
    for action in probe["down_actions"]:
        t = action["time_us"]
        k = bisect.bisect_left(times, t)
        nearest = min((i for i in (k - 1, k) if 0 <= i < len(times)),
                      key=lambda i: abs(times[i] - t))
        downs.append({**action, "nearest_note_index": nearest,
                      "signed_nearest_note_error_us": t - times[nearest]})
    attempts = [e["hit_error_us"] for e in probe["events"]
                if e["hit_error_us"] is not None]
    return {"down_actions_with_nearest_note": downs,
            "median_signed_all_down_ms": statistics.median(
                a["signed_nearest_note_error_us"] for a in downs) / 1000 if downs else None,
            "mean_signed_attempt_error_ms": statistics.mean(attempts) / 1000
            if attempts else None,
            "mean_absolute_attempt_error_ms": statistics.mean(abs(x) for x in attempts) / 1000
            if attempts else None,
            "attempt_count_with_error": len(attempts),
            "hit_mean_absolute_error_ms": probe["metrics"]["hit_mean_absolute_error_ms"],
            "hit_mean_signed_error_ms": probe["metrics"]["hit_mean_signed_error_ms"]}


def frozen_at(session: TinyLaneSession, common: tuple) -> tuple[dict, bytes]:
    snapshot = session.checkpoint_bytes()
    now = session.simulator.current_time_us
    note_times = tuple(now + offset for offset in common[0])
    probe = make_probe(snapshot, note_times, common[1], False, None)
    assert probe["exploration_pulses_us"] == []
    return probe, snapshot


def run_seed(seed: int, start: int, end: int, originals: dict,
             long_rows: dict, long_protocol: dict, common: tuple,
             protocol_sha: str, source_sha: str) -> dict:
    source = long_rows[seed]
    session = TinyLaneSession(make_config(seed, originals, long_rows, long_protocol))
    for outcome in range(1, start + 1):
        while session.resolved_count < outcome:
            session.step()
        assert event_record(session, outcome - 1) == source["training_events"][outcome - 1]
        if outcome in (24, 96):
            assert_replay(session, source, {24: 0, 96: 24}[outcome], outcome)
    start_probe, _ = frozen_at(session, common)
    if start == 96:
        inspect_original_common(start_probe, source["checkpoints"][1]["probe"])
    records = [{"after_outcomes": start,
                "checkpoint_time_us": session.simulator.current_time_us,
                "training_event": None, "update": None,
                "probe": start_probe,
                "timing": timing_summary(start_probe)}]
    original_apply = session.simulator.apply_dopamine
    intercepted = {}

    def capture(dopamine: float):
        outcome = session.resolved_count + 1
        assert start < outcome <= end
        del session.simulator.apply_dopamine
        try:
            pre_bytes = session.checkpoint_bytes()
            geo = geometry(session, dopamine)
            changes = original_apply(dopamine)
        finally:
            session.simulator.apply_dopamine = capture
        saved = source["update_diagnostics"][outcome - 1]
        intercepted[outcome] = {"pre_update_canonical_sha256": canonical_hash(pre_bytes),
                                "update": update_record(session, dopamine, changes,
                                                        geo, weights(session), saved)}
        return changes

    session.simulator.apply_dopamine = capture
    for outcome in range(start + 1, end + 1):
        while session.resolved_count < outcome:
            session.step()
        assert outcome in intercepted
        actual_event = event_record(session, outcome - 1)
        assert actual_event == source["training_events"][outcome - 1]
        del session.simulator.apply_dopamine
        try:
            probe, _ = frozen_at(session, common)
        finally:
            session.simulator.apply_dopamine = capture
        records.append({"after_outcomes": outcome,
                        "checkpoint_time_us": session.simulator.current_time_us,
                        "training_event": actual_event,
                        **intercepted[outcome],
                        "probe": probe,
                        "timing": timing_summary(probe)})
        print(json.dumps({"seed": seed, "after_outcomes": outcome,
                          "probe_utility": probe["metrics"]["mean_utility"],
                          "probe_good": probe["metrics"]["good_or_better_count"]}),
              flush=True)
    del session.simulator.apply_dopamine
    if end == 384:
        assert_replay(session, source, 96, 384)
        inspect_original_common(records[-1]["probe"], source["checkpoints"][2]["probe"])
    assert len(records) == end - start + 1 == 17
    return {"key": str(seed), "seed": seed,
            "start_after_outcomes": start, "end_after_outcomes": end,
            "protocol_sha256": protocol_sha,
            "source_long_ledger_sha256": source_sha,
            "training_replay_events_checked": end,
            "source_training_note_times_us": source["resolved_config"]["training_note_times_us"][start:end],
            "source_training_cue_gains": source["resolved_config"]["training_cue_gains"][start:end],
            "checkpoints": records,
            "completed_utc": datetime.now(timezone.utc).isoformat()}


def meaningful_drop(previous: dict, current: dict, end: int) -> bool:
    pm, cm = previous["probe"]["metrics"], current["probe"]["metrics"]
    return (pm["good_or_better_count"] >= 16
            and pm["good_or_better_count"] - cm["good_or_better_count"] >= 8
            and pm["mean_utility"] - cm["mean_utility"] >= 0.25
            and current["after_outcomes"] <= end - 4)


def select_candidate(rows: dict[int, dict]) -> tuple[int, int] | None:
    for seed in (2001, 2002):
        points = rows[seed]["checkpoints"]
        end = rows[seed]["end_after_outcomes"]
        for earlier, later in zip(points, points[1:]):
            if meaningful_drop(earlier, later, end):
                return seed, later["after_outcomes"]
    return None


def replay_to(seed: int, target: int, originals: dict, long_rows: dict,
              long_protocol: dict) -> TinyLaneSession:
    session = TinyLaneSession(make_config(seed, originals, long_rows, long_protocol))
    source = long_rows[seed]
    for outcome in range(1, target + 1):
        while session.resolved_count < outcome:
            session.step()
        assert event_record(session, outcome - 1) == source["training_events"][outcome - 1]
    return session


def continue_branch(before_event: bytes, seed: int, target: int, end: int,
                    skip: bool, source: dict, original_target: dict,
                    common: tuple) -> dict:
    session = TinyLaneSession.from_trusted_checkpoint_bytes(before_event)
    original_apply = session.simulator.apply_dopamine
    intercepted = {}

    def intervene(dopamine: float):
        assert session.resolved_count + 1 == target
        del session.simulator.apply_dopamine
        try:
            pre = session.checkpoint_bytes()
            geo = geometry(session, dopamine)
            changes = original_apply(0.0 if skip else dopamine)
        finally:
            session.simulator.apply_dopamine = intervene
        assert geo["raw_proposed_update_mv"] == original_target["update"]["raw_proposed_update_mv"]
        assert geo["weights_before_mv"] == original_target["update"]["weights_before_mv"]
        assert geo["eligibility"] == original_target["update"]["eligibility"]
        assert geo["time_us"] == original_target["update"]["time_us"]
        # The in-memory replay and a checkpoint-loaded clone can serialize
        # identical behavior with different pickle memo/alias traversal. The
        # two intervention branches start from the same loaded checkpoint;
        # their pre-update hashes must match each other, and the real branch
        # must reproduce the source event and frozen probe exactly.
        intercepted["pre_update_canonical_sha256"] = canonical_hash(pre)
        intercepted["rng_state_at_update_sha256"] = hashlib.sha256(
            repr(TinyLaneSession.from_trusted_checkpoint_bytes(pre).rng.getstate()).encode()).hexdigest()
        intercepted["requested_dopamine"] = dopamine
        intercepted["delivered_dopamine"] = 0.0 if skip else dopamine
        intercepted["target_changed_edges"] = len(changes)
        intercepted["target_applied_l1_mv"] = sum(abs(c.applied_delta_mv) for c in changes)
        return changes

    session.simulator.apply_dopamine = intervene
    pulse_start = len(session.exploration_pulses)
    action_start = len(session.game.result().actions)
    while session.resolved_count < target:
        session.step()
    assert intercepted
    del session.simulator.apply_dopamine
    immediate_event = event_record(session, target - 1)
    for key in ("judgement", "hit_error_us", "game_utility", "learning_utility",
                "expected_utility_before", "rpe", "dopamine_like_amplitude"):
        assert immediate_event[key] == source["training_events"][target - 1][key]
    if skip:
        assert immediate_event["weight_changes"] == 0
    else:
        assert immediate_event == source["training_events"][target - 1]
    immediate_probe, _ = frozen_at(session, common)
    if not skip:
        assert immediate_probe == original_target["probe"]
    continuation = []
    for outcome in range(target + 1, end + 1):
        while session.resolved_count < outcome:
            session.step()
        e = event_record(session, outcome - 1)
        if not skip:
            assert e == source["training_events"][outcome - 1]
        continuation.append(e)
    final_probe, _ = frozen_at(session, common)
    actions = session.game.result().actions[action_start:]
    return {"branch": "skip_target_update" if skip else "real_update",
            "intervention": intercepted,
            "target_event": immediate_event,
            "subsequent_training_events": continuation,
            "exploration_pulses_us": session.exploration_pulses[pulse_start:],
            "training_down_actions": [{"time_us": a.action.time_us,
                                      "disposition": a.disposition.value,
                                      "note_id": a.note_id}
                                     for a in actions if a.action.kind.value == "down"],
            "end_checkpoint_time_us": session.simulator.current_time_us,
            "end_rng_state_sha256": hashlib.sha256(repr(session.rng.getstate()).encode()).hexdigest(),
            "immediate_probe": immediate_probe,
            "immediate_timing": timing_summary(immediate_probe),
            "final_probe": final_probe,
            "final_timing": timing_summary(final_probe)}


def run_counterfactual(candidate: tuple[int, int] | None, rows: dict[int, dict],
                       originals: dict, long_rows: dict, long_protocol: dict,
                       common: tuple, protocol_sha: str, source_sha: str) -> dict:
    if candidate is None:
        return {"status": "no_qualifying_transition", "protocol_sha256": protocol_sha,
                "source_long_ledger_sha256": source_sha,
                "reason": "No predeclared one-step deterioration qualified early enough; no skip branch was run."}
    seed, target = candidate
    row = rows[seed]
    end = row["end_after_outcomes"]
    original_target = row["checkpoints"][target - row["start_after_outcomes"]]
    before_session = replay_to(seed, target - 1, originals, long_rows, long_protocol)
    before_event = before_session.checkpoint_bytes()
    A = continue_branch(before_event, seed, target, end, False,
                        long_rows[seed], original_target, common)
    B = continue_branch(before_event, seed, target, end, True,
                        long_rows[seed], original_target, common)
    assert A["intervention"]["pre_update_canonical_sha256"] == B["intervention"]["pre_update_canonical_sha256"]
    assert A["intervention"]["rng_state_at_update_sha256"] == B["intervention"]["rng_state_at_update_sha256"]
    assert A["intervention"]["requested_dopamine"] == B["intervention"]["requested_dopamine"]
    assert A["intervention"]["target_applied_l1_mv"] > 0
    assert B["intervention"]["target_applied_l1_mv"] == 0
    assert A["final_probe"] == row["checkpoints"][-1]["probe"]
    return {"status": "complete", "seed": seed, "target_outcome": target,
            "window_end_outcome": end,
            "protocol_sha256": protocol_sha,
            "source_long_ledger_sha256": source_sha,
            "matched_pre_update_state": True,
            "matched_rng_state_at_update": True,
            "same_realized_exploration_pulses": A["exploration_pulses_us"] == B["exploration_pulses_us"],
            "same_end_checkpoint_time": A["end_checkpoint_time_us"] == B["end_checkpoint_time_us"],
            "branches": {"real_update": A, "skip_target_update": B},
            "completed_utc": datetime.now(timezone.utc).isoformat()}


def main() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert [(x["seed"], x["start_after_outcomes"], x["end_after_outcomes"])
            for x in protocol["seeds_and_windows"]] == [(2001, 96, 112), (2002, 368, 384)]
    protocol_sha = sha(PROTOCOL)
    source_sha = sha(LONG_LEDGER)
    long_meta = json.loads(LONG_META.read_text(encoding="utf-8"))
    assert long_meta["protocol_sha256"] == sha(LONG_PROTOCOL)
    assert long_meta["source_ledger_sha256"] == sha(ORIGINAL_LEDGER)
    source_hashes = {relative: sha(ROOT / relative)
                     for relative in long_meta["model_source_sha256"]}
    drift = {relative: {"saved": expected, "replay": source_hashes[relative]}
             for relative, expected in long_meta["model_source_sha256"].items()
             if source_hashes[relative] != expected}
    assert {k: v["replay"] for k, v in drift.items()} == PERMITTED_REPLAY_SOURCE_DRIFT
    originals = load_rows(ORIGINAL_LEDGER)
    long_rows = load_long_rows()
    assert long_rows[2001]["checkpoints"][1]["probe"]["metrics"]["good_or_better_count"] == 32
    assert long_rows[2001]["checkpoints"][2]["probe"]["metrics"]["good_or_better_count"] == 0
    assert long_rows[2002]["checkpoints"][2]["probe"]["metrics"]["good_or_better_count"] == 25
    common = (tuple(long_meta["probe_relative_note_offsets_us"]),
              tuple(long_meta["probe_cue_gains"]))
    long_protocol = json.loads(LONG_PROTOCOL.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    if META.exists():
        meta = json.loads(META.read_text(encoding="utf-8"))
        assert meta["protocol_sha256"] == protocol_sha
        assert meta["source_long_ledger_sha256"] == source_sha
    else:
        atomic_json(META, {"study_id": protocol["study_id"],
                           "started_utc": datetime.now(timezone.utc).isoformat(),
                           "python": sys.version.split()[0],
                           "protocol_sha256": protocol_sha,
                           "source_long_ledger_sha256": source_sha,
                           "source_long_meta_sha256": sha(LONG_META),
                           "source_original_ledger_sha256": sha(ORIGINAL_LEDGER),
                           "saved_model_source_sha256": long_meta["model_source_sha256"],
                           "replay_model_source_sha256": source_hashes,
                           "source_hash_drift_requiring_exact_replay": drift,
                           "synthetic_topology": "build_tiny_brain; no imported connectome"})
    rows = {}
    if LEDGER.exists():
        for line in LEDGER.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            assert row["key"] not in rows
            assert row["protocol_sha256"] == protocol_sha
            assert row["source_long_ledger_sha256"] == source_sha
            rows[int(row["key"])] = row
    for selection in protocol["seeds_and_windows"]:
        seed = selection["seed"]
        if seed in rows:
            continue
        atomic_json(STATUS, {"status": "running", "completed_seeds": list(rows),
                             "current_seed": seed})
        row = run_seed(seed, selection["start_after_outcomes"],
                       selection["end_after_outcomes"], originals, long_rows,
                       long_protocol, common, protocol_sha, source_sha)
        with LEDGER.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, separators=(",", ":")) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        rows[seed] = row
        atomic_json(STATUS, {"status": "running", "completed_seeds": list(rows),
                             "last_seed": seed})
    assert set(rows) == {2001, 2002}
    candidate = select_candidate(rows)
    print(json.dumps({"selected_causal_skip": candidate}), flush=True)
    if COUNTERFACTUAL.exists():
        result = json.loads(COUNTERFACTUAL.read_text(encoding="utf-8"))
        assert result["protocol_sha256"] == protocol_sha
        assert result["source_long_ledger_sha256"] == source_sha
    else:
        result = run_counterfactual(candidate, rows, originals, long_rows,
                                    long_protocol, common, protocol_sha, source_sha)
        atomic_json(COUNTERFACTUAL, result)
    atomic_json(STATUS, {"status": "complete", "completed_seeds": [2001, 2002],
                         "candidate": candidate,
                         "ledger_sha256": sha(LEDGER),
                         "counterfactual_sha256": sha(COUNTERFACTUAL)})
    print(json.dumps({"status": "complete", "candidate": candidate,
                      "counterfactual_status": result["status"]}), flush=True)


if __name__ == "__main__":
    main()
