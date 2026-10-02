"""A2: exact pre-update forks and fixed local direction/magnitude probes.

This is a synthetic diagnostic. It does not change the production learning rule.
Run from the project root with PYTHONPATH=src as a module.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

from project_b.experiments import TinyLaneSession
from scripts.diagnose_mechanisms import config_from_record
from scripts.exploration_map_diagnostic import (
    assert_replay, continuation_map, inspect_original_common,
    load_long_rows, load_rows, make_probe,
)
from scripts.long_continuation import atomic_json, event_record, sha
from scripts.weight_rollback_diagnostic import PERMITTED_REPLAY_SOURCE_DRIFT


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/update_direction_magnitude_diagnostic.json"
LONG_PROTOCOL = ROOT / "configs/long_continuation.json"
LONG_LEDGER = ROOT / "docs/figures/long_continuation/runs.jsonl"
LONG_META = ROOT / "docs/figures/long_continuation/meta.json"
ORIGINAL_LEDGER = ROOT / "docs/figures/overnight_synthetic/runs.jsonl"
OUTPUT = ROOT / "docs/figures/update_direction_magnitude_diagnostic"
LEDGER = OUTPUT / "runs.jsonl"
META = OUTPUT / "meta.json"
STATUS = OUTPUT / "status.json"
BRANCHES = ("no_update", "small_positive", "full_actual", "small_negative")


def selected_outcomes(long_row: dict) -> list[int]:
    eligible = [u for u in long_row["update_diagnostics"]
                if 193 <= u["note_index"] + 1 <= 288
                and u["raw_l1_mv"] >= 20
                and u["proposed_below_min_edges"] == 0
                and u["proposed_above_max_edges"] == 0]
    assert eligible
    return [eligible[0]["note_index"] + 1, 384]


def geometry(session: TinyLaneSession, dopamine: float) -> dict:
    slots = session.layout.plastic_slots
    p = session.plasticity.parameters
    t = session.simulator.current_time_us
    before = [session.plasticity.effective_weight(s) for s in slots]
    eligibility = [session.plasticity.eligibility_at(s, t) for s in slots]
    raw = [p.eta * e * dopamine for e in eligibility]
    proposed = [w + d for w, d in zip(before, raw)]
    return {"edge_slots": list(slots), "time_us": t,
            "dopamine": dopamine, "eta": p.eta,
            "weight_bounds_mv": [p.w_min_mv, p.w_max_mv],
            "weights_before_mv": before, "eligibility": eligibility,
            "raw_proposed_update_mv": raw,
            "raw_l1_mv": sum(abs(x) for x in raw),
            "raw_l2_mv": math.sqrt(sum(x*x for x in raw)),
            "raw_max_abs_mv": max(abs(x) for x in raw),
            "eligibility_nonzero_edges": sum(x != 0 for x in eligibility),
            "eligibility_mean": statistics.mean(eligibility),
            "eligibility_max": max(eligibility),
            "eligibility_l1": sum(abs(x) for x in eligibility),
            "proposed_below_min_slots": [s for s, x in zip(slots, proposed)
                                         if x < p.w_min_mv],
            "proposed_above_max_slots": [s for s, x in zip(slots, proposed)
                                         if x > p.w_max_mv]}


def compare_source_update(geo: dict, after: list[float], saved: dict) -> None:
    before = geo["weights_before_mv"]
    applied = [a - b for a, b in zip(after, before)]
    numeric = {
        "raw_l1_mv": geo["raw_l1_mv"], "raw_l2_mv": geo["raw_l2_mv"],
        "raw_max_abs_mv": geo["raw_max_abs_mv"],
        "applied_l1_mv": sum(abs(x) for x in applied),
        "applied_l2_mv": math.sqrt(sum(x*x for x in applied)),
        "applied_max_abs_mv": max(abs(x) for x in applied),
    }
    assert geo["time_us"] == saved["time_us"]
    assert geo["dopamine"] == saved["dopamine"]
    assert len(geo["proposed_below_min_slots"]) == saved["proposed_below_min_edges"]
    assert len(geo["proposed_above_max_slots"]) == saved["proposed_above_max_edges"]
    for key, actual in numeric.items():
        assert math.isclose(actual, saved[key], rel_tol=0, abs_tol=1e-9), (key, actual, saved[key])


def capture_pre_updates(session: TinyLaneSession, wanted: set[int],
                        long_row: dict) -> dict[int, dict]:
    original = session.simulator.apply_dopamine
    captured = {}

    def intercepted(dopamine: float):
        outcome = session.resolved_count + 1
        if outcome not in wanted:
            return original(dopamine)
        # Temporarily remove the local closure so the trusted checkpoint holds
        # the real simulator method and no unpicklable diagnostic machinery.
        del session.simulator.apply_dopamine
        try:
            pre = session.checkpoint_bytes()
            geo = geometry(session, dopamine)
            changes = original(dopamine)
            post = session.checkpoint_bytes()
        finally:
            session.simulator.apply_dopamine = intercepted
        after = [session.plasticity.effective_weight(s)
                 for s in session.layout.plastic_slots]
        saved = long_row["update_diagnostics"][outcome - 1]
        assert saved["note_index"] == outcome - 1
        compare_source_update(geo, after, saved)
        assert len(changes) == saved["changed_edges"]
        captured[outcome] = {"pre": pre, "post": post, "geometry": geo,
                             "source_update": saved}
        return changes

    session.simulator.apply_dopamine = intercepted
    for outcome in range(1, 385):
        while session.resolved_count < outcome:
            session.step()
        assert event_record(session, outcome - 1) == long_row["training_events"][outcome - 1], outcome
        if outcome in (24, 96, 384):
            assert_replay(session, long_row,
                          {24: 0, 96: 24, 384: 96}[outcome], outcome)
    assert set(captured) == wanted
    del session.simulator.apply_dopamine
    return captured


def apply_branch(pre: bytes, name: str, dopamine: float,
                 small_fraction: float, reference_weights: list[float],
                 reference_nonweight: bytes) -> tuple[bytes, dict]:
    session = TinyLaneSession.from_trusted_checkpoint_bytes(pre)
    assert session.plasticity is session.simulator.plasticity
    assert list(session.layout.plastic_slots)
    scale = {"no_update": 0.0, "small_positive": small_fraction,
             "full_actual": 1.0, "small_negative": -small_fraction}[name]
    geo = geometry(session, scale * dopamine)
    changes = session.simulator.apply_dopamine(scale * dopamine)
    after = [session.plasticity.effective_weight(s)
             for s in session.layout.plastic_slots]
    applied = [a - b for a, b in zip(after, geo["weights_before_mv"])]
    p = session.plasticity.parameters
    expected = [min(p.w_max_mv, max(p.w_min_mv, w + d))
                for w, d in zip(geo["weights_before_mv"], geo["raw_proposed_update_mv"])]
    assert all(abs(a - e) < 1e-12 for a, e in zip(after, expected))
    branch_bytes = session.checkpoint_bytes()
    # A zero-dopamine call and every nonzero call advance the same plasticity
    # clock. Restoring only effective weights must reproduce the entire zero
    # branch, including neuron/queue/eligibility/predictor/RNG/readout/topology.
    for slot, weight in zip(session.layout.plastic_slots, reference_weights):
        session.plasticity._weights[slot] = weight
    assert session.checkpoint_bytes() == reference_nonweight, name
    clipped = [s for s, raw, real in zip(session.layout.plastic_slots,
                                         geo["raw_proposed_update_mv"], applied)
               if not math.isclose(raw, real, rel_tol=0, abs_tol=1e-12)]
    summary = {"scale_of_real_dopamine": scale,
               "dopamine": scale * dopamine,
               "raw_proposed_update_mv": geo["raw_proposed_update_mv"],
               "applied_update_mv": applied,
               "weights_after_mv": after,
               "raw_l1_mv": geo["raw_l1_mv"],
               "raw_l2_mv": geo["raw_l2_mv"],
               "applied_l1_mv": sum(abs(x) for x in applied),
               "applied_l2_mv": math.sqrt(sum(x*x for x in applied)),
               "raw_max_abs_mv": geo["raw_max_abs_mv"],
               "applied_max_abs_mv": max(abs(x) for x in applied),
               "clipped_slots": clipped,
               "clipped_edge_count": len(clipped),
               "proposed_below_min_slots": geo["proposed_below_min_slots"],
               "proposed_above_max_slots": geo["proposed_above_max_slots"],
               "lower_bound_edges_after": sum(w == p.w_min_mv for w in after),
               "upper_bound_edges_after": sum(w == p.w_max_mv for w in after),
               "changed_edges": len(changes)}
    return branch_bytes, summary


def contrasts(branches: dict) -> dict:
    baseline = branches["no_update"]["probe"]
    result = {}
    for name in BRANCHES[1:]:
        probe = branches[name]["probe"]
        assert probe["relative_note_offsets_us"] == baseline["relative_note_offsets_us"]
        assert probe["cue_gains"] == baseline["cue_gains"]
        result[name] = {
            "delta_mean_utility": probe["metrics"]["mean_utility"] - baseline["metrics"]["mean_utility"],
            "delta_good_or_better_count": probe["metrics"]["good_or_better_count"] - baseline["metrics"]["good_or_better_count"],
            "delta_down_count": probe["metrics"]["down_count"] - baseline["metrics"]["down_count"],
            "delta_hit_mean_absolute_error_ms": (
                probe["metrics"]["hit_mean_absolute_error_ms"] - baseline["metrics"]["hit_mean_absolute_error_ms"]
                if probe["metrics"]["hit_mean_absolute_error_ms"] is not None
                and baseline["metrics"]["hit_mean_absolute_error_ms"] is not None else None),
            "delta_utility_by_note": [a["game_utility"] - b["game_utility"]
                                      for a, b in zip(probe["events"], baseline["events"])],
            "signed_hit_error_delta_us_where_both_present": [
                a["hit_error_us"] - b["hit_error_us"]
                if a["hit_error_us"] is not None and b["hit_error_us"] is not None else None
                for a, b in zip(probe["events"], baseline["events"])],
        }
    return result


def run_case(seed: int, outcome: int, capture: dict,
             common: tuple[tuple[int, ...], tuple[float, ...]],
             long_row: dict, fraction: float, protocol_sha: str,
             source_sha: str) -> dict:
    pre, post, geo = capture["pre"], capture["post"], capture["geometry"]
    time_us = geo["time_us"]
    note_times = tuple(time_us + x for x in common[0])
    assert len(note_times) == 32
    source_event = long_row["training_events"][outcome - 1]
    assert source_event["dopamine_like_amplitude"] == geo["dopamine"]
    assert source_event["delivered_time_us"] == time_us
    zero_session = TinyLaneSession.from_trusted_checkpoint_bytes(pre)
    zero_session.simulator.apply_dopamine(0.0)
    no_bytes = zero_session.checkpoint_bytes()
    reference_weights = [zero_session.plasticity.effective_weight(s)
                         for s in zero_session.layout.plastic_slots]
    assert reference_weights == geo["weights_before_mv"]
    branches = {}
    for name in BRANCHES:
        branch_bytes, update = apply_branch(pre, name, geo["dopamine"], fraction,
                                            reference_weights, no_bytes)
        if name == "no_update":
            assert branch_bytes == no_bytes
        if name == "full_actual":
            source_post = TinyLaneSession.from_trusted_checkpoint_bytes(post)
            # Pickle byte streams can differ between an in-memory replay object
            # and a loaded clone because memo traversal records alias history.
            # Compare all effective weights and canonical loaded snapshots.
            assert [source_post.plasticity.effective_weight(s)
                    for s in source_post.layout.plastic_slots] == update["weights_after_mv"]
            assert branch_bytes == source_post.checkpoint_bytes()
            assert update["changed_edges"] == capture["source_update"]["changed_edges"]
        probe = make_probe(branch_bytes, note_times, common[1], False, None)
        assert probe["exploration_pulses_us"] == []
        branches[name] = {"update": update, "probe": probe}
    if outcome == 384:
        inspect_original_common(branches["full_actual"]["probe"],
                                long_row["checkpoints"][2]["probe"])
    return {"key": f"{seed}:{outcome}", "seed": seed,
            "one_based_training_outcome": outcome,
            "zero_based_note_index": outcome - 1,
            "checkpoint_time_us": time_us,
            "source_training_event": source_event,
            "source_update_diagnostic": capture["source_update"],
            "pre_update_geometry": geo,
            "pre_update_checkpoint_sha256": hashlib.sha256(pre).hexdigest(),
            "actual_post_update_checkpoint_sha256": hashlib.sha256(post).hexdigest(),
            "zero_branch_checkpoint_sha256": hashlib.sha256(no_bytes).hexdigest(),
            "protocol_sha256": protocol_sha,
            "source_long_ledger_sha256": source_sha,
            "branches": branches,
            "contrasts_vs_no_update": contrasts(branches),
            "completed_utc": datetime.now(timezone.utc).isoformat()}


def main() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert protocol["seeds"] == [2004, 2002]
    assert protocol["branches"] == list(BRANCHES)
    assert protocol["small_raw_fraction"] == 0.05
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
    long_protocol = json.loads(LONG_PROTOCOL.read_text(encoding="utf-8"))
    common = (tuple(long_meta["probe_relative_note_offsets_us"]),
              tuple(long_meta["probe_cue_gains"]))
    planned = []
    for seed in protocol["seeds"]:
        selected = selected_outcomes(long_rows[seed])
        assert selected == protocol["selected_outcomes"][str(seed)]
        planned.extend(f"{seed}:{outcome}" for outcome in selected)
    OUTPUT.mkdir(parents=True, exist_ok=True)
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
                           "planned_keys": planned,
                           "synthetic_topology": "build_tiny_brain; no imported connectome"})
    rows = {}
    if LEDGER.exists():
        for line in LEDGER.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            assert row["key"] in planned and row["key"] not in rows
            assert row["protocol_sha256"] == protocol_sha
            assert row["source_long_ledger_sha256"] == source_sha
            rows[row["key"]] = row
    for seed in protocol["seeds"]:
        wanted = selected_outcomes(long_rows[seed])
        if all(f"{seed}:{outcome}" in rows for outcome in wanted):
            continue
        atomic_json(STATUS, {"status": "running", "completed_keys": list(rows),
                             "planned_keys": planned, "current_seed": seed})
        original_config = config_from_record(originals[seed])
        times, gains = continuation_map(original_config, seed, long_protocol,
                                        long_rows[seed])
        from dataclasses import replace
        config = replace(original_config, note_count=384, training_notes=384,
                         explicit_note_times_us=times[:384],
                         cue_gain_by_note=gains[:384])
        session = TinyLaneSession(config)
        captures = capture_pre_updates(session, set(wanted), long_rows[seed])
        print(json.dumps({"seed": seed, "replay": "all 384 events exact",
                          "captured": wanted}), flush=True)
        for outcome in wanted:
            key = f"{seed}:{outcome}"
            if key in rows:
                continue
            row = run_case(seed, outcome, captures[outcome], common,
                           long_rows[seed], protocol["small_raw_fraction"],
                           protocol_sha, source_sha)
            with LEDGER.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(row, separators=(",", ":")) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            rows[key] = row
            atomic_json(STATUS, {"status": "running", "completed_keys": list(rows),
                                 "planned_keys": planned, "last_key": key})
            print(json.dumps({"key": key,
                              "utility": {name: row["branches"][name]["probe"]["metrics"]["mean_utility"]
                                          for name in BRANCHES},
                              "clipped": {name: row["branches"][name]["update"]["clipped_edge_count"]
                                          for name in BRANCHES}}), flush=True)
    assert set(rows) == set(planned)
    atomic_json(STATUS, {"status": "complete", "completed_keys": planned,
                         "planned_keys": planned,
                         "ledger_sha256": sha(LEDGER)})
    print(json.dumps({"status": "complete", "cases": len(rows),
                      "ledger_sha256": sha(LEDGER)}), flush=True)


if __name__ == "__main__":
    main()
