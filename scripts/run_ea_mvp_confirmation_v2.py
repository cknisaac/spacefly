"""Frozen EA-6 v2 confirmation: eight initializations, matched arms, fresh leads."""

from __future__ import annotations

from dataclasses import asdict
import gzip
import hashlib
import json
from pathlib import Path
import random

from project_b.ea_mvp.bridge import StreamingTapBridge
from project_b.ea_mvp.frozen_policy import FrozenFlyTapPolicy
from project_b.malecns_continuous_position_learning.online_policy import load_position_config
from project_b.osu.config import OsuConfig
from project_b.osu.types import KeyActionKind, TapNote

from run_ea_mvp_development import run_episode
from run_ea_mvp_teacher_local import verify_source


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/ea_mvp_confirmation_v2.json"
OUTPUT_DIR = ROOT / "runs/ea_mvp/confirmation_v2"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _evaluate(config: dict, weights: list[float], *, run_seed: int,
              arm: str, note_index: int, lead_us: int, note_time_us: int,
              od: float) -> dict:
    note_id = f"ea6-{run_seed}-{arm}-{note_index}"
    policy = FrozenFlyTapPolicy(config, weights=weights)
    trace = StreamingTapBridge(
        TapNote(note_id, 0, note_time_us), OsuConfig(od=od, ruleset="lazer"),
        visible_lead_us=lead_us, dt_us=policy.dt_us).run(policy)
    first_down = next((action.time_us for action in trace.actions
                       if action.kind is KeyActionKind.DOWN), None)
    error_us = None if first_down is None else first_down - note_time_us
    return {"note_id": note_id, "lead_us": lead_us, "note_time_us": note_time_us,
            "first_down_us": first_down, "first_down_error_us": error_us,
            "good_or_better": error_us is not None and abs(error_us) <= 73500,
            "actions": [asdict(row) for row in trace.actions],
            "feedback": [asdict(row) for row in trace.feedback],
            "results": [asdict(row) for row in trace.results],
            "weights_unchanged": policy.fly.weights == weights}


def _save_arm(run_seed: int, arm: str, record: dict) -> str:
    path = OUTPUT_DIR / f"seed_{run_seed}_{arm}.json.gz"
    with gzip.open(path, "wt", encoding="utf-8") as stream:
        json.dump(record, stream, sort_keys=True, separators=(",", ":"), default=str)
    return _sha256(path)


def main() -> None:
    p = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    for relative_path, expected_hash in p["code_sha256"].items():
        if _sha256(ROOT / relative_path) != expected_hash:
            raise RuntimeError(f"confirmation code changed after freeze: {relative_path}")
    teacher_path = ROOT / p["teacher_protocol"]
    if _sha256(teacher_path) != p["teacher_protocol_sha256"]:
        raise RuntimeError("teacher protocol changed after freeze")
    teacher = json.loads(teacher_path.read_text(encoding="utf-8"))
    verify_source(ROOT / teacher["source_config"], teacher["source_config_lf_sha256"],
                  teacher["source_config_legacy_crlf_sha256"])
    verify_source(ROOT / teacher["anatomy_audit"], teacher["anatomy_audit_lf_sha256"],
                  teacher["anatomy_audit_legacy_crlf_sha256"])
    config = load_position_config(ROOT, teacher["source_config"])
    audit = json.loads((ROOT / teacher["anatomy_audit"]).read_text(encoding="utf-8"))
    roster = audit["previously_audited_pam08_roster_scope"][
        "minimum_cardinality_set_for_maximum_coverage"]
    coverage = {int(row["source_id"]): set(row["gamma4_kc_source_ids"]) for row in roster}
    cells = config["circuit"]["selected_kcs"]
    kc_ids = tuple(int(row["source_id"]) for row in cells)
    if set().union(*coverage.values()) != set(kc_ids):
        raise RuntimeError("source KC/DAN coverage changed")
    total = sum(row["plastic_contact_rows"] for row in cells)
    source_weights = [row["plastic_contact_rows"] / total for row in cells]
    leads = list(range(p["fresh_lead_start_us"],
                       p["fresh_lead_start_us"] + p["fresh_lead_step_us"] * p["fresh_note_count"],
                       p["fresh_lead_step_us"]))
    if len(leads) != p["fresh_note_count"] or len(p["seeds"]) != 8:
        raise RuntimeError("confirmation note/seed count differs from frozen protocol")
    if set(p["arms"]) != {"learning_on", "dan_off", "plasticity_off",
                          "shuffled_teaching", "untrained"}:
        raise RuntimeError("confirmation arms differ from frozen protocol")
    dev = {"od": p["od"], "note_time_us": p["training_note_time_us"],
           "visible_lead_us": p["training_lead_us"]}
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = {"protocol_id": p["protocol_id"], "protocol_sha256": _sha256(PROTOCOL),
               "teacher_protocol_sha256": _sha256(teacher_path), "runs": [],
               "status": "RUNNING"}
    summary_path = OUTPUT_DIR / "summary.json"
    for seed in p["seeds"]:
        rng = random.Random(seed)
        initial = [weight * (1.0 + rng.uniform(-p["initial_weight_jitter_fraction"],
                                               p["initial_weight_jitter_fraction"]))
                   for weight in source_weights]
        run = {"seed": seed, "initial_weights": initial, "arms": {}}
        learning_labels = []
        for arm in p["arms"]:
            weights = list(initial)
            episodes = []
            if arm != "untrained":
                for index in range(1, p["training_episodes"] + 1):
                    override = None
                    if arm == "shuffled_teaching":
                        override = learning_labels[
                            (index - 1 + p["shuffle_offset_episodes"]) % p["training_episodes"]]
                    weights, record = run_episode(
                        config, teacher, dev, coverage, kc_ids, initial, weights,
                        arm, index, teaching_label_override=override)
                    episodes.append(record)
                if arm == "learning_on":
                    learning_labels = [row["feedback"][0]["event"]["judgement_label"]
                                       for row in episodes]
            evaluations = []
            exact_replay = True
            for index, lead_us in enumerate(leads):
                note_time = p["fresh_note_time_start_us"] + index * p["fresh_note_time_step_us"]
                first = _evaluate(config, weights, run_seed=seed, arm=arm,
                                  note_index=index, lead_us=lead_us,
                                  note_time_us=note_time, od=p["od"])
                second = _evaluate(config, weights, run_seed=seed, arm=arm,
                                   note_index=index, lead_us=lead_us,
                                   note_time_us=note_time, od=p["od"])
                exact_replay &= first == second
                evaluations.append(first)
            changed_slots = [i for i, (before, after) in enumerate(zip(initial, weights))
                             if before != after]
            local_integrity = all(
                change["edge_index"] in changed_slots
                and change["eligibility"] > 0
                and change["connected_active_dans"]
                and change["new_weight_mv"] >= initial[change["edge_index"]] *
                    teacher["ltd"]["minimum_fraction"]
                for episode in episodes for teaching in episode["local_teaching"]
                for change in teaching["result"]["changes"])
            arm_record = {"seed": seed, "arm": arm, "initial_weights": initial,
                          "final_weights": weights, "changed_slots": changed_slots,
                          "training_episodes": episodes, "fresh_evaluations": evaluations,
                          "exact_eval_replay": exact_replay,
                          "local_integrity": local_integrity}
            receipt_hash = _save_arm(seed, arm, arm_record)
            hit_count = sum(row["good_or_better"] for row in evaluations)
            run["arms"][arm] = {"receipt_sha256": receipt_hash,
                                "good_or_better_count": hit_count,
                                "changed_slots": changed_slots,
                                "exact_eval_replay": exact_replay,
                                "local_integrity": local_integrity}
            summary["runs"].append(run) if arm == p["arms"][-1] else None
            summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n",
                                    encoding="utf-8")
            print(json.dumps({"seed": seed, "arm": arm, "fresh_hits": hit_count,
                              "changed_slots": len(changed_slots)}, sort_keys=True), flush=True)
    passing_runs = []
    for run in summary["runs"]:
        arms = run["arms"]
        trained = arms["learning_on"]["good_or_better_count"]
        controls = [arms[name]["good_or_better_count"] for name in p["arms"]
                    if name != "learning_on"]
        passing_runs.append(trained >= p["min_hits_per_run"]
                            and all(trained - control >= p["min_margin_hits"]
                                    for control in controls))
    integrity = all(arm["exact_eval_replay"] and arm["local_integrity"]
                    for run in summary["runs"] for arm in run["arms"].values())
    controls_unchanged = all(not run["arms"][name]["changed_slots"]
                             for run in summary["runs"]
                             for name in ("dan_off", "plasticity_off", "untrained"))
    summary["checks"] = {"source_and_code_pinned": True, "integrity": integrity,
                         "controls_unchanged": controls_unchanged,
                         "passing_runs": passing_runs,
                         "behavior": sum(passing_runs) >= p["min_passing_runs"]}
    summary["status"] = "PASS" if all((integrity, controls_unchanged,
                                       summary["checks"]["behavior"])) else "FAIL"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")
    print(json.dumps({"status": summary["status"], "checks": summary["checks"]},
                     sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
