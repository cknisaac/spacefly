"""One diagnostic motor-readout rearm rule on eight development seeds."""

from __future__ import annotations

import json
import os
import statistics
import sys
from collections import deque
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path

from project_b.experiments import TinyBrainConfig, TinyLaneSession
from project_b.motor import FixedMotorReadout, MotorDecision
from project_b.osu import KeyAction, KeyActionKind
from project_b.utils.time import require_time_us
from scripts.checkpoint_controls import shuffled_utilities, summarize
from scripts.heldout_first_action_audit import classify_note_actions
from scripts.long_continuation import atomic_json, sha
from scripts.null_press_action_cost_development import action_record
from scripts.overnight_synthetic import map_for_seed


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/quiet_rearm_readout_development.json"
OVERNIGHT = ROOT / "configs/overnight_synthetic.json"
OUT = ROOT / "docs/figures/quiet_rearm_readout_development"
CONDITIONS = ("legacy_on", "quiet_rearm_on", "quiet_rearm_off", "quiet_rearm_shuffled")


class QuietRearmReadout(FixedMotorReadout):
    """Existing readout with one additional quiet-before-next-DOWN state bit."""

    def __init__(self, neuron_indices, **kwargs) -> None:
        super().__init__(neuron_indices, **kwargs)
        self.armed = True
        self.rearm_events: list[dict] = []
        self.disarm_events: list[dict] = []

    def observe(self, time_us: int, spiking_indices) -> MotorDecision | None:
        require_time_us(time_us)
        if self._last_time_us is not None and time_us <= self._last_time_us:
            raise ValueError("motor readout requires strictly increasing ticks")
        indices = tuple(spiking_indices)
        if any(type(i) is not int or i < 0 for i in indices):
            raise ValueError("spiking_indices contains an invalid index")
        if len(set(indices)) != len(indices):
            raise ValueError("a neuron can spike only once in a tick batch")
        self._last_time_us = time_us
        self._spike_times.extend(time_us for i in indices if i in self._index_set)
        while self._spike_times and self._spike_times[0] <= time_us-self.window_us:
            self._spike_times.popleft()
        count = len(self._spike_times)
        if self.key_down:
            assert self._last_down_us is not None
            elapsed_us = time_us-self._last_down_us
            if (elapsed_us >= self.max_hold_us
                    or (elapsed_us >= self.min_hold_us and count <= self.off_threshold)):
                self.key_down = False
                return MotorDecision(time_us,count,self.on_threshold,
                                     KeyAction(time_us,self.lane,KeyActionKind.UP))
            return None
        if not self.armed and count <= self.off_threshold:
            self.armed = True
            self.rearm_events.append({"time_us":time_us,"spike_count_in_window":count})
        if (self.armed and count >= self.on_threshold
                and (self._last_down_us is None
                     or time_us-self._last_down_us >= self.cooldown_us)):
            self.key_down = True
            self._last_down_us = time_us
            self.armed = False
            self.disarm_events.append({"time_us":time_us,"spike_count_in_window":count})
            return MotorDecision(time_us,count,self.on_threshold,
                                 KeyAction(time_us,self.lane,KeyActionKind.DOWN))
        return None


def run_condition(seed: int, condition: str, overnight: dict,
                  shuffled_schedule: tuple[float, ...] | None) -> dict:
    train,frozen = overnight["training_notes"],overnight["frozen_notes"]
    times,gains = map_for_seed(seed,train+frozen,overnight)
    config = TinyBrainConfig(note_count=train+frozen,training_notes=train,seed=seed,
                             explicit_note_times_us=times,cue_gain_by_note=gains,
                             readout_on_threshold=10)
    if condition == "quiet_rearm_off":
        config = replace(config,plasticity_enabled=False)
    elif condition == "quiet_rearm_shuffled":
        assert shuffled_schedule is not None
        config = replace(config,reward_utility_schedule=shuffled_schedule)
    session = TinyLaneSession(config)
    if condition != "legacy_on":
        session.readout = QuietRearmReadout(
            session.layout.motor,window_us=config.readout_window_us,
            on_threshold=config.readout_on_threshold)
    simulation = session.run()
    summary = summarize(simulation,train)
    actions,action_metrics = action_record(session,train)
    frozen_notes = classify_note_actions(actions,summary["events"],train)
    weights = simulation.final_plastic_weights_mv
    return {
        "seed":seed,"condition":condition,"resolved_config":asdict(config),
        "note_times_us":list(times),"cue_gains":list(gains),
        "summary":summary,"actions":actions,"action_metrics":action_metrics,
        "frozen_note_actions":frozen_notes,
        "readout_disarm_events":list(session.readout.disarm_events)
        if isinstance(session.readout,QuietRearmReadout) else [],
        "readout_rearm_events":list(session.readout.rearm_events)
        if isinstance(session.readout,QuietRearmReadout) else [],
        "final_plastic_weights_mv":list(weights),
        "final_upper_bound_edges":sum(w==2 for w in weights),
        "final_lower_bound_edges":sum(w==0 for w in weights),
        "exploration_pulses_us":list(simulation.exploration_pulses),
        "peak_queued_arrivals":simulation.peak_queued_arrivals,
        "completed_utc":datetime.now(timezone.utc).isoformat(),
    }


def cohort_summary(rows: dict[tuple[int,str],dict], seeds: list[int]) -> dict:
    conditions = {}
    for name in CONDITIONS:
        cases = [rows[(s,name)] for s in seeds]
        hits = [abs(e["hit_error_us"])/1000 for x in cases
                for e in x["summary"]["events"][24:]
                if e["judgement"] != "MISS" and e["hit_error_us"] is not None]
        offsets = [n["first_down_offset_us"]/1000 for x in cases
                   for n in x["frozen_note_actions"] if n["first_down_offset_us"] is not None]
        conditions[name] = {
            "mean_frozen_good_or_better_percent":statistics.mean(
                x["summary"]["frozen_good_or_better_percent"] for x in cases),
            "pooled_frozen_hit_mae_ms":statistics.mean(hits) if hits else None,
            "frozen_hit_count":len(hits),
            "frozen_null_down_count":sum(x["action_metrics"]["frozen_null_down_count"] for x in cases),
            "frozen_early_miss_down_count":sum(x["action_metrics"]["frozen_early_miss_down_count"] for x in cases),
            "frozen_silent_note_count":sum(x["action_metrics"]["frozen_silent_note_count"] for x in cases),
            "frozen_extra_down_count":sum(max(0,n["down_count"]-1) for x in cases
                                           for n in x["frozen_note_actions"]),
            "frozen_good_plus_after_null_count":sum(n["good_plus_after_null"] for x in cases
                                                     for n in x["frozen_note_actions"]),
            "mean_frozen_first_down_offset_ms":statistics.mean(offsets) if offsets else None,
            "readout_disarm_event_count":sum(len(x["readout_disarm_events"]) for x in cases),
            "readout_rearm_event_count":sum(len(x["readout_rearm_events"]) for x in cases),
        }
    wins = {other:sum(rows[(s,"quiet_rearm_on")]["summary"]["frozen_good_or_better_percent"]
                     > rows[(s,other)]["summary"]["frozen_good_or_better_percent"]
                     for s in seeds)
            for other in ("legacy_on","quiet_rearm_off","quiet_rearm_shuffled")}
    b,old = conditions["quiet_rearm_on"],conditions["legacy_on"]
    promising = (all(n>=6 for n in wins.values())
                 and b["pooled_frozen_hit_mae_ms"] is not None
                 and old["pooled_frozen_hit_mae_ms"] is not None
                 and b["pooled_frozen_hit_mae_ms"] < old["pooled_frozen_hit_mae_ms"]
                 and b["frozen_good_plus_after_null_count"] < old["frozen_good_plus_after_null_count"]
                 and b["frozen_extra_down_count"] < old["frozen_extra_down_count"]
                 and b["frozen_silent_note_count"] <= old["frozen_silent_note_count"])
    return {"conditions":conditions,"strict_good_plus_wins":wins,
            "seed_good_plus_percent":{str(s):{n:rows[(s,n)]["summary"]["frozen_good_or_better_percent"]
                                             for n in CONDITIONS} for s in seeds},
            "progression_rule_met":promising}


def main() -> None:
    spec = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    overnight = json.loads(OVERNIGHT.read_text(encoding="utf-8"))
    seeds = spec["seeds"]
    assert seeds == list(range(1000,1008)) and spec["conditions"] == list(CONDITIONS)
    OUT.mkdir(parents=True,exist_ok=True)
    ledger = OUT/"runs.jsonl"
    protocol_sha = sha(PROTOCOL)
    source_paths = ["src/project_b/experiments/tiny_brain.py",
                    "src/project_b/motor/fixed_readout.py",
                    "src/project_b/osu/environment.py",
                    "scripts/quiet_rearm_readout_development.py",
                    "scripts/heldout_first_action_audit.py",
                    "scripts/null_press_action_cost_development.py"]
    meta = {"study_id":spec["study_id"],"protocol_sha256":protocol_sha,
            "overnight_config_sha256":sha(OVERNIGHT),"python":sys.version.split()[0],
            "source_sha256":{p:sha(ROOT/p) for p in source_paths},
            "synthetic_topology":"build_tiny_brain; no imported connectome"}
    meta_path = OUT/"meta.json"
    if meta_path.exists():
        assert json.loads(meta_path.read_text(encoding="utf-8")) == meta
    else:
        atomic_json(meta_path,meta)
    rows = {}
    if ledger.exists():
        for line in ledger.read_text(encoding="utf-8").splitlines():
            x = json.loads(line); key=(x["seed"],x["condition"])
            assert key not in rows and x["protocol_sha256"] == protocol_sha
            rows[key]=x
    for seed in seeds:
        for condition in CONDITIONS:
            key=(seed,condition)
            if key in rows: continue
            shuffled=None
            if condition == "quiet_rearm_shuffled":
                utilities=tuple(e["game_utility"] for e in rows[(seed,"quiet_rearm_on")]["summary"]["events"][:24])
                shuffled=shuffled_utilities(utilities,seed)
            x=run_condition(seed,condition,overnight,shuffled)
            x["protocol_sha256"]=protocol_sha
            with ledger.open("a",encoding="utf-8") as f:
                f.write(json.dumps(x,separators=(",",":"))+"\n");f.flush();os.fsync(f.fileno())
            rows[key]=x
            atomic_json(OUT/"status.json",{"status":"running","completed_runs":len(rows),
                                            "planned_runs":32,"last_seed":seed,"last_condition":condition})
            print(json.dumps({"seed":seed,"condition":condition,
                              "frozen_good_plus_percent":x["summary"]["frozen_good_or_better_percent"],
                              "frozen_null_down_count":x["action_metrics"]["frozen_null_down_count"],
                              "frozen_good_plus_after_null":sum(n["good_plus_after_null"] for n in x["frozen_note_actions"])}),flush=True)
    assert len(rows)==32
    cohort=cohort_summary(rows,seeds)
    atomic_json(OUT/"result.json",{"status":"complete","study_id":spec["study_id"],
                                    "protocol_sha256":protocol_sha,"ledger_sha256":sha(ledger),
                                    "seeds":seeds,"cohort":cohort,
                                    "completed_utc":datetime.now(timezone.utc).isoformat()})
    atomic_json(OUT/"status.json",{"status":"complete","completed_runs":32,
                                    "planned_runs":32,"result_sha256":sha(OUT/"result.json")})
    print(json.dumps(cohort,indent=2),flush=True)


if __name__=="__main__":
    main()
