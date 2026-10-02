"""Produce the bounded A2.2/A2.3 coupled replay and frozen-run evidence."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from project_b.checkpoint.codec import _canonical, _encode
from project_b.checkpoint.frozen import FrozenPolicySnapshot
from project_b.mvp_c1.feedback import FirstActionOutcome, NoteWindow
from project_b.mvp_c1.runtime import MvpSession
from project_b.mvp_c1.source import load_mvp_circuit


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/figures/a2_mvp_coupled"


def write_json(path: Path, value) -> str:
    payload = _canonical(_encode(value))
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def main() -> None:
    if OUT.exists():
        raise FileExistsError("A2 receipt directory already exists; preserve the prior run")
    OUT.mkdir(parents=True)
    circuit = load_mvp_circuit(ROOT)
    notes = (NoteWindow("replay-1", 100_000, 900_000),)
    left = MvpSession(circuit, ROOT, notes, seed=11)
    left.run_until(139_000)
    cut_counts = {"chemical": len(left.chemical_queue),
                  "apl": len(left.apl_queue),
                  "sensory": len(left.encoder._queue)}
    checkpoint_sha = left.save(OUT / "committed_cut_139000")
    right = MvpSession(circuit, ROOT, notes, seed=11)
    right.load(OUT / "committed_cut_139000")
    assert right.state() == left.state() and all(cut_counts.values())
    left.run_until(1_100_000)
    right.run_until(1_100_000)
    if left.ledger_bytes() != right.ledger_bytes() or left.state() != right.state():
        raise AssertionError("full coupled continuation differs")
    left_ledger_sha = write_json(OUT / "uninterrupted_ledger.json", left.ledger)
    right_ledger_sha = write_json(OUT / "restored_ledger.json", right.ledger)
    assert left_ledger_sha == right_ledger_sha

    controlled = MvpSession(circuit, ROOT, notes, seed=11)
    controlled.run_until(139_000)
    controlled.task.feedback.resolve(FirstActionOutcome(
        "replay-1", 139_000, -90_000, "early_judged", "early_miss", 0), 139_000)
    controlled._flush_task_events()
    controlled.save(OUT / "controlled_pending_feedback_cut")
    controlled_restored = MvpSession(circuit, ROOT, notes, seed=11)
    controlled_restored.load(OUT / "controlled_pending_feedback_cut")
    controlled.run_until(170_000)
    controlled_restored.run_until(170_000)
    if (controlled.state() != controlled_restored.state() or
            controlled.ledger_bytes() != controlled_restored.ledger_bytes()):
        raise AssertionError("pending feedback continuation differs")

    donor = MvpSession(circuit, ROOT, (NoteWindow("template", 100_000, 900_000),),
                       seed=11)
    kc = min(donor.rule.mask.by_kc)
    donor.rule.observe_spikes(1_000, [donor.index[kc]])
    donor.rule.observe_spikes(2_000, [donor.index[circuit.pam_ids[0]]])
    policy = FrozenPolicySnapshot.capture(donor.rule)
    policy_sha = write_json(OUT / "controlled_noninitial_policy.json", asdict(policy))
    fresh_notes = (NoteWindow("fresh-1", 100_000, 900_000),
                   NoteWindow("fresh-2", 1_300_000, 2_100_000))
    fresh = MvpSession(circuit, ROOT, fresh_notes, seed=11, frozen_policy=policy)
    fresh_initial = MvpSession(circuit, ROOT, fresh_notes, seed=11, frozen_policy=policy)
    assert fresh.state() == fresh_initial.state()
    initial_weights = fresh.rule.state()["selected_plastic_weights_by_kc_source_id"]
    fresh.run_until(2_200_000)
    if (fresh.rule.state()["selected_plastic_weights_by_kc_source_id"] != initial_weights
            or fresh.task.feedback.pulse_records
            or any(d.pam_request for d in fresh.task.feedback.decisions)
            or len(fresh.task.game.result().judgements) != 2):
        raise AssertionError("frozen owner or fresh note invariant failed")
    fresh_ledger_sha = write_json(OUT / "fresh_frozen_ledger.json", fresh.ledger)
    receipt = {
        "stage": "A2.2+A2.3", "candidate": "MVP-C1",
        "status": {"A2.2": "PASS", "A2.3": "PASS"},
        "scope": "checkpoint infrastructure and fresh frozen behavior; no B3/training",
        "identity": left.identity,
        "source_coverage": {k: list(v) for k, v in circuit.category_counts.items()},
        "coupled_replay": {
            "cut_us": 139_000, "end_us": 1_100_000,
            "pending_at_cut": cut_counts,
            "checkpoint_state_sha256": checkpoint_sha,
            "uninterrupted_ledger_sha256": left_ledger_sha,
            "restored_ledger_sha256": right_ledger_sha,
            "event_counts": dict(Counter(row[0] for row in left.ledger)),
            "chemical_arrival_hash_chain_head": left.chemical_hash_head,
            "state_sha256": hashlib.sha256(_canonical(_encode(left.state()))).hexdigest(),
            "game_judgements": [asdict(x) for x in left.task.game.result().judgements],
            "first_action_decisions": [asdict(x) for x in left.task.feedback.decisions],
        },
        "controlled_feedback_replay": {
            "control": "synthetic first-action outcome injected only to exercise pending owner",
            "cut_us": 139_000, "end_us": 170_000,
            "pulse_start_us": controlled.task.feedback.pulse_records[0].start_us,
            "pulse_count": len(controlled.task.feedback.pulse_records),
            "ledger_sha256": hashlib.sha256(controlled.ledger_bytes()).hexdigest(),
        },
        "fresh_frozen": {
            "policy_sha256": policy_sha,
            "controlled_changed_kc_source_id": kc,
            "fresh_note_ids": [n.note_id for n in fresh_notes],
            "end_us": 2_200_000,
            "initial_state_equal_to_second_fresh_instance": True,
            "weights_unchanged": True,
            "teaching_pulses": 0,
            "judgements": [asdict(x) for x in fresh.task.game.result().judgements],
            "first_action_decisions": [asdict(x) for x in fresh.task.feedback.decisions],
            "ledger_sha256": fresh_ledger_sha,
            "event_counts": dict(Counter(row[0] for row in fresh.ledger)),
        },
    }
    write_json(OUT / "receipt.json", receipt)
    print(json.dumps({"status": receipt["status"],
                      "cut_pending": cut_counts,
                      "replay_events": len(left.ledger),
                      "frozen_events": len(fresh.ledger),
                      "frozen_judgements": len(fresh.task.game.result().judgements)},
                     sort_keys=True))


if __name__ == "__main__":
    main()
