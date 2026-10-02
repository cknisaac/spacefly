"""Forensic replay and one-update causal ablations; no parameter search.

Uses three saved held-out seeds: first all-GOOD+ (2000), first all-hit but
zero-GOOD+ (2009), and first all-MISS (2013). These seeds are now diagnostic.
Production model code is unchanged. Private state is inspected deliberately.
"""

from __future__ import annotations

import json
import hashlib
import math
import statistics
from collections import Counter
from dataclasses import replace
from pathlib import Path

from project_b.experiments import TinyBrainConfig, TinyLaneSession
from scripts.checkpoint_controls import summarize

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs/figures/overnight_synthetic/runs.jsonl"
OUTPUT = ROOT / "docs/figures/mechanism_diagnostics.json"


def config_from_record(row: dict) -> TinyBrainConfig:
    values = dict(row["resolved_config"])
    for key in ("explicit_note_times_us", "cue_gain_by_note", "reward_utility_schedule"):
        if values.get(key) is not None:
            values[key] = tuple(values[key])
    return TinyBrainConfig(**values)


def oracle_eligibility(pre: list[int], post: list[int], t: int, pre_tau: int, e_tau: int) -> float:
    return sum(math.exp(-(t-v)/e_tau) *
               sum(math.exp(-(v-u)/pre_tau) for u in pre if u < v)
               for v in post if v <= t)


def next_outcome(session: TinyLaneSession) -> dict:
    action_start = len(session.game.result().actions)
    target = session.resolved_count + 1
    while session.resolved_count < target:
        session.step()
    j = session.feedback[-1].reinforcement.judgement_record
    return {"judgement": j.judgement.name, "hit_error_us": j.hit_error_us,
            "note_time_us": j.note_time_us, "event_time_us": j.event_time_us,
            "down_actions": [{"time_us": a.action.time_us,
                              "hit_error_us": a.action.time_us-j.note_time_us,
                              "disposition": a.disposition.value}
                             for a in session.game.result().actions[action_start:]
                             if a.action.kind.value == "down"]}


def replay(row: dict) -> dict:
    config = config_from_record(row)
    session = TinyLaneSession(config)
    slots = session.layout.plastic_slots
    sample_slots = (slots[0], slots[len(slots)//2], slots[-1])
    spike_times = {i: [] for slot in sample_slots
                   for i in (session.layout.graph.pre_indices[slot],
                             session.layout.graph.post_indices[slot])}
    captured = []
    actions = []
    pulse_spikes = []
    observe = session.plasticity.observe_spikes
    apply = session.simulator.apply_dopamine
    before_final = None
    before_last_note_checkpoint = None

    def observe_record(time_us, indices):
        for i in indices:
            if i in spike_times:
                spike_times[i].append(time_us)
        observe(time_us, indices)

    def apply_record(dopamine):
        nonlocal before_final
        p = session.plasticity.parameters
        t = session.simulator.current_time_us
        before = [session.plasticity.effective_weight(s) for s in slots]
        e = [session.plasticity.eligibility_at(s, t) for s in slots]
        raw = [p.eta * value * dopamine for value in e]
        proposed = [w+d for w, d in zip(before, raw)]
        expected = [min(p.w_max_mv, max(p.w_min_mv, value)) for value in proposed]
        changes = apply(dopamine)
        after = [session.plasticity.effective_weight(s) for s in slots]
        err = max(abs(a-b) for a, b in zip(after, expected))
        assert err < 1e-12
        e_error = max(abs(session.plasticity.eligibility_at(s, t) - oracle_eligibility(
            spike_times[session.layout.graph.pre_indices[s]],
            spike_times[session.layout.graph.post_indices[s]], t,
            p.tau_pre_us, p.tau_eligibility_us)) for s in sample_slots)
        assert e_error < 1e-9
        mean_by_bin = lambda values: [statistics.mean(values[i*48:(i+1)*48])
                                     for i in range(10)]
        captured.append({
            "note_index": session.resolved_count, "time_us": t, "dopamine": dopamine,
            "eligibility_sum": sum(e), "eligibility_max": max(e),
            "eligibility_oracle_max_abs_error": e_error,
            "update_oracle_max_abs_error": err,
            "eligibility_by_ttc_bin": mean_by_bin(e),
            "weights_before_by_ttc_bin": mean_by_bin(before),
            "weights_after_by_ttc_bin": mean_by_bin(after),
            "weight_sum_before": sum(before), "weight_sum_after": sum(after),
            "raw_delta_l1": sum(map(abs, raw)),
            "applied_delta_l1": sum(abs(a-b) for a, b in zip(before, after)),
            "raw_delta_max_abs": max(map(abs, raw)),
            "clipped_low_edges": sum(value < p.w_min_mv for value in proposed),
            "clipped_high_edges": sum(value > p.w_max_mv for value in proposed),
            "zero_weight_edges_after": sum(value == 0 for value in after),
            "upper_bound_edges_after": sum(value == p.w_max_mv for value in after),
            "changed_edges": len(changes),
        })
        if session.resolved_count == session.training_notes-1:
            before_final = dict(zip(slots, before))
        return changes

    session.plasticity.observe_spikes = observe_record
    session.simulator.apply_dopamine = apply_record
    while session.resolved_count < session.training_notes:
        n_decisions = len(session.decisions)
        n_pulses = len(session.exploration_pulses)
        session.step()
        pulsed = len(session.exploration_pulses) != n_pulses
        motor_spikes = sum(session.simulator.spiked_this_tick[i] for i in session.layout.motor)
        if pulsed:
            pulse_spikes.append(motor_spikes)
        if len(session.decisions) != n_decisions:
            action = session.game.result().actions[-1]
            if action.action.kind.value == "down":
                actions.append({"time_us": action.action.time_us,
                                "disposition": action.disposition.value,
                                "exploration_same_tick": pulsed,
                                "motor_spikes_this_tick": motor_spikes})
        if (session.resolved_count == session.training_notes-1
                and before_last_note_checkpoint is None):
            del session.plasticity.observe_spikes
            del session.simulator.apply_dopamine
            before_last_note_checkpoint = session.checkpoint_bytes()
            session.plasticity.observe_spikes = observe_record
            session.simulator.apply_dopamine = apply_record
    # Remove temporary callbacks so trusted same-version serialization stays exact.
    del session.plasticity.observe_spikes
    del session.simulator.apply_dopamine
    data = session.checkpoint_bytes()
    with_update = TinyLaneSession.from_trusted_checkpoint_bytes(data)
    without_update = TinyLaneSession.from_trusted_checkpoint_bytes(data)
    assert before_final is not None
    without_update.plasticity._weights.update(before_final)
    comparison = {"with_final_update": next_outcome(with_update),
                  "undo_final_update_only": next_outcome(without_update),
                  "last_training_event": row["summary"]["events"][23],
                  "frozen_initial_neural_and_game_state_identical": True}
    assert before_last_note_checkpoint is not None
    pulse_on = TinyLaneSession.from_trusted_checkpoint_bytes(before_last_note_checkpoint)
    pulse_off = TinyLaneSession.from_trusted_checkpoint_bytes(before_last_note_checkpoint)
    pulse_on.config = replace(pulse_on.config, plasticity_enabled=False)
    pulse_off.config = replace(pulse_off.config, plasticity_enabled=False,
                               exploration_probability=0.0)
    pulse_comparison = {"exploration_on_weights_frozen": next_outcome(pulse_on),
                        "exploration_off_weights_frozen": next_outcome(pulse_off)}
    assert pulse_on.plasticity._weights == pulse_off.plasticity._weights
    frozen_action_start = len(session.game.result().actions)
    fresh_summary = summarize(session.run(), config.training_notes)
    assert fresh_summary == row["summary"], "instrumentation changed the saved run"
    return {"seed": config.seed, "saved_summary_exact_replay": True,
            "updates": captured, "training_down_actions": actions,
            "exploration_pulses": len(pulse_spikes),
            "exploration_pulse_motor_spikes": dict(Counter(pulse_spikes)),
            "last_training_note_exploration_ablation": pulse_comparison,
            "frozen_down_actions": [{"time_us": a.action.time_us,
                                     "disposition": a.disposition.value}
                                    for a in session.game.result().actions[frozen_action_start:]
                                    if a.action.kind.value == "down"],
            "final_update_causal_comparison": comparison}


def main() -> None:
    all_rows = [json.loads(line) for line in LEDGER.read_text(encoding="utf-8").splitlines()]
    on = [r for r in all_rows if r["stage"] == "heldout" and r["condition"] == "on"]
    blocks = []
    for a, b in ((0, 8), (8, 16), (16, 24), (24, 40)):
        events = [e for r in on for e in r["summary"]["events"][a:b]]
        blocks.append({"notes": [a+1, b], "good_or_better_percent":
                       100*statistics.mean(e["hit_value"] >= 200 for e in events),
                       "mean_utility": statistics.mean(e["game_utility"] for e in events)})
    traces = []
    for seed in (2000, 2009, 2013):
        row = next(r for r in on if r["seed"] == seed)
        traces.append(replay(row))
        print(json.dumps({"seed": seed,
                          "branch": traces[-1]["final_update_causal_comparison"],
                          "exploration": traces[-1]["last_training_note_exploration_ablation"]}), flush=True)
    result = {"method": "Exact saved-config replay; no parameters tuned. Last update undone in a clone with otherwise identical state; one frozen next-note comparison.",
              "ledger_sha256": hashlib.sha256(LEDGER.read_bytes()).hexdigest(),
              "model_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in sorted((ROOT / "src/project_b").rglob("*.py"))},
              "ttc_bins_ms": [500, 400, 300, 200, 150, 100, 75, 50, 25, 0],
              "training_blocks": blocks, "replays": traces}
    OUTPUT.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
