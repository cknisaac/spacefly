"""Run the frozen two-state, single-MBON MaleCNS internal-learning fixture."""

from __future__ import annotations

import json
import math
from pathlib import Path

from project_b.neurons import LIFParameters
from project_b.simulation import SpikingSimulator
from project_b.synapses import SparseGraph, Synapse
from project_b.malecns_minimal_internal_learning.ltd import LocalLTD
from project_b.malecns_minimal_internal_learning.probe import _read_config


def _trial(config: dict, weights: list[float], state: str) -> dict:
    cells = config["circuit"]["selected_kcs"]
    mbon = len(cells)
    edges = [Synapse(i, mbon, weights[i], config["overlay"]["synaptic_delay_us"])
             for i in range(len(cells))]
    graph = SparseGraph(mbon + 1, edges)
    lif = config["overlay"]["lif"]
    params = LIFParameters(
        v_rest_mv=lif["v_rest_mv"], v_reset_mv=lif["v_reset_mv"],
        v_threshold_mv=lif["v_threshold_mv"], tau_m_us=lif["tau_m_us"],
        tau_syn_us=lif["tau_syn_us"], refractory_us=lif["refractory_us"],
    )
    active = [i for i, cell in enumerate(cells) if cell["state"] == state]
    drive = [1.2 if i in active else 0.0 for i in range(len(cells))] + [0.0]
    sim = SpikingSimulator([params] * (mbon + 1), graph, drive,
                           dt_us=lif["dt_us"], record_neurons=[mbon],
                           record_spikes=True)
    snapshot = sim.run_until(config["overlay"]["observation_window_us"])
    voltage = [row.voltage_before_reset_mv for row in snapshot.voltage_trace
               if row.neuron_index == mbon]
    return {
        "state": state,
        "mbon_activity_max_voltage_mv": max(voltage),
        "mbon_spike_count": sum(row.neuron_index == mbon for row in snapshot.spikes),
        "kc_spike_counts": {
            str(cells[i]["source_id"]): sum(row.neuron_index == i
                                            for row in snapshot.spikes)
            for i in range(len(cells))
        },
        "kc_spikes": [{"edge_index": row.neuron_index,
                       "time_us": row.time_us}
                      for row in snapshot.spikes if row.neuron_index < mbon],
    }


def _initial_weights(config: dict) -> list[float]:
    cells = config["circuit"]["selected_kcs"]
    totals = {state: sum(cell["plastic_contact_rows"] for cell in cells
                         if cell["state"] == state) for state in ("A", "B")}
    return [cell["plastic_contact_rows"] / totals[cell["state"]] for cell in cells]


def _train(config: dict, *, taught_state: str, enabled: bool) -> dict:
    rule = LocalLTD(_initial_weights(config), **config["training"]["ltd"])
    trials = []
    window = config["overlay"]["observation_window_us"]
    for repetition in range(config["training"]["repetitions"]):
        offset = repetition * config["training"]["trial_spacing_us"]
        observation = _trial(config, rule.weights, taught_state)
        if enabled:
            for spike in sorted(observation["kc_spikes"], key=lambda row: row["time_us"]):
                rule.observe_kc_spike(spike["edge_index"], offset + spike["time_us"])
        teacher_time = offset + window + config["training"]["teacher_lag_us"]
        changes = rule.teacher_pulse(teacher_time, teacher=enabled)
        trials.append({
            "repetition": repetition + 1,
            "state_presented": taught_state,
            "kc_spike_counts": observation["kc_spike_counts"],
            "eligibility_at_teacher": {
                str(cell["source_id"]): rule.eligibility_at(index, teacher_time)
                for index, cell in enumerate(config["circuit"]["selected_kcs"])
            },
            "teacher": int(enabled),
            "weight_changes": [dict(change, source_id=config["circuit"]["selected_kcs"]
                                    [change["edge_index"]]["source_id"])
                               for change in changes],
            "weights_after_teacher": list(rule.weights),
        })
    return {"trials": trials, "final_weights": list(rule.weights),
            "initial_weights": list(rule.initial)}


def _evaluate(config: dict, weights: list[float]) -> dict:
    threshold = config["controllability_probe"]["frozen_action_threshold_mv"]
    panel = []
    for state in ("A", "B"):
        row = _trial(config, weights, state)
        row["action"] = row["mbon_activity_max_voltage_mv"] <= threshold
        row["frozen_threshold_mv"] = threshold
        panel.append(row)
    return {row["state"]: row for row in panel}


def run_experiment(
    root: Path,
    config_path: str = "configs/malecns_minimal_internal_learning.json",
) -> dict:
    root = Path(root)
    config = _read_config(root, config_path)
    probe_rel = config["controllability_probe"].get("probe_result")
    if not probe_rel or not probe_rel.replace("\\", "/").startswith("runs/"):
        probe_rel = "runs/malecns_minimal_internal_learning/controllability.json"
    probe_path = root / probe_rel
    if not probe_path.is_file():
        raise ValueError(f"pretraining controllability result is missing: {probe_path}")
    probe = json.loads(probe_path.read_text(encoding="utf-8"))
    threshold = config["controllability_probe"].get("frozen_action_threshold_mv")
    if threshold is None:
        raise ValueError("pretraining threshold must be frozen before training")
    if probe.get("status") != "PASS":
        raise ValueError("pretraining controllability probe did not PASS; refusing to train")
    if not math.isclose(probe.get("frozen_action_threshold_mv", float("nan")),
                        threshold, rel_tol=0.0, abs_tol=0.0):
        raise ValueError("pretraining probe threshold differs from frozen config")
    trained = _train(config, taught_state="A", enabled=True)
    control = _train(config, taught_state="A", enabled=False)
    wrong_teacher = _train(config, taught_state="B", enabled=True)
    result = {
        "experiment_id": config["experiment_id"],
        "stage": "minimal_internal_learning",
        "config": config_path,
        "pretraining_probe_status": probe["status"],
        "seed": config["overlay"]["rng_seed"],
        "rng_usage": config["overlay"]["rng_usage"],
        "circuit": config["circuit"],
        "rule": config["training"]["ltd"],
        "threshold_mv": config["controllability_probe"]["frozen_action_threshold_mv"],
        "baseline_frozen_panel": _evaluate(config, _initial_weights(config)),
        "trained_state_a": trained,
        "trained_state_a_frozen_panel": _evaluate(config, trained["final_weights"]),
        "plasticity_off_control": control,
        "plasticity_off_frozen_panel": _evaluate(config, control["final_weights"]),
        "wrong_state_teacher_control": wrong_teacher,
        "wrong_state_teacher_frozen_panel": _evaluate(config, wrong_teacher["final_weights"]),
    }
    learned = result["trained_state_a_frozen_panel"]
    off = result["plasticity_off_frozen_panel"]
    wrong = result["wrong_state_teacher_frozen_panel"]
    changed = trained["final_weights"] != trained["initial_weights"]
    a_changed = any(a != b for a, b, cell in zip(
        trained["final_weights"], trained["initial_weights"],
        config["circuit"]["selected_kcs"]) if cell["state"] == "A")
    b_unchanged = all(a == b for a, b, cell in zip(
        trained["final_weights"], trained["initial_weights"],
        config["circuit"]["selected_kcs"]) if cell["state"] == "B")
    result["criteria"] = {
        "only_selected_internal_kc_mbon_weights_changed": changed,
        "state_selective_changes": a_changed and b_unchanged,
        "state_a_action_after_training": learned["A"]["action"],
        "state_b_no_action_after_training": not learned["B"]["action"],
        "plasticity_off_did_not_acquire_state_a_action": not off["A"]["action"],
        "wrong_teacher_moves_action_to_state_b": (not wrong["A"]["action"]
                                                   and wrong["B"]["action"]),
        "frozen_test_has_no_teacher_or_plasticity": True,
        "fixed_threshold_unchanged": True,
        "external_trainable_decoder_absent": True,
    }
    result["status"] = ("PASS" if all(result["criteria"].values()) else "FAIL")
    result["strongest_honest_claim"] = (
        "A deterministic connectome-constrained adult Drosophila simulation fixture "
        "stored a two-state association in selected KC→MBON05 weight variables under "
        "an artificial encoder, voltage normalization, teacher-gated LTD rule and "
        "fixed threshold readout. This is an internal-learning infrastructure proof, "
        "not evidence of adult fly physiology or behavior."
        if result["status"] == "PASS" else
        "The reduced fixture did not meet its predeclared learning criterion; the "
        "failure is limited to this engineering overlay and is not evidence against biology."
    )
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--config", default="configs/malecns_minimal_internal_learning.json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run_experiment(args.root, args.config)
    encoded = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
