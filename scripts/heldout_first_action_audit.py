"""Reproduce old held-out on runs and record every first versus scored DOWN."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from project_b.experiments import TinyBrainConfig, TinyLaneSession
from scripts.checkpoint_controls import summarize
from scripts.long_continuation import atomic_json, sha
from scripts.null_press_action_cost_development import action_record
from scripts.overnight_synthetic import map_for_seed


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/heldout_first_action_audit.json"
OVERNIGHT = ROOT / "configs/overnight_synthetic.json"
OLD = ROOT / "docs/figures/overnight_synthetic/runs.jsonl"
OUT = ROOT / "docs/figures/heldout_first_action_audit"


def classify_note_actions(actions: list[dict], events: list[dict], train: int) -> list[dict]:
    classified = []
    for i in range(train,len(events)):
        downs = [a for a in actions if a["nearest_visible_note_index"] == i
                 and a["kind"] == "down"]
        judged = next((a for a in downs if a["note_id"] == f"lane1-{i}"),None)
        prior_null = (sum(a["disposition"] == "null_press"
                          for a in downs if judged is not None and a["time_us"] < judged["time_us"])
                      if judged is not None else 0)
        event = events[i]
        classified.append({"note_index":i,"judgement":event["judgement"],
                           "hit_value":event["hit_value"],"hit_error_us":event["hit_error_us"],
                           "first_down_time_us":downs[0]["time_us"] if downs else None,
                           "first_down_offset_us":downs[0]["signed_note_offset_us"] if downs else None,
                           "first_down_disposition":downs[0]["disposition"] if downs else None,
                           "down_count":len(downs),
                           "judged_down_time_us":judged["time_us"] if judged else None,
                           "judged_down_position":(downs.index(judged)+1) if judged else None,
                           "prior_null_down_count":prior_null,
                           "good_plus_after_null":event["hit_value"] >= 200 and prior_null > 0,
                           "good_plus_on_first_down":event["hit_value"] >= 200 and judged == downs[0]
                           if downs else False})
    return classified


def main() -> None:
    spec = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    overnight = json.loads(OVERNIGHT.read_text(encoding="utf-8"))
    seeds = list(range(spec["seeds"]["start"],spec["seeds"]["start"]+spec["seeds"]["count"]))
    assert seeds == list(range(2000,2032))
    assert overnight["training_notes"] == 24 and overnight["frozen_notes"] == 16
    old = {x["key"]:x for x in (json.loads(line) for line in OLD.read_text(encoding="utf-8").splitlines())}
    OUT.mkdir(parents=True,exist_ok=True)
    ledger = OUT / "runs.jsonl"
    protocol_sha = sha(PROTOCOL)
    source_paths = ["src/project_b/experiments/tiny_brain.py",
                    "src/project_b/motor/fixed_readout.py",
                    "src/project_b/osu/environment.py",
                    "scripts/heldout_first_action_audit.py",
                    "scripts/null_press_action_cost_development.py"]
    meta = {"study_id":spec["study_id"],"protocol_sha256":protocol_sha,
            "overnight_config_sha256":sha(OVERNIGHT),
            "original_ledger_sha256":sha(OLD),"python":sys.version.split()[0],
            "source_sha256":{p:sha(ROOT/p) for p in source_paths},
            "synthetic_topology":"build_tiny_brain; no imported connectome"}
    meta_path = OUT / "meta.json"
    if meta_path.exists():
        assert json.loads(meta_path.read_text(encoding="utf-8")) == meta
    else:
        atomic_json(meta_path,meta)
    rows = {}
    if ledger.exists():
        for line in ledger.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            assert row["seed"] not in rows and row["protocol_sha256"] == protocol_sha
            rows[row["seed"]] = row
    for seed in seeds:
        if seed in rows:
            continue
        times,gains = map_for_seed(seed,40,overnight)
        config = TinyBrainConfig(note_count=40,training_notes=24,seed=seed,
                                 explicit_note_times_us=times,cue_gain_by_note=gains,
                                 readout_on_threshold=10)
        session = TinyLaneSession(config)
        simulation = session.run()
        summary = summarize(simulation,24)
        original = old[f"heldout:10:{seed}:on"]
        resolved_config = json.loads(json.dumps(asdict(config)))
        assert summary == original["summary"]
        assert resolved_config == original["resolved_config"]
        actions,action_metrics = action_record(session,24)
        frozen_notes = classify_note_actions(actions,summary["events"],24)
        assert len(frozen_notes) == 16
        row = {"seed":seed,"protocol_sha256":protocol_sha,"resolved_config":resolved_config,
               "note_times_us":list(times),"cue_gains":list(gains),
               "historical_summary_exact_match":True,"summary":summary,
               "actions":actions,"action_metrics":action_metrics,
               "frozen_note_actions":frozen_notes,
               "completed_utc":datetime.now(timezone.utc).isoformat()}
        with ledger.open("a",encoding="utf-8") as stream:
            stream.write(json.dumps(row,separators=(",",":"))+"\n")
            stream.flush();os.fsync(stream.fileno())
        rows[seed] = row
        atomic_json(OUT / "status.json", {"status":"running","completed_seeds":len(rows),
                                          "planned_seeds":len(seeds),"last_seed":seed})
        print(json.dumps({"seed":seed,"good_plus":sum(n["hit_value"]>=200 for n in frozen_notes),
                          "good_plus_after_null":sum(n["good_plus_after_null"] for n in frozen_notes),
                          "frozen_null_down":action_metrics["frozen_null_down_count"]}),flush=True)
    assert len(rows) == 32
    notes = [n for seed in seeds for n in rows[seed]["frozen_note_actions"]]
    good = [n for n in notes if n["hit_value"] >= 200]
    null_first_good = [n for n in good if n["good_plus_after_null"]]
    first_good = [n for n in good if n["good_plus_on_first_down"]]
    aggregate = {
        "frozen_note_count":len(notes),"frozen_good_plus_count":len(good),
        "good_plus_after_same_note_null_count":len(null_first_good),
        "good_plus_after_same_note_null_fraction":len(null_first_good)/len(good) if good else None,
        "good_plus_on_first_down_count":len(first_good),
        "frozen_null_down_count":sum(rows[s]["action_metrics"]["frozen_null_down_count"] for s in seeds),
        "frozen_early_miss_down_count":sum(rows[s]["action_metrics"]["frozen_early_miss_down_count"] for s in seeds),
        "frozen_silent_note_count":sum(rows[s]["action_metrics"]["frozen_silent_note_count"] for s in seeds),
        "first_down_disposition_counts":{d:sum(n["first_down_disposition"]==d for n in notes)
                                         for d in ("null_press","early_miss","hit",None)},
        "per_seed":{str(s):{"good_plus":sum(n["hit_value"]>=200 for n in rows[s]["frozen_note_actions"]),
                             "good_plus_after_null":sum(n["good_plus_after_null"] for n in rows[s]["frozen_note_actions"]),
                             "good_plus_on_first_down":sum(n["good_plus_on_first_down"] for n in rows[s]["frozen_note_actions"])}
                    for s in seeds},
    }
    atomic_json(OUT / "result.json", {"status":"complete","study_id":spec["study_id"],
                                       "protocol_sha256":protocol_sha,"ledger_sha256":sha(ledger),
                                       "seeds":seeds,"aggregate":aggregate,
                                       "completed_utc":datetime.now(timezone.utc).isoformat()})
    atomic_json(OUT / "status.json", {"status":"complete","completed_seeds":32,
                                      "planned_seeds":32,"result_sha256":sha(OUT/"result.json")})
    print(json.dumps(aggregate,indent=2),flush=True)


if __name__ == "__main__":
    main()
