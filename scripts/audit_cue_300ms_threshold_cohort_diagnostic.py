"""Independent source, structural-mask, state, spike/readout and probe audit."""

from __future__ import annotations

import hashlib
import json
import math
import pickle
import statistics
from collections import Counter
from pathlib import Path

from project_b.experiments import TinyLaneSession
from scripts.audit_cue_300ms_necessity_diagnostic import audit_readout
from scripts.exploration_map_diagnostic import make_probe


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/cue_300ms_threshold_cohort_diagnostic.json"
A5 = ROOT / "docs/figures/cue_300ms_necessity"
OUT = ROOT / "docs/figures/cue_300ms_threshold_cohort"
BRANCHES = ("no_update", "real_full", "real_except_300ms_targets_94_96")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value: object) -> str:
    return hashlib.sha256(pickle.dumps(value, protocol=5)).hexdigest()


def weights(session: TinyLaneSession) -> list[float]:
    return [session.plasticity.effective_weight(slot)
            for slot in session.layout.plastic_slots]


def count_window(trace: dict, t: int) -> int:
    low = t - trace["initial"]["window_us"]
    return (sum(low < spike_time <= t for spike_time in trace["initial"]["spike_times_us"])
            + sum(len(batch["motor_neuron_indices"])
                  for batch in trace["motor_spike_batches"]
                  if low < batch["time_us"] <= t))


def assert_same_nonweight_state(a: TinyLaneSession,
                                b: TinyLaneSession) -> None:
    assert a.plasticity is a.simulator.plasticity
    assert b.plasticity is b.simulator.plasticity
    assert vars(a).keys() == vars(b).keys()
    for name in vars(a):
        if name == "game":
            assert vars(a.game).keys() == vars(b.game).keys()
            for game_field in vars(a.game):
                if game_field == "_resolved":
                    assert a.game._resolved == b.game._resolved
                else:
                    assert digest(getattr(a.game, game_field)) == digest(
                        getattr(b.game, game_field)), game_field
        elif name == "population_sets":
            assert a.population_sets == b.population_sets
        elif name not in ("plasticity", "simulator"):
            assert digest(getattr(a, name)) == digest(getattr(b, name)), name
    a_weights = weights(a)
    b_weights = weights(b)
    for slot, w in zip(a.layout.plastic_slots, b_weights):
        a.plasticity._weights[slot] = w
    assert digest(a.plasticity) == digest(b.plasticity)
    assert digest(a.simulator) == digest(b.simulator)
    for slot, w in zip(a.layout.plastic_slots, a_weights):
        a.plasticity._weights[slot] = w


def check_probe(item: dict, checkpoint: bytes, note_times: tuple[int, ...],
                gains: tuple[float, ...]) -> tuple[int, int, int]:
    probe = item["probe"]
    trace = item["readout_trace"]
    assert probe == make_probe(checkpoint, note_times, gains, False, None)
    assert not probe["exploration"] and probe["exploration_pulses_us"] == []
    assert all(e["weight_changes"] == 0 for e in probe["events"])
    assert probe["relative_note_offsets_us"] == [t - probe["checkpoint_time_us"]
                                                 for t in note_times]
    assert probe["cue_gains"] == list(gains)
    events = probe["events"]
    downs = probe["down_actions"]
    metrics = probe["metrics"]
    assert len(events) == 32
    assert metrics["good_or_better_count"] == sum(e["hit_value"] >= 200 for e in events)
    assert metrics["judgement_counts"] == dict(Counter(e["judgement"] for e in events))
    assert math.isclose(metrics["mean_utility"],
                        statistics.mean(e["game_utility"] for e in events), abs_tol=1e-12)
    assert metrics["down_count"] == len(downs)
    readout_summary = audit_readout(trace, probe, checkpoint)
    first_rise = next(x for x in trace["threshold_crossings"]
                      if x["threshold"] == "on" and x["direction"] == "rise")
    t = first_rise["time_us"]
    dt = trace["initial"]["dt_us"]
    first_scored = next((d["time_us"] for d in downs if d["note_id"] == "probe-0"), None)
    expected = {
        "first_on_threshold_rise_us": t,
        "readout_window_count_previous_tick": count_window(trace, t - dt),
        "readout_window_count_at_crossing": count_window(trace, t),
        "on_threshold": trace["initial"]["on_threshold"],
        "first_down_us": downs[0]["time_us"] if downs else None,
        "first_down_disposition": downs[0]["disposition"] if downs else None,
        "first_scored_down_us": first_scored,
        "first_judgement": events[0]["judgement"],
        "first_scored_error_us": events[0]["hit_error_us"],
    }
    assert item["first_note"] == expected
    assert expected["readout_window_count_previous_tick"] < expected["on_threshold"]
    assert expected["readout_window_count_at_crossing"] >= expected["on_threshold"]
    return len(events), len(downs), readout_summary["on_rise_count"]


def main() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    result = json.loads((OUT / "result.json").read_text(encoding="utf-8"))
    meta = json.loads((OUT / "meta.json").read_text(encoding="utf-8"))
    status = json.loads((OUT / "status.json").read_text(encoding="utf-8"))
    a5 = json.loads((A5 / "result.json").read_text(encoding="utf-8"))
    assert protocol["branches"] == list(BRANCHES)
    assert result["status"] == status["status"] == "complete"
    assert result["protocol_sha256"] == meta["protocol_sha256"] == status["protocol_sha256"] == sha(PROTOCOL)
    assert result["a5_result_sha256"] == meta["a5_result_sha256"] == sha(A5 / "result.json")
    assert meta["a5_audit_sha256"] == sha(A5 / "audit.json")
    assert status["result_sha256"] == sha(OUT / "result.json")
    pre_bytes = (A5 / "pre_update_checkpoint.pkl").read_bytes()
    assert result["a5_pre_checkpoint_sha256"] == meta["a5_pre_checkpoint_sha256"] == sha(A5 / "pre_update_checkpoint.pkl")
    assert result["a5_pre_checkpoint_sha256"] == a5["checkpoint_files_sha256"]["pre_update"]
    geo = a5["pre_update_geometry"]
    assert result["pre_update_geometry"] == geo
    pre = TinyLaneSession.from_trusted_checkpoint_bytes(pre_bytes)
    assert weights(pre) == geo["weights_before_mv"]
    assert pre.simulator.current_time_us == geo["time_us"]
    state = a5["pre_update_state"]
    assert digest((pre.simulator.voltage_mv, pre.simulator.synaptic_drive_mv,
                   pre.simulator.refractory_until_us, pre.simulator._queue,
                   pre.simulator.spiked_this_tick)) == state["neural_state_pickle_sha256"]
    assert pre.simulator.snapshot().queued_arrivals == state["queued_arrivals"]
    assert digest(pre.readout) == state["readout_state_pickle_sha256"]
    assert digest(pre.reward) == state["reward_state_pickle_sha256"]
    assert digest(pre.rng.getstate()) == state["rng_state_sha256"]
    assert digest(pre.layout.graph) == state["topology_sha256"]
    assert geo["dopamine"] == state["source_event"]["rpe"]
    for i, slot in enumerate(geo["edge_slots"]):
        e = pre.plasticity.eligibility_at(slot, geo["time_us"])
        assert math.isclose(e, geo["eligibility"][i], abs_tol=1e-12)
        assert math.isclose(geo["raw_proposed_update_mv"][i],
                            geo["eta"] * e * geo["dopamine"], abs_tol=1e-12)
    source_trace = a5["branches"]["real_full"]["readout_trace"]
    old_first_rise = next(x for x in source_trace["threshold_crossings"]
                          if x["threshold"] == "on" and x["direction"] == "rise")
    assert old_first_rise["time_us"] == 372_383_000
    assert count_window(source_trace, 372_382_000) == 9
    assert count_window(source_trace, 372_383_000) == 12
    crossing_batch = next(x for x in source_trace["motor_spike_batches"]
                          if x["time_us"] == 372_383_000)
    assert crossing_batch["motor_neuron_indices"] == [94, 95, 96]
    edge_meta = a5["source_pathway_structure"]["edge_metadata"]
    selected = [i for i, edge in enumerate(edge_meta)
                if edge["preferred_time_to_contact_us"] == 300_000
                and edge["post_motor_id"] in (94, 95, 96)]
    slots = [geo["edge_slots"][i] for i in selected]
    assert slots == result["selected_300ms_target_cohort"]["edge_slots"]
    assert slots == [136, 137, 138, 148, 149, 150, 160, 161, 162, 172, 173, 174]
    assert len(selected) == 12
    assert {edge_meta[i]["pre_relay_id"] for i in selected} == {48, 49, 50, 51}
    assert result["selected_300ms_target_cohort"]["relay_source_ids"] == [48, 49, 50, 51]
    assert result["selected_300ms_target_cohort"]["motor_target_ids"] == [94, 95, 96]
    zero = TinyLaneSession.from_trusted_checkpoint_bytes(pre_bytes)
    zero.simulator.apply_dopamine(0.0)
    full = TinyLaneSession.from_trusted_checkpoint_bytes(pre_bytes)
    full.simulator.apply_dopamine(geo["dopamine"])
    assert weights(zero) == a5["branches"]["no_update"]["update"]["weights_after_mv"]
    assert weights(full) == geo["real_weights_after_mv"]
    checkpoints = {name: (OUT / f"{name}_checkpoint.pkl").read_bytes()
                   for name in BRANCHES}
    for name, checkpoint in checkpoints.items():
        assert hashlib.sha256(checkpoint).hexdigest() == result["checkpoint_sha256"][name]
        assert meta["checkpoint_sha256"][name] == result["checkpoint_sha256"][name]
        saved = TinyLaneSession.from_trusted_checkpoint_bytes(checkpoint)
        assert saved.plasticity is saved.simulator.plasticity
        assert weights(saved) == result["branches"][name]["weights_after_mv"]
        if name == "no_update":
            assert_same_nonweight_state(saved, zero)
        elif name == "real_full":
            assert_same_nonweight_state(saved, full)
        else:
            assert_same_nonweight_state(saved, full)
    omission = TinyLaneSession.from_trusted_checkpoint_bytes(checkpoints[BRANCHES[2]])
    cut_w, full_w, before = weights(omission), weights(full), geo["weights_before_mv"]
    assert all(cut_w[i] == (before[i] if i in selected else full_w[i])
               for i in range(480))
    removed_l1 = sum(abs(full_w[i] - before[i]) for i in selected)
    assert math.isclose(result["selected_300ms_target_cohort"]["removed_applied_l1_mv"], removed_l1)
    assert math.isclose(result["selected_300ms_target_cohort"]["raw_proposal_l1_mv"],
                        sum(abs(geo["raw_proposed_update_mv"][i]) for i in selected))
    assert math.isclose(result["selected_300ms_target_cohort"]["retained_applied_l1_mv"],
                        sum(abs(a-b) for a,b in zip(cut_w,before)))
    source_probe = a5["branches"]["no_update"]["probe"]
    times = tuple(geo["time_us"] + x for x in source_probe["relative_note_offsets_us"])
    gains = tuple(source_probe["cue_gains"])
    events = actions = rises = 0
    for name in BRANCHES:
        item = result["branches"][name]
        if name in ("no_update", "real_full"):
            assert item["probe"] == a5["branches"][name]["probe"]
        e, a, r = check_probe(item, checkpoints[name], times, gains)
        events += e
        actions += a
        rises += r
    first = {name: result["branches"][name]["first_note"]["first_on_threshold_rise_us"]
             for name in BRANCHES}
    primary = result["primary_comparison"]
    assert primary["no_update_first_rise_us"] == first["no_update"] == 372_456_000
    assert primary["real_full_first_rise_us"] == first["real_full"] == 372_383_000
    assert primary["omission_first_rise_us"] == first[BRANCHES[2]]
    assert primary["movement_from_full_toward_no_us"] == first[BRANCHES[2]] - first["real_full"]
    assert primary["fraction_of_73000us_separation"] == ((first[BRANCHES[2]] - first["real_full"])
                                                      / (first["no_update"] - first["real_full"]))
    expected_class = ("causal_upstream_timing_contributor" if first[BRANCHES[2]] > first["real_full"]
                      else "no_detected_first_threshold_timing_contribution"
                      if first[BRANCHES[2]] == first["real_full"]
                      else "nonlinear_or_opposing_effect")
    assert primary["classification"] == expected_class
    receipt = {"status": "passed", "branches": 3,
               "frozen_note_outcomes": events, "down_actions": actions,
               "readout_on_threshold_rises": rises,
               "selected_300ms_edges": len(selected),
               "protocol_sha256": sha(PROTOCOL),
               "result_sha256": sha(OUT / "result.json")}
    (OUT / "audit.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
