"""One fixed action-boundary trace reset on eight development seeds."""

from __future__ import annotations

import json
import os
import statistics
import sys
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path

from project_b.experiments import TinyBrainConfig, TinyLaneSession
from project_b.osu import ActionDisposition
from scripts.checkpoint_controls import shuffled_utilities, summarize
from scripts.long_continuation import atomic_json, sha
from scripts.null_press_action_cost_development import action_record
from scripts.overnight_synthetic import map_for_seed


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/null_press_trace_boundary_development.json"
OVERNIGHT = ROOT / "configs/overnight_synthetic.json"
OUT = ROOT / "docs/figures/null_press_trace_boundary_development"
CONDITIONS = ("legacy_on", "boundary_reset_on", "boundary_reset_off",
              "boundary_reset_shuffled")


def run_condition(seed: int, condition: str, overnight: dict,
                  shuffled_schedule: tuple[float, ...] | None) -> dict:
    train, frozen = overnight["training_notes"], overnight["frozen_notes"]
    times, gains = map_for_seed(seed, train+frozen, overnight)
    config = TinyBrainConfig(note_count=train+frozen, training_notes=train, seed=seed,
                             explicit_note_times_us=times, cue_gain_by_note=gains,
                             readout_on_threshold=10)
    if condition == "boundary_reset_off":
        config = replace(config, plasticity_enabled=False)
    elif condition == "boundary_reset_shuffled":
        assert shuffled_schedule is not None
        config = replace(config, reward_utility_schedule=shuffled_schedule)
    session = TinyLaneSession(config)
    reset_events = []
    if condition in ("boundary_reset_on", "boundary_reset_shuffled"):
        original_apply = session.game.apply_action
        p = session.plasticity

        def apply_with_reset(action):
            record = original_apply(action)
            if (record.disposition is ActionDisposition.NULL_PRESS
                    and session.resolved_count < train):
                t = action.time_us
                weight_before = tuple(p._weights.values())
                pre_l1 = sum(abs(p._decayed(v,t,p.parameters.tau_pre_us))
                             for v in p._pre.values())
                elig_l1 = sum(abs(p._decayed(v,t,p.parameters.tau_eligibility_us))
                              for v in p._eligibility.values())
                for key in p._pre:
                    p._pre[key] = (0.0,t)
                for slot in p._eligibility:
                    p._eligibility[slot] = (0.0,t)
                assert tuple(p._weights.values()) == weight_before
                assert all(v[0] == 0 for v in p._pre.values())
                assert all(v[0] == 0 for v in p._eligibility.values())
                reset_events.append({"time_us": t, "disposition": record.disposition.value,
                                     "presynaptic_trace_l1_before": pre_l1,
                                     "eligibility_l1_before": elig_l1,
                                     "presynaptic_trace_count": len(p._pre),
                                     "selected_edge_trace_count": len(p._eligibility),
                                     "weights_changed_by_reset": 0})
            return record

        session.game.apply_action = apply_with_reset
    result = session.run()
    actions, action_metrics = action_record(session, train)
    weights = result.final_plastic_weights_mv
    return {
        "seed": seed, "condition": condition, "resolved_config": asdict(config),
        "note_times_us": list(times), "cue_gains": list(gains),
        "summary": summarize(result, train),
        "actions": actions, "action_metrics": action_metrics,
        "trace_reset_events": reset_events,
        "final_plastic_weights_mv": list(weights),
        "final_upper_bound_edges": sum(w == 2.0 for w in weights),
        "final_lower_bound_edges": sum(w == 0.0 for w in weights),
        "exploration_pulses_us": list(result.exploration_pulses),
        "peak_queued_arrivals": result.peak_queued_arrivals,
        "completed_utc": datetime.now(timezone.utc).isoformat(),
    }


def cohort_summary(rows: dict[tuple[int,str],dict], seeds: list[int]) -> dict:
    conditions = {}
    for name in CONDITIONS:
        cases = [rows[(s,name)] for s in seeds]
        hits = [abs(e["hit_error_us"])/1000 for x in cases
                for e in x["summary"]["events"][24:]
                if e["judgement"] != "MISS" and e["hit_error_us"] is not None]
        offsets = [o["first_down_offset_us"]/1000 for x in cases
                   for o in x["action_metrics"]["frozen_first_down_offsets_us"]
                   if o["first_down_offset_us"] is not None]
        conditions[name] = {
            "mean_frozen_good_or_better_percent": statistics.mean(
                x["summary"]["frozen_good_or_better_percent"] for x in cases),
            "pooled_frozen_hit_mae_ms": statistics.mean(hits) if hits else None,
            "frozen_hit_count": len(hits),
            "frozen_null_down_count": sum(x["action_metrics"]["frozen_null_down_count"]
                                          for x in cases),
            "frozen_early_miss_down_count": sum(x["action_metrics"]["frozen_early_miss_down_count"]
                                                for x in cases),
            "frozen_silent_note_count": sum(x["action_metrics"]["frozen_silent_note_count"]
                                            for x in cases),
            "mean_frozen_first_down_offset_ms": statistics.mean(offsets) if offsets else None,
            "total_trace_reset_events": sum(len(x["trace_reset_events"]) for x in cases),
            "total_pre_reset_eligibility_l1": sum(e["eligibility_l1_before"]
                for x in cases for e in x["trace_reset_events"]),
        }
    wins = {other: sum(rows[(s,"boundary_reset_on")]["summary"]["frozen_good_or_better_percent"]
                       > rows[(s,other)]["summary"]["frozen_good_or_better_percent"]
                       for s in seeds)
            for other in ("legacy_on", "boundary_reset_off", "boundary_reset_shuffled")}
    b, old = conditions["boundary_reset_on"], conditions["legacy_on"]
    progress = (all(n >= 6 for n in wins.values())
                and b["pooled_frozen_hit_mae_ms"] is not None
                and old["pooled_frozen_hit_mae_ms"] is not None
                and b["pooled_frozen_hit_mae_ms"] < old["pooled_frozen_hit_mae_ms"]
                and b["frozen_null_down_count"] < old["frozen_null_down_count"]
                and b["frozen_early_miss_down_count"] <= old["frozen_early_miss_down_count"]
                and b["frozen_silent_note_count"] <= old["frozen_silent_note_count"])
    return {"conditions": conditions, "strict_good_plus_wins": wins,
            "seed_good_plus_percent": {str(s): {n: rows[(s,n)]["summary"]["frozen_good_or_better_percent"]
                                               for n in CONDITIONS} for s in seeds},
            "progression_rule_met": progress}


def main() -> None:
    spec = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    overnight = json.loads(OVERNIGHT.read_text(encoding="utf-8"))
    seeds = spec["seeds"]
    assert seeds == list(range(1000,1008)) and spec["conditions"] == list(CONDITIONS)
    assert overnight["training_notes"] == 24 and overnight["frozen_notes"] == 16
    OUT.mkdir(parents=True, exist_ok=True)
    ledger = OUT / "runs.jsonl"
    protocol_sha = sha(PROTOCOL)
    source_paths = ["src/project_b/experiments/tiny_brain.py",
                    "src/project_b/plasticity/eligibility.py",
                    "src/project_b/neuromodulation/reward.py",
                    "src/project_b/motor/fixed_readout.py",
                    "src/project_b/osu/environment.py",
                    "scripts/null_press_action_cost_development.py",
                    "scripts/null_press_trace_boundary_development.py"]
    meta = {"study_id": spec["study_id"], "protocol_sha256": protocol_sha,
            "overnight_config_sha256": sha(OVERNIGHT), "python": sys.version.split()[0],
            "source_sha256": {p: sha(ROOT/p) for p in source_paths},
            "synthetic_topology": "build_tiny_brain; no imported connectome"}
    meta_path = OUT / "meta.json"
    if meta_path.exists():
        assert json.loads(meta_path.read_text(encoding="utf-8")) == meta
    else:
        atomic_json(meta_path, meta)
    rows = {}
    if ledger.exists():
        for line in ledger.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            key = (row["seed"], row["condition"])
            assert key not in rows and row["protocol_sha256"] == protocol_sha
            rows[key] = row
    for seed in seeds:
        for condition in CONDITIONS:
            key = (seed,condition)
            if key in rows:
                continue
            shuffled = None
            if condition == "boundary_reset_shuffled":
                utilities = tuple(x["game_utility"] for x in rows[(seed,"boundary_reset_on")]["summary"]["events"][:24])
                shuffled = shuffled_utilities(utilities,seed)
            row = run_condition(seed, condition, overnight, shuffled)
            row["protocol_sha256"] = protocol_sha
            with ledger.open("a",encoding="utf-8") as stream:
                stream.write(json.dumps(row,separators=(",",":")) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            rows[key] = row
            atomic_json(OUT / "status.json", {"status": "running", "completed_runs": len(rows),
                                              "planned_runs": 32, "last_seed": seed,
                                              "last_condition": condition})
            print(json.dumps({"seed":seed,"condition":condition,
                              "frozen_good_plus_percent":row["summary"]["frozen_good_or_better_percent"],
                              "frozen_null_down_count":row["action_metrics"]["frozen_null_down_count"],
                              "reset_events":len(row["trace_reset_events"])}),flush=True)
    assert len(rows) == 32
    cohort = cohort_summary(rows,seeds)
    atomic_json(OUT / "result.json", {"status":"complete","study_id":spec["study_id"],
                                       "protocol_sha256":protocol_sha,"ledger_sha256":sha(ledger),
                                       "seeds":seeds,"cohort":cohort,
                                       "completed_utc":datetime.now(timezone.utc).isoformat()})
    atomic_json(OUT / "status.json", {"status":"complete","completed_runs":32,
                                      "planned_runs":32,"result_sha256":sha(OUT / "result.json")})
    print(json.dumps(cohort,indent=2),flush=True)


if __name__ == "__main__":
    main()
