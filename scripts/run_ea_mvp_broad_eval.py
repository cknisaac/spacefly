"""Frozen EA-13 broad-pattern evaluation using existing retained weights only."""

from __future__ import annotations

import gzip
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from project_b.ea_mvp.continuous_chords import ContinuousChordFlyPolicy, play_equal_time_chords
from project_b.ea_mvp.continuous_holds import ContinuousHoldFlyPolicy, play_sequential_holds
from project_b.ea_mvp.continuous_multilane import (
    ContinuousFourLaneFlyPolicy, play_continuous_multilane_taps,
)
from project_b.malecns_continuous_position_learning.online_policy import load_position_config
from project_b.osu.config import OsuConfig
from project_b.osu.types import HoldNote, KeyActionKind, TapNote

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/ea_mvp_broad_eval_v1.json"
OUTPUT = ROOT / "runs/ea_mvp/broad_eval_v1.json"
ARMS = ("learning_on", "shuffled_teaching", "untrained")
SEEDS = (907, 1009, 1103)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _score_result(row: dict) -> bool:
    return row["result"] in {"PERFECT", "GREAT", "GOOD"}


def _play_case(config: dict, weights: list[float], protocol: dict, pattern: str) -> dict:
    game_config = OsuConfig(od=protocol["fixed_conditions"]["od"],
                            ruleset=protocol["fixed_conditions"]["ruleset"])
    lead = protocol["fixed_conditions"]["visible_lead_us"]
    if pattern == "dense_lane_switch_taps":
        notes = tuple(TapNote(**row) for row in protocol["fresh_patterns"][pattern]["notes"])
        policy = ContinuousFourLaneFlyPolicy(config, weights)
        trace = play_continuous_multilane_taps(notes, game_config, policy,
                                               visible_lead_us=lead)
        expected = [(note.lane, note.time_us) for note in notes]
        downs = [row for row in trace.actions if row.kind is KeyActionKind.DOWN]
        ups = [row for row in trace.actions if row.kind is KeyActionKind.UP]
        checks = {
            "correct_downs_in_window": len(downs) == len(notes) and all(
                (row.lane, row.time_us) == (lane, time) or
                (row.lane == lane and abs(row.time_us - time) <= 73_500)
                for row, (lane, time) in zip(downs, expected)),
            "one_up_per_down_no_extra_actions": len(ups) == len(downs)
                and len(trace.actions) == 2 * len(notes),
            "all_notes_good_or_better": len(trace.results) == len(notes)
                and all(_score_result(asdict(row)) for row in trace.results),
            "weights_unchanged": tuple(weights) == policy.weights,
        }
    elif pattern == "new_chord_lane_sets":
        groups = tuple(tuple(TapNote(**row) for row in group)
                       for group in protocol["fresh_patterns"][pattern]["chords"])
        notes = tuple(note for group in groups for note in group)
        policy = ContinuousChordFlyPolicy(config, weights)
        trace = play_equal_time_chords(groups, game_config, policy, visible_lead_us=lead)
        expected = [(note.lane, note.time_us) for note in sorted(notes,
                    key=lambda item: (item.time_us, item.lane))]
        downs = sorted((row for row in trace.actions if row.kind is KeyActionKind.DOWN),
                       key=lambda row: (row.time_us, row.lane))
        ups = [row for row in trace.actions if row.kind is KeyActionKind.UP]
        checks = {
            "one_correct_down_per_note_in_window": len(downs) == len(notes) and all(
                row.lane == lane and abs(row.time_us - (time + 1000)) <= 73_500
                for row, (lane, time) in zip(downs, expected)),
            "one_up_per_down_no_extra_actions": len(ups) == len(downs)
                and len(trace.actions) == 2 * len(notes),
            "all_notes_good_or_better": len(trace.results) == len(notes)
                and all(_score_result(asdict(row)) for row in trace.results),
            "weights_unchanged": tuple(weights) == policy.weights,
        }
    elif pattern == "new_sequential_hold_lengths":
        notes = tuple(HoldNote(**row) for row in protocol["fresh_patterns"][pattern]["notes"])
        policy = ContinuousHoldFlyPolicy(config, weights)
        trace = play_sequential_holds(notes, game_config, policy, visible_lead_us=lead)
        downs = [row for row in trace.actions if row.kind is KeyActionKind.DOWN]
        ups = [row for row in trace.actions if row.kind is KeyActionKind.UP]
        scoring = [asdict(row) for row in trace.results if row.component in {"head", "tail"}]
        body_breaks = [row for row in trace.results if row.component == "body"
                       and row.result == "COMBO_BREAK"]
        checks = {
            "exact_head_downs_and_tail_ups": len(downs) == len(ups) == len(notes)
                and [(row.lane, row.time_us) for row in downs]
                    == [(note.lane, note.time_us + 1000) for note in notes]
                and [(row.lane, row.time_us) for row in ups]
                    == [(note.lane, note.end_time_us) for note in notes],
            "all_head_tail_judgements_perfect": len(scoring) == 2 * len(notes)
                and all(row["result"] == "PERFECT" for row in scoring),
            "no_body_combo_break": not body_breaks,
            "weights_unchanged": tuple(weights) == policy.weights,
        }
    else:
        raise ValueError(f"unknown pattern: {pattern}")

    record = {
        "actions": [asdict(row) for row in trace.actions],
        "results": [asdict(row) for row in trace.results],
        "score": asdict(trace.score),
        "neural_reset_count": trace.neural_reset_count,
        "readout_rearm_count": trace.readout_rearm_count,
        "spike_count": trace.spike_count,
        "checks": checks,
        "status": "PASS" if all(checks.values()) else "FAIL",
    }
    return record


def main() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if protocol["fixed_conditions"]["seeds"] != list(SEEDS):
        raise RuntimeError("protocol seeds changed")
    if protocol["fixed_conditions"]["arms"] != list(ARMS):
        raise RuntimeError("protocol arms changed")
    for relative, expected in protocol["code_sha256"].items():
        if sha(ROOT / relative) != expected:
            raise RuntimeError(f"frozen code changed: {relative}")
    if sha(ROOT / protocol["source_config"]) != protocol["source_config_sha256"]:
        raise RuntimeError("frozen neural configuration changed")

    config = load_position_config(ROOT, protocol["source_config"])
    result = {"protocol_id": protocol["protocol_id"],
              "protocol_sha256": sha(PROTOCOL), "seeds": {}, "checks": {}}
    patterns = tuple(protocol["fresh_patterns"])
    all_replays_exact = True
    all_trained_cases_pass = True
    all_untrained_controls_pass = True
    for seed in SEEDS:
        seed_result = result["seeds"].setdefault(str(seed), {})
        for pattern in patterns:
            pattern_result = seed_result.setdefault(pattern, {})
            for arm in ARMS:
                receipt = ROOT / f"runs/ea_mvp/confirmation_fixed_v1/seed_{seed}_{arm}.json.gz"
                if sha(receipt) != protocol["weight_receipts"][str(seed)][arm]["sha256"]:
                    raise RuntimeError(f"frozen weight receipt changed: {receipt.name}")
                with gzip.open(receipt, "rt", encoding="utf-8") as stream:
                    source = json.load(stream)
                weights = source["initial_weights"] if arm == "untrained" else source["final_weights"]
                repeats = [_play_case(config, weights, protocol, pattern)
                           for _ in range(protocol["fixed_conditions"]["replays_per_case"])]
                exact = all(item == repeats[0] for item in repeats)
                pattern_result[arm] = {"record": repeats[0], "exact_replay": exact,
                                       "source_arm": source["arm"],
                                       "source_local_integrity": source.get("local_integrity")}
                all_replays_exact &= exact
                if arm == "learning_on":
                    all_trained_cases_pass &= repeats[0]["status"] == "PASS"
                if arm == "untrained":
                    silent = not repeats[0]["actions"]
                    scored = [row for row in repeats[0]["results"]
                              if pattern != "new_sequential_hold_lengths"
                              or row["component"] in {"head", "tail"}]
                    missed = bool(scored) and all(row["result"] == "MISS" for row in scored)
                    control_ok = silent and missed
                    pattern_result[arm]["control_checks"] = {
                        "silent": silent, "all_target_objects_missed": missed,
                        "pass": control_ok,
                    }
                    all_untrained_controls_pass &= control_ok
    result["checks"] = {
        "all_trained_pattern_cases_pass": all_trained_cases_pass,
        "all_untrained_controls_silent_and_missed": all_untrained_controls_pass,
        "all_replays_exact": all_replays_exact,
    }
    result["status"] = "PASS" if all(result["checks"].values()) else "FAIL"
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True, default=str) + "\n",
                      encoding="utf-8")
    summary = {"status": result["status"], "checks": result["checks"], "patterns": {}}
    for pattern in patterns:
        summary["patterns"][pattern] = {}
        for arm in ARMS:
            cases = [result["seeds"][str(seed)][pattern][arm]["record"] for seed in SEEDS]
            summary["patterns"][pattern][arm] = {
                "case_passes": sum(row["status"] == "PASS" for row in cases),
                "case_count": len(cases),
                "perfect_objects": sum(sum(x["result"] == "PERFECT" for x in row["results"]
                                             if pattern != "new_sequential_hold_lengths"
                                             or x["component"] in {"head", "tail"})
                                        for row in cases),
            }
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
