"""Predeclared MVP-C1 B3 matched-state controllability panel; no training."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path

from project_b.checkpoint.codec import _canonical, _decode, _encode
from project_b.checkpoint.frozen import FrozenPolicySnapshot
from project_b.mvp_c1.feedback import NoteWindow
from project_b.mvp_c1.first_action_audit import (
    compare_owner_outcomes, game_events_from_mvp_ledger, reconstruct_first_actions)
from project_b.mvp_c1.runtime import MvpSession
from project_b.mvp_c1.source import load_mvp_circuit


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/b3_controllability_protocol.json"
OUT = ROOT / "docs/figures/b3_controllability_v2"


def save(path: Path, value) -> str:
    payload = _canonical(_encode(value))
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def selected_policy(circuit, factor: float, notes: tuple[NoteWindow, ...]) -> FrozenPolicySnapshot:
    donor = MvpSession(circuit, ROOT, notes, seed=31001)
    if factor != 1.0:
        state = donor.rule.state()
        state["selected_plastic_weights_by_kc_source_id"] = {
            kc: value * factor for kc, value in
            state["selected_plastic_weights_by_kc_source_id"].items()}
        donor.rule.restore(state)
    return FrozenPolicySnapshot.capture(donor.rule)


def install_probe(session: MvpSession, arm: str) -> None:
    """Diagnostic transmission switches; source graph and frozen weights stay intact."""
    original = session.rule.effective_weight
    graph = session.circuit.graph
    ids = session.circuit.source_ids
    kc = set(session.circuit.kc_ids)
    if arm in ("selected_output_off", "mbon05_output_off", "bypass_off"):
        def effective(slot: int) -> float:
            pre = ids[int(graph.pre_indices[slot])]
            post = ids[int(graph.post_indices[slot])]
            weight = original(slot)
            if arm == "selected_output_off" and slot in session.rule._plastic_by_slot:
                return weight - session.rule._plastic_by_slot[slot]
            if arm == "mbon05_output_off" and pre == 10495:
                return 0.0
            if arm == "bypass_off" and pre in kc and post == 11145:
                return 0.0
            return weight
        session.rule.effective_weight = effective
    elif arm == "background_only":
        original_refresh = session._refresh_external
        def refresh() -> None:
            original_refresh()
            session.external[session.kc_indices] = 0.0
        session._refresh_external = refresh
        session._refresh_external()
    elif arm not in ("weight_0.5", "weight_1.0", "weight_1.5"):
        raise ValueError(f"undeclared B3 arm: {arm}")


def pairing(circuit, notes, seed: int, order: str) -> dict:
    session = MvpSession(circuit, ROOT, notes, seed=seed)
    kc = min(session.rule._slot_by_kc)
    pam = min(circuit.pam_ids)
    before = session.rule.state()["selected_plastic_weights_by_kc_source_id"]
    graph_before = session.circuit.graph.weights_mv.copy()
    source_order = (kc, pam) if order == "kc_before_pam" else (pam, kc)
    records = []
    for time_us, source in zip((1000, 2000), source_order):
        records.append(asdict(session.rule.observe_spikes(time_us, [session.index[source]])))
    after = session.rule.state()["selected_plastic_weights_by_kc_source_id"]
    changed = {key: {"before": value, "after": after[key]}
               for key, value in before.items() if after[key] != value}
    expected_sign = -1 if order == "kc_before_pam" else 1
    target = str(kc)
    confined = bool(set(changed) == {target} and
                    (after[target] - before[target]) * expected_sign > 0 and
                    (session.circuit.graph.weights_mv == graph_before).all())
    return {"seed": seed, "order": order, "kc_source_id": kc,
            "pam_source_id": pam, "changed_selected_pairs": changed,
            "all_selected_before_sha256": hashlib.sha256(_canonical(_encode(before))).hexdigest(),
            "all_selected_after_sha256": hashlib.sha256(_canonical(_encode(after))).hexdigest(),
            "source_graph_unchanged": bool((session.circuit.graph.weights_mv == graph_before).all()),
            "record": records, "correct_and_confined": confined}


def run_arm(circuit, notes, seed: int, level: str, arm: str,
            policies: dict[float, FrozenPolicySnapshot]) -> dict:
    factor = float(arm.split("_")[1]) if arm.startswith("weight_") else 1.0
    session = MvpSession(circuit, ROOT, notes, seed=seed, level=level,
                         frozen_policy=policies[factor])
    initial = session.state()
    install_probe(session, arm)
    session.run_until(1_100_000)
    ledger_sha = save(OUT / f"seed_{seed}_{level}_{arm}_ledger.json", session.ledger)
    audit = reconstruct_first_actions(notes, game_events_from_mvp_ledger(session.ledger),
                                      1_100_000)
    closed_owner = deepcopy(session.task.first_action)
    closed_owner.finish(1_100_000)
    compare_owner_outcomes(audit, closed_owner.outcomes)
    audit_sha = save(OUT / f"seed_{seed}_{level}_{arm}_first_action.json", audit.as_dict())
    cue_start, cue_end = notes[0].visible_from_us, notes[0].hit_us
    dn_spikes = [row[1] for row in session.ledger if row[0] == "spike" and
                 row[2] == 10713 and cue_start <= row[1] <= cue_end]
    first = audit.rows[0].first_down_us
    return {"seed": seed, "level": level, "arm": arm,
            "start_state_sha256": hashlib.sha256(_canonical(_encode(initial))).hexdigest(),
            "start_boundary_rng_sha256": hashlib.sha256(_canonical(_encode(initial["boundary"]["rng_states"]))).hexdigest(),
            "frozen_policy_sha256": session.identity["frozen_policy_sha256"],
            "ledger_sha256": ledger_sha, "first_action_audit_sha256": audit_sha,
            "cue_dn_spike_count": len(dn_spikes), "cue_dn_spike_times_us": dn_spikes,
            "first_down_us": first, "first_action_category": audit.rows[0].category,
            "background_downs_before_cue": len(audit.background_actions),
            "extra_downs": audit.rows[0].extra_downs,
            "selected_weight_final_sha256": hashlib.sha256(_canonical(_encode(
                session.rule.state()["selected_plastic_weights_by_kc_source_id"]))).hexdigest(),
            "pam_pulses": len(session.task.feedback.pulse_records),
            "peak_queue": session.peak_queue}


def recover_arm(circuit, notes, seed: int, level: str, arm: str,
                policies: dict[float, FrozenPolicySnapshot]) -> dict:
    """Finalize only the already completed neural runs after an output error."""
    stem = f"seed_{seed}_{level}_{arm}"
    ledger_path = OUT / f"{stem}_ledger.json"
    audit_path = OUT / f"{stem}_first_action.json"
    ledger = _decode(json.loads(ledger_path.read_text(encoding="utf-8")))
    _decode(json.loads(audit_path.read_text(encoding="utf-8")))
    audit = reconstruct_first_actions(notes, game_events_from_mvp_ledger(ledger), 1_100_000)
    if _canonical(_encode(audit.as_dict())) != audit_path.read_bytes():
        raise ValueError(f"saved B3 first-action audit differs: {stem}")
    factor = float(arm.split("_")[1]) if arm.startswith("weight_") else 1.0
    session = MvpSession(circuit, ROOT, notes, seed=seed, level=level,
                         frozen_policy=policies[factor])
    initial = session.state()
    install_probe(session, arm)
    cue_start, cue_end = notes[0].visible_from_us, notes[0].hit_us
    dn_spikes = [row[1] for row in ledger if row[0] == "spike" and
                 row[2] == 10713 and cue_start <= row[1] <= cue_end]
    if any(row[0] == "pam_pulse" for row in ledger):
        raise ValueError(f"unexpected B3 task teaching: {stem}")
    return {"seed": seed, "level": level, "arm": arm,
            "start_state_sha256": hashlib.sha256(_canonical(_encode(initial))).hexdigest(),
            "start_boundary_rng_sha256": hashlib.sha256(_canonical(_encode(initial["boundary"]["rng_states"]))).hexdigest(),
            "frozen_policy_sha256": session.identity["frozen_policy_sha256"],
            "ledger_sha256": hashlib.sha256(ledger_path.read_bytes()).hexdigest(),
            "first_action_audit_sha256": hashlib.sha256(audit_path.read_bytes()).hexdigest(),
            "cue_dn_spike_count": len(dn_spikes), "cue_dn_spike_times_us": dn_spikes,
            "first_down_us": audit.rows[0].first_down_us,
            "first_action_category": audit.rows[0].category,
            "background_downs_before_cue": len(audit.background_actions),
            "extra_downs": audit.rows[0].extra_downs,
            "selected_weight_final_sha256": hashlib.sha256(_canonical(_encode(
                session.rule.state()["selected_plastic_weights_by_kc_source_id"]))).hexdigest(),
            "pam_pulses": 0, "peak_queue": None}


def main() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    recovering = OUT.exists()
    if recovering and ((OUT / "receipt.json").exists() or
                       len(list(OUT.glob("seed_*_ledger.json"))) != 39 or
                       len(list(OUT.glob("seed_*_first_action.json"))) != 39):
        raise FileExistsError("B3 evidence is complete or incomplete; refuse overwrite")
    if (protocol["seeds"] != [31001, 31002, 31003] or
            protocol["selected_weight_factors"] != [0.5, 1.0, 1.5]):
        raise ValueError("B3 protocol differs from B2 declaration")
    if not recovering:
        OUT.mkdir(parents=True)
    circuit = load_mvp_circuit(ROOT)
    notes = (NoteWindow(**protocol["note"]),)
    policies = {factor: selected_policy(circuit, factor, notes)
                for factor in protocol["selected_weight_factors"]}
    rows = []
    pairings = []
    for seed in protocol["seeds"]:
        for level in [protocol["nominal_level"], *protocol["sensitivity_levels"]]:
            arms = [f"weight_{x:.1f}" for x in protocol["selected_weight_factors"]]
            if level == "nominal":
                arms += protocol["nominal_single_mechanism_controls"]
            for arm in arms:
                row = (recover_arm(circuit, notes, seed, level, arm, policies)
                       if recovering else run_arm(circuit, notes, seed, level, arm, policies))
                rows.append(row)
                print(json.dumps({key: row[key] for key in
                                  ("seed", "level", "arm", "cue_dn_spike_count", "first_down_us")}),
                      flush=True)
        for order in ("kc_before_pam", "pam_before_kc"):
            pairings.append(pairing(circuit, notes, seed, order))
    save(OUT / "pairing_records.json", pairings)
    save(OUT / "arm_results.json", rows)
    nominal = {(r["seed"], r["arm"]): r for r in rows if r["level"] == "nominal"}
    seed_gates = []
    for seed in protocol["seeds"]:
        low, base, high = (nominal[seed, f"weight_{x:.1f}"] for x in (0.5, 1.0, 1.5))
        down = [r["first_down_us"] for r in (low, base, high)]
        dn = [r["cue_dn_spike_count"] for r in (low, base, high)]
        seed_gates.append({"seed": seed, "dn_counts_low_base_high": dn,
                           "first_down_low_base_high_us": down,
                           "monotone_dn": dn[0] < dn[1] < dn[2],
                           "earlier_first_down": all(t is not None for t in down) and
                           down[0] - down[2] >= 1000,
                           "background_only_first_down": nominal[seed, "background_only"]["first_down_us"]})
    matched_rng = all(len({r["start_boundary_rng_sha256"] for r in rows
                           if r["seed"] == seed and r["level"] == level}) == 1
                      for seed in protocol["seeds"]
                      for level in ["nominal", "low", "high"])
    weight_frozen = all(r["pam_pulses"] == 0 for r in rows)
    polarity = all(p["correct_and_confined"] for p in pairings)
    nominal_pass = sum(g["monotone_dn"] and g["earlier_first_down"]
                       for g in seed_gates) >= 2
    no_background = all(g["background_only_first_down"] is None for g in seed_gates)
    status = ("INCONCLUSIVE" if not matched_rng or not weight_frozen else
              "PASS" if nominal_pass and polarity and no_background else "FAIL")
    receipt = {"stage_id": "MVP-B3", "status": status,
               "protocol_sha256": hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
               "source_identity": rows[0]["frozen_policy_sha256"],
               "circuit_resolved_sha256": circuit.resolved_sha256,
               "seed_gates": seed_gates, "matched_boundary_rng": matched_rng,
               "frozen_no_task_teaching": weight_frozen,
               "pairing_polarity_and_confinement": polarity,
               "nominal_two_of_three": nominal_pass,
               "no_background_only_first_down": no_background,
               "arms": len(rows), "pairing_replays": len(pairings)}
    save(OUT / "receipt.json", receipt)
    print(json.dumps(receipt, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
