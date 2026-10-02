"""Independent action, trace-reset and frozen-metric audit."""

from __future__ import annotations

import json
import statistics
from pathlib import Path

from project_b.osu import GameEnvironment, KeyAction, KeyActionKind, TapNote
from scripts.checkpoint_controls import shuffled_utilities
from scripts.long_continuation import sha
from scripts.overnight_synthetic import map_for_seed


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/null_press_trace_boundary_development.json"
OVERNIGHT = ROOT / "configs/overnight_synthetic.json"
OLD = ROOT / "docs/figures/overnight_synthetic/runs.jsonl"
OUT = ROOT / "docs/figures/null_press_trace_boundary_development"
CONDITIONS = ("legacy_on", "boundary_reset_on", "boundary_reset_off",
              "boundary_reset_shuffled")


def main() -> None:
    spec = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    overnight = json.loads(OVERNIGHT.read_text(encoding="utf-8"))
    result = json.loads((OUT / "result.json").read_text(encoding="utf-8"))
    meta = json.loads((OUT / "meta.json").read_text(encoding="utf-8"))
    status = json.loads((OUT / "status.json").read_text(encoding="utf-8"))
    ledger_path = OUT / "runs.jsonl"
    assert result["status"] == status["status"] == "complete"
    assert result["protocol_sha256"] == meta["protocol_sha256"] == sha(PROTOCOL)
    assert result["ledger_sha256"] == sha(ledger_path)
    assert status["result_sha256"] == sha(OUT / "result.json")
    assert meta["overnight_config_sha256"] == sha(OVERNIGHT)
    assert all(sha(ROOT/p) == h for p,h in meta["source_sha256"].items())
    assert spec["seeds"] == list(range(1000,1008))
    assert spec["conditions"] == list(CONDITIONS)
    rows = {}
    for line in ledger_path.read_text(encoding="utf-8").splitlines():
        x = json.loads(line)
        key = (x["seed"],x["condition"])
        assert key not in rows and key[0] in spec["seeds"] and key[1] in CONDITIONS
        assert x["protocol_sha256"] == sha(PROTOCOL)
        rows[key] = x
    assert len(rows) == status["completed_runs"] == 32
    old = {x["key"]: x for x in (json.loads(line) for line in OLD.read_text(encoding="utf-8").splitlines())}
    action_count = frozen_count = reset_count = 0
    for seed in spec["seeds"]:
        times,gains = map_for_seed(seed,40,overnight)
        on = rows[(seed,"boundary_reset_on")]
        schedule = shuffled_utilities(tuple(e["game_utility"] for e in on["summary"]["events"][:24]),seed)
        for condition in CONDITIONS:
            x = rows[(seed,condition)]
            cfg = x["resolved_config"]
            assert x["note_times_us"] == cfg["explicit_note_times_us"] == list(times)
            assert x["cue_gains"] == cfg["cue_gain_by_note"] == list(gains)
            assert cfg["seed"] == seed and cfg["note_count"] == 40
            assert cfg["training_notes"] == 24 and cfg["readout_on_threshold"] == 10
            assert cfg["plasticity_enabled"] == (condition != "boundary_reset_off")
            assert cfg["reward_utility_schedule"] == (list(schedule)
                    if condition == "boundary_reset_shuffled" else None)
            game = GameEnvironment(tuple(TapNote(f"lane1-{i}",0,t) for i,t in enumerate(times)))
            for a in x["actions"]:
                record = game.apply_action(KeyAction(a["time_us"],0,KeyActionKind(a["kind"])))
                assert record.disposition.value == a["disposition"]
                assert record.note_id == a["note_id"]
                if a["nearest_visible_note_index"] is not None:
                    i = a["nearest_visible_note_index"]
                    assert a["signed_note_offset_us"] == a["time_us"]-times[i]
                    assert a["phase"] == ("training" if i < 24 else "frozen")
                action_count += 1
            judged = game.finish().judgements
            assert len(judged) == len(x["summary"]["events"]) == 40
            for i,(j,e) in enumerate(zip(judged,x["summary"]["events"])):
                assert j.note_id == f"lane1-{i}"
                assert j.judgement.name == e["judgement"]
                assert j.hit_error_us == e["hit_error_us"]
                assert e["phase"] == ("training" if i < 24 else "frozen")
                if i >= 24:
                    assert e["weight_changes"] == 0
                    frozen_count += 1
            frozen = x["summary"]["events"][24:]
            good = sum(e["hit_value"] >= 200 for e in frozen)
            assert x["summary"]["frozen_good_or_better_percent"] == 100*good/16
            hits = [abs(e["hit_error_us"])/1000 for e in frozen
                    if e["judgement"] != "MISS" and e["hit_error_us"] is not None]
            assert x["summary"]["frozen_mean_absolute_error_ms"] == (statistics.mean(hits) if hits else None)
            frozen_down = [a for a in x["actions"] if a["phase"] == "frozen" and a["kind"] == "down"]
            assert x["action_metrics"]["frozen_down_count"] == len(frozen_down)
            assert x["action_metrics"]["frozen_null_down_count"] == sum(a["disposition"] == "null_press"
                                                                      for a in frozen_down)
            assert x["action_metrics"]["frozen_early_miss_down_count"] == sum(a["disposition"] == "early_miss"
                                                                            for a in frozen_down)
            first = x["action_metrics"]["frozen_first_down_offsets_us"]
            assert len(first) == 16
            for i,f in enumerate(first,24):
                candidates = [a for a in frozen_down if a["nearest_visible_note_index"] == i]
                assert f["note_index"] == i and f["down_count"] == len(candidates)
                assert f["first_down_offset_us"] == (candidates[0]["signed_note_offset_us"]
                                                    if candidates else None)
                assert f["first_down_disposition"] == (candidates[0]["disposition"]
                                                       if candidates else None)
            assert x["action_metrics"]["frozen_silent_note_count"] == sum(f["down_count"] == 0 for f in first)
            training_null = [a["time_us"] for a in x["actions"] if a["phase"] == "training"
                             and a["disposition"] == "null_press"]
            reset_times = [e["time_us"] for e in x["trace_reset_events"]]
            if condition in ("boundary_reset_on","boundary_reset_shuffled"):
                assert reset_times == training_null
                assert all(e["disposition"] == "null_press"
                           and e["presynaptic_trace_count"] == 40
                           and e["selected_edge_trace_count"] == 480
                           and e["presynaptic_trace_l1_before"] >= 0
                           and e["eligibility_l1_before"] >= 0
                           and e["weights_changed_by_reset"] == 0 for e in x["trace_reset_events"])
            else:
                assert reset_times == []
            reset_count += len(reset_times)
            weights = x["final_plastic_weights_mv"]
            assert len(weights) == 480 and all(0 <= w <= 2 for w in weights)
            assert x["final_upper_bound_edges"] == sum(w == 2 for w in weights)
            assert x["final_lower_bound_edges"] == sum(w == 0 for w in weights)
            if condition == "boundary_reset_off":
                assert all(w == 0.04 for w in weights)
            if condition == "legacy_on":
                assert x["summary"] == old[f"dev:10:{seed}:on"]["summary"]
    cohort = result["cohort"]
    for condition in CONDITIONS:
        cases = [rows[(s,condition)] for s in spec["seeds"]]
        assert cohort["conditions"][condition]["mean_frozen_good_or_better_percent"] == statistics.mean(
            x["summary"]["frozen_good_or_better_percent"] for x in cases)
        hits = [abs(e["hit_error_us"])/1000 for x in cases
                for e in x["summary"]["events"][24:] if e["judgement"] != "MISS"
                and e["hit_error_us"] is not None]
        assert cohort["conditions"][condition]["pooled_frozen_hit_mae_ms"] == (statistics.mean(hits) if hits else None)
        assert cohort["conditions"][condition]["frozen_null_down_count"] == sum(
            x["action_metrics"]["frozen_null_down_count"] for x in cases)
    wins = {other: sum(rows[(s,"boundary_reset_on")]["summary"]["frozen_good_or_better_percent"]
                       > rows[(s,other)]["summary"]["frozen_good_or_better_percent"]
                       for s in spec["seeds"])
            for other in ("legacy_on","boundary_reset_off","boundary_reset_shuffled")}
    assert cohort["strict_good_plus_wins"] == wins == {
        "legacy_on":1,"boundary_reset_off":4,"boundary_reset_shuffled":4}
    assert cohort["progression_rule_met"] is False
    receipt = {"status":"passed","seeds":spec["seeds"],"runs":32,
               "action_records_replayed":action_count,"frozen_note_outcomes":frozen_count,
               "training_trace_resets":reset_count,"legacy_reference_matches":8,
               "protocol_sha256":sha(PROTOCOL),"ledger_sha256":sha(ledger_path),
               "result_sha256":sha(OUT / "result.json")}
    (OUT / "audit.json").write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(receipt,indent=2))


if __name__ == "__main__":
    main()
