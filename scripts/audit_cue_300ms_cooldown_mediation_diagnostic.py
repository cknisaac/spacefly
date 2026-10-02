"""Independent source, frozen-probe and dynamic-readout audit."""

from __future__ import annotations

import hashlib
import json
import statistics
from collections import Counter, deque
from pathlib import Path

from project_b.experiments import TinyLaneSession
from project_b.motor.fixed_readout import FixedMotorReadout
from scripts.exploration_map_diagnostic import make_probe


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/cue_300ms_cooldown_mediation_diagnostic.json"
A5 = ROOT / "docs/figures/cue_300ms_necessity"
OUT = ROOT / "docs/figures/cue_300ms_cooldown_mediation"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_state(checkpoint: bytes) -> dict:
    session = TinyLaneSession.from_trusted_checkpoint_bytes(checkpoint)
    r = session.readout
    return {"key_down": r.key_down, "last_down_us": r._last_down_us,
            "last_time_us": r._last_time_us,
            "spike_times_us": list(r._spike_times),
            "motor_neuron_indices": list(r.neuron_indices),
            "window_us": r.window_us, "on_threshold": r.on_threshold,
            "off_threshold": r.off_threshold,
            "min_hold_us": r.min_hold_us, "max_hold_us": r.max_hold_us,
            "cooldown_us": r.cooldown_us, "dt_us": session.config.dt_us}


def replay_readout(trace: dict, probe: dict, checkpoint: bytes,
                   extend: bool, original_second_us: int) -> dict:
    """Rebuild threshold crossings and actions from recorded motor spike ticks."""
    initial = source_state(checkpoint)
    assert trace["initial"] == initial
    assert initial["cooldown_us"] == 200_000 and initial["dt_us"] == 1_000
    by_time = {}
    motor_ids = set(initial["motor_neuron_indices"])
    for batch in trace["motor_spike_batches"]:
        t = batch["time_us"]
        assert t not in by_time
        cells = batch["motor_neuron_indices"]
        assert cells and len(cells) == len(set(cells))
        assert all(i in motor_ids for i in cells)
        by_time[t] = cells
    assert sum(map(len, by_time.values())) == probe["motor_spikes"]
    now = TinyLaneSession.from_trusted_checkpoint_bytes(checkpoint).simulator.current_time_us
    assert trace["first_observe_us"] == now + 1_000
    ticks = range(trace["first_observe_us"], trace["last_observe_us"] + 1, 1_000)
    assert len(ticks) == trace["observe_tick_count"]
    assert all(t in ticks for t in by_time)
    recent = deque(initial["spike_times_us"])
    key_down = initial["key_down"]
    last_down = initial["last_down_us"]
    cooldown = initial["cooldown_us"]
    prior_on = len(recent) >= initial["on_threshold"]
    prior_off = len(recent) <= initial["off_threshold"]
    downs = 0
    crossings = []
    decisions = []
    intervention_events = []
    window_at_original_second = None
    for t in ticks:
        before_key = key_down
        used_cooldown = cooldown
        recent.extend([t] * len(by_time.get(t, ())))
        while recent and recent[0] <= t - initial["window_us"]:
            recent.popleft()
        count = len(recent)
        kind = None
        if key_down:
            assert last_down is not None
            elapsed = t - last_down
            if elapsed >= initial["max_hold_us"] or (
                    elapsed >= initial["min_hold_us"]
                    and count <= initial["off_threshold"]):
                key_down = False
                kind = "up"
        elif count >= initial["on_threshold"] and (
                last_down is None or t - last_down >= cooldown):
            key_down = True
            last_down = t
            kind = "down"
            downs += 1
            if extend and downs in (1, 2):
                changed = 201_000 if downs == 1 else 200_000
                intervention_events.append({
                    "time_us": t, "after_down_number": downs,
                    "cooldown_before_us": cooldown,
                    "cooldown_after_us": changed,
                })
                cooldown = changed
        on = count >= initial["on_threshold"]
        off = count <= initial["off_threshold"]
        for name, previous, current in (("on", prior_on, on),
                                        ("off", prior_off, off)):
            if previous != current:
                crossings.append({"time_us": t, "threshold": name,
                                  "direction": "rise" if current else "fall",
                                  "spike_count_in_window": count,
                                  "key_down_before": before_key,
                                  "key_down_after": key_down})
        prior_on, prior_off = on, off
        if t == original_second_us:
            window_at_original_second = {
                "time_us": t, "spike_count_in_window": count,
                "on_threshold": initial["on_threshold"],
                "cooldown_used_us": used_cooldown,
                "readout_decision": kind,
            }
        if kind is not None:
            decisions.append({"time_us": t, "kind": kind, "lane": 0,
                              "spike_count_in_window": count,
                              "threshold": initial["on_threshold"],
                              "cooldown_used_us": used_cooldown})
    assert trace["threshold_crossings"] == crossings
    assert trace["readout_decisions"] == decisions
    assert trace["intervention_events"] == intervention_events
    assert trace["observed_window_at_original_second"] == window_at_original_second
    assert [d["time_us"] for d in decisions if d["kind"] == "down"] == [
        d["time_us"] for d in probe["down_actions"]]
    assert (len(intervention_events) == 2) == extend
    return {"on_threshold_rises": sum(x["threshold"] == "on"
                                      and x["direction"] == "rise"
                                      for x in crossings),
            "decisions": len(decisions)}


def rerun_with_extension(checkpoint: bytes, note_times: tuple[int, ...],
                         gains: tuple[float, ...]) -> dict:
    """Independently execute the same single diagnostic readout intervention."""
    original = FixedMotorReadout.observe
    downs = 0

    def shifted(self: FixedMotorReadout, t: int, spikes):
        nonlocal downs
        decision = original(self, t, spikes)
        if decision is not None and decision.action.kind.value == "down":
            downs += 1
            if downs == 1:
                assert self.cooldown_us == 200_000
                self.cooldown_us = 201_000
            elif downs == 2:
                assert self.cooldown_us == 201_000
                self.cooldown_us = 200_000
        return decision

    FixedMotorReadout.observe = shifted
    try:
        result = make_probe(checkpoint, note_times, gains, False, None)
    finally:
        FixedMotorReadout.observe = original
    assert downs >= 2
    return result


def check_metrics(probe: dict, item: dict) -> None:
    events = probe["events"]
    downs = probe["down_actions"]
    metrics = probe["metrics"]
    assert len(events) == 32
    assert not probe["exploration"] and probe["exploration_pulses_us"] == []
    assert all(event["weight_changes"] == 0 for event in events)
    assert metrics["good_or_better_count"] == sum(e["hit_value"] >= 200 for e in events)
    assert metrics["judgement_counts"] == dict(Counter(e["judgement"] for e in events))
    assert metrics["mean_utility"] == statistics.mean(e["game_utility"] for e in events)
    assert metrics["down_count"] == len(downs)
    first_two = downs[:2]
    first_on = next(x["time_us"] for x in item["readout_trace"]["threshold_crossings"]
                    if x["threshold"] == "on" and x["direction"] == "rise")
    assert first_two[0]["disposition"] == "null_press"
    assert first_two[1]["note_id"] == "probe-0"
    expected = {
        "first_on_threshold_rise_us": first_on,
        "first_null_down_us": first_two[0]["time_us"],
        "first_scored_down_us": first_two[1]["time_us"],
        "null_to_scored_gap_us": first_two[1]["time_us"] - first_two[0]["time_us"],
        "first_scored_error_us": events[0]["hit_error_us"],
        "first_judgement": events[0]["judgement"],
        "first_utility": events[0]["game_utility"],
        "spike_window_at_scored_down": next(
            d["spike_count_in_window"] for d in item["readout_trace"]["readout_decisions"]
            if d["kind"] == "down" and d["time_us"] == first_two[1]["time_us"]),
    }
    assert item["first_note"] == expected


def main() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    result = json.loads((OUT / "result.json").read_text(encoding="utf-8"))
    meta = json.loads((OUT / "meta.json").read_text(encoding="utf-8"))
    status = json.loads((OUT / "status.json").read_text(encoding="utf-8"))
    a5 = json.loads((A5 / "result.json").read_text(encoding="utf-8"))
    assert protocol["branches"] == [
        "no_update_reference", "real_full_reference",
        "no_update_cooldown_plus_one_tick", "real_full_cooldown_plus_one_tick"]
    assert status["status"] == result["status"] == "complete"
    assert status["protocol_sha256"] == result["protocol_sha256"] == meta["protocol_sha256"] == sha(PROTOCOL)
    assert status["result_sha256"] == sha(OUT / "result.json")
    assert result["a5_result_sha256"] == meta["a5_result_sha256"] == sha(A5 / "result.json")
    assert meta["a5_audit_sha256"] == sha(A5 / "audit.json")
    checkpoints = {source: (A5 / f"{source}_checkpoint.pkl").read_bytes()
                   for source in ("no_update", "real_full")}
    for source, checkpoint in checkpoints.items():
        assert hashlib.sha256(checkpoint).hexdigest() == result["a5_checkpoint_sha256"][source]
        assert result["a5_checkpoint_sha256"][source] == meta["a5_checkpoint_sha256"][source]
        assert result["a5_checkpoint_sha256"][source] == a5["checkpoint_files_sha256"][source]
    note_times = tuple(result["probe_note_times_us"])
    gains = tuple(result["probe_cue_gains"])
    assert len(note_times) == len(gains) == 32
    assert note_times == tuple(a5["branches"]["no_update"]["probe"]["checkpoint_time_us"]
                               + x for x in a5["branches"]["no_update"]["probe"]["relative_note_offsets_us"])
    events = actions = rises = 0
    effects = {}
    for source in ("no_update", "real_full"):
        original_second = a5["branches"][source]["probe"]["down_actions"][1]["time_us"]
        for extended in (False, True):
            name = f"{source}_cooldown_plus_one_tick" if extended else f"{source}_reference"
            item = result["branches"][name]
            probe = item["probe"]
            assert item["source_checkpoint_sha256"] == result["a5_checkpoint_sha256"][source]
            assert probe["relative_note_offsets_us"] == list(x - probe["checkpoint_time_us"] for x in note_times)
            assert probe["cue_gains"] == list(gains)
            if extended:
                assert rerun_with_extension(checkpoints[source], note_times, gains) == probe
            else:
                assert make_probe(checkpoints[source], note_times, gains, False, None) == probe
                assert probe == a5["branches"][source]["probe"]
            check_metrics(probe, item)
            activity = replay_readout(item["readout_trace"], probe,
                                      checkpoints[source], extended, original_second)
            events += len(probe["events"])
            actions += len(probe["down_actions"])
            rises += activity["on_threshold_rises"]
        base = result["branches"][f"{source}_reference"]["first_note"]
        changed = result["branches"][f"{source}_cooldown_plus_one_tick"]["first_note"]
        trace = result["branches"][f"{source}_cooldown_plus_one_tick"]["readout_trace"]
        cutoff = base["first_scored_down_us"]
        base_batches = result["branches"][f"{source}_reference"]["readout_trace"]["motor_spike_batches"]
        changed_batches = trace["motor_spike_batches"]
        effects[source] = {
            "first_threshold_delta_us": changed["first_on_threshold_rise_us"] - base["first_on_threshold_rise_us"],
            "first_null_delta_us": changed["first_null_down_us"] - base["first_null_down_us"],
            "scored_down_delta_us": changed["first_scored_down_us"] - base["first_scored_down_us"],
            "same_motor_spikes_through_original_scored_tick": (
                [x for x in base_batches if x["time_us"] <= cutoff]
                == [x for x in changed_batches if x["time_us"] <= cutoff]),
            "window_at_original_scored_tick": trace["observed_window_at_original_second"],
        }
    interp = result["interpretation"]
    assert interp["matched_intervention_effects"] == effects
    no = result["branches"]["no_update_reference"]["first_note"]
    full = result["branches"]["real_full_reference"]["first_note"]
    assert interp["reference_first_null_advance_us"] == full["first_null_down_us"] - no["first_null_down_us"]
    assert interp["reference_first_scored_advance_us"] == full["first_scored_down_us"] - no["first_scored_down_us"]
    bound = (interp["reference_first_null_advance_us"] == interp["reference_first_scored_advance_us"]
             and all(x["first_threshold_delta_us"] == 0
                     and x["first_null_delta_us"] == 0
                     and x["scored_down_delta_us"] == 1_000
                     and x["same_motor_spikes_through_original_scored_tick"]
                     for x in effects.values()))
    assert interp["classification"] == ("first_scored_press_cooldown_bound_in_both_states"
                                         if bound else "nonlinear_or_drive_limited")
    receipt = {"status": "passed", "branches": 4,
               "frozen_note_outcomes": events, "down_actions": actions,
               "readout_on_threshold_rises": rises,
               "protocol_sha256": sha(PROTOCOL),
               "result_sha256": sha(OUT / "result.json")}
    (OUT / "audit.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
