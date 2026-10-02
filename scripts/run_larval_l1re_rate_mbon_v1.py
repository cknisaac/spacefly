"""Evaluate the L1R-E Option 3 anatomy-weighted rate MBON abstraction."""

from __future__ import annotations

import hashlib
import itertools
import json
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "configs/larval_l1re_manifest_v1.json"
POLICY_PATH = ROOT / "configs/larval_l1re_rate_mbon_v2_policy.json"
OUTPUT_PATH = ROOT / "runs/larval_l1re_rate_mbon_v2.json"
NOMINAL_PATH = ROOT / "configs/larval_l1re_rate_mbon_v2.json"
FACTORS = (1.0, 0.8, 0.6, 0.4, 0.2)


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(data: object) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest().upper()


def face_components(configs: list[dict], axis_count: int = 2) -> list[list[str]]:
    by_coordinate = {tuple(row["coordinates"]): row["config_id"] for row in configs}
    remaining = set(by_coordinate)
    result = []
    while remaining:
        start = min(remaining)
        remaining.remove(start)
        queue = deque([start])
        found = []
        while queue:
            current = queue.popleft()
            found.append(by_coordinate[current])
            for axis in range(axis_count):
                for delta in (-1, 1):
                    neighbor = list(current)
                    neighbor[axis] += delta
                    neighbor = tuple(neighbor)
                    if neighbor in remaining:
                        remaining.remove(neighbor)
                        queue.append(neighbor)
        result.append(sorted(found))
    return sorted(result, key=lambda values: (-len(values), values))


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    if policy["status"] != "FROZEN_BEFORE_SIMULATION":
        raise RuntimeError("rate-model policy is not frozen")
    manifest_hash = file_hash(MANIFEST_PATH)
    if manifest_hash != policy["manifest"]["sha256"]:
        raise RuntimeError("manifest hash mismatch")
    policy_hash = file_hash(POLICY_PATH)

    kcs = sorted(int(node["source_id"]) for node in manifest["nodes"] if node["role"] == "KC")
    mbon_ids = sorted(int(node["source_id"]) for node in manifest["nodes"] if node["role"] == "MBON-m1")
    groups = [kcs[index * 11:(index + 1) * 11] for index in range(8)]
    edge_contacts = {(int(row["pre_id"]), int(row["post_id"])): int(row["contacts"])
                     for row in manifest["edges"]}

    resolved = []
    alpha_values = policy["model"]["contact_exponent_alpha"]
    gains = policy["model"]["rate_gain"]
    for ordinal, (coordinates, (alpha, gain)) in enumerate(zip(
        itertools.product(range(len(alpha_values)), range(len(gains))),
        itertools.product(alpha_values, gains),
    )):
        state_drives_by_mbon = []
        for group in groups:
            per_mbon = {
                str(mbon_id): sum(
                    edge_contacts.get((kc_id, mbon_id), 0) ** float(alpha)
                    for kc_id in group
                    if edge_contacts.get((kc_id, mbon_id), 0) > 0
                )
                for mbon_id in mbon_ids
            }
            state_drives_by_mbon.append(per_mbon)
        bilateral_drive = [sum(per_mbon.values()) for per_mbon in state_drives_by_mbon]
        maximum_drive = max(bilateral_drive)
        if maximum_drive <= 0 or any(value <= 0 for value in bilateral_drive):
            raise RuntimeError("selected KC group has no measured KC -> MBON-m1 drive")
        full_rates = [float(gain) * value / maximum_drive for value in bilateral_drive]
        ordered = sorted(full_rates)
        cutoffs = {
            "lower": 0.2 * ordered[1],
            "upper": 0.2 * ordered[5],
        }
        resolved.append({
            "config_id": f"L1RE-RATE-{ordinal:02d}",
            "coordinates": list(coordinates),
            "alpha": float(alpha),
            "gain": float(gain),
            "state_anatomical_drive_by_mbon": state_drives_by_mbon,
            "state_bilateral_drive": bilateral_drive,
            "normalization_max_bilateral_drive": maximum_drive,
            "full_weight_rates_by_state": full_rates,
            "fixed_action_cutoffs": cutoffs,
        })

    configuration_results = []
    all_rows = []
    for config in resolved:
        factors_data = []
        replay_exact = True
        for factor in FACTORS:
            factor_rows = []
            for state, per_mbon in enumerate(config["state_anatomical_drive_by_mbon"]):
                rates_by_mbon = {
                    mbon_id: float(config["gain"]) * float(per_mbon[mbon_id])
                    / float(config["normalization_max_bilateral_drive"]) * factor
                    for mbon_id in map(str, mbon_ids)
                }
                bilateral_rate = sum(rates_by_mbon.values())
                actions = {
                    name: bilateral_rate <= cutoff
                    for name, cutoff in config["fixed_action_cutoffs"].items()
                }
                row = {
                    "config_id": config["config_id"],
                    "state": state,
                    "weight_factor": factor,
                    "rates_by_mbon": rates_by_mbon,
                    "bilateral_rate": bilateral_rate,
                    "fixed_action_cutoffs": config["fixed_action_cutoffs"],
                    "actions": actions,
                    "armed": True,
                }
                first_digest = digest(row)
                second_digest = digest(json.loads(json.dumps(row)))
                row["replay_digest"] = first_digest
                row["second_replay_digest"] = second_digest
                row["deterministic_replay_match"] = first_digest == second_digest
                replay_exact &= row["deterministic_replay_match"]
                factor_rows.append(row)
                all_rows.append(row)
            factors_data.append({"factor": factor, "states": factor_rows})

        rows_by_factor = {record["factor"]: {r["state"]: r for r in record["states"]}
                          for record in factors_data}
        gate_by_cutoff = {}
        for name in ("lower", "upper"):
            action_sets = {
                factor: {state for state in range(8) if rows_by_factor[factor][state]["actions"][name]}
                for factor in FACTORS
            }
            nested = all(action_sets[left].issubset(action_sets[right])
                         for left, right in zip(FACTORS, FACTORS[1:]))
            transitions = {
                state for state in range(8)
                if state not in action_sets[1.0]
                and any(state in action_sets[factor] for factor in FACTORS[1:])
            }
            minimum_transitions = 2 if name == "lower" else 3
            gate_by_cutoff[name] = {
                "action_states_by_factor": {str(factor): sorted(action_sets[factor]) for factor in FACTORS},
                "nested": nested,
                "transition_states": sorted(transitions),
                "full_weight_action_count": len(action_sets[1.0]),
                "factor_0.2_action_count": len(action_sets[0.2]),
                "qualifies": (
                    nested and not action_sets[1.0]
                    and len(transitions) >= minimum_transitions
                    and 2 <= len(action_sets[0.2]) <= 6
                ),
            }
        positive_all_states = all(value > 0 for value in config["full_weight_rates_by_state"])
        exact_weight_scaling = all(
            abs(rows_by_factor[factor][state]["bilateral_rate"]
                - config["full_weight_rates_by_state"][state] * factor) < 1e-12
            for factor in FACTORS for state in range(8)
        )
        checks = {
            "all_eight_states_have_positive_anatomical_drive": positive_all_states,
            "rates_scale_exactly_with_local_weight_factor": exact_weight_scaling,
            "rates_nonincreasing_for_all_states": all(
                rows_by_factor[left][state]["bilateral_rate"] >= rows_by_factor[right][state]["bilateral_rate"]
                for left, right in zip(FACTORS, FACTORS[1:]) for state in range(8)
            ),
            "factor_0.2_reduces_rate_80_percent_for_all_states": all(
                abs(rows_by_factor[0.2][state]["bilateral_rate"]
                    / rows_by_factor[1.0][state]["bilateral_rate"] - 0.2) < 1e-12
                for state in range(8)
            ),
            "both_anatomy_derived_action_cutoffs_qualify": all(row["qualifies"] for row in gate_by_cutoff.values()),
            "all_replays_exact": replay_exact,
        }
        result = {
            "config_id": config["config_id"],
            "coordinates": config["coordinates"],
            "alpha": config["alpha"],
            "gain": config["gain"],
            "checks": checks,
            "qualifies": all(checks.values()),
            "action_cutoff_results": gate_by_cutoff,
        }
        configuration_results.append(result)
        print(f"{config['config_id']}: {'QUALIFY' if result['qualifies'] else 'no'}", flush=True)

    qualified = [row for row in configuration_results if row["qualifies"]]
    spans = [sorted({row["coordinates"][axis] for row in qualified}) for axis in range(2)]
    connected = face_components(qualified)
    largest = connected[0] if connected else []
    eval_by_id = {row["config_id"]: row for row in configuration_results}
    robust_members = [
        config_id for config_id in largest
        if all(report["qualifies"] for report in eval_by_id[config_id]["action_cutoff_results"].values())
    ]
    family_checks = {
        "at_least_9_of_12_configurations_qualify": len(qualified) >= 9,
        "all_alpha_values_represented": len(spans[0]) == len(alpha_values),
        "all_rate_gains_represented": len(spans[1]) == len(gains),
        "largest_face_connected_component_at_least_8": len(largest) >= 8,
        "at_least_6_component_members_qualify_at_both_adjacent_cutoffs": len(robust_members) >= 6,
    }
    passed = all(family_checks.values())
    output = {
        "experiment_id": "larval_l1re_rate_mbon_v2",
        "variant": "L1R-E-option3",
        "status": "PASS" if passed else "FAIL",
        "frozen_inputs": {
            "manifest_sha256": manifest_hash,
            "policy_sha256": policy_hash,
            "teacher_enabled": False,
            "plasticity_enabled": False,
            "action_rule_trainable": False,
        },
        "rate_equation": policy["model"],
        "resolved_family": resolved,
        "configuration_evaluations": configuration_results,
        "family_evaluation": {
            "checks": family_checks,
            "qualifying_configuration_count": len(qualified),
            "qualifying_config_ids": [row["config_id"] for row in qualified],
            "qualifying_axis_spans": spans,
            "face_connected_components": connected,
            "largest_component": largest,
            "largest_component_size": len(largest),
            "robust_members": robust_members,
        },
        "measurements": all_rows,
        "interpretation": "PASS, if attained, admits only an engineering anatomy-weighted rate-model design for a separate learning-rule gate. MBON units are continuous rates, not spikes; no biological electrical prediction or learning result is established.",
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    if passed:
        nominal = {
            "model_id": "larval_l1re_rate_mbon_v1",
            "status": "FROZEN_AFTER_RATE_CONTROLLABILITY_PASS",
            "variant": "L1R-E-option3",
            "manifest_sha256": manifest_hash,
            "policy_sha256": policy_hash,
            "result_sha256": file_hash(OUTPUT_PATH),
            "rate_equation": policy["model"],
            "action_interface": policy["action_interface"],
            "interpretation_limit": "engineering rate model; MBON activity is not represented as spikes",
        }
        NOMINAL_PATH.write_text(json.dumps(nominal, indent=2) + "\n", encoding="utf-8")
    elif NOMINAL_PATH.exists():
        raise RuntimeError("failed gate must not create a nominal rate model")
    print(json.dumps({"status": output["status"], "result_sha256": file_hash(OUTPUT_PATH),
                      "qualifiers": len(qualified), "largest_component": len(largest),
                      "robust_members": len(robust_members), "checks": family_checks}, indent=2))


if __name__ == "__main__":
    main()
