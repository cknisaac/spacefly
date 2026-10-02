"""Evidence-labelled Circuit V1 electrical-policy resolution, without simulation.

The anatomical connectome is immutable. An effect of UNKNOWN never acquires a
positive weight from transmitter identity, contact count, or a default.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


EVIDENCE = {"LITERATURE-CONSTRAINED", "INFERRED", "ENGINEERING ASSUMPTION", "UNKNOWN"}
NUMERIC_EVIDENCE = EVIDENCE - {"UNKNOWN"}
EFFECTS = {"EXCITATORY", "INHIBITORY", "MODULATORY", "UNKNOWN"}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _number(spec: dict | None, label: str, *, integer: bool = False) -> int | float | None:
    """Require provenance for any future numerical model parameter."""
    if spec is None:
        return None
    _require(isinstance(spec, dict), f"{label}: numeric parameter needs a provenance object")
    _require(spec.get("evidence") in NUMERIC_EVIDENCE and bool(spec.get("source")),
             f"{label}: numeric parameter lacks literature/inference/engineering provenance")
    value = spec.get("value")
    _require(type(value) in (int, float) and math.isfinite(value),
             f"{label}: numeric value must be finite")
    if integer:
        _require(type(value) is int and value > 0, f"{label}: expected a positive integer")
    return value


class ConnectionEffectPolicy:
    """Resolve target-specific class evidence; missing rules stay UNKNOWN."""

    def __init__(self, config: dict):
        self.default = config["connection_default"]
        _require(self.default["effect_state"] == "UNKNOWN"
                 and self.default["evidence"] == "UNKNOWN"
                 and self.default["weight_mv"] is None,
                 "Connection default must be an unweighted UNKNOWN")
        self.rules: dict[tuple[str, str], dict] = {}
        for rule in config["connection_rules"]:
            key = (rule["pre_role"], rule["post_role"])
            _require(key not in self.rules, f"Overlapping connection rules: {key}")
            state = rule["effect_state"]
            _require(state in EFFECTS - {"UNKNOWN"}, f"Invalid explicit effect: {key}")
            _require(rule["evidence"] in EVIDENCE - {"UNKNOWN"}
                     and bool(rule.get("source")) and bool(rule.get("scope_limit")),
                     f"Connection rule lacks evidence or scope: {key}")
            value = _number(rule.get("weight_mv"), f"{key} weight_mv")
            if state in {"MODULATORY", "UNKNOWN"}:
                _require(value is None, f"{key}: modulatory/unknown effect cannot be fast current")
            elif value is not None:
                _require((value > 0) == (state == "EXCITATORY") and value != 0,
                         f"{key}: weight sign conflicts with declared effect")
            _require(bool(rule.get("pre_transmitter")), f"Rule lacks transmitter guard: {key}")
            self.rules[key] = rule

    def resolve(self, edge: dict, pre_role: str, post_role: str,
                pre_transmitter: str | None) -> dict:
        rule = self.rules.get((pre_role, post_role))
        if rule is None:
            return {"effect_state": "UNKNOWN", "effect_evidence": "UNKNOWN",
                    "effect_rule": "default_unknown", "effect_source": None,
                    "effect_scope_limit": self.default["reason"],
                    "weight_mv": None, "weight_provenance": None}
        _require(pre_transmitter == rule["pre_transmitter"],
                 f"Transmitter annotation conflicts with effect rule {rule['name']}"
                 f" at source row {edge['source_row']}")
        numeric = rule.get("weight_mv")
        return {"effect_state": rule["effect_state"],
                "effect_evidence": rule["evidence"],
                "effect_rule": rule["name"],
                "effect_source": rule["source"],
                "effect_scope_limit": rule["scope_limit"],
                "weight_mv": None if numeric is None else numeric["value"],
                "weight_provenance": None if numeric is None else json.dumps(numeric, sort_keys=True)}


class NeuronParameterPolicy:
    """Assign a model family per biological role; numeric parameters may remain unknown."""

    def __init__(self, config: dict, valid_roles: set[str]):
        policy = config["neuron_parameter_policy"]
        self.families = policy["families"]
        self.roles = policy["role_families"]
        self.parameters = policy["numeric_parameters"]
        _require(set(self.roles) == valid_roles, "Neuron policy does not cover every selected role")
        _require(set(self.parameters) == set(self.families),
                 "Neuron numeric-parameter families differ from model families")
        for name, family in self.families.items():
            _require(family["evidence"] in EVIDENCE - {"UNKNOWN"} and bool(family["source"]),
                     f"Neuron family lacks evidence: {name}")
            values = self.parameters[name]
            if values is not None:
                _require(isinstance(values, dict) and bool(values),
                         f"Neuron family parameters must be a nonempty mapping: {name}")
                for key, spec in values.items():
                    _require(spec is not None, f"{name}.{key}: unresolved value must not appear in a numeric mapping")
                    _number(spec, f"{name}.{key}", integer=key.endswith("_us"))
        _require(all(name in self.families for name in self.roles.values()),
                 "Neuron role uses an undefined family")

    def resolve(self, source_id: int, role: str, transmitter: str | None) -> dict:
        family_name = self.roles[role]
        family = self.families[family_name]
        values = self.parameters[family_name]
        return {"source_id": source_id, "role": role,
                "transmitter_consensus": transmitter,
                "model_family": family_name,
                "model_kind": family["model_kind"],
                "model_evidence": family["evidence"],
                "model_source": family["source"],
                "model_reason": family["reason"],
                "numeric_parameters_json": None if values is None else json.dumps(values, sort_keys=True),
                "numeric_parameters_state": "UNKNOWN" if values is None else "PROVENANCE_DECLARED"}


class DelayPolicy:
    """Keep biological arrival/release timing unresolved until evidence is supplied."""

    def __init__(self, config: dict, families: set[str]):
        policy = config["delay_policy"]
        self.default = policy["default"]
        self.kinds = policy["by_presynaptic_family"]
        _require(set(self.kinds) == families, "Delay policy does not cover each model family")
        _require(self.default["delay_state"] == "UNKNOWN"
                 and self.default["delay_us"] is None
                 and self.default["evidence"] == "UNKNOWN",
                 "Delay default must remain UNKNOWN with no numeric delay")
        for family, rule in self.kinds.items():
            _require(bool(rule.get("kind")), f"Delay kind missing for {family}")
            state = rule["delay_state"]
            _require(state in {"UNKNOWN", "DECLARED"}, f"Invalid delay state for {family}")
            value = _number(rule.get("delay_us"), f"{family}.delay_us", integer=True)
            _require((state == "UNKNOWN" and value is None and rule["evidence"] == "UNKNOWN")
                     or (state == "DECLARED" and value is not None
                         and rule["evidence"] in NUMERIC_EVIDENCE),
                     f"Delay state/value/provenance mismatch for {family}")

    def resolve(self, pre_family: str) -> dict:
        rule = self.kinds[pre_family]
        numeric = rule["delay_us"]
        return {"delay_kind": rule["kind"],
                "delay_state": rule["delay_state"],
                "delay_us": None if numeric is None else numeric["value"],
                "delay_evidence": rule["evidence"],
                "delay_provenance": None if numeric is None else json.dumps(numeric, sort_keys=True),
                "delay_reason": self.default["reason"] if numeric is None else numeric["source"]}


class BoundaryInputPolicy:
    """Expose cut drive and task interfaces as unresolved external boundaries."""

    def __init__(self, config: dict, roles: set[str]):
        self.policy = config["boundary_input_policy"]
        _require(self.policy["missing_neural_drive_state"] == "UNKNOWN"
                 and self.policy["missing_neural_drive_mv"] is None
                 and self.policy["missing_neural_drive_evidence"] == "UNKNOWN",
                 "Omitted-neuron drive must remain UNKNOWN")
        _require(self.policy["interface_evidence"] == "ENGINEERING ASSUMPTION"
                 and bool(self.policy["reason"]),
                 "Task interface must be an explicit engineering assumption")
        self.amplitude = _number(self.policy.get("interface_amplitude_mv"), "interface_amplitude_mv")
        self.latency = _number(self.policy.get("interface_latency_us"),
                               "interface_latency_us", integer=True)
        groups = [set(self.policy[key]) for key in ("input_roles", "teaching_roles", "action_roles")]
        _require(all(group <= roles for group in groups)
                 and sum(map(len, groups)) == len(set().union(*groups)),
                 "Boundary interface roles overlap or refer to missing roles")

    def resolve(self, entry: dict) -> dict:
        role = entry["role"]
        if role in self.policy["input_roles"]:
            interface = "ARTIFICIAL_VISUAL_INPUT_PENDING"
        elif role in self.policy["teaching_roles"]:
            interface = "ARTIFICIAL_TEACHING_INPUT_PENDING"
        elif role in self.policy["action_roles"]:
            interface = "ARTIFICIAL_ACTION_READOUT_PENDING"
        else:
            interface = "NONE_DECLARED"
        return {**entry, "missing_neural_drive_state": "UNKNOWN",
                "missing_neural_drive_mv": None,
                "interface_state": interface,
                "interface_evidence": self.policy["interface_evidence"] if interface != "NONE_DECLARED" else None,
                "interface_amplitude_mv": self.amplitude if interface != "NONE_DECLARED" else None,
                "interface_latency_us": self.latency if interface != "NONE_DECLARED" else None,
                "interface_amplitude_provenance": (None if self.amplitude is None or interface == "NONE_DECLARED"
                                                   else json.dumps(self.policy["interface_amplitude_mv"], sort_keys=True)),
                "interface_latency_provenance": (None if self.latency is None or interface == "NONE_DECLARED"
                                                 else json.dumps(self.policy["interface_latency_us"], sort_keys=True)),
                "boundary_reason": self.policy["reason"]}


def require_runtime_ready(neurons: pa.Table, edges: pa.Table, boundary: list[dict]) -> None:
    """Fail closed before anyone converts unresolved policy records to a spiking graph."""
    blockers = []
    states = Counter(edges["effect_state"].to_pylist())
    if states["UNKNOWN"]:
        blockers.append(f"{states['UNKNOWN']} UNKNOWN effects")
    if states["MODULATORY"]:
        blockers.append(f"{states['MODULATORY']} modulatory anatomical pairs need a separate model")
    if edges["weight_mv"].null_count:
        blockers.append("unresolved numerical edge effects")
    if edges["delay_us"].null_count:
        blockers.append("unresolved delays")
    if neurons["numeric_parameters_state"].to_pylist().count("UNKNOWN"):
        blockers.append("unresolved neuron parameters")
    if any(kind.endswith("_UNPARAMETERIZED") for kind in neurons["model_kind"].to_pylist()):
        blockers.append("cell-family dynamics are not implemented")
    if any(row["missing_neural_drive_state"] == "UNKNOWN" for row in boundary):
        blockers.append("unresolved cut-edge input")
    if any("GRADED" in kind or "DOPAMINERGIC" in kind or "EXTERNAL" in kind
           for kind in neurons["model_kind"].to_pylist()):
        blockers.append("non-LIF cell families need explicit runtime models")
    _require(not blockers, "Circuit policy is not runtime ready: " + "; ".join(blockers))


def build_policy_product(subset: Path, config_path: Path, output: Path) -> dict:
    subset, config_path, output = Path(subset), Path(config_path), Path(output)
    _require(subset.resolve() != output.resolve(), "Policy output may not overwrite anatomy")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    selection = json.loads((subset / "manifest.json").read_text(encoding="utf-8"))
    _require(config.get("schema_version") == 1 and config.get("dataset") == selection["dataset"] == "MaleCNS"
             and config.get("release") == selection["release"] == "v1.0",
             "Wrong Circuit V1 policy or anatomical source")
    _require(config["selection_source_id_sha256"] == selection["source_id_sha256"],
             "Policy targets a different anatomical selection")
    for name in ("neurons.parquet", "connections.parquet", "plastic_candidates.parquet"):
        _require(_sha(subset / name) == selection["artifact_sha256"][name],
                 f"Anatomical subset artifact differs from manifest: {name}")
    roles = {role["name"]: role for role in selection["roles"]}
    role_of_id = {body: name for name, role in roles.items() for body in role["source_ids"]}
    nodes = pq.read_table(subset / "neurons.parquet")
    source_edges = pq.read_table(subset / "connections.parquet")
    node_by_id = {row["source_id"]: row for row in nodes.to_pylist()}
    _require(set(node_by_id) == set(role_of_id), "Anatomical role inventory differs from neuron table")
    neuron_policy = NeuronParameterPolicy(config, set(roles))
    effects = ConnectionEffectPolicy(config)
    delays = DelayPolicy(config, set(neuron_policy.families))
    boundaries = BoundaryInputPolicy(config, set(roles))

    neuron_records = [neuron_policy.resolve(row["source_id"], role_of_id[row["source_id"]],
                                            row["transmitter_consensus"])
                      for row in nodes.to_pylist()]
    resolved_nodes = pa.Table.from_pylist(neuron_records)
    edge_records = []
    for edge in source_edges.to_pylist():
        pre_id, post_id = edge["pre_source_id"], edge["post_source_id"]
        pre_role, post_role = role_of_id[pre_id], role_of_id[post_id]
        transmitter = node_by_id[pre_id]["transmitter_consensus"]
        effect = effects.resolve(edge, pre_role, post_role, transmitter)
        delay = delays.resolve(neuron_policy.roles[pre_role])
        edge_records.append({"source_row": edge["source_row"],
                             "pre_source_id": pre_id, "post_source_id": post_id,
                             "synapse_count": edge["synapse_count"],
                             "pre_role": pre_role, "post_role": post_role,
                             "pre_transmitter_consensus": transmitter,
                             "post_receptor_type_annotation": node_by_id[post_id]["receptor_type_annotation"],
                             **effect, **delay})
    resolved_edges = pa.Table.from_pylist(edge_records)
    boundary_records = [boundaries.resolve(entry) for entry in selection["boundary_by_role"]]
    # The saved data product must remain incapable of silently becoming an all-positive graph.
    states = Counter(record["effect_state"] for record in edge_records)
    contact_states = Counter()
    for record in edge_records:
        contact_states[record["effect_state"]] += record["synapse_count"]
    _require(sum(states.values()) == selection["directed_pairs"],
             "Effect policy omitted anatomical edges")
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "manifest.json"
    if manifest_path.exists():
        manifest_path.unlink()
    pq.write_table(resolved_nodes, output / "neuron_policy.parquet", compression="zstd")
    pq.write_table(resolved_edges, output / "connection_policy.parquet", compression="zstd")
    (output / "boundary_policy.json").write_text(
        json.dumps(boundary_records, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    runtime_blockers = []
    try:
        require_runtime_ready(resolved_nodes, resolved_edges, boundary_records)
    except ValueError as error:
        runtime_blockers = str(error).split(": ", 1)[-1].split("; ")
    manifest = {"dataset": "MaleCNS", "release": "v1.0", "policy_schema_version": 1,
                "anatomical_subset_manifest_sha256": _sha(subset / "manifest.json"),
                "anatomical_source_id_sha256": selection["source_id_sha256"],
                "policy_config_sha256": _sha(config_path),
                "selection_basis": selection["selection_basis"],
                "neurons": len(neuron_records), "source_pairs": len(edge_records),
                "source_contacts": selection["internal_contacts"],
                "effect_pairs": dict(sorted(states.items())),
                "effect_contacts": dict(sorted(contact_states.items())),
                "unknown_effect_pair_fraction": states["UNKNOWN"] / len(edge_records),
                "unknown_effect_contact_fraction": contact_states["UNKNOWN"] / selection["internal_contacts"],
                "numeric_edge_weights_assigned": sum(record["weight_mv"] is not None for record in edge_records),
                "numeric_delays_assigned": sum(record["delay_us"] is not None for record in edge_records),
                "numeric_neuron_families_assigned": sum(value is not None for value in neuron_policy.parameters.values()),
                "runtime_ready": not runtime_blockers,
                "runtime_blockers": runtime_blockers,
                "artifact_sha256": {name: _sha(output / name) for name in
                                    ("neuron_policy.parquet", "connection_policy.parquet", "boundary_policy.json")},
                "simulated": False, "trained": False}
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                             encoding="utf-8")
    return manifest
