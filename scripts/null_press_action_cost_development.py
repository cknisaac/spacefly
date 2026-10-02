"""One fixed null-action cost overlay on eight existing development seeds."""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path

from project_b.experiments import TinyBrainConfig, TinyLaneSession
from project_b.osu import ActionDisposition, KeyActionKind
from scripts.checkpoint_controls import shuffled_utilities, summarize
from scripts.long_continuation import atomic_json, sha
from scripts.overnight_synthetic import map_for_seed


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/null_press_action_cost_development.json"
OVERNIGHT = ROOT / "configs/overnight_synthetic.json"
OUT = ROOT / "docs/figures/null_press_action_cost_development"
CONDITIONS = ("legacy_on", "null_cost_on", "null_cost_off", "null_cost_shuffled")


def action_record(session: TinyLaneSession, train: int) -> tuple[list[dict], dict]:
    note_times = session.note_times_us
    actions = []
    for record in session.game.result().actions:
        t = record.action.time_us
        is_down = record.action.kind is KeyActionKind.DOWN
        note_index = next((i for i, note_t in enumerate(note_times)
                           if note_t-500_000 <= t <= note_t+session.game.windows.expiry_offset_us), None)
        actions.append({"time_us": t, "kind": record.action.kind.value,
                        "disposition": record.disposition.value,
                        "note_id": record.note_id, "nearest_visible_note_index": note_index,
                        "signed_note_offset_us": t-note_times[note_index]
                        if note_index is not None else None,
                        "phase": "training" if note_index is not None and note_index < train
                        else "frozen" if note_index is not None else "outside_note_window"})
    frozen_down = [a for a in actions if a["phase"] == "frozen" and a["kind"] == "down"]
    first = []
    for i in range(train, len(note_times)):
        candidates = [a for a in frozen_down if a["nearest_visible_note_index"] == i]
        first.append({"note_index": i,
                      "first_down_offset_us": candidates[0]["signed_note_offset_us"]
                      if candidates else None,
                      "first_down_disposition": candidates[0]["disposition"]
                      if candidates else None,
                      "down_count": len(candidates)})
    summary = {
        "frozen_down_count": len(frozen_down),
        "frozen_null_down_count": sum(a["disposition"] == "null_press" for a in frozen_down),
        "frozen_early_miss_down_count": sum(a["disposition"] == "early_miss" for a in frozen_down),
        "frozen_first_down_offsets_us": first,
        "frozen_silent_note_count": sum(x["first_down_offset_us"] is None for x in first),
    }
    return actions, summary


def run_condition(seed: int, condition: str, spec: dict, overnight: dict,
                  shuffled_schedule: tuple[float, ...] | None) -> dict:
    train, frozen = overnight["training_notes"], overnight["frozen_notes"]
    times, gains = map_for_seed(seed, train+frozen, overnight)
    base = TinyBrainConfig(note_count=train+frozen, training_notes=train, seed=seed,
                           explicit_note_times_us=times, cue_gain_by_note=gains,
                           readout_on_threshold=10)
    if condition == "null_cost_off":
        base = replace(base, plasticity_enabled=False)
    elif condition == "null_cost_shuffled":
        assert shuffled_schedule is not None
        base = replace(base, reward_utility_schedule=shuffled_schedule)
    session = TinyLaneSession(base)
    cost_events: list[dict] = []
    if condition in ("null_cost_on", "null_cost_shuffled"):
        original_apply = session.game.apply_action

        def apply_with_null_cost(action):
            record = original_apply(action)
            if (record.disposition is ActionDisposition.NULL_PRESS
                    and session.resolved_count < train):
                changes = session.simulator.apply_dopamine(-1.0)
                cost_events.append({"time_us": action.time_us,
                                    "disposition": record.disposition.value,
                                    "dopamine_like_amplitude": -1.0,
                                    "changed_edge_count": len(changes),
                                    "applied_l1_mv": sum(abs(c.applied_delta_mv)
                                                         for c in changes),
                                    "edge_slots": [c.edge_slot for c in changes]})
            return record

        session.game.apply_action = apply_with_null_cost
    result = session.run()
    metrics = summarize(result, train)
    actions, action_metrics = action_record(session, train)
    weights = result.final_plastic_weights_mv
    return {
        "seed": seed, "condition": condition, "resolved_config": asdict(base),
        "note_times_us": list(times), "cue_gains": list(gains),
        "summary": metrics, "actions": actions, "action_metrics": action_metrics,
        "null_cost_events": cost_events,
        "null_cost_applied_l1_mv_total": sum(e["applied_l1_mv"] for e in cost_events),
        "final_plastic_weights_mv": list(weights),
        "final_upper_bound_edges": sum(w == 2.0 for w in weights),
        "final_lower_bound_edges": sum(w == 0.0 for w in weights),
        "exploration_pulses_us": list(result.exploration_pulses),
        "peak_queued_arrivals": result.peak_queued_arrivals,
        "completed_utc": datetime.now(timezone.utc).isoformat(),
    }


def summarize_cohort(rows: dict[tuple[int, str], dict], seeds: list[int]) -> dict:
    totals = {}
    for condition in CONDITIONS:
        cases = [rows[(seed, condition)] for seed in seeds]
        good = [x["summary"]["frozen_good_or_better_percent"] for x in cases]
        abs_hit_errors = [abs(e["hit_error_us"])/1000 for x in cases
                          for e in x["summary"]["events"] if e["phase"] == "frozen"
                          and e["judgement"] != "MISS" and e["hit_error_us"] is not None]
        offsets = [o["first_down_offset_us"]/1000 for x in cases
                   for o in x["action_metrics"]["frozen_first_down_offsets_us"]
                   if o["first_down_offset_us"] is not None]
        totals[condition] = {
            "mean_frozen_good_or_better_percent": sum(good)/len(good),
            "pooled_frozen_hit_mae_ms": sum(abs_hit_errors)/len(abs_hit_errors)
            if abs_hit_errors else None,
            "frozen_hit_count": len(abs_hit_errors),
            "frozen_null_down_count": sum(x["action_metrics"]["frozen_null_down_count"]
                                          for x in cases),
            "frozen_early_miss_down_count": sum(x["action_metrics"]["frozen_early_miss_down_count"]
                                                for x in cases),
            "frozen_silent_note_count": sum(x["action_metrics"]["frozen_silent_note_count"]
                                            for x in cases),
            "mean_frozen_first_down_offset_ms": sum(offsets)/len(offsets) if offsets else None,
            "total_null_cost_events": sum(len(x["null_cost_events"]) for x in cases),
            "total_null_cost_applied_l1_mv": sum(x["null_cost_applied_l1_mv_total"]
                                                  for x in cases),
        }
    on = "null_cost_on"
    wins = {other: sum(rows[(seed,on)]["summary"]["frozen_good_or_better_percent"]
                       > rows[(seed,other)]["summary"]["frozen_good_or_better_percent"]
                       for seed in seeds)
            for other in ("legacy_on", "null_cost_off", "null_cost_shuffled")}
    return {"conditions": totals, "strict_good_plus_wins": wins,
            "seed_good_plus_percent": {str(seed): {condition:
                rows[(seed,condition)]["summary"]["frozen_good_or_better_percent"]
                for condition in CONDITIONS} for seed in seeds},
            "progression_rule_met": (all(n >= 6 for n in wins.values())
                                    and totals[on]["frozen_null_down_count"]
                                    < totals["legacy_on"]["frozen_null_down_count"]
                                    and totals[on]["frozen_silent_note_count"] == 0
                                    and totals[on]["pooled_frozen_hit_mae_ms"] is not None
                                    and totals["legacy_on"]["pooled_frozen_hit_mae_ms"] is not None
                                    and totals[on]["pooled_frozen_hit_mae_ms"]
                                    < totals["legacy_on"]["pooled_frozen_hit_mae_ms"])}


def main() -> None:
    spec = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    overnight = json.loads(OVERNIGHT.read_text(encoding="utf-8"))
    seeds = spec["seeds"]
    assert seeds == list(range(1000, 1008))
    assert spec["conditions"] == list(CONDITIONS)
    assert overnight["training_notes"] == 24 and overnight["frozen_notes"] == 16
    OUT.mkdir(parents=True, exist_ok=True)
    ledger = OUT / "runs.jsonl"
    protocol_sha = sha(PROTOCOL)
    source_paths = ["src/project_b/experiments/tiny_brain.py",
                    "src/project_b/plasticity/eligibility.py",
                    "src/project_b/neuromodulation/reward.py",
                    "src/project_b/motor/fixed_readout.py",
                    "src/project_b/osu/environment.py",
                    "scripts/null_press_action_cost_development.py"]
    meta = {"study_id": spec["study_id"], "protocol_sha256": protocol_sha,
            "overnight_config_sha256": sha(OVERNIGHT),
            "python": sys.version.split()[0],
            "source_sha256": {p: sha(ROOT/p) for p in source_paths},
            "synthetic_topology": "build_tiny_brain; no imported connectome"}
    meta_path = OUT / "meta.json"
    if meta_path.exists():
        assert json.loads(meta_path.read_text(encoding="utf-8")) == meta
    else:
        atomic_json(meta_path, meta)
    rows: dict[tuple[int,str],dict] = {}
    if ledger.exists():
        for line in ledger.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            key = (row["seed"], row["condition"])
            assert key not in rows and row["protocol_sha256"] == protocol_sha
            rows[key] = row
    for seed in seeds:
        for condition in CONDITIONS:
            key = (seed, condition)
            if key in rows:
                continue
            shuffled_schedule = None
            if condition == "null_cost_shuffled":
                original = rows[(seed,"null_cost_on")]["summary"]["events"][:24]
                shuffled_schedule = shuffled_utilities(tuple(x["game_utility"] for x in original), seed)
            row = run_condition(seed, condition, spec, overnight, shuffled_schedule)
            row["protocol_sha256"] = protocol_sha
            with ledger.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, separators=(",", ":")) + "\n")
                f.flush()
                os.fsync(f.fileno())
            rows[key] = row
            atomic_json(OUT / "status.json", {"status": "running", "completed_runs": len(rows),
                                              "planned_runs": len(seeds)*len(CONDITIONS),
                                              "last_seed": seed, "last_condition": condition})
            print(json.dumps({"seed": seed, "condition": condition,
                              "frozen_good_plus_percent": row["summary"]["frozen_good_or_better_percent"],
                              "frozen_null_down_count": row["action_metrics"]["frozen_null_down_count"],
                              "null_cost_events": len(row["null_cost_events"])}), flush=True)
    assert len(rows) == len(seeds)*len(CONDITIONS)
    cohort = summarize_cohort(rows, seeds)
    atomic_json(OUT / "result.json", {"status": "complete", "study_id": spec["study_id"],
                                       "protocol_sha256": protocol_sha,
                                       "ledger_sha256": sha(ledger), "seeds": seeds,
                                       "cohort": cohort,
                                       "completed_utc": datetime.now(timezone.utc).isoformat()})
    atomic_json(OUT / "status.json", {"status": "complete", "completed_runs": len(rows),
                                      "planned_runs": len(rows),
                                      "result_sha256": sha(OUT / "result.json")})
    print(json.dumps(cohort, indent=2), flush=True)


if __name__ == "__main__":
    main()
