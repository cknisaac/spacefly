"""Reproduce the synthetic lane-one closed loop and its plasticity-off control."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, replace
from pathlib import Path

import yaml

from project_b.experiments import ClosedLoopResult, TinyBrainConfig, run_tiny_lane_one
from project_b.osu import ManiaJudgement


def _phase_metrics(result: ClosedLoopResult, start: int, stop: int) -> dict[str, object]:
    records = result.judgements[start:stop]
    hits = [record for record in records if record.judgement is not ManiaJudgement.MISS]
    return {
        "notes": len(records),
        "hits": len(hits),
        "hit_rate": len(hits) / len(records) if records else None,
        "timing_mae_ms_on_hits": (
            sum(abs(record.hit_error_us) for record in hits) / len(hits) / 1_000
            if hits else None),
        "judgement_counts": {
            judgement.name: sum(record.judgement is judgement for record in records)
            for judgement in ManiaJudgement},
    }


def _run_report(result: ClosedLoopResult) -> dict[str, object]:
    train = (result.config.note_count if result.config.training_notes is None
             else result.config.training_notes)
    return {
        "topology": {
            "neurons": result.config.neuron_count,
            "edges": result.graph_edge_count,
            "plastic_edges": result.plastic_edge_count,
            "source": "synthetic_tiny_brain_v1",
            "fly_connectome": None,
        },
        "population_spike_counts": {
            "sensory": result.sensory_spikes,
            "relay": result.relay_spikes,
            "motor": result.motor_spikes,
            "inhibitory": result.inhibitory_spikes,
        },
        "peak_queued_arrivals": result.peak_queued_arrivals,
        "exploration_pulse_times_us": result.exploration_pulses,
        "decisions": [
            {
                "time_us": decision.time_us,
                "lane": decision.action.lane,
                "key_action": decision.action.kind.value,
                "motor_spikes_in_window": decision.spike_count_in_window,
                "fixed_threshold": decision.threshold,
            } for decision in result.decisions],
        "training_metrics": _phase_metrics(result, 0, train),
        "frozen_metrics": _phase_metrics(result, train, result.config.note_count),
        "note_events": [
            {
                "note_id": judgement.note_id,
                "lane": judgement.lane,
                "note_time_us": judgement.note_time_us,
                "judgement_time_us": judgement.event_time_us,
                "hit_error_us": judgement.hit_error_us,
                "judgement": judgement.judgement.name,
                "hit_value": delivery.reinforcement.utility.hit_value,
                "utility": delivery.reinforcement.utility.utility,
                "expected_utility_before": (
                    delivery.reinforcement.prediction.expected_before),
                "rpe": delivery.reinforcement.prediction.rpe,
                "expected_utility_after": (
                    delivery.reinforcement.prediction.expected_after),
                "dopamine_like_amplitude": (
                    delivery.reinforcement.modulation.amplitude),
                "modulation_generated_time_us": (
                    delivery.reinforcement.modulation.time_us),
                "modulation_delivered_time_us": delivery.delivered_time_us,
                "weight_changes": [asdict(change)
                                   for change in delivery.weight_changes],
            }
            for judgement, delivery in zip(result.judgements, result.feedback)],
        "weights": {
            "initial_min_mv": min(result.initial_plastic_weights_mv),
            "initial_max_mv": max(result.initial_plastic_weights_mv),
            "final_min_mv": min(result.final_plastic_weights_mv),
            "final_max_mv": max(result.final_plastic_weights_mv),
            "changed_edges": sum(before != after for before, after in zip(
                result.initial_plastic_weights_mv,
                result.final_plastic_weights_mv)),
            "edges_at_lower_bound": sum(weight <= 0.0
                                        for weight in result.final_plastic_weights_mv),
            "edges_at_upper_bound": sum(weight >= 2.0
                                        for weight in result.final_plastic_weights_mv),
        },
    }


def build_report(config_path: Path) -> dict[str, object]:
    with config_path.open("r", encoding="utf-8") as stream:
        document = yaml.safe_load(stream)
    if not isinstance(document, dict) or set(document) != {"tiny_brain"}:
        raise ValueError("config must contain one 'tiny_brain' mapping")
    if not isinstance(document["tiny_brain"], dict):
        raise ValueError("tiny_brain settings must be a mapping")
    config = TinyBrainConfig(**document["tiny_brain"])
    learned = run_tiny_lane_one(config)
    control = run_tiny_lane_one(replace(config, plasticity_enabled=False))
    return {
        "resolved_config": asdict(config),
        "ruleset": {"mode": "osu!mania 4K", "profile": "stable_native", "od": 8},
        "seed_policy": "same declared seed and tickwise RNG stream for both runs",
        "metrics_definition": "hit = non-MISS; MAE uses judged hit errors only",
        "plasticity_on": _run_report(learned),
        "plasticity_off": _run_report(control),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/m2_tiny.yaml"))
    parser.add_argument("--output", type=Path,
                        default=Path("docs/figures/m2_tiny_run.json"))
    args = parser.parse_args()
    report = build_report(args.config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    trained = report["plasticity_on"]["frozen_metrics"]
    control = report["plasticity_off"]["frozen_metrics"]
    print(f"Wrote {args.output}; frozen hits: {trained['hits']}/{trained['notes']} "
          f"versus plasticity-off {control['hits']}/{control['notes']}")


if __name__ == "__main__":
    main()
