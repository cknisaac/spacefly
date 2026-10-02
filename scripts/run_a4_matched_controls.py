"""Persist A4 matched-start and declared-control infrastructure evidence."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from project_b.checkpoint.codec import _canonical, _encode
from project_b.mvp_c1.control_manifest import create_manifest, digest, validate_pair_start
from project_b.mvp_c1.controls import ControlPolicy
from project_b.mvp_c1.feedback import FirstActionOutcome, NoteWindow
from project_b.mvp_c1.runtime import MvpSession
from project_b.mvp_c1.source import load_mvp_circuit


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/a4_matched_control_contract.json"
OUT = ROOT / "docs/figures/a4_matched_controls_v2"


def save_json(path: Path, value) -> str:
    payload = _canonical(_encode(value))
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def main() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    if OUT.exists():
        raise FileExistsError("A4 evidence directory already exists; preserve prior run")
    OUT.mkdir(parents=True)
    circuit = load_mvp_circuit(ROOT)
    parent_config = config["parent"]
    notes = tuple(NoteWindow(**n) for n in parent_config["notes"])
    policies = {name: ControlPolicy(**values) for name, values in config["arms"].items()}
    parent = MvpSession(circuit, ROOT, notes, seed=parent_config["master_seed"],
                        level=parent_config["boundary_level"])
    parent.run_until(parent_config["committed_cut_us"])
    checkpoint_path = OUT / "parent_committed_cut"
    checkpoint_sha = parent.save(checkpoint_path)
    manifest = create_manifest(parent, str(checkpoint_path), checkpoint_sha, policies)
    manifest_sha = save_json(OUT / "condition_manifest.json", manifest)
    parent_weights = parent.rule.state()["selected_plastic_weights_by_kc_source_id"]
    short = config["controlled_fixture"]
    arms = {}
    start_receipts = []
    result_rows = []
    for name, policy in policies.items():
        arm = MvpSession(circuit, ROOT, notes, seed=parent.seed, level=parent.level)
        arm.load(checkpoint_path)
        arm.apply_controls(policy)
        start_receipts.append(validate_pair_start(manifest, parent, name, arm))
        arm.task.feedback.resolve(FirstActionOutcome(
            short["synthetic_feedback_origin"], short["synthetic_feedback_time_us"],
            short["synthetic_feedback_time_us"] - notes[0].hit_us,
            short["synthetic_feedback_category"],
            short["synthetic_feedback_disposition"], 0),
            short["synthetic_feedback_time_us"])
        arm._flush_task_events()
        arm.run_until(short["short_end_us"])
        arms[name] = arm
        counts = Counter(row[0] for row in arm.ledger)
        weights = arm.rule.state()["selected_plastic_weights_by_kc_source_id"]
        changed = sum(weights[k] != parent_weights[k] for k in parent_weights)
        ledger_sha = save_json(OUT / f"{name}_short_ledger.json", arm.ledger)
        result_rows.append({"arm": name, "control_policy": asdict(policy),
                            "ledger_sha256": ledger_sha, "event_counts": dict(counts),
                            "selected_weight_changed_pairs": changed,
                            "selected_weight_state_sha256": digest(weights),
                            "encoder_observation_cursor": arm.encoder.observation_cursor,
                            "boundary_rng_states_sha256": digest(
                                arm.boundary.state()["rng_states"]),
                            "motor_identity_sha256": digest(arm.motor.state()["identity"])})
    by_name = {row["arm"]: row for row in result_rows}
    baseline = by_name["baseline"]
    if not baseline["selected_weight_changed_pairs"]:
        raise AssertionError("baseline fixture did not exercise selected updates")
    for name in ("plasticity_off", "wrong_note", "dan_disabled", "eligibility_disabled"):
        if by_name[name]["selected_weight_changed_pairs"]:
            raise AssertionError(f"{name} unexpectedly changed a selected contribution")
    for name in ("baseline", "plasticity_off", "eligibility_disabled"):
        if not by_name[name]["event_counts"].get("pam_actual_spikes"):
            raise AssertionError(f"{name} did not expose actual PAM spikes")
    if (by_name["dan_disabled"]["event_counts"].get("pam_actual_spikes") or
            not by_name["dan_disabled"]["event_counts"].get("pam_delivery_suppressed") or
            by_name["wrong_note"]["event_counts"].get("pam_delivery")):
        raise AssertionError("DAN/teaching controls did not separate actual delivery")
    for row in result_rows:
        if (row["encoder_observation_cursor"] != baseline["encoder_observation_cursor"] or
                row["boundary_rng_states_sha256"] != baseline["boundary_rng_states_sha256"] or
                row["motor_identity_sha256"] != baseline["motor_identity_sha256"]):
            raise AssertionError("a control changed matched observation or fixed identity")

    long = MvpSession(circuit, ROOT, notes, seed=parent.seed, level=parent.level)
    long.load(checkpoint_path)
    long.apply_controls(policies["wrong_note"])
    validate_pair_start(manifest, parent, "wrong_note", long)
    long.task.feedback.resolve(FirstActionOutcome(
        short["wrong_note_long_origin"], short["synthetic_feedback_time_us"],
        short["synthetic_feedback_time_us"] - notes[0].hit_us,
        short["synthetic_feedback_category"],
        short["synthetic_feedback_disposition"], 0),
        short["synthetic_feedback_time_us"])
    long._flush_task_events()
    long.run_until(short["wrong_note_long_end_us"])
    routed = [row[1] for row in long.ledger if row[0] == "pam_delivery" and
              row[1]["origin_note_id"] == short["wrong_note_long_origin"]]
    if (len(routed) != 1 or routed[0]["actual_start_us"] != notes[1].visible_from_us or
            routed[0]["recipient_note_id"] != notes[1].note_id or
            not any(row[0] == "pam_actual_spikes" and row[1] >= notes[1].visible_from_us
                    for row in long.ledger)):
        raise AssertionError("wrong-note delivery did not wait for actual next cue")
    long_sha = save_json(OUT / "wrong_note_next_cue_ledger.json", long.ledger)
    receipt = {
        "stage_id": "A4", "status": {"A4.1": "PASS", "A4.2": "PASS", "A4.3": "PASS"},
        "scope": "matched control infrastructure fixture; no B3 or learning claim",
        "contract_sha256": hashlib.sha256(CONFIG.read_bytes()).hexdigest(),
        "parent_checkpoint_sha256": checkpoint_sha,
        "condition_manifest_sha256": manifest_sha,
        "start_audits": start_receipts,
        "short_control_results": result_rows,
        "wrong_note_long_result": {"ledger_sha256": long_sha,
                                   "source_start_us": routed[0]["source_start_us"],
                                   "actual_start_us": routed[0]["actual_start_us"],
                                   "recipient_note_id": routed[0]["recipient_note_id"],
                                   "actual_pam_spike_batches": sum(
                                       row[0] == "pam_actual_spikes" and
                                       row[1] >= notes[1].visible_from_us for row in long.ledger)},
    }
    save_json(OUT / "receipt.json", receipt)
    print(json.dumps({"status": receipt["status"],
                      "selected_weight_changes": {r["arm"]:
                          r["selected_weight_changed_pairs"] for r in result_rows},
                      "wrong_note_actual_start_us": routed[0]["actual_start_us"]},
                     sort_keys=True))


if __name__ == "__main__":
    main()
