"""Independent checkpoint, intervention, probe and readout audit for cue-300."""

from __future__ import annotations

import bisect
import hashlib
import json
import math
import pickle
import statistics
from collections import Counter, deque
from pathlib import Path

from project_b.experiments import TinyLaneSession
from scripts.exploration_map_diagnostic import make_probe


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/figures/cue_300ms_necessity"
A4 = ROOT / "docs/figures/eligibility_timing_credit"
LONG = ROOT / "docs/figures/long_continuation"
PROTOCOL = ROOT / "configs/cue_300ms_necessity_diagnostic.json"
FILENAMES = {
    "pre_update": "pre_update_checkpoint.pkl",
    "no_update": "no_update_checkpoint.pkl",
    "real_full": "real_full_checkpoint.pkl",
    "real_except_300ms": "real_except_300ms_checkpoint.pkl",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value: object) -> str:
    return hashlib.sha256(pickle.dumps(value, protocol=5)).hexdigest()


def close(a: float, b: float, tol: float = 1e-9) -> bool:
    return math.isclose(a, b, rel_tol=0, abs_tol=tol)


def weights(session: TinyLaneSession) -> list[float]:
    return [session.plasticity.effective_weight(slot)
            for slot in session.layout.plastic_slots]


def assert_same_session_state(a: TinyLaneSession, b: TinyLaneSession) -> None:
    """Compare coupled state fieldwise; whole-object pickle bytes are noncanonical."""
    assert a.plasticity is a.simulator.plasticity
    assert b.plasticity is b.simulator.plasticity
    assert vars(a).keys() == vars(b).keys()
    for name in vars(a):
        assert digest(getattr(a, name)) == digest(getattr(b, name)), name


def audit_readout(trace: dict, probe: dict, checkpoint: bytes) -> dict:
    """Reconstruct every threshold crossing/decision from motor spike batches."""
    session = TinyLaneSession.from_trusted_checkpoint_bytes(checkpoint)
    r = session.readout
    initial = trace["initial"]
    assert initial == {
        "key_down": r.key_down, "last_down_us": r._last_down_us,
        "last_time_us": r._last_time_us,
        "spike_times_us": list(r._spike_times),
        "motor_neuron_indices": list(r.neuron_indices),
        "window_us": r.window_us, "on_threshold": r.on_threshold,
        "off_threshold": r.off_threshold,
        "min_hold_us": r.min_hold_us, "max_hold_us": r.max_hold_us,
        "cooldown_us": r.cooldown_us, "dt_us": session.config.dt_us,
    }
    by_time = {}
    for batch in trace["motor_spike_batches"]:
        t = batch["time_us"]
        assert t not in by_time
        assert all(i in r.neuron_indices for i in batch["motor_neuron_indices"])
        assert len(batch["motor_neuron_indices"]) == len(set(batch["motor_neuron_indices"]))
        by_time[t] = batch["motor_neuron_indices"]
    assert sum(map(len, by_time.values())) == probe["motor_spikes"]
    assert trace["first_observe_us"] == session.simulator.current_time_us + session.config.dt_us
    assert trace["last_observe_us"] >= trace["first_observe_us"]
    times = range(trace["first_observe_us"], trace["last_observe_us"] + 1,
                  session.config.dt_us)
    assert len(times) == trace["observe_tick_count"]
    spike_times = deque(initial["spike_times_us"])
    key_down = initial["key_down"]
    last_down = initial["last_down_us"]
    was_on = len(spike_times) >= r.on_threshold
    was_off = len(spike_times) <= r.off_threshold
    crossings = []
    decisions = []
    for t in times:
        before_key_down = key_down
        spike_times.extend([t] * len(by_time.get(t, ())))
        while spike_times and spike_times[0] <= t - r.window_us:
            spike_times.popleft()
        count = len(spike_times)
        decision = None
        if key_down:
            assert last_down is not None
            elapsed = t - last_down
            if elapsed >= r.max_hold_us or (elapsed >= r.min_hold_us
                                             and count <= r.off_threshold):
                key_down = False
                decision = "up"
        elif count >= r.on_threshold and (last_down is None
                                           or t - last_down >= r.cooldown_us):
            key_down = True
            last_down = t
            decision = "down"
        now_on = count >= r.on_threshold
        now_off = count <= r.off_threshold
        for name, previous, current in (("on", was_on, now_on),
                                        ("off", was_off, now_off)):
            if previous != current:
                crossings.append({"time_us": t, "threshold": name,
                                  "direction": "rise" if current else "fall",
                                  "spike_count_in_window": count,
                                  "key_down_before": before_key_down,
                                  "key_down_after": key_down})
        was_on, was_off = now_on, now_off
        if decision is not None:
            decisions.append({"time_us": t, "kind": decision, "lane": r.lane,
                              "spike_count_in_window": count,
                              "threshold": r.on_threshold})
    assert trace["threshold_crossings"] == crossings
    assert trace["readout_decisions"] == decisions
    assert [d["time_us"] for d in decisions if d["kind"] == "down"] == [
        d["time_us"] for d in probe["down_actions"]]
    assert all(t in times for t in by_time)
    return {"motor_spikes": probe["motor_spikes"],
            "on_rise_count": sum(x["threshold"] == "on" and x["direction"] == "rise"
                                 for x in crossings),
            "readout_decision_count": len(decisions)}


def audit_metrics(item: dict, reference: dict) -> tuple[int, int]:
    probe = item["probe"]
    events = probe["events"]
    downs = probe["down_actions"]
    metrics = probe["metrics"]
    timing = item["timing"]
    assert len(events) == 32
    assert probe["exploration"] is False
    assert probe["exploration_pulses_us"] == []
    assert all(e["weight_changes"] == 0 for e in events)
    assert metrics["note_count"] == 32
    assert metrics["good_or_better_count"] == sum(e["hit_value"] >= 200 for e in events)
    assert close(metrics["mean_utility"], statistics.mean(e["game_utility"] for e in events))
    assert metrics["judgement_counts"] == dict(Counter(e["judgement"] for e in events))
    assert metrics["down_count"] == len(downs)
    assert metrics["null_down_count"] == sum(d["disposition"] == "null_press" for d in downs)
    note_times = [probe["checkpoint_time_us"] + x
                  for x in probe["relative_note_offsets_us"]]
    assert [e["note_time_us"] for e in events] == note_times
    signed_down = []
    detailed_down = []
    for down in downs:
        t = down["time_us"]
        j = bisect.bisect_left(note_times, t)
        i = min((k for k in (j - 1, j) if 0 <= k < 32),
                key=lambda k: abs(note_times[k] - t))
        signed_down.append(t - note_times[i])
        detailed_down.append({**down, "nearest_note_index": i,
                              "signed_nearest_note_error_us": t - note_times[i]})
    assert timing["down_actions_with_nearest_note"] == detailed_down
    assert timing["median_signed_all_down_ms"] == (
        statistics.median(signed_down) / 1000 if signed_down else None)
    assert timing["mean_signed_all_down_ms"] == (
        statistics.mean(signed_down) / 1000 if signed_down else None)
    attempt = [e["hit_error_us"] for e in events if e["hit_error_us"] is not None]
    assert timing["attempt_count_with_error"] == len(attempt)
    assert timing["mean_signed_attempt_error_ms"] == (
        statistics.mean(attempt) / 1000 if attempt else None)
    assert timing["mean_absolute_attempt_error_ms"] == (
        statistics.mean(map(abs, attempt)) / 1000 if attempt else None)
    hits = [e["hit_error_us"] for e in events if e["judgement"] != "MISS"]
    assert metrics["hit_mean_absolute_error_ms"] == (
        statistics.mean(map(abs, hits)) / 1000 if hits else None)
    assert metrics["hit_mean_signed_error_ms"] == (
        statistics.mean(hits) / 1000 if hits else None)
    pairs = [(x["hit_error_us"], y["hit_error_us"])
             for x, y in zip(events, reference["events"])
             if x["hit_error_us"] is not None and y["hit_error_us"] is not None]
    paired = item["paired_timing_vs_no"]
    assert paired["paired_note_count"] == len(pairs)
    expected_per_note = [(x["hit_error_us"] - y["hit_error_us"]) / 1000
                         if x["hit_error_us"] is not None and y["hit_error_us"] is not None
                         else None for x, y in zip(events, reference["events"])]
    assert paired["paired_signed_error_delta_ms_by_note"] == expected_per_note
    assert paired["mean_paired_signed_error_delta_ms"] == (
        statistics.mean((x-y)/1000 for x, y in pairs) if pairs else None)
    return len(events), len(downs)


def main() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    result = json.loads((OUT / "result.json").read_text(encoding="utf-8"))
    meta = json.loads((OUT / "meta.json").read_text(encoding="utf-8"))
    status = json.loads((OUT / "status.json").read_text(encoding="utf-8"))
    a4 = json.loads((A4 / "result.json").read_text(encoding="utf-8"))
    long_meta = json.loads((LONG / "meta.json").read_text(encoding="utf-8"))
    assert protocol["branches"] == ["no_update", "real_full", "real_except_300ms"]
    assert status["status"] == result["status"] == "complete"
    assert status["result_sha256"] == sha(OUT / "result.json")
    assert result["protocol_sha256"] == meta["protocol_sha256"] == sha(PROTOCOL)
    assert result["a4_result_sha256"] == meta["a4_result_sha256"] == sha(A4 / "result.json")
    assert meta["a4_audit_sha256"] == sha(A4 / "audit.json")
    assert result["pre_update_geometry"] == a4["pre_update_geometry"]
    assert result["a4_reference_pre_checkpoint_sha256"] == a4["pre_update_state"]["pre_update_checkpoint_sha256"]
    for key, value in result["pre_update_state"].items():
        if key != "pre_update_checkpoint_sha256":
            assert value == a4["pre_update_state"][key], key
    assert result["source_pathway_structure"] == a4["source_pathway_structure"]
    checkpoints = {name: (OUT / filename).read_bytes()
                   for name, filename in FILENAMES.items()}
    for name, checkpoint in checkpoints.items():
        expected = result["checkpoint_files_sha256"][name]
        assert checkpoint_digest(checkpoint) == expected
        assert meta["checkpoint_files_sha256"][name] == expected
        if name != "pre_update":
            assert result["branches"][name]["checkpoint_sha256"] == expected
    assert checkpoint_digest(checkpoints["pre_update"]) == result["pre_update_state"]["pre_update_checkpoint_sha256"]
    pre = TinyLaneSession.from_trusted_checkpoint_bytes(checkpoints["pre_update"])
    state = result["pre_update_state"]
    assert state["neural_state_pickle_sha256"] == digest((
        pre.simulator.voltage_mv, pre.simulator.synaptic_drive_mv,
        pre.simulator.refractory_until_us, pre.simulator._queue,
        pre.simulator.spiked_this_tick))
    assert state["readout_state_pickle_sha256"] == digest(pre.readout)
    assert state["reward_state_pickle_sha256"] == digest(pre.reward)
    assert state["rng_state_sha256"] == digest(pre.rng.getstate())
    assert state["topology_sha256"] == digest(pre.layout.graph)
    assert state["queued_arrivals"] == pre.simulator.snapshot().queued_arrivals
    geo = result["pre_update_geometry"]
    slots = geo["edge_slots"]
    assert list(pre.layout.plastic_slots) == slots
    assert pre.simulator.current_time_us == geo["time_us"]
    assert weights(pre) == geo["weights_before_mv"]
    assert state["source_event"]["rpe"] == geo["dopamine"]
    for i, slot in enumerate(slots):
        eligibility = pre.plasticity.eligibility_at(slot, geo["time_us"])
        assert close(eligibility, geo["eligibility"][i], 1e-12)
        assert close(geo["raw_proposed_update_mv"][i],
                     geo["eta"] * geo["dopamine"] * eligibility, 1e-12)
    zero = TinyLaneSession.from_trusted_checkpoint_bytes(checkpoints["pre_update"])
    zero.simulator.apply_dopamine(0.0)
    assert_same_session_state(zero, TinyLaneSession.from_trusted_checkpoint_bytes(
        checkpoints["no_update"]))
    full = TinyLaneSession.from_trusted_checkpoint_bytes(checkpoints["pre_update"])
    full.simulator.apply_dopamine(geo["dopamine"])
    assert_same_session_state(full, TinyLaneSession.from_trusted_checkpoint_bytes(
        checkpoints["real_full"]))
    assert weights(full) == geo["real_weights_after_mv"]
    cut = TinyLaneSession.from_trusted_checkpoint_bytes(checkpoints["real_except_300ms"])
    cut_update = result["branches"]["real_except_300ms"]["update"]
    edge_meta = result["source_pathway_structure"]["edge_metadata"]
    omitted_indices = [i for i, edge in enumerate(edge_meta)
                       if edge["preferred_time_to_contact_us"] == 300_000]
    assert len(omitted_indices) == 48
    assert cut_update["omitted_edge_slots"] == [slots[i] for i in omitted_indices]
    before = geo["weights_before_mv"]
    full_weights = weights(full)
    cut_weights = weights(cut)
    assert cut_weights == cut_update["weights_after_mv"]
    for i in range(480):
        assert cut_weights[i] == (before[i] if i in omitted_indices else full_weights[i])
        assert close(cut_update["applied_update_mv"][i], cut_weights[i] - before[i], 1e-12)
        assert close(cut_update["removed_applied_update_mv"][i],
                     full_weights[i] - cut_weights[i], 1e-12)
    assert close(cut_update["applied_l1_mv"],
                 sum(abs(x) for x in cut_update["applied_update_mv"]))
    assert close(cut_update["removed_applied_l1_mv"],
                 sum(abs(x) for x in cut_update["removed_applied_update_mv"]))
    assert cut_update["changed_edge_count"] == sum(x != y for x, y in zip(cut_weights, before))
    for session in (full, cut):
        for i, slot in enumerate(slots):
            session.plasticity._weights[slot] = before[i]
        assert_same_session_state(session, TinyLaneSession.from_trusted_checkpoint_bytes(
            checkpoints["no_update"]))
    assert result["branches"]["no_update"]["update"] == a4["branches"]["no_update"]["update"]
    assert result["branches"]["real_full"]["update"] == a4["branches"]["real_full"]["update"]
    offsets = tuple(long_meta["probe_relative_note_offsets_us"])
    gains = tuple(long_meta["probe_cue_gains"])
    note_times = tuple(geo["time_us"] + offset for offset in offsets)
    events_count = actions_count = crossings_count = 0
    no_probe = result["branches"]["no_update"]["probe"]
    for name in protocol["branches"]:
        item = result["branches"][name]
        probe = item["probe"]
        assert probe["relative_note_offsets_us"] == list(offsets)
        assert probe["cue_gains"] == list(gains)
        assert probe["checkpoint_time_us"] == geo["time_us"]
        assert probe["uses_checkpoint_rng"] is True
        rerun = make_probe(checkpoints[name], note_times, gains, False, None)
        assert rerun == probe
        if name in ("no_update", "real_full"):
            assert probe == a4["branches"][name]["probe"]
        e, a = audit_metrics(item, no_probe)
        events_count += e
        actions_count += a
        summary = audit_readout(item["readout_trace"], probe, checkpoints[name])
        crossings_count += summary["on_rise_count"]
    full_shift = result["branches"]["real_full"]["paired_timing_vs_no"]["mean_paired_signed_error_delta_ms"]
    cut_shift = result["branches"]["real_except_300ms"]["paired_timing_vs_no"]["mean_paired_signed_error_delta_ms"]
    assert full_shift == -61.71875
    cut_probe = result["branches"]["real_except_300ms"]["probe"]
    comparable = (result["branches"]["real_except_300ms"]["paired_timing_vs_no"]["paired_note_count"] == 32
                  and cut_probe["metrics"]["down_count"] == 64
                  and cut_probe["metrics"]["null_down_count"] == 32)
    if not comparable or cut_shift is None:
        classification = "nonlinear_mechanistically_ambiguous"
    elif cut_shift >= 0 or abs(cut_shift) <= .5 * abs(full_shift):
        classification = "major_necessary_contributor_at_this_state"
    elif cut_shift < 0 and abs(cut_shift) >= .75 * abs(full_shift):
        classification = "not_necessary_other_far_cue_components_suffice"
    else:
        classification = "contributory_necessity_not_established"
    assert result["interpretation"] == {
        "full_shift_ms": full_shift, "omission_shift_ms": cut_shift,
        "full_minus_omission_ms": (full_shift - cut_shift if cut_shift is not None else None),
        "comparable_attempt_pattern": comparable,
        "classification": classification,
    }
    receipt = {"status": "passed", "branches": 3,
               "frozen_note_outcomes": events_count,
               "down_actions": actions_count,
               "readout_on_threshold_rises": crossings_count,
               "omitted_300ms_edges": len(omitted_indices),
               "protocol_sha256": sha(PROTOCOL),
               "result_sha256": sha(OUT / "result.json")}
    (OUT / "audit.json").write_text(json.dumps(receipt, indent=2) + "\n",
                                    encoding="utf-8")
    print(json.dumps(receipt, indent=2))


def checkpoint_digest(checkpoint: bytes) -> str:
    return hashlib.sha256(checkpoint).hexdigest()


if __name__ == "__main__":
    main()
