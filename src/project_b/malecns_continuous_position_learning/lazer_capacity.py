"""Frozen, task-free controllability gate for the one-lane lazer MVP."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from project_b.malecns_continuous_position_learning.online_policy import (
    OnlineFlyPolicy,
    PositionObservation,
    load_position_config,
)
from project_b.osu import KeyActionKind, TapNote, load_config
from project_b.osu.adapter import HeadlessManiaTapAdapter
from project_b.osu.feedback import NoteCue
from project_b.osu.windows import ManiaHitWindows


CAPACITY_CONFIG_DEFAULT = "configs/lazer_mvp_capacity.json"
RESULT_DEFAULT = "runs/lazer_mvp_capacity/result.json"
NOTE_ID = "capacity-note"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_inputs(root: Path, config_path: str) -> tuple[dict, dict, dict]:
    root = Path(root)
    stage = json.loads((root / config_path).read_text(encoding="utf-8"))
    candidate_path = stage["candidate_config"]
    game_path = stage["game_config"]
    if _sha256(root / candidate_path) != stage["candidate_config_sha256"]:
        raise ValueError("frozen position-policy config changed after capacity-plan freeze")
    if _sha256(root / game_path) != stage["game_config_sha256"]:
        raise ValueError("frozen lazer game config changed after capacity-plan freeze")
    candidate = load_position_config(root, candidate_path)
    game = load_config(root / game_path)
    if (game.ruleset != "lazer" or game.keys != stage["game"]["keys"]
            or int(game.od) != stage["game"]["od"]):
        raise ValueError("loaded game config differs from the frozen capacity plan")
    if (stage["game"]["dt_us"] != candidate["overlay"]["lif"]["dt_us"]
            or stage["game"]["approach_duration_us"] != stage["game"]["note_time_us"]):
        raise ValueError("capacity timeline must match the frozen integration step and approach")
    if stage["intervention"]["maximum_local_ltd_fraction_of_original"] != candidate[
            "training"]["ltd"]["minimum_fraction"]:
        raise ValueError("capacity intervention differs from the inherited LTD floor")
    expected_conditions = {
        "baseline_initial", "plasticity_off",
        "target_good_window_floor", "matched_out_of_window_floor",
    }
    if {row["id"] for row in stage["conditions"]} != expected_conditions:
        raise ValueError("capacity condition set differs from the frozen four-arm panel")

    cells = candidate["circuit"]["selected_kcs"]
    source_ids = [int(cell["source_id"]) for cell in cells]
    target_ids = [source_id for source_id, cell in zip(source_ids, cells)
                  if cell["preferred_position"] <= stage["intervention"][
                      "target_preferred_position_max_inclusive"]]
    center = stage["intervention"]["matched_out_of_window_control_center"]
    source_order = sorted(
        range(len(cells)),
        key=lambda i: (abs(cells[i]["preferred_position"] - center), i),
    )
    matched_ids = [source_ids[i] for i in source_order[:len(target_ids)]]
    if target_ids != stage["intervention"]["target_kc_source_ids"]:
        raise ValueError("frozen target KC IDs differ from preferred-position selection")
    if matched_ids != stage["intervention"]["out_of_window_control_kc_source_ids"]:
        raise ValueError("frozen control KC IDs differ from matched-size selection")
    return stage, candidate, {"game": game, "source_ids": source_ids}


def _weights_for_condition(candidate: dict, stage: dict,
                           condition: str) -> tuple[list[float], list[int]]:
    cells = candidate["circuit"]["selected_kcs"]
    total = sum(cell["plastic_contact_rows"] for cell in cells)
    original = [cell["plastic_contact_rows"] / total for cell in cells]
    if condition in ("baseline_initial", "plasticity_off"):
        return original, []
    intervention = stage["intervention"]
    if condition == "target_good_window_floor":
        selected = set(intervention["target_kc_source_ids"])
    elif condition == "matched_out_of_window_floor":
        selected = set(intervention["out_of_window_control_kc_source_ids"])
    else:
        raise ValueError(f"unknown capacity condition: {condition}")
    floor = intervention["maximum_local_ltd_fraction_of_original"]
    weights = [weight * floor if int(cell["source_id"]) in selected else weight
               for cell, weight in zip(cells, original)]
    return weights, sorted(selected)


def _run_note(stage: dict, candidate: dict, game_config,
              condition: str, weights: list[float], clamped_ids: list[int]) -> dict:
    game = stage["game"]
    dt_us = game["dt_us"]
    duration_us = game["approach_duration_us"]
    note_time_us = game["note_time_us"]
    policy = OnlineFlyPolicy(candidate, lane=game["lane"], weights=weights)
    observations = [PositionObservation(True, game["lane"], 1.0)]
    for time_us in range(dt_us, duration_us + dt_us, dt_us):
        position = 1.0 - time_us / duration_us
        observation = PositionObservation(True, game["lane"], position)
        observations.append(observation)
    windows = ManiaHitWindows.from_od(game_config.od, game_config.ruleset)
    cue = NoteCue(NOTE_ID, game["lane"], 0, note_time_us,
                  note_time_us + windows.expiry_offset_us)
    adapter = HeadlessManiaTapAdapter(
        (TapNote(NOTE_ID, game["lane"], note_time_us),), (cue,), game_config,
        episode_start_time_us=0, observation_dt_us=dt_us,
        good_window_us=int(windows.good_ms * 1_000),
    )
    episode = adapter.run(policy, observations)
    actions = episode.game_actions
    game_result = episode.game_result
    down_actions = [action for action in actions if action.kind is KeyActionKind.DOWN]
    first_down = None
    if down_actions:
        action = down_actions[0]
        error_us = action.time_us - note_time_us
        bin_row = next((row for row in policy.decisions
                        if row.action is True and row.decision_time_us == action.time_us), None)
        judgement = next((row for row in game_result.judgements
                          if row.note_id == NOTE_ID), None)
        action_record = next(row for row in game_result.actions
                             if row.action == action)
        first_down = {
            "time_us": action.time_us,
            "error_us": error_us,
            "disposition": action_record.disposition.value,
            "readout_position": None if bin_row is None else bin_row.position,
            "result": None if judgement is None else judgement.result_name,
            "base_accuracy_value": (None if judgement is None
                                    else judgement.base_accuracy_value),
            "hit_error_us": None if judgement is None else judgement.hit_error_us,
        }

    judgement = next(row for row in game_result.judgements if row.note_id == NOTE_ID)
    event_rows = []
    for event in game_result.events:
        if hasattr(event, "judgement"):
            event_rows.append({
                "type": "judgement", "note_id": event.note_id,
                "time_us": event.event_time_us, "result": event.result_name,
                "hit_error_us": event.hit_error_us,
            })
        else:
            event_rows.append({
                "type": "action", "time_us": event.action.time_us,
                "lane": event.action.lane, "kind": event.action.kind.value,
                "disposition": event.disposition.value,
            })
    voltage_trace = policy.mbon_voltage_trace
    trace_bytes = json.dumps(voltage_trace, separators=(",", ":")).encode()
    return {
        "condition": condition,
        "weight_vector_sha256": hashlib.sha256(json.dumps(
            weights, separators=(",", ":")).encode()).hexdigest(),
        "clamped_kc_source_ids": clamped_ids,
        "clamped_weight_floor_exact": all(
            weights[i] == (candidate["circuit"]["selected_kcs"][i][
                "plastic_contact_rows"] / sum(
                    cell["plastic_contact_rows"]
                    for cell in candidate["circuit"]["selected_kcs"]))
            * stage["intervention"]["maximum_local_ltd_fraction_of_original"]
            for i, cell in enumerate(candidate["circuit"]["selected_kcs"])
            if int(cell["source_id"]) in set(clamped_ids)),
        "first_down": first_down,
        "down_count": len(down_actions),
        "up_count": sum(action.kind is KeyActionKind.UP for action in actions),
        "first_mbon_valid_time_us": policy.first_valid_time_us,
        "mbon_voltage_trace_sha256": hashlib.sha256(trace_bytes).hexdigest(),
        "position_decisions": [
            {"position": row.position, "sample_count": row.sample_count,
             "max_voltage_mv": row.max_voltage_mv, "action": row.action,
             "decision_time_us": row.decision_time_us}
            for row in policy.decisions
        ],
        "game_events": event_rows,
        "judgement": {
            "result": judgement.result_name,
            "base_accuracy_value": judgement.base_accuracy_value,
            "hit_error_us": judgement.hit_error_us,
            "event_time_us": judgement.event_time_us,
        },
    }


def run_capacity(root: Path, config_path: str = CAPACITY_CONFIG_DEFAULT) -> dict:
    """Run the frozen one-note capacity panel without any weight learning."""
    root = Path(root)
    stage, candidate, refs = _load_inputs(root, config_path)
    game_config = refs["game"]
    condition_results = {}
    for condition_row in stage["conditions"]:
        condition = condition_row["id"]
        weights, clamped_ids = _weights_for_condition(candidate, stage, condition)
        first = _run_note(stage, candidate, game_config,
                          condition, weights, clamped_ids)
        second = _run_note(stage, candidate, game_config,
                           condition, weights, clamped_ids)
        condition_results[condition] = {
            "replay_identical": first == second,
            "run": first,
        }

    baseline = condition_results["baseline_initial"]["run"]
    plasticity_off = condition_results["plasticity_off"]["run"]
    target = condition_results["target_good_window_floor"]["run"]
    wrong = condition_results["matched_out_of_window_floor"]["run"]
    target_down = target["first_down"]
    wrong_down = wrong["first_down"]
    baseline_no_condition = dict(baseline)
    plasticity_off_no_condition = dict(plasticity_off)
    baseline_no_condition.pop("condition")
    plasticity_off_no_condition.pop("condition")
    good_half_window = stage["criteria"][
        "target_exactly_one_first_down_with_abs_error_at_most_us"]
    criteria = {
        "source_hashes_match": True,
        "baseline_no_down": baseline["down_count"] == 0,
        "plasticity_off_no_down": plasticity_off["down_count"] == 0,
        "target_exactly_one_first_down_with_abs_error_at_most_us": (
            target["down_count"] == 1 and target_down is not None
            and abs(target_down["error_us"]) <= good_half_window
            and target_down["result"] in {"PERFECT", "GREAT", "GOOD"}),
        "matched_out_of_window_not_good_or_better": (
            wrong_down is None or wrong_down["result"] not in {
                "PERFECT", "GREAT", "GOOD"}),
        "all_replays_exact": all(row["replay_identical"]
                                  for row in condition_results.values()),
        "floor_is_exactly_inherited": all(
            row["run"]["clamped_weight_floor_exact"]
            for row in condition_results.values()),
        "plasticity_off_matches_baseline": (
            plasticity_off_no_condition == baseline_no_condition),
    }
    return {
        "experiment_id": stage["experiment_id"],
        "stage": "L0.4_causal_capacity",
        "capacity_config": config_path,
        "capacity_config_sha256": _sha256(root / config_path),
        "candidate_config_sha256": _sha256(root / stage["candidate_config"]),
        "game_config_sha256": _sha256(root / stage["game_config"]),
        "outcome_scope": "engineering controllability only; not biological learning evidence",
        "training_executed": False,
        "conditions": condition_results,
        "criteria": criteria,
        "status": "PASS" if all(criteria.values()) else "FAIL",
        "decision": ("The frozen circuit/readout has capacity for the predeclared timing target; propose a separate feedback-teacher evidence gate."
                     if all(criteria.values()) else
                     "The frozen circuit/readout failed the predeclared capacity gate; do not implement or run training."),
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--config", default=CAPACITY_CONFIG_DEFAULT)
    parser.add_argument("--output", type=Path, default=Path(RESULT_DEFAULT))
    args = parser.parse_args()
    result = run_capacity(args.root, args.config)
    output = args.output if args.output.is_absolute() else args.root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    print(json.dumps({"status": result["status"], "criteria": result["criteria"]},
                     indent=2))
