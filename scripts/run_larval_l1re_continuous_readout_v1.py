"""Test L1R-E Option 2: continuous MBON membrane readout for action."""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import sys
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from project_b.neurons import LIFParameters
from project_b.simulation import SpikingSimulator
from project_b.synapses import SparseGraph, Synapse


MANIFEST_PATH = ROOT / "configs/larval_l1re_manifest_v1.json"
FAMILY_PATH = ROOT / "configs/larval_l1re_electrical_family_v2_policy.json"
POLICY_PATH = ROOT / "configs/larval_l1re_continuous_readout_v1_policy.json"
OUTPUT_PATH = ROOT / "runs/larval_l1re_continuous_readout_v1.json"
NOMINAL_PATH = ROOT / "configs/larval_l1re_continuous_readout_electrical_v1.json"
FACTORS = (1.0, 0.8, 0.6, 0.4, 0.2)


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest().upper()


def groups_for(kc_ids: list[int], group_count: int) -> list[list[int]]:
    base, remainder = divmod(len(kc_ids), group_count)
    groups = []
    cursor = 0
    for group_index in range(group_count):
        size = base + int(group_index < remainder)
        groups.append(kc_ids[cursor:cursor + size])
        cursor += size
    if cursor != len(kc_ids) or len({item for group in groups for item in group}) != len(kc_ids):
        raise RuntimeError("invalid deterministic KC partition")
    return groups


def run_one(manifest: dict, family: dict, config: dict, factor: float, state: int | None) -> dict:
    nodes = manifest["nodes"]
    ids = [int(node["source_id"]) for node in nodes]
    idx = {source_id: i for i, source_id in enumerate(ids)}
    roles = {int(node["source_id"]): node["role"] for node in nodes}
    kc_ids = sorted(source_id for source_id in ids if roles[source_id] == "KC")
    mbon_ids = sorted(source_id for source_id in ids if roles[source_id] == "MBON-m1")
    groups = groups_for(kc_ids, int(family["encoder"]["state_count"]))
    edges = [Synapse(
        idx[int(row["pre_id"])],
        idx[int(row["post_id"])],
        int(row["contacts"]) * float(config["contact_effect_mv_per_contact"]) * factor,
        int(family["synapse_model"]["delay_us"]),
    ) for row in manifest["edges"]]
    graph = SparseGraph(len(nodes), edges)

    kc_model, mbon_model = family["kc_neuron_model"], family["mbon_neuron_model"]
    params = []
    for source_id in ids:
        if roles[source_id] == "KC":
            model = kc_model
            tau_m = int(model["tau_m_us"])
            threshold = float(model["threshold_above_rest_mv_equivalent"])
        else:
            model = mbon_model
            tau_m = int(config["mbon_tau_m_us"])
            threshold = float(config["mbon_threshold_mv"])
        params.append(LIFParameters(
            v_rest_mv=float(model["v_rest_mv_equivalent"]),
            v_reset_mv=float(model["v_reset_mv_equivalent"]),
            v_threshold_mv=threshold,
            tau_m_us=tau_m,
            tau_syn_us=int(model["tau_syn_us"]),
            refractory_us=int(model["refractory_us"]),
        ))
    drive = [0.0] * len(nodes)
    intended_kcs: list[int] = []
    if state is not None:
        intended_kcs = groups[state]
        for source_id in intended_kcs:
            drive[idx[source_id]] = float(config["pulse_mv"])
    mbon_indices = [idx[source_id] for source_id in mbon_ids]
    sim = SpikingSimulator(
        params, graph, drive,
        dt_us=int(family["integration"]["dt_us"]),
        record_neurons=mbon_indices,
        record_spikes=True,
        max_queued_events=int(family["integration"]["max_queued_events"]),
        max_scheduled_events=int(family["integration"]["max_scheduled_events"]),
    )
    if state is not None:
        sim.run_until(int(family["encoder"]["pulse_duration_us"]))
        sim.set_external_drive_mv([0.0] * len(nodes))
    duration = int(config["response_window_us"])
    snapshot = sim.run_until(duration)
    diagnostics = sim.diagnostics()

    # Voltage after reset is the continuous subthreshold state. Sampling includes
    # every integration tick from 1 ms through the fixed response-window end.
    trace = [sample for sample in snapshot.voltage_trace if sample.time_us > 0]
    if len(trace) != duration // int(family["integration"]["dt_us"]) * len(mbon_ids):
        raise RuntimeError("MBON voltage trace is incomplete for the declared window")
    mean_voltage = sum(sample.voltage_after_reset_mv for sample in trace) / len(trace)
    normalized_activity = mean_voltage / float(config["mbon_threshold_mv"])
    activity_milliunits = 1000.0 * normalized_activity
    thresholds = [int(value) for value in [250, 500, 750]]
    actions = {
        str(threshold): bool(state is not None and activity_milliunits <= threshold)
        for threshold in thresholds
    }
    by_source = {str(ids[i]): int(value) for i, value in enumerate(snapshot.spike_counts) if value}
    intended_spikes = {str(source_id): int(snapshot.spike_counts[idx[source_id]]) for source_id in intended_kcs}
    mbon_spikes = {str(source_id): int(snapshot.spike_counts[idx[source_id]]) for source_id in mbon_ids}
    finite = (
        all(math.isfinite(value) for value in snapshot.voltage_mv)
        and all(math.isfinite(value) for value in snapshot.synaptic_drive_mv)
        and all(math.isfinite(sample.voltage_after_reset_mv) for sample in trace)
        and math.isfinite(mean_voltage)
        and math.isfinite(normalized_activity)
    )
    payload = {
        "factor": factor,
        "state": state,
        "voltage_after_reset": [sample.voltage_after_reset_mv.hex() for sample in trace],
        "spikes": [[event.time_us, ids[event.neuron_index], event.voltage_before_reset_mv.hex()]
                   for event in snapshot.spikes],
        "actions": actions,
        "events": [diagnostics.scheduled_events, diagnostics.delivered_events,
                   diagnostics.peak_queued_events, snapshot.queued_arrivals],
    }
    return {
        "state": state,
        "weight_factor": factor,
        "intended_kc_source_ids": intended_kcs,
        "intended_kc_spikes_by_source_id": intended_spikes,
        "all_intended_kcs_activated": bool(intended_kcs) and all(value > 0 for value in intended_spikes.values()),
        "spikes_by_source_id_nonzero": by_source,
        "mbon_m1_spikes_by_source_id": mbon_spikes,
        "bilateral_mbon_m1_spike_count": sum(mbon_spikes.values()),
        "bilateral_mbon_mean_voltage_mv_equivalent": mean_voltage,
        "continuous_activity_normalized_to_threshold": normalized_activity,
        "continuous_activity_threshold_milliunits": activity_milliunits,
        "actions_by_threshold_milliunits": actions,
        "interface_armed": state is not None,
        "mbon_voltage_range_mv": {
            "minimum_after_reset": min(sample.voltage_after_reset_mv for sample in trace),
            "maximum_after_reset": max(sample.voltage_after_reset_mv for sample in trace),
        },
        "events": {
            "scheduled": diagnostics.scheduled_events,
            "delivered": diagnostics.delivered_events,
            "peak_queued": diagnostics.peak_queued_events,
            "queued_at_end": snapshot.queued_arrivals,
            "max_spikes_one_tick": max(diagnostics.spike_counts_by_tick, default=0),
        },
        "numerical": {
            "finite": finite,
            "queue_within_bound": diagnostics.peak_queued_events <= int(family["integration"]["max_queued_events"]),
            "scheduled_within_bound": diagnostics.scheduled_events <= int(family["integration"]["max_scheduled_events"]),
        },
        "replay_digest": digest(payload),
    }


def action_gate(rows_by_factor: dict[float, dict[int, dict]], threshold: int) -> dict:
    factors = FACTORS
    action_sets = {
        factor: {state for state, row in rows_by_factor[factor].items()
                 if row["actions_by_threshold_milliunits"][str(threshold)]}
        for factor in factors
    }
    nested = all(action_sets[left].issubset(action_sets[right]) for left, right in zip(factors, factors[1:]))
    transitions = {
        state for state in range(8)
        if state not in action_sets[1.0]
        and any(state in action_sets[factor] for factor in factors[1:])
    }
    low_count = len(action_sets[0.2])
    qualifies = nested and len(transitions) >= 3 and 2 <= low_count <= 6
    return {
        "threshold_milliunits": threshold,
        "action_states_by_factor": {str(factor): sorted(action_sets[factor]) for factor in factors},
        "nested": nested,
        "transition_states": sorted(transitions),
        "factor_0.2_action_count": low_count,
        "qualifies": qualifies,
    }


def evaluate(config: dict, baseline: dict, measurements: list[dict]) -> dict:
    by_factor: dict[float, dict[int, dict]] = {factor: {} for factor in FACTORS}
    for row in measurements:
        by_factor[float(row["weight_factor"])][int(row["state"])] = row
    zero_ok = not baseline["spikes_by_source_id_nonzero"] and not baseline["interface_armed"] and all(baseline["numerical"].values())
    replay_ok = all(row["deterministic_replay_match"] for row in measurements)
    finite_ok = all(all(row["numerical"].values()) for row in measurements)
    cues_ok = all(row["all_intended_kcs_activated"] for row in measurements)
    full_active = [s for s, row in by_factor[1.0].items() if row["bilateral_mbon_m1_spike_count"] >= 1]
    effect_states, monotone_states, reversal_states, spike_monotone_states = [], [], [], []
    for state in range(8):
        rows = [by_factor[factor][state] for factor in FACTORS]
        full = rows[0]["continuous_activity_normalized_to_threshold"]
        low = rows[-1]["continuous_activity_normalized_to_threshold"]
        if full > 0 and (full - low) / full >= 0.30:
            effect_states.append(state)
        if all(a["continuous_activity_normalized_to_threshold"] >= b["continuous_activity_normalized_to_threshold"]
               for a, b in zip(rows, rows[1:])):
            monotone_states.append(state)
        if any(b["continuous_activity_normalized_to_threshold"] - a["continuous_activity_normalized_to_threshold"]
               > max(a["continuous_activity_normalized_to_threshold"] * 0.01, 1e-12)
               for a, b in zip(rows, rows[1:])):
            reversal_states.append(state)
        counts = [row["bilateral_mbon_m1_spike_count"] for row in rows]
        if all(a >= b for a, b in zip(counts, counts[1:])):
            spike_monotone_states.append(state)

    action_reports = {str(threshold): action_gate(by_factor, threshold) for threshold in (250, 500, 750)}
    qualifying = [int(threshold) for threshold, report in action_reports.items() if report["qualifies"]]
    adjacent_robust = [threshold for threshold in qualifying
                       if any(abs(threshold - other) == 250 for other in qualifying)]
    checks = {
        "zero_drive_silent_disarmed_finite_bounded": zero_ok,
        "all_replays_exact": replay_ok,
        "all_driven_runs_finite_bounded": finite_ok,
        "all_cues_activate_every_intended_KC": cues_ok,
        "full_weight_spiking_activity_in_at_least_6_states": len(full_active) >= 6,
        "continuous_activity_reduction_at_least_30_percent_in_6_states": len(effect_states) >= 6,
        "continuous_readout_monotone_in_at_least_7_states": len(monotone_states) >= 7,
        "no_continuous_readout_reversal_over_1_percent": not reversal_states,
        "spike_counts_monotone_in_at_least_7_states": len(spike_monotone_states) >= 7,
        "at_least_one_continuous_action_cutoff_qualifies": bool(qualifying),
    }
    return {
        "config_id": config["config_id"],
        "coordinates": config["coordinates"],
        "values": config,
        "qualifies": all(checks.values()),
        "checks": checks,
        "full_weight_active_states": full_active,
        "continuous_effect_states": effect_states,
        "continuous_monotone_states": monotone_states,
        "continuous_reversal_states": reversal_states,
        "spike_monotone_states": spike_monotone_states,
        "action_cutoff_reports": action_reports,
        "qualifying_action_cutoffs_milliunits": qualifying,
        "robust_at_adjacent_action_cutoff": bool(adjacent_robust),
        "robust_adjacent_action_cutoffs_milliunits": adjacent_robust,
    }


def components(qualifiers: list[dict], axis_count: int) -> list[list[str]]:
    by_coordinate = {tuple(row["coordinates"]): row["config_id"] for row in qualifiers}
    unseen = set(by_coordinate)
    found = []
    while unseen:
        start = min(unseen)
        unseen.remove(start)
        queue = deque([start])
        part = []
        while queue:
            here = queue.popleft()
            part.append(by_coordinate[here])
            for axis in range(axis_count):
                for delta in (-1, 1):
                    nxt = list(here)
                    nxt[axis] += delta
                    nxt = tuple(nxt)
                    if nxt in unseen:
                        unseen.remove(nxt)
                        queue.append(nxt)
        found.append(sorted(part))
    return sorted(found, key=lambda part: (-len(part), part))


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    family = json.loads(FAMILY_PATH.read_text(encoding="utf-8"))
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    if policy["status"] != "FROZEN_BEFORE_SIMULATION":
        raise RuntimeError("continuous-readout policy is not frozen")
    hashes = {"manifest": file_hash(MANIFEST_PATH), "family": file_hash(FAMILY_PATH), "policy": file_hash(POLICY_PATH)}
    if hashes["manifest"] != policy["manifest"]["sha256"] or hashes["family"] != policy["family_policy"]["sha256"]:
        raise RuntimeError("frozen input hash mismatch")

    axes = (
        family["synapse_model"]["KC_to_MBON-m1_contact_effect_mv_equivalent"],
        family["mbon_neuron_model"]["tau_m_us"],
        family["mbon_neuron_model"]["threshold_above_rest_mv_equivalent"],
        family["encoder"]["pulse_mv_equivalent"],
        family["integration"]["response_window_us"],
    )
    resolved = []
    for ordinal, (coords, values) in enumerate(zip(
        itertools.product(*(range(len(axis)) for axis in axes)),
        itertools.product(*axes),
    )):
        contact, tau, threshold, pulse, window = values
        resolved.append({
            "config_id": f"L1RE-CR-{ordinal:03d}",
            "coordinates": list(coords),
            "contact_effect_mv_per_contact": float(contact),
            "mbon_tau_m_us": int(tau),
            "mbon_threshold_mv": float(threshold),
            "pulse_mv": float(pulse),
            "response_window_us": int(window),
        })
    if len(resolved) != int(policy["family_policy"]["configuration_count"]):
        raise RuntimeError("resolved family size mismatch")

    evaluations, all_runs = [], []
    for config in resolved:
        baseline = run_one(manifest, family, config, 1.0, None)
        records = []
        for factor in FACTORS:
            for state in range(8):
                first = run_one(manifest, family, config, factor, state)
                second = run_one(manifest, family, config, factor, state)
                first["second_replay_digest"] = second["replay_digest"]
                first["deterministic_replay_match"] = first["replay_digest"] == second["replay_digest"]
                records.append(first)
        result = evaluate(config, baseline, records)
        evaluations.append(result)
        all_runs.append({"config_id": config["config_id"], "configuration": config,
                         "zero_drive_baseline": baseline, "measurements": records})
        print(f"{config['config_id']}: {'QUALIFY' if result['qualifies'] else 'no'}", flush=True)

    qualified = [row for row in evaluations if row["qualifies"]]
    spans = [sorted({row["coordinates"][axis] for row in qualified}) for axis in range(5)]
    connected = components(qualified, 5)
    largest = connected[0] if connected else []
    by_eval = {row["config_id"]: row for row in evaluations}
    checks = {
        "at_least_12_qualifiers": len(qualified) >= 12,
        "at_least_two_values_on_every_axis": all(len(span) >= 2 for span in spans),
        "largest_face_connected_component_at_least_8": len(largest) >= 8,
        "at_least_6_largest_component_members_robust_at_adjacent_cutoff": sum(
            by_eval[config_id]["robust_at_adjacent_action_cutoff"] for config_id in largest
        ) >= 6,
    }
    passed = all(checks.values())
    result = {
        "experiment_id": "larval_l1re_continuous_readout_v1",
        "variant": "L1R-E-option2",
        "status": "PASS" if passed else "FAIL",
        "frozen_input_hashes": hashes,
        "readout_contract": policy["readout"],
        "resolved_family": resolved,
        "configuration_evaluations": evaluations,
        "family_evaluation": {
            "checks": checks,
            "qualifying_configuration_count": len(qualified),
            "qualifying_config_ids": [row["config_id"] for row in qualified],
            "qualifying_axis_spans": spans,
            "face_connected_components": connected,
            "largest_component": largest,
            "largest_component_size": len(largest),
            "robust_adjacent_cutoff_members_in_largest": [
                config_id for config_id in largest if by_eval[config_id]["robust_at_adjacent_action_cutoff"]
            ],
        },
        "runs": all_runs,
        "interpretation": "The action boundary reads a continuous MBON membrane state. All electrical values remain engineering assumptions; no plasticity, teaching, learning, or biological pathway inference was tested.",
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if passed:
        nominal = {
            "model_id": "larval_l1re_continuous_readout_electrical_v1",
            "variant": "L1R-E-option2",
            "status": "FROZEN_AFTER_PREDECLARED_CONTROLLABILITY_PASS",
            "manifest_sha256": hashes["manifest"],
            "family_policy_sha256": hashes["family"],
            "readout_policy_sha256": hashes["policy"],
            "result_sha256": file_hash(OUTPUT_PATH),
            "family_checks": checks,
            "teacher": "artificial local port; inactive in controllability gate",
            "plasticity": "disabled in controllability gate",
            "continuous_readout": policy["readout"],
        }
        NOMINAL_PATH.write_text(json.dumps(nominal, indent=2) + "\n", encoding="utf-8")
    elif NOMINAL_PATH.exists():
        raise RuntimeError("failed gate must not leave a nominal model")
    print(json.dumps({"status": result["status"], "result_sha256": file_hash(OUTPUT_PATH),
                      "qualifiers": len(qualified), "largest_component": len(largest),
                      "checks": checks}, indent=2))


if __name__ == "__main__":
    main()
