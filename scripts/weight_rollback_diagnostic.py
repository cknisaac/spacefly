"""Counterfactual earlier-weight transplants into identical late synthetic states."""

from __future__ import annotations

import hashlib
import json
import math
import os
import statistics
import sys
import time
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from project_b.experiments import TinyLaneSession
from scripts.diagnose_mechanisms import config_from_record
from scripts.exploration_map_diagnostic import (
    LONG_DIRECTORY, LONG_LEDGER, LONG_META, LONG_PROTOCOL, ORIGINAL_LEDGER,
    assert_replay, continuation_map, inspect_original_common,
    load_long_rows, load_rows, make_probe,
)
from scripts.long_continuation import atomic_json, sha


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/weight_rollback_diagnostic.json"
PRIOR_STOP = ROOT / "docs/figures/exploration_map_diagnostic/stop.json"
OUTPUT = ROOT / "docs/figures/weight_rollback_diagnostic"
META = OUTPUT / "meta.json"
LEDGER = OUTPUT / "runs.jsonl"
STATUS = OUTPUT / "status.json"
RESULT = OUTPUT / "result.json"
WEIGHT_SOURCES = (384, 96, 24)
MAPS = ("common", "continuation")
# The subsequent MaleCNS scale study added runtime diagnostics and complete-
# batch safety prechecks to these two files. This exact source drift is allowed
# only when every replayed training event and the saved 384 common probe match.
PERMITTED_REPLAY_SOURCE_DRIFT = {
    "src\\project_b\\simulation\\__init__.py": "27457a1aeecc8da92999768a5555b51efdcd19e3e154d29c08382ac340ad2d92",
    "src\\project_b\\simulation\\spiking.py": "bb93e933b654ff972689c8fd09a07b2c621b7642e0a8309ed2d95e8d3ee1e24a",
}


def weights(session: TinyLaneSession) -> tuple[float, ...]:
    return tuple(session.plasticity.effective_weight(slot)
                 for slot in session.layout.plastic_slots)


def transplant(snapshot384: bytes, donor: tuple[float, ...]) -> tuple[bytes, dict]:
    session = TinyLaneSession.from_trusted_checkpoint_bytes(snapshot384)
    assert session.checkpoint_bytes() == snapshot384
    assert session.plasticity is session.simulator.plasticity
    slots = session.layout.plastic_slots
    assert len(slots) == len(donor) == 480
    assert set(session.plasticity._weights) == set(slots)
    present = weights(session)
    parameters = session.plasticity.parameters
    assert all(parameters.w_min_mv <= value <= parameters.w_max_mv
               for value in donor)
    for slot, value in zip(slots, donor):
        session.plasticity._weights[slot] = value
    assert weights(session) == donor
    altered = session.checkpoint_bytes()
    # Restoring the selected weights must reproduce every byte of the late
    # checkpoint: neuron/queue/eligibility/predictor/RNG/readout/topology state
    # and all unselected synapses are otherwise untouched by this branch.
    for slot, value in zip(slots, present):
        session.plasticity._weights[slot] = value
    assert session.checkpoint_bytes() == snapshot384
    for slot, value in zip(slots, donor):
        session.plasticity._weights[slot] = value
    assert session.checkpoint_bytes() == altered
    delta = [a - b for a, b in zip(donor, present)]
    return altered, {
        "changed_edges": sum(a != b for a, b in zip(donor, present)),
        "l1_weight_displacement_mv": sum(abs(x) for x in delta),
        "l2_weight_displacement_mv": math.sqrt(sum(x*x for x in delta)),
        "max_abs_weight_displacement_mv": max(abs(x) for x in delta),
        "weight_sum_mv": sum(donor),
        "lower_bound_edges": sum(x == parameters.w_min_mv for x in donor),
        "upper_bound_edges": sum(x == parameters.w_max_mv for x in donor),
    }


def run_seed(seed: int, original_row: dict, long_row: dict,
             long_protocol: dict, common: tuple, protocol_sha: str,
             source_sha: str) -> dict:
    original = config_from_record(original_row)
    times, gains = continuation_map(original, seed, long_protocol, long_row)
    config = replace(original, note_count=384, training_notes=384,
                     explicit_note_times_us=times[:384],
                     cue_gain_by_note=gains[:384])
    session = TinyLaneSession(config)
    donors = {}
    previous = 0
    for checkpoint in (24, 96, 384):
        while session.resolved_count < checkpoint:
            session.step()
        assert session.resolved_count == checkpoint
        assert_replay(session, long_row, previous, checkpoint)
        donors[checkpoint] = weights(session)
        previous = checkpoint
    assert len(donors[384]) == 480
    now = session.simulator.current_time_us
    snapshot384 = session.checkpoint_bytes()
    panels = {"common": (tuple(now + offset for offset in common[0]), common[1]),
              "continuation": (times[384:416], gains[384:416])}
    branches = {}
    for source in WEIGHT_SOURCES:
        altered, displacement = transplant(snapshot384, donors[source])
        branch_maps = {}
        for map_name in MAPS:
            note_times, cue_gains = panels[map_name]
            probe = make_probe(altered, note_times, cue_gains, False, None)
            if source == 384 and map_name == "common":
                inspect_original_common(probe, long_row["checkpoints"][2]["probe"])
            branch_maps[map_name] = probe
        branches[str(source)] = {"displacement_from_384": displacement,
                                 "maps": branch_maps}
    return {"key": str(seed), "seed": seed,
            "protocol_sha256": protocol_sha,
            "source_long_ledger_sha256": source_sha,
            "checkpoint_time_us": now,
            "donor_checkpoints": list(WEIGHT_SOURCES),
            "branches": branches,
            "completed_utc": datetime.now(timezone.utc).isoformat()}


def aggregate(rows: dict[str, dict], protocol: dict) -> dict:
    result = {"study_id": protocol["study_id"], "status": "complete",
              "seeds": protocol["seeds"], "maps": {}}
    for map_name in MAPS:
        by_source = {}
        for source in WEIGHT_SOURCES:
            probes = [rows[str(seed)]["branches"][str(source)]["maps"][map_name]
                      for seed in protocol["seeds"]]
            by_source[str(source)] = {
                "mean_good_percent": statistics.mean(p["metrics"]["good_or_better_percent"] for p in probes),
                "mean_utility": statistics.mean(p["metrics"]["mean_utility"] for p in probes),
                "mean_early_attempted_misses": statistics.mean(p["metrics"]["attempted_early_miss_count"] for p in probes),
                "mean_down_actions": statistics.mean(p["metrics"]["down_count"] for p in probes),
                "mean_null_downs": statistics.mean(p["metrics"]["null_down_count"] for p in probes),
                "per_seed": {str(seed): {
                    "good_percent": probe["metrics"]["good_or_better_percent"],
                    "mean_utility": probe["metrics"]["mean_utility"],
                    "early_attempted_misses": probe["metrics"]["attempted_early_miss_count"],
                    "weight_displacement_l1_mv": rows[str(seed)]["branches"][str(source)]["displacement_from_384"]["l1_weight_displacement_mv"],
                } for seed, probe in zip(protocol["seeds"], probes)},
            }
        result["maps"][map_name] = by_source
    result["branch_count"] = len(protocol["seeds"]) * len(WEIGHT_SOURCES) * len(MAPS)
    result["frozen_outcomes"] = result["branch_count"] * 32
    return result


def main() -> None:
    protocol_raw = PROTOCOL.read_bytes()
    protocol = json.loads(protocol_raw)
    assert protocol["seeds"] == [2000, 2001, 2002, 2003, 2004]
    assert protocol["weight_sources_after_training_outcomes"] == list(WEIGHT_SOURCES)
    assert protocol["maps"] == list(MAPS)
    stop = json.loads(PRIOR_STOP.read_text(encoding="utf-8"))
    assert stop["completed_seeds"] == protocol["seeds"]
    protocol_sha = hashlib.sha256(protocol_raw).hexdigest()
    source_sha = sha(LONG_LEDGER)
    long_meta = json.loads(LONG_META.read_text(encoding="utf-8"))
    long_protocol = json.loads(LONG_PROTOCOL.read_text(encoding="utf-8"))
    assert long_meta["protocol_sha256"] == sha(LONG_PROTOCOL)
    assert long_meta["source_ledger_sha256"] == sha(ORIGINAL_LEDGER)
    replay_hashes = {relative: sha(ROOT / relative)
                     for relative in long_meta["model_source_sha256"]}
    source_drift = {relative: {"saved": expected, "replay": replay_hashes[relative]}
                    for relative, expected in long_meta["model_source_sha256"].items()
                    if replay_hashes[relative] != expected}
    assert {relative: item["replay"] for relative, item in source_drift.items()} == PERMITTED_REPLAY_SOURCE_DRIFT
    original_rows = load_rows(ORIGINAL_LEDGER)
    long_rows = load_long_rows()
    common = (tuple(long_meta["probe_relative_note_offsets_us"]),
              tuple(long_meta["probe_cue_gains"]))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if META.exists():
        meta = json.loads(META.read_text(encoding="utf-8"))
        assert meta["protocol_sha256"] == protocol_sha
        assert meta["source_long_ledger_sha256"] == source_sha
    else:
        meta = {"study_id": protocol["study_id"],
                "started_utc": datetime.now(timezone.utc).isoformat(),
                "started_unix": time.time(),
                "python": sys.version.split()[0],
                "protocol_sha256": protocol_sha,
                "source_long_ledger_sha256": source_sha,
                "source_long_meta_sha256": sha(LONG_META),
                "source_original_ledger_sha256": sha(ORIGINAL_LEDGER),
                "model_source_sha256": long_meta["model_source_sha256"],
                "replay_model_source_sha256": replay_hashes,
                "source_hash_drift_requiring_exact_replay": source_drift,
                "synthetic_topology": "build_tiny_brain; no imported connectome"}
        atomic_json(META, meta)
    rows = {}
    if LEDGER.exists():
        for line in LEDGER.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            assert row["key"] not in rows
            assert row["protocol_sha256"] == protocol_sha
            assert row["source_long_ledger_sha256"] == source_sha
            rows[row["key"]] = row
    for seed in protocol["seeds"]:
        key = str(seed)
        if key in rows:
            continue
        if time.time() - meta["started_unix"] >= protocol["runtime_cap_seconds"]:
            atomic_json(STATUS, {"status": "budget_exhausted", "completed": len(rows),
                                 "planned": len(protocol["seeds"]), "next_seed": seed})
            return
        atomic_json(STATUS, {"status": "running", "completed": len(rows),
                             "planned": len(protocol["seeds"]), "current_seed": seed})
        row = run_seed(seed, original_rows[seed], long_rows[seed], long_protocol,
                       common, protocol_sha, source_sha)
        with LEDGER.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, separators=(",", ":")) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        rows[key] = row
        atomic_json(STATUS, {"status": "running", "completed": len(rows),
                             "planned": len(protocol["seeds"]), "last_seed": seed})
        print(json.dumps({"completed": len(rows), "planned": len(protocol["seeds"]),
                          "seed": seed,
                          "common_good_by_weight_source": {
                              str(source): row["branches"][str(source)]["maps"]["common"]["metrics"]["good_or_better_percent"]
                              for source in WEIGHT_SOURCES},
                          "continuation_good_by_weight_source": {
                              str(source): row["branches"][str(source)]["maps"]["continuation"]["metrics"]["good_or_better_percent"]
                              for source in WEIGHT_SOURCES}}), flush=True)
    summary = aggregate(rows, protocol)
    atomic_json(RESULT, summary)
    atomic_json(STATUS, {"status": "complete", "completed": len(rows),
                         "planned": len(protocol["seeds"]),
                         "finished_utc": datetime.now(timezone.utc).isoformat()})
    print(json.dumps({"status": "complete", "completed": len(rows)}), flush=True)


if __name__ == "__main__":
    main()
