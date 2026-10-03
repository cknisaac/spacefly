"""Independently recompute the frozen EA-6 v2 gate from raw receipts."""

from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/ea_mvp_confirmation_v2.json"
RESULT_DIR = ROOT / "runs/ea_mvp/confirmation_v2"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _first_down(actions: list[dict]) -> int | None:
    return next((action["time_us"] for action in actions if action["kind"] == "down"), None)


def main() -> None:
    p = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    summary_path = RESULT_DIR / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["protocol_sha256"] == _sha(PROTOCOL)
    assert summary["status"] == "FAIL" and len(summary["runs"]) == 8
    report = {"protocol_sha256": _sha(PROTOCOL), "runs": [], "violations": []}
    for run in summary["runs"]:
        seed = run["seed"]
        counts = {}
        initial = run["initial_weights"]
        for arm in p["arms"]:
            path = RESULT_DIR / f"seed_{seed}_{arm}.json.gz"
            if _sha(path) != run["arms"][arm]["receipt_sha256"]:
                report["violations"].append(f"{seed}/{arm}: receipt hash mismatch")
            with gzip.open(path, "rt", encoding="utf-8") as stream:
                raw = json.load(stream)
            if raw["initial_weights"] != initial or len(raw["fresh_evaluations"]) != 40:
                report["violations"].append(f"{seed}/{arm}: unmatched initial or fresh count")
            weights = list(initial)
            for episode in raw["training_episodes"]:
                if episode["weights_before"] != weights:
                    report["violations"].append(f"{seed}/{arm}: broken weight continuity")
                if len(episode["feedback"]) != 1:
                    report["violations"].append(f"{seed}/{arm}: missing training feedback")
                for local in episode["local_teaching"]:
                    teacher_event = local["teaching_event"]
                    if teacher_event["available_at_us"] > episode["feedback"][0]["delivered_at_us"]:
                        report["violations"].append(f"{seed}/{arm}: early teaching")
                    pulse = local["pulse"]
                    if pulse and pulse["onset_us"] < teacher_event["available_at_us"]:
                        report["violations"].append(f"{seed}/{arm}: early DAN pulse")
                    result = local["result"]
                    if result["weights_before"] != weights:
                        report["violations"].append(f"{seed}/{arm}: local before mismatch")
                    changed = [i for i, (before, after) in enumerate(
                        zip(result["weights_before"], result["weights_after"]))
                        if before != after]
                    logged = [row["edge_index"] for row in result["changes"]]
                    if changed != logged:
                        report["violations"].append(f"{seed}/{arm}: unlogged/nonlocal change")
                    for change in result["changes"]:
                        if not (change["eligibility"] > 0 and change["connected_active_dans"]
                                and change["new_weight_mv"] >=
                                initial[change["edge_index"]] * 0.2):
                            report["violations"].append(f"{seed}/{arm}: invalid local update")
                    weights = list(result["weights_after"])
                if episode["weights_after"] != weights:
                    report["violations"].append(f"{seed}/{arm}: episode after mismatch")
            if raw["final_weights"] != weights:
                report["violations"].append(f"{seed}/{arm}: final weight mismatch")
            if arm in {"dan_off", "plasticity_off", "untrained"} and weights != initial:
                report["violations"].append(f"{seed}/{arm}: control learned")
            hits = 0
            for index, trial in enumerate(raw["fresh_evaluations"]):
                expected_lead = p["fresh_lead_start_us"] + index * p["fresh_lead_step_us"]
                expected_time = p["fresh_note_time_start_us"] + index * p["fresh_note_time_step_us"]
                first = _first_down(trial["actions"])
                error = None if first is None else first - expected_time
                hit = error is not None and abs(error) <= 73500
                hits += hit
                if (trial["lead_us"] != expected_lead or trial["note_time_us"] != expected_time
                        or trial["first_down_us"] != first
                        or trial["first_down_error_us"] != error
                        or trial["good_or_better"] != hit
                        or not trial["weights_unchanged"]):
                    report["violations"].append(f"{seed}/{arm}/{index}: first-action mismatch")
            counts[arm] = hits
            if hits != run["arms"][arm]["good_or_better_count"]:
                report["violations"].append(f"{seed}/{arm}: summary hit mismatch")
        pass_run = counts["learning_on"] >= p["min_hits_per_run"] and all(
            counts["learning_on"] - counts[arm] >= p["min_margin_hits"]
            for arm in p["arms"] if arm != "learning_on")
        report["runs"].append({"seed": seed, "fresh_hits": counts, "passes": pass_run})
    report["passing_runs"] = sum(row["passes"] for row in report["runs"])
    report["recomputed_status"] = ("PASS" if not report["violations"] and
                                   report["passing_runs"] >= p["min_passing_runs"]
                                   else "FAIL")
    assert report["recomputed_status"] == summary["status"]
    path = RESULT_DIR / "independent_audit.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"recomputed_status": report["recomputed_status"],
                      "passing_runs": report["passing_runs"],
                      "violations": len(report["violations"])}, sort_keys=True))


if __name__ == "__main__":
    main()
