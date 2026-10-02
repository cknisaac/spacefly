"""One-tick first-cycle cooldown intervention on saved frozen checkpoints."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from project_b.motor.fixed_readout import FixedMotorReadout
from scripts.cue_300ms_necessity_diagnostic import readout_initial_state
from scripts.exploration_map_diagnostic import make_probe
from scripts.long_continuation import atomic_json, sha
from scripts.successive_update_interference_diagnostic import timing_summary


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/cue_300ms_cooldown_mediation_diagnostic.json"
A5 = ROOT / "docs/figures/cue_300ms_necessity"
OUTPUT = ROOT / "docs/figures/cue_300ms_cooldown_mediation"
SOURCE_CHECKPOINTS = {
    "no_update": A5 / "no_update_checkpoint.pkl",
    "real_full": A5 / "real_full_checkpoint.pkl",
}


def traced_probe(checkpoint: bytes, note_times: tuple[int, ...],
                 gains: tuple[float, ...], *, extend_first_cooldown: bool,
                 original_second_down_us: int) -> tuple[dict, dict]:
    initial = readout_initial_state(checkpoint)
    assert initial["cooldown_us"] == 200_000
    assert initial["dt_us"] == 1_000
    motor_set = set(initial["motor_neuron_indices"])
    trace = {
        "initial": initial, "motor_spike_batches": [],
        "threshold_crossings": [], "readout_decisions": [],
        "intervention_events": [], "observed_window_at_original_second": None,
        "first_observe_us": None, "last_observe_us": None,
        "observe_tick_count": 0,
    }
    previous_on = len(initial["spike_times_us"]) >= initial["on_threshold"]
    previous_off = len(initial["spike_times_us"]) <= initial["off_threshold"]
    original_observe = FixedMotorReadout.observe
    down_count = 0

    def observe(self: FixedMotorReadout, time_us: int, spiking_indices):
        nonlocal previous_on, previous_off, down_count
        spikes = tuple(spiking_indices)
        key_down_before = self.key_down
        cooldown_used = self.cooldown_us
        decision = original_observe(self, time_us, spikes)
        if decision is not None and decision.action.kind.value == "down":
            down_count += 1
            if extend_first_cooldown and down_count == 1:
                assert self.cooldown_us == 200_000
                self.cooldown_us = 201_000
                trace["intervention_events"].append({
                    "time_us": time_us, "after_down_number": 1,
                    "cooldown_before_us": 200_000, "cooldown_after_us": 201_000,
                })
            elif extend_first_cooldown and down_count == 2:
                assert self.cooldown_us == 201_000
                self.cooldown_us = 200_000
                trace["intervention_events"].append({
                    "time_us": time_us, "after_down_number": 2,
                    "cooldown_before_us": 201_000, "cooldown_after_us": 200_000,
                })
        motor = [i for i in spikes if i in motor_set]
        if motor:
            trace["motor_spike_batches"].append({
                "time_us": time_us, "motor_neuron_indices": motor})
        count = len(self._spike_times)
        on = count >= self.on_threshold
        off = count <= self.off_threshold
        for name, was, now in (("on", previous_on, on),
                               ("off", previous_off, off)):
            if was != now:
                trace["threshold_crossings"].append({
                    "time_us": time_us, "threshold": name,
                    "direction": "rise" if now else "fall",
                    "spike_count_in_window": count,
                    "key_down_before": key_down_before,
                    "key_down_after": self.key_down,
                })
        previous_on, previous_off = on, off
        if time_us == original_second_down_us:
            trace["observed_window_at_original_second"] = {
                "time_us": time_us, "spike_count_in_window": count,
                "on_threshold": self.on_threshold,
                "cooldown_used_us": cooldown_used,
                "readout_decision": decision.action.kind.value if decision else None,
            }
        if decision is not None:
            trace["readout_decisions"].append({
                "time_us": decision.time_us,
                "kind": decision.action.kind.value,
                "lane": decision.action.lane,
                "spike_count_in_window": decision.spike_count_in_window,
                "threshold": decision.threshold,
                "cooldown_used_us": cooldown_used,
            })
        if trace["first_observe_us"] is None:
            trace["first_observe_us"] = time_us
        trace["last_observe_us"] = time_us
        trace["observe_tick_count"] += 1
        return decision

    FixedMotorReadout.observe = observe
    try:
        probe = make_probe(checkpoint, note_times, gains, False, None)
    finally:
        FixedMotorReadout.observe = original_observe
    assert sum(len(x["motor_neuron_indices"])
               for x in trace["motor_spike_batches"]) == probe["motor_spikes"]
    assert [d["time_us"] for d in trace["readout_decisions"] if d["kind"] == "down"] == [
        d["time_us"] for d in probe["down_actions"]]
    assert (len(trace["intervention_events"]) == 2) == extend_first_cooldown
    return probe, trace


def first_note_summary(probe: dict, trace: dict) -> dict:
    first_two = probe["down_actions"][:2]
    assert len(first_two) == 2
    assert first_two[0]["disposition"] == "null_press"
    assert first_two[1]["note_id"] == "probe-0"
    first_on = next(x for x in trace["threshold_crossings"]
                    if x["threshold"] == "on" and x["direction"] == "rise")
    event = probe["events"][0]
    return {
        "first_on_threshold_rise_us": first_on["time_us"],
        "first_null_down_us": first_two[0]["time_us"],
        "first_scored_down_us": first_two[1]["time_us"],
        "null_to_scored_gap_us": first_two[1]["time_us"] - first_two[0]["time_us"],
        "first_scored_error_us": event["hit_error_us"],
        "first_judgement": event["judgement"],
        "first_utility": event["game_utility"],
        "spike_window_at_scored_down": next(
            d["spike_count_in_window"] for d in trace["readout_decisions"]
            if d["kind"] == "down" and d["time_us"] == first_two[1]["time_us"]),
    }


def main() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert protocol["branches"] == [
        "no_update_reference", "real_full_reference",
        "no_update_cooldown_plus_one_tick", "real_full_cooldown_plus_one_tick"]
    a5 = json.loads((A5 / "result.json").read_text(encoding="utf-8"))
    assert json.loads((A5 / "audit.json").read_text(encoding="utf-8"))["status"] == "passed"
    assert sha(A5 / "result.json") == json.loads((A5 / "status.json").read_text(
        encoding="utf-8"))["result_sha256"]
    checkpoints = {name: path.read_bytes() for name, path in SOURCE_CHECKPOINTS.items()}
    for name, checkpoint in checkpoints.items():
        assert hashlib.sha256(checkpoint).hexdigest() == a5["checkpoint_files_sha256"][name]
    reference = a5["branches"]["no_update"]["probe"]
    offsets = tuple(reference["relative_note_offsets_us"])
    gains = tuple(reference["cue_gains"])
    note_times = tuple(reference["checkpoint_time_us"] + offset for offset in offsets)
    assert len(note_times) == 32
    OUTPUT.mkdir(parents=True, exist_ok=True)
    atomic_json(OUTPUT / "status.json", {"status": "running",
                                          "protocol_sha256": sha(PROTOCOL)})
    records = {}
    for source_name in ("no_update", "real_full"):
        ref_second = a5["branches"][source_name]["probe"]["down_actions"][1]["time_us"]
        for extended in (False, True):
            name = (f"{source_name}_cooldown_plus_one_tick" if extended
                    else f"{source_name}_reference")
            probe, trace = traced_probe(checkpoints[source_name], note_times, gains,
                                        extend_first_cooldown=extended,
                                        original_second_down_us=ref_second)
            if not extended:
                assert probe == a5["branches"][source_name]["probe"]
            records[name] = {"source_checkpoint_sha256": hashlib.sha256(
                checkpoints[source_name]).hexdigest(),
                "probe": probe, "readout_trace": trace,
                "first_note": first_note_summary(probe, trace),
                "timing": timing_summary(probe)}
            print(json.dumps({"branch": name,
                              "first_note": records[name]["first_note"],
                              "good": probe["metrics"]["good_or_better_count"]}), flush=True)
    matched = {}
    for source_name in ("no_update", "real_full"):
        baseline = records[f"{source_name}_reference"]["first_note"]
        changed = records[f"{source_name}_cooldown_plus_one_tick"]["first_note"]
        trace = records[f"{source_name}_cooldown_plus_one_tick"]["readout_trace"]
        batches_ref = records[f"{source_name}_reference"]["readout_trace"]["motor_spike_batches"]
        batches_changed = trace["motor_spike_batches"]
        cutoff = baseline["first_scored_down_us"]
        same_spikes_through_original_second = (
            [x for x in batches_ref if x["time_us"] <= cutoff]
            == [x for x in batches_changed if x["time_us"] <= cutoff])
        matched[source_name] = {
            "first_threshold_delta_us": (changed["first_on_threshold_rise_us"]
                                         - baseline["first_on_threshold_rise_us"]),
            "first_null_delta_us": (changed["first_null_down_us"]
                                    - baseline["first_null_down_us"]),
            "scored_down_delta_us": (changed["first_scored_down_us"]
                                     - baseline["first_scored_down_us"]),
            "same_motor_spikes_through_original_scored_tick": same_spikes_through_original_second,
            "window_at_original_scored_tick": trace["observed_window_at_original_second"],
        }
    reference_null_advance = (
        records["real_full_reference"]["first_note"]["first_null_down_us"]
        - records["no_update_reference"]["first_note"]["first_null_down_us"])
    reference_scored_advance = (
        records["real_full_reference"]["first_note"]["first_scored_down_us"]
        - records["no_update_reference"]["first_note"]["first_scored_down_us"])
    cooldown_bound = (reference_null_advance == reference_scored_advance
                      and all(x["first_threshold_delta_us"] == 0
                              and x["first_null_delta_us"] == 0
                              and x["scored_down_delta_us"] == 1_000
                              and x["same_motor_spikes_through_original_scored_tick"]
                              for x in matched.values()))
    interpretation = {
        "reference_first_null_advance_us": reference_null_advance,
        "reference_first_scored_advance_us": reference_scored_advance,
        "matched_intervention_effects": matched,
        "classification": ("first_scored_press_cooldown_bound_in_both_states"
                           if cooldown_bound else "nonlinear_or_drive_limited"),
    }
    result = {
        "study_id": protocol["study_id"], "status": "complete",
        "protocol_sha256": sha(PROTOCOL),
        "a5_result_sha256": sha(A5 / "result.json"),
        "a5_checkpoint_sha256": {name: hashlib.sha256(value).hexdigest()
                                 for name, value in checkpoints.items()},
        "probe_note_times_us": list(note_times), "probe_cue_gains": list(gains),
        "branches": records, "interpretation": interpretation,
        "completed_utc": datetime.now(timezone.utc).isoformat(),
    }
    atomic_json(OUTPUT / "result.json", result)
    atomic_json(OUTPUT / "meta.json", {
        "study_id": protocol["study_id"], "protocol_sha256": sha(PROTOCOL),
        "a5_result_sha256": sha(A5 / "result.json"),
        "a5_audit_sha256": sha(A5 / "audit.json"),
        "a5_checkpoint_sha256": result["a5_checkpoint_sha256"],
        "model": "synthetic tiny-lane fixture; diagnostic readout wrapper only",
    })
    atomic_json(OUTPUT / "status.json", {
        "status": "complete", "protocol_sha256": sha(PROTOCOL),
        "result_sha256": sha(OUTPUT / "result.json")})
    print(json.dumps(interpretation, indent=2))


if __name__ == "__main__":
    main()
