"""Independent historical reproduction, game-action and note-pairing audit."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from project_b.osu import GameEnvironment, KeyAction, KeyActionKind, TapNote
from scripts.long_continuation import sha
from scripts.overnight_synthetic import map_for_seed


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/heldout_first_action_audit.json"
OVERNIGHT = ROOT / "configs/overnight_synthetic.json"
OLD = ROOT / "docs/figures/overnight_synthetic/runs.jsonl"
OUT = ROOT / "docs/figures/heldout_first_action_audit"


def main() -> None:
    spec = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    overnight = json.loads(OVERNIGHT.read_text(encoding="utf-8"))
    result = json.loads((OUT / "result.json").read_text(encoding="utf-8"))
    meta = json.loads((OUT / "meta.json").read_text(encoding="utf-8"))
    status = json.loads((OUT / "status.json").read_text(encoding="utf-8"))
    ledger = OUT / "runs.jsonl"
    assert result["status"] == status["status"] == "complete"
    assert result["protocol_sha256"] == meta["protocol_sha256"] == sha(PROTOCOL)
    assert result["ledger_sha256"] == sha(ledger)
    assert status["result_sha256"] == sha(OUT / "result.json")
    assert meta["overnight_config_sha256"] == sha(OVERNIGHT)
    assert meta["original_ledger_sha256"] == sha(OLD)
    assert all(sha(ROOT/p) == h for p,h in meta["source_sha256"].items())
    seeds = list(range(2000,2032))
    assert result["seeds"] == seeds
    old = {x["key"]:x for x in (json.loads(line) for line in OLD.read_text(encoding="utf-8").splitlines())}
    rows = {}
    for line in ledger.read_text(encoding="utf-8").splitlines():
        x = json.loads(line)
        assert x["seed"] not in rows and x["seed"] in seeds
        assert x["protocol_sha256"] == sha(PROTOCOL)
        rows[x["seed"]] = x
    assert len(rows) == status["completed_seeds"] == 32
    good_total = good_after_null = good_first = 0
    null_down_total = early_miss_down_total = silent_notes = all_actions = 0
    first_dispositions = Counter()
    per_seed = {}
    for seed in seeds:
        x = rows[seed]
        times,gains = map_for_seed(seed,40,overnight)
        assert x["note_times_us"] == x["resolved_config"]["explicit_note_times_us"] == list(times)
        assert x["cue_gains"] == x["resolved_config"]["cue_gain_by_note"] == list(gains)
        assert x["resolved_config"] == old[f"heldout:10:{seed}:on"]["resolved_config"]
        assert x["historical_summary_exact_match"] is True
        assert x["summary"] == old[f"heldout:10:{seed}:on"]["summary"]
        game = GameEnvironment(tuple(TapNote(f"lane1-{i}",0,t) for i,t in enumerate(times)))
        actions = x["actions"]
        for a in actions:
            actual = game.apply_action(KeyAction(a["time_us"],0,KeyActionKind(a["kind"])))
            assert actual.disposition.value == a["disposition"]
            assert actual.note_id == a["note_id"]
            associations = [i for i,t in enumerate(times)
                            if t-500_000 <= a["time_us"] <= t+game.windows.expiry_offset_us]
            assert len(associations) <= 1
            i = associations[0] if associations else None
            assert a["nearest_visible_note_index"] == i
            assert a["signed_note_offset_us"] == (a["time_us"]-times[i] if i is not None else None)
            assert a["phase"] == ("training" if i is not None and i < 24
                                  else "frozen" if i is not None else "outside_note_window")
            all_actions += 1
        judged = game.finish().judgements
        assert len(judged) == len(x["summary"]["events"]) == 40
        for i,(j,e) in enumerate(zip(judged,x["summary"]["events"])):
            assert j.note_id == f"lane1-{i}" and j.judgement.name == e["judgement"]
            assert j.hit_error_us == e["hit_error_us"]
            if i >= 24:
                assert e["weight_changes"] == 0
        seed_good = seed_after_null = seed_first = 0
        for i in range(24,40):
            item = x["frozen_note_actions"][i-24]
            downs = [a for a in actions if a["kind"] == "down"
                     and a["nearest_visible_note_index"] == i]
            hit_action = next((a for a in downs if a["note_id"] == f"lane1-{i}"),None)
            prior_null = sum(a["disposition"] == "null_press" for a in downs
                             if hit_action is not None and a["time_us"] < hit_action["time_us"])
            e = x["summary"]["events"][i]
            good = e["hit_value"] >= 200
            assert item["note_index"] == i
            assert item["judgement"] == e["judgement"]
            assert item["hit_value"] == e["hit_value"]
            assert item["hit_error_us"] == e["hit_error_us"]
            assert item["first_down_time_us"] == (downs[0]["time_us"] if downs else None)
            assert item["first_down_offset_us"] == (downs[0]["signed_note_offset_us"] if downs else None)
            assert item["first_down_disposition"] == (downs[0]["disposition"] if downs else None)
            assert item["down_count"] == len(downs)
            assert item["judged_down_time_us"] == (hit_action["time_us"] if hit_action else None)
            assert item["judged_down_position"] == (downs.index(hit_action)+1 if hit_action else None)
            assert item["prior_null_down_count"] == prior_null
            assert item["good_plus_after_null"] == (good and prior_null > 0)
            assert item["good_plus_on_first_down"] == (good and bool(downs) and hit_action == downs[0])
            first_dispositions[item["first_down_disposition"]] += 1
            seed_good += good
            seed_after_null += good and prior_null > 0
            seed_first += good and bool(downs) and hit_action == downs[0]
            silent_notes += not downs
            null_down_total += sum(a["disposition"] == "null_press" for a in downs)
            early_miss_down_total += sum(a["disposition"] == "early_miss" for a in downs)
        assert x["summary"]["frozen_good_or_better_percent"] == 100*seed_good/16
        assert x["action_metrics"]["frozen_null_down_count"] == sum(
            a["disposition"] == "null_press" for a in actions if a["phase"] == "frozen" and a["kind"] == "down")
        per_seed[str(seed)] = {"good_plus":seed_good,
                              "good_plus_after_null":seed_after_null,
                              "good_plus_on_first_down":seed_first}
        good_total += seed_good
        good_after_null += seed_after_null
        good_first += seed_first
    agg = result["aggregate"]
    assert agg["frozen_note_count"] == 512
    assert agg["frozen_good_plus_count"] == good_total == 236
    assert agg["good_plus_after_same_note_null_count"] == good_after_null == 233
    assert agg["good_plus_on_first_down_count"] == good_first == 3
    assert agg["good_plus_after_same_note_null_fraction"] == good_after_null/good_total
    assert agg["frozen_null_down_count"] == null_down_total == 304
    assert agg["frozen_early_miss_down_count"] == early_miss_down_total == 143
    assert agg["frozen_silent_note_count"] == silent_notes == 0
    assert agg["first_down_disposition_counts"] == {
        "null_press":first_dispositions["null_press"],
        "early_miss":first_dispositions["early_miss"],
        "hit":first_dispositions["hit"],
        "null":first_dispositions[None]}
    assert agg["per_seed"] == per_seed
    receipt = {"status":"passed","seeds":32,"frozen_notes":512,
               "historical_summary_matches":32,"game_action_records_replayed":all_actions,
               "good_plus":good_total,"good_plus_after_same_note_null":good_after_null,
               "good_plus_on_first_down":good_first,
               "protocol_sha256":sha(PROTOCOL),"ledger_sha256":sha(ledger),
               "result_sha256":sha(OUT/"result.json")}
    (OUT/"audit.json").write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(receipt,indent=2))


if __name__ == "__main__":
    main()
