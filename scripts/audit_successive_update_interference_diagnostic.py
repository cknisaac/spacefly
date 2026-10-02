"""Independent provenance, arithmetic and decision audit of the A3 ledger."""

from __future__ import annotations

import bisect
import hashlib
import json
import math
import statistics
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/successive_update_interference_diagnostic.json"
OUT = ROOT / "docs/figures/successive_update_interference"
LONG = ROOT / "docs/figures/long_continuation"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def close(a: float, b: float, tolerance: float = 1e-9) -> bool:
    return math.isclose(a, b, rel_tol=0, abs_tol=tolerance)


def check_probe(probe: dict, timing: dict, panel: tuple) -> tuple[int, int]:
    assert probe["exploration"] is False and probe["exploration_pulses_us"] == []
    assert probe["uses_checkpoint_rng"] is True
    assert (probe["relative_note_offsets_us"], probe["cue_gains"]) == panel
    events = probe["events"]
    actions = probe["down_actions"]
    metrics = probe["metrics"]
    assert len(events) == 32 and all(e["weight_changes"] == 0 for e in events)
    assert all(e["note_time_us"] == probe["checkpoint_time_us"] + panel[0][i]
               for i, e in enumerate(events))
    assert close(metrics["mean_utility"], statistics.mean(e["game_utility"] for e in events))
    assert close(metrics["mean_expected_utility_before"],
                 statistics.mean(e["expected_utility_before"] for e in events))
    assert close(metrics["mean_signed_rpe"], statistics.mean(e["rpe"] for e in events))
    assert metrics["judgement_counts"] == dict(Counter(e["judgement"] for e in events))
    assert metrics["good_or_better_count"] == sum(e["hit_value"] >= 200 for e in events)
    assert metrics["down_count"] == len(actions)
    assert metrics["null_down_count"] == sum(a["disposition"] == "null_press" for a in actions)
    for event in events:
        assert close(event["rpe"], event["learning_utility"] - event["expected_utility_before"])
    hits = [e for e in events if e["judgement"] != "MISS"]
    if hits:
        assert close(metrics["hit_mean_absolute_error_ms"],
                     statistics.mean(abs(e["hit_error_us"]) for e in hits) / 1000)
        assert close(metrics["hit_mean_signed_error_ms"],
                     statistics.mean(e["hit_error_us"] for e in hits) / 1000)
    else:
        assert metrics["hit_mean_absolute_error_ms"] is None
    attempts = [e["hit_error_us"] for e in events if e["hit_error_us"] is not None]
    assert timing["attempt_count_with_error"] == len(attempts)
    if attempts:
        assert close(timing["mean_signed_attempt_error_ms"], statistics.mean(attempts) / 1000)
        assert close(timing["mean_absolute_attempt_error_ms"],
                     statistics.mean(abs(x) for x in attempts) / 1000)
    else:
        assert timing["mean_signed_attempt_error_ms"] is None
    assert timing["hit_mean_absolute_error_ms"] == metrics["hit_mean_absolute_error_ms"]
    all_downs = timing["down_actions_with_nearest_note"]
    assert len(all_downs) == len(actions)
    times = [probe["checkpoint_time_us"] + o for o in panel[0]]
    for action, augmented in zip(actions, all_downs):
        assert all(augmented[k] == v for k, v in action.items())
        t = action["time_us"]
        i = bisect.bisect_left(times, t)
        nearest = min((j for j in (i - 1, i) if 0 <= j < 32),
                      key=lambda j: abs(times[j] - t))
        assert augmented["nearest_note_index"] == nearest
        assert augmented["signed_nearest_note_error_us"] == t - times[nearest]
    if all_downs:
        assert close(timing["median_signed_all_down_ms"],
                     statistics.median(a["signed_nearest_note_error_us"] for a in all_downs) / 1000)
    else:
        assert timing["median_signed_all_down_ms"] is None
    return len(events), len(actions)


def check_update(update: dict, source: dict) -> None:
    assert update["saved_training_update"] == source
    assert update["time_us"] == source["time_us"]
    assert update["dopamine"] == source["dopamine"]
    slots = update["edge_slots"]
    assert len(slots) == len(set(slots)) == 480
    before = update["weights_before_mv"]
    after = update["weights_after_mv"]
    eligibility = update["eligibility"]
    raw = update["raw_proposed_update_mv"]
    applied = update["applied_update_mv"]
    assert len(before) == len(after) == len(eligibility) == len(raw) == len(applied) == 480
    clipped = []
    lo, hi = update["weight_bounds_mv"]
    for slot, w, new, e, r, a in zip(slots, before, after, eligibility, raw, applied):
        assert close(r, update["eta"] * e * update["dopamine"])
        assert close(a, new - w)
        assert close(new, min(hi, max(lo, w + r)))
        if not close(r, a, 1e-12):
            clipped.append(slot)
    assert update["clipped_slots"] == clipped
    assert update["clipped_edge_count"] == len(clipped)
    assert len(update["proposed_below_min_slots"]) == source["proposed_below_min_edges"]
    assert len(update["proposed_above_max_slots"]) == source["proposed_above_max_edges"]
    assert close(update["raw_l1_mv"], sum(abs(x) for x in raw))
    assert close(update["raw_l2_mv"], math.sqrt(sum(x*x for x in raw)))
    assert close(update["applied_l1_mv"], sum(abs(x) for x in applied))
    assert close(update["applied_l2_mv"], math.sqrt(sum(x*x for x in applied)))
    assert close(update["applied_l1_mv"], source["applied_l1_mv"])
    assert update["changed_edges"] == source["changed_edges"]
    assert update["lower_bound_edges_after"] == sum(w == lo for w in after)
    assert update["upper_bound_edges_after"] == sum(w == hi for w in after)


def qualifies(previous: dict, current: dict, end: int) -> bool:
    pm, cm = previous["probe"]["metrics"], current["probe"]["metrics"]
    return (pm["good_or_better_count"] >= 16
            and pm["good_or_better_count"] - cm["good_or_better_count"] >= 8
            and pm["mean_utility"] - cm["mean_utility"] >= 0.25
            and current["after_outcomes"] <= end - 4)


def main() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    meta = json.loads((OUT / "meta.json").read_text(encoding="utf-8"))
    status = json.loads((OUT / "status.json").read_text(encoding="utf-8"))
    source_meta = json.loads((LONG / "meta.json").read_text(encoding="utf-8"))
    counter = json.loads((OUT / "counterfactual.json").read_text(encoding="utf-8"))
    raw = [json.loads(x) for x in (OUT / "runs.jsonl").read_text(encoding="utf-8").splitlines()]
    rows = {r["seed"]: r for r in raw}
    source = {r["seed"]: r for r in (json.loads(x) for x in
              (LONG / "runs.jsonl").read_text(encoding="utf-8").splitlines())
              if r["condition"] == "on"}
    assert len(raw) == len(rows) == 2 and set(rows) == {2001, 2002}
    assert status["status"] == "complete" and status["completed_seeds"] == [2001, 2002]
    assert meta["protocol_sha256"] == sha(PROTOCOL)
    assert meta["source_long_ledger_sha256"] == sha(LONG / "runs.jsonl")
    assert meta["source_long_meta_sha256"] == sha(LONG / "meta.json")
    assert status["ledger_sha256"] == sha(OUT / "runs.jsonl")
    assert status["counterfactual_sha256"] == sha(OUT / "counterfactual.json")
    assert meta["saved_model_source_sha256"] == source_meta["model_source_sha256"]
    for relative, digest in meta["replay_model_source_sha256"].items():
        assert sha(ROOT / relative) == digest
    drift = {name: {"saved": meta["saved_model_source_sha256"][name], "replay": digest}
             for name, digest in meta["replay_model_source_sha256"].items()
             if digest != meta["saved_model_source_sha256"][name]}
    assert drift == meta["source_hash_drift_requiring_exact_replay"]
    assert set(drift) == {"src\\project_b\\simulation\\__init__.py",
                          "src\\project_b\\simulation\\spiking.py"}
    panel = (source_meta["probe_relative_note_offsets_us"], source_meta["probe_cue_gains"])
    event_count = action_count = update_count = 0
    selected = None
    for selection in protocol["seeds_and_windows"]:
        seed = selection["seed"]
        row = rows[seed]
        original = source[seed]
        start, end = selection["start_after_outcomes"], selection["end_after_outcomes"]
        assert row["start_after_outcomes"] == start and row["end_after_outcomes"] == end
        assert row["training_replay_events_checked"] == end
        assert row["source_training_note_times_us"] == original["resolved_config"]["training_note_times_us"][start:end]
        assert row["source_training_cue_gains"] == original["resolved_config"]["training_cue_gains"][start:end]
        points = row["checkpoints"]
        assert len(points) == 17
        for offset, point in enumerate(points):
            outcome = start + offset
            assert point["after_outcomes"] == outcome
            assert point["checkpoint_time_us"] == point["probe"]["checkpoint_time_us"]
            n, a = check_probe(point["probe"], point["timing"], panel)
            event_count += n
            action_count += a
            if offset:
                assert point["training_event"] == original["training_events"][outcome - 1]
                check_update(point["update"], original["update_diagnostics"][outcome - 1])
                assert isinstance(point["pre_update_canonical_sha256"], str)
                assert len(point["pre_update_canonical_sha256"]) == 64
                update_count += 1
            else:
                assert point["training_event"] is point["update"] is None
        if seed == 2001:
            saved = original["checkpoints"][1]["probe"]
            for field in ("relative_note_offsets_us", "cue_gains", "events", "down_actions", "metrics"):
                assert points[0]["probe"][field] == saved[field]
        if seed == 2002:
            saved = original["checkpoints"][2]["probe"]
            for field in ("relative_note_offsets_us", "cue_gains", "events", "down_actions", "metrics"):
                assert points[-1]["probe"][field] == saved[field]
        if selected is None:
            for earlier, later in zip(points, points[1:]):
                if qualifies(earlier, later, end):
                    selected = [seed, later["after_outcomes"]]
                    break
    assert status["candidate"] == selected
    if selected is None:
        assert counter["status"] == "no_qualifying_transition"
        assert "branches" not in counter
    else:
        assert counter["status"] == "complete"
        seed, target = selected
        assert counter["seed"] == seed and counter["target_outcome"] == target
        assert counter["window_end_outcome"] == rows[seed]["end_after_outcomes"]
        A = counter["branches"]["real_update"]
        B = counter["branches"]["skip_target_update"]
        assert A["intervention"]["pre_update_canonical_sha256"] == B["intervention"]["pre_update_canonical_sha256"]
        assert A["intervention"]["rng_state_at_update_sha256"] == B["intervention"]["rng_state_at_update_sha256"]
        assert A["intervention"]["target_applied_l1_mv"] > 0
        assert B["intervention"]["target_applied_l1_mv"] == 0
        assert A["intervention"]["requested_dopamine"] == B["intervention"]["requested_dopamine"]
        assert A["target_event"] == source[seed]["training_events"][target - 1]
        assert B["target_event"]["weight_changes"] == 0
        for key in ("judgement", "game_utility", "learning_utility",
                    "expected_utility_before", "rpe", "hit_error_us"):
            assert B["target_event"][key] == A["target_event"][key]
        assert A["immediate_probe"] == rows[seed]["checkpoints"][target - rows[seed]["start_after_outcomes"]]["probe"]
        assert A["final_probe"] == rows[seed]["checkpoints"][-1]["probe"]
        assert A["subsequent_training_events"] == source[seed]["training_events"][target:rows[seed]["end_after_outcomes"]]
        assert counter["same_realized_exploration_pulses"] == (A["exploration_pulses_us"] == B["exploration_pulses_us"])
        assert counter["same_end_checkpoint_time"] == (A["end_checkpoint_time_us"] == B["end_checkpoint_time_us"])
        for branch in (A, B):
            for point, timing in ((branch["immediate_probe"], branch["immediate_timing"]),
                                  (branch["final_probe"], branch["final_timing"])):
                n, a = check_probe(point, timing, panel)
                event_count += n
                action_count += a
    receipt = {"status": "passed", "trajectories": 2,
               "frozen_checkpoints": 34,
               "real_updates": update_count,
               "audited_frozen_note_outcomes": event_count,
               "audited_down_actions": action_count,
               "selected_causal_skip": selected,
               "counterfactual_status": counter["status"],
               "protocol_sha256": sha(PROTOCOL),
               "ledger_sha256": sha(OUT / "runs.jsonl"),
               "counterfactual_sha256": sha(OUT / "counterfactual.json")}
    (OUT / "audit.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
