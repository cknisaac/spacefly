"""Independent exact-row and fail-closed audit of Circuit V1 policy products."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
PRODUCTS = ("neuron_policy.parquet", "connection_policy.parquet", "boundary_policy.json")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def audit(subset: Path, config_path: Path, product: Path) -> dict:
    subset, config_path, product = Path(subset), Path(config_path), Path(product)
    selection = json.loads((subset / "manifest.json").read_text(encoding="utf-8"))
    config = json.loads(config_path.read_text(encoding="utf-8"))
    manifest = json.loads((product / "manifest.json").read_text(encoding="utf-8"))
    require(sha(subset / "manifest.json") == manifest["anatomical_subset_manifest_sha256"],
            "Anatomical subset manifest changed")
    require(sha(config_path) == manifest["policy_config_sha256"], "Policy configuration changed")
    require(config["selection_source_id_sha256"] == selection["source_id_sha256"] ==
            manifest["anatomical_source_id_sha256"], "Wrong source-ID population")
    for name in PRODUCTS:
        require(sha(product / name) == manifest["artifact_sha256"][name],
                f"Saved policy artifact changed: {name}")
    nodes = pq.read_table(subset / "neurons.parquet").to_pylist()
    edges = pq.read_table(subset / "connections.parquet").to_pylist()
    neuron_policy = pq.read_table(product / "neuron_policy.parquet").to_pylist()
    connection_policy = pq.read_table(product / "connection_policy.parquet").to_pylist()
    boundary = json.loads((product / "boundary_policy.json").read_text(encoding="utf-8"))
    require(len(nodes) == len(neuron_policy) == manifest["neurons"] and
            len(edges) == len(connection_policy) == manifest["source_pairs"],
            "Policy row counts differ from anatomy")
    node_by_id = {row["source_id"]: row for row in nodes}
    role_by_id = {body: role["name"] for role in selection["roles"] for body in role["source_ids"]}
    role_family = config["neuron_parameter_policy"]["role_families"]
    for anatomy, policy in zip(nodes, neuron_policy):
        body = anatomy["source_id"]
        family = role_family[role_by_id[body]]
        require(policy["source_id"] == body and policy["role"] == role_by_id[body]
                and policy["transmitter_consensus"] == anatomy["transmitter_consensus"]
                and policy["model_family"] == family
                and policy["model_kind"] == config["neuron_parameter_policy"]["families"][family]["model_kind"],
                f"Neuron class/transmitter/model mismatch: {body}")
        require(policy["numeric_parameters_state"] == "UNKNOWN"
                and policy["numeric_parameters_json"] is None,
                f"Unjustified numeric neuron parameters: {body}")
        if family == "APL":
            require("GRADED_LOCAL_NON_SPIKING" in policy["model_kind"],
                    "APL was converted to a spiking LIF cell")
    rule_by_pair = {(r["pre_role"], r["post_role"]): r for r in config["connection_rules"]}
    states = Counter()
    contacts = Counter()
    for anatomy, policy in zip(edges, connection_policy):
        pre, post = anatomy["pre_source_id"], anatomy["post_source_id"]
        pre_role, post_role = role_by_id[pre], role_by_id[post]
        rule = rule_by_pair.get((pre_role, post_role))
        expected_effect = "UNKNOWN" if rule is None else rule["effect_state"]
        expected_evidence = "UNKNOWN" if rule is None else rule["evidence"]
        require(all(policy[field] == anatomy[field] for field in
                    ("source_row", "pre_source_id", "post_source_id", "synapse_count")),
                f"Policy has a missing, invented or reordered source pair: {anatomy['source_row']}")
        require((policy["pre_role"], policy["post_role"], policy["effect_state"],
                 policy["effect_evidence"]) ==
                (pre_role, post_role, expected_effect, expected_evidence),
                f"Unexpected effect classification: {anatomy['source_row']}")
        require(policy["pre_transmitter_consensus"] == node_by_id[pre]["transmitter_consensus"]
                and policy["post_receptor_type_annotation"] ==
                node_by_id[post]["receptor_type_annotation"],
                f"Lost transmitter/receptor metadata: {anatomy['source_row']}")
        if rule is not None:
            require(policy["effect_rule"] == rule["name"]
                    and node_by_id[pre]["transmitter_consensus"] == rule["pre_transmitter"],
                    f"Rule/transmitter mismatch: {anatomy['source_row']}")
        else:
            require(policy["effect_rule"] == "default_unknown",
                    f"Unmatched pair received a guessed sign: {anatomy['source_row']}")
        require(policy["weight_mv"] is None and policy["delay_us"] is None
                and policy["delay_state"] == "UNKNOWN",
                f"Unjustified weight/delay: {anatomy['source_row']}")
        states[expected_effect] += 1
        contacts[expected_effect] += anatomy["synapse_count"]
    require(dict(sorted(states.items())) == manifest["effect_pairs"] and
            dict(sorted(contacts.items())) == manifest["effect_contacts"],
            "Manifest effect totals differ from full row audit")
    require(len(boundary) == len(selection["boundary_by_role"]), "Missing boundary roles")
    for saved, parent in zip(boundary, selection["boundary_by_role"]):
        require(all(saved[key] == value for key, value in parent.items()),
                f"Boundary cuts differ for role {parent['role']}")
        require(saved["missing_neural_drive_state"] == "UNKNOWN"
                and saved["missing_neural_drive_mv"] is None
                and saved["interface_amplitude_mv"] is None
                and saved["interface_latency_us"] is None,
                f"Boundary {parent['role']} silently received drive")
    require(manifest["runtime_ready"] is False and bool(manifest["runtime_blockers"])
            and manifest["simulated"] is False and manifest["trained"] is False,
            "Unresolved product was marked executable or trained")
    return {"status": "passed", "source_neurons": len(nodes),
            "source_pairs_exactly_classified": len(edges),
            "unknown_effect_pairs": states["UNKNOWN"],
            "unknown_effect_contacts": contacts["UNKNOWN"],
            "numeric_weights": 0, "numeric_delays": 0,
            "boundary_roles_verified": len(boundary),
            "runtime_ready": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subset", type=Path,
                        default=ROOT / "data/processed/malecns_v1_circuit_v1")
    parser.add_argument("--policy", type=Path,
                        default=ROOT / "configs/circuit_v1_effect_policies.json")
    parser.add_argument("--product", type=Path,
                        default=ROOT / "data/processed/malecns_v1_circuit_v1_policy_v1")
    args = parser.parse_args()
    result = audit(args.subset, args.policy, args.product)
    (args.product / "audit.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                                              encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
