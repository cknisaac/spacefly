"""Independent saved-ledger, action/game, intervention and metric audit."""

from __future__ import annotations

import json
import math
import statistics
from pathlib import Path

from project_b.osu import GameEnvironment, KeyAction, KeyActionKind, TapNote
from scripts.checkpoint_controls import shuffled_utilities
from scripts.long_continuation import sha
from scripts.overnight_synthetic import map_for_seed


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/null_press_action_cost_development.json"
OVERNIGHT = ROOT / "configs/overnight_synthetic.json"
OLD = ROOT / "docs/figures/overnight_synthetic/runs.jsonl"
OUT = ROOT / "docs/figures/null_press_action_cost_development"
CONDITIONS = ("legacy_on", "null_cost_on", "null_cost_off", "null_cost_shuffled")


def main() -> None:
    spec = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    overnight = json.loads(OVERNIGHT.read_text(encoding="utf-8"))
    result = json.loads((OUT / "result.json").read_text(encoding="utf-8"))
    status = json.loads((OUT / "status.json").read_text(encoding="utf-8"))
    meta = json.loads((OUT / "meta.json").read_text(encoding="utf-8"))
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
        key = (x["seed"], x["condition"])
        assert key not in rows and key[0] in spec["seeds"] and key[1] in CONDITIONS
        assert x["protocol_sha256"] == sha(PROTOCOL)
        rows[key] = x
    assert len(rows) == 32 == status["completed_runs"]
    old = {x["key"]: x for x in (json.loads(line) for line in OLD.read_text(encoding="utf-8").splitlines())}
    all_actions = cost_events = frozen_events = 0
    for seed in spec["seeds"]:
        times, gains = map_for_seed(seed, 40, overnight)
        on = rows[(seed,"null_cost_on")]
        scheduled = shuffled_utilities(tuple(x["game_utility"] for x in on["summary"]["events"][:24]), seed)
        for condition in CONDITIONS:
            x = rows[(seed,condition)]
            assert x["note_times_us"] == list(times)
            assert x["cue_gains"] == list(gains)
            cfg = x["resolved_config"]
            assert cfg["seed"] == seed and cfg["note_count"] == 40
            assert cfg["training_notes"] == 24 and cfg["readout_on_threshold"] == 10
            assert cfg["explicit_note_times_us"] == list(times)
            assert cfg["cue_gain_by_note"] == list(gains)
            assert cfg["plasticity_enabled"] == (condition != "null_cost_off")
            assert cfg["reward_utility_schedule"] == (list(scheduled)
                    if condition == "null_cost_shuffled" else None)
            assert len(x["summary"]["events"]) == 40
            assert all(e["phase"] == ("training" if i < 24 else "frozen")
                       for i,e in enumerate(x["summary"]["events"]))
            assert all(e["weight_changes"] == 0 for e in x["summary"]["events"][24:])
            game = GameEnvironment(tuple(TapNote(f"lane1-{i}", 0, t)
                                         for i,t in enumerate(times)))
            for a in x["actions"]:
                k = KeyActionKind(a["kind"])
                actual = game.apply_action(KeyAction(a["time_us"], 0, k))
                assert actual.disposition.value == a["disposition"]
                assert actual.note_id == a["note_id"]
                if a["nearest_visible_note_index"] is not None:
                    i = a["nearest_visible_note_index"]
                    assert a["signed_note_offset_us"] == a["time_us"] - times[i]
                    assert a["phase"] == ("training" if i < 24 else "frozen")
                all_actions += 1
            judgements = game.finish().judgements
            assert len(judgements) == 40
            for i,(j,e) in enumerate(zip(judgements,x["summary"]["events"])):
                assert j.note_id == f"lane1-{i}"
                assert j.judgement.name == e["judgement"]
                assert j.hit_error_us == e["hit_error_us"]
                frozen_events += i >= 24
            frozen = x["summary"]["events"][24:]
            good = sum(e["hit_value"] >= 200 for e in frozen)
            assert x["summary"]["frozen_good_or_better_percent"] == 100*good/16
            hits = [abs(e["hit_error_us"])/1000 for e in frozen
                    if e["judgement"] != "MISS" and e["hit_error_us"] is not None]
            expected_mae = statistics.mean(hits) if hits else None
            assert x["summary"]["frozen_mean_absolute_error_ms"] == expected_mae
            frozen_down = [a for a in x["actions"] if a["phase"] == "frozen"
                           and a["kind"] == "down"]
            assert x["action_metrics"]["frozen_down_count"] == len(frozen_down)
            assert x["action_metrics"]["frozen_null_down_count"] == sum(
                a["disposition"] == "null_press" for a in frozen_down)
            assert x["action_metrics"]["frozen_early_miss_down_count"] == sum(
                a["disposition"] == "early_miss" for a in frozen_down)
            first = x["action_metrics"]["frozen_first_down_offsets_us"]
            assert len(first) == 16
            for i,f in enumerate(first,24):
                candidates = [a for a in frozen_down if a["nearest_visible_note_index"] == i]
                assert f["note_index"] == i and f["down_count"] == len(candidates)
                assert f["first_down_offset_us"] == (candidates[0]["signed_note_offset_us"]
                                                    if candidates else None)
                assert f["first_down_disposition"] == (candidates[0]["disposition"]
                                                       if candidates else None)
            assert x["action_metrics"]["frozen_silent_note_count"] == sum(
                f["down_count"] == 0 for f in first)
            training_null_times = [a["time_us"] for a in x["actions"]
                                   if a["phase"] == "training"
                                   and a["disposition"] == "null_press"]
            observed_cost_times = [e["time_us"] for e in x["null_cost_events"]]
            if condition in ("null_cost_on", "null_cost_shuffled"):
                assert observed_cost_times == training_null_times
                assert all(e["dopamine_like_amplitude"] == -1.0
                           and e["disposition"] == "null_press"
                           and e["changed_edge_count"] == len(e["edge_slots"])
                           and e["applied_l1_mv"] >= 0 for e in x["null_cost_events"])
            else:
                assert observed_cost_times == []
            cost_events += len(observed_cost_times)
            assert math.isclose(x["null_cost_applied_l1_mv_total"],
                                sum(e["applied_l1_mv"] for e in x["null_cost_events"]),
                                abs_tol=1e-9)
            weights = x["final_plastic_weights_mv"]
            assert len(weights) == 480 and all(0 <= w <= 2 for w in weights)
            assert x["final_upper_bound_edges"] == sum(w == 2 for w in weights)
            assert x["final_lower_bound_edges"] == sum(w == 0 for w in weights)
            if condition == "null_cost_off":
                assert all(w == 0.04 for w in weights)
            if condition == "legacy_on":
                assert x["summary"] == old[f"dev:10:{seed}:on"]["summary"]
    cohort = result["cohort"]
    for condition in CONDITIONS:
        cases = [rows[(s,condition)] for s in spec["seeds"]]
        good = [x["summary"]["frozen_good_or_better_percent"] for x in cases]
        assert cohort["conditions"][condition]["mean_frozen_good_or_better_percent"] == statistics.mean(good)
        hits = [abs(e["hit_error_us"])/1000 for x in cases
                for e in x["summary"]["events"][24:] if e["judgement"] != "MISS"
                and e["hit_error_us"] is not None]
        expected_mae = statistics.mean(hits) if hits else None
        assert cohort["conditions"][condition]["pooled_frozen_hit_mae_ms"] == expected_mae
        assert cohort["conditions"][condition]["frozen_null_down_count"] == sum(
            x["action_metrics"]["frozen_null_down_count"] for x in cases)
    wins = {other: sum(rows[(s,"null_cost_on")]["summary"]["frozen_good_or_better_percent"]
                       > rows[(s,other)]["summary"]["frozen_good_or_better_percent"]
                       for s in spec["seeds"])
            for other in ("legacy_on", "null_cost_off", "null_cost_shuffled")}
    assert cohort["strict_good_plus_wins"] == wins == {
        "legacy_on": 1, "null_cost_off": 5, "null_cost_shuffled": 5}
    assert cohort["progression_rule_met"] is False
    receipt = {"status": "passed", "seeds": spec["seeds"], "runs": len(rows),
               "action_records_replayed": all_actions, "frozen_note_outcomes": frozen_events,
               "training_null_cost_events": cost_events,
               "legacy_reference_matches": len(spec["seeds"]),
               "protocol_sha256": sha(PROTOCOL), "ledger_sha256": sha(ledger_path),
               "result_sha256": sha(OUT / "result.json")}
    (OUT / "audit.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
