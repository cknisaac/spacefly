"""Independent action/game, rearm-state and cohort-metric audit."""

from __future__ import annotations

import json
import statistics
from pathlib import Path

from project_b.osu import GameEnvironment, KeyAction, KeyActionKind, TapNote
from scripts.checkpoint_controls import shuffled_utilities
from scripts.long_continuation import sha
from scripts.overnight_synthetic import map_for_seed


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT/"configs/quiet_rearm_readout_development.json"
OVERNIGHT = ROOT/"configs/overnight_synthetic.json"
OLD = ROOT/"docs/figures/overnight_synthetic/runs.jsonl"
OUT = ROOT/"docs/figures/quiet_rearm_readout_development"
CONDITIONS = ("legacy_on","quiet_rearm_on","quiet_rearm_off","quiet_rearm_shuffled")


def main() -> None:
    spec=json.loads(PROTOCOL.read_text(encoding="utf-8"))
    overnight=json.loads(OVERNIGHT.read_text(encoding="utf-8"))
    result=json.loads((OUT/"result.json").read_text(encoding="utf-8"))
    status=json.loads((OUT/"status.json").read_text(encoding="utf-8"))
    meta=json.loads((OUT/"meta.json").read_text(encoding="utf-8"))
    ledger=OUT/"runs.jsonl"
    assert result["status"]==status["status"]=="complete"
    assert result["protocol_sha256"]==meta["protocol_sha256"]==sha(PROTOCOL)
    assert result["ledger_sha256"]==sha(ledger)
    assert status["result_sha256"]==sha(OUT/"result.json")
    assert meta["overnight_config_sha256"]==sha(OVERNIGHT)
    assert all(sha(ROOT/p)==h for p,h in meta["source_sha256"].items())
    assert spec["seeds"]==list(range(1000,1008)) and spec["conditions"]==list(CONDITIONS)
    old={x["key"]:x for x in (json.loads(line) for line in OLD.read_text(encoding="utf-8").splitlines())}
    rows={}
    for line in ledger.read_text(encoding="utf-8").splitlines():
        x=json.loads(line);key=(x["seed"],x["condition"])
        assert key not in rows and x["protocol_sha256"]==sha(PROTOCOL)
        rows[key]=x
    assert len(rows)==status["completed_runs"]==32
    action_count=frozen_count=disarm_count=rearm_count=0
    for seed in spec["seeds"]:
        times,gains=map_for_seed(seed,40,overnight)
        on=rows[(seed,"quiet_rearm_on")]
        schedule=shuffled_utilities(tuple(e["game_utility"] for e in on["summary"]["events"][:24]),seed)
        for condition in CONDITIONS:
            x=rows[(seed,condition)]
            cfg=x["resolved_config"]
            assert x["note_times_us"]==cfg["explicit_note_times_us"]==list(times)
            assert x["cue_gains"]==cfg["cue_gain_by_note"]==list(gains)
            assert cfg["seed"]==seed and cfg["note_count"]==40
            assert cfg["training_notes"]==24 and cfg["readout_on_threshold"]==10
            assert cfg["plasticity_enabled"]==(condition!="quiet_rearm_off")
            assert cfg["reward_utility_schedule"]==(list(schedule) if condition=="quiet_rearm_shuffled" else None)
            game=GameEnvironment(tuple(TapNote(f"lane1-{i}",0,t) for i,t in enumerate(times)))
            actions=x["actions"]
            for a in actions:
                actual=game.apply_action(KeyAction(a["time_us"],0,KeyActionKind(a["kind"])))
                assert actual.disposition.value==a["disposition"] and actual.note_id==a["note_id"]
                associations=[i for i,t in enumerate(times)
                              if t-500_000<=a["time_us"]<=t+game.windows.expiry_offset_us]
                assert len(associations)<=1
                i=associations[0] if associations else None
                assert a["nearest_visible_note_index"]==i
                assert a["signed_note_offset_us"]==(a["time_us"]-times[i] if i is not None else None)
                action_count+=1
            judged=game.finish().judgements
            assert len(judged)==len(x["summary"]["events"])==40
            for i,(j,e) in enumerate(zip(judged,x["summary"]["events"])):
                assert j.judgement.name==e["judgement"] and j.hit_error_us==e["hit_error_us"]
                if i>=24:
                    assert e["weight_changes"]==0
                    frozen_count+=1
            frozen=x["summary"]["events"][24:]
            good=sum(e["hit_value"]>=200 for e in frozen)
            assert x["summary"]["frozen_good_or_better_percent"]==100*good/16
            hits=[abs(e["hit_error_us"])/1000 for e in frozen
                  if e["judgement"]!="MISS" and e["hit_error_us"] is not None]
            assert x["summary"]["frozen_mean_absolute_error_ms"]==(statistics.mean(hits) if hits else None)
            for i,n in enumerate(x["frozen_note_actions"],24):
                downs=[a for a in actions if a["kind"]=="down" and a["nearest_visible_note_index"]==i]
                hit=next((a for a in downs if a["note_id"]==f"lane1-{i}"),None)
                prior_null=sum(a["disposition"]=="null_press" for a in downs
                               if hit is not None and a["time_us"]<hit["time_us"])
                assert n["note_index"]==i and n["down_count"]==len(downs)
                assert n["first_down_offset_us"]==(downs[0]["signed_note_offset_us"] if downs else None)
                assert n["first_down_disposition"]==(downs[0]["disposition"] if downs else None)
                assert n["good_plus_after_null"]==(n["hit_value"]>=200 and prior_null>0)
            weights=x["final_plastic_weights_mv"]
            assert len(weights)==480 and all(0<=w<=2 for w in weights)
            assert x["final_upper_bound_edges"]==sum(w==2 for w in weights)
            assert x["final_lower_bound_edges"]==sum(w==0 for w in weights)
            if condition=="quiet_rearm_off":
                assert all(w==0.04 for w in weights)
            if condition=="legacy_on":
                assert x["summary"]==old[f"dev:10:{seed}:on"]["summary"]
                assert x["readout_disarm_events"]==x["readout_rearm_events"]==[]
            else:
                downs=[a["time_us"] for a in actions if a["kind"]=="down"]
                disarms=x["readout_disarm_events"]
                rearms=x["readout_rearm_events"]
                assert [e["time_us"] for e in disarms]==downs
                assert all(e["spike_count_in_window"]>=10 for e in disarms)
                assert all(e["spike_count_in_window"]<=2 for e in rearms)
                assert len(rearms)<=len(disarms)
                for later_down in downs[1:]:
                    previous_down=max(d for d in downs if d<later_down)
                    assert later_down-previous_down>=200_000
                    assert any(previous_down<e["time_us"]<later_down for e in rearms)
                disarm_count+=len(disarms)
                rearm_count+=len(rearms)
    cohort=result["cohort"]
    for condition in CONDITIONS:
        cases=[rows[(s,condition)] for s in spec["seeds"]]
        stats=cohort["conditions"][condition]
        assert stats["mean_frozen_good_or_better_percent"]==statistics.mean(
            x["summary"]["frozen_good_or_better_percent"] for x in cases)
        assert stats["frozen_null_down_count"]==sum(x["action_metrics"]["frozen_null_down_count"] for x in cases)
        assert stats["frozen_good_plus_after_null_count"]==sum(n["good_plus_after_null"]
            for x in cases for n in x["frozen_note_actions"])
        assert stats["frozen_extra_down_count"]==sum(max(0,n["down_count"]-1)
            for x in cases for n in x["frozen_note_actions"])
    wins={other:sum(rows[(s,"quiet_rearm_on")]["summary"]["frozen_good_or_better_percent"]
                    >rows[(s,other)]["summary"]["frozen_good_or_better_percent"]
                    for s in spec["seeds"])
          for other in ("legacy_on","quiet_rearm_off","quiet_rearm_shuffled")}
    assert cohort["strict_good_plus_wins"]==wins=={
        "legacy_on":0,"quiet_rearm_off":2,"quiet_rearm_shuffled":2}
    assert cohort["progression_rule_met"] is False
    receipt={"status":"passed","runs":32,"frozen_note_outcomes":frozen_count,
             "game_action_records_replayed":action_count,
             "quiet_readout_disarms":disarm_count,"quiet_readout_rearms":rearm_count,
             "legacy_reference_matches":8,"protocol_sha256":sha(PROTOCOL),
             "ledger_sha256":sha(ledger),"result_sha256":sha(OUT/"result.json")}
    (OUT/"audit.json").write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(receipt,indent=2))


if __name__=="__main__":
    main()
