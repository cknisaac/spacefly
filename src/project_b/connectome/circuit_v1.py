"""Exact, data-only MaleCNS Circuit V1 selection.

Role selectors are pinned in configs/circuit_v1_selection.json. This module
copies the complete induced source graph; it assigns no electrical effects,
delays, dopamine dynamics, or trainable weights.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq


SELECTOR_VERSION = 1
PARENT_FILES = ("neurons.parquet", "connections.parquet")
OUTPUT_FILES = ("neurons.parquet", "connections.parquet", "plastic_candidates.parquet")
MATCH_FIELDS = {"source_id", "status", "superclass", "cell_class", "cell_subclass",
                "cell_type", "instance", "soma_side", "root_side"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_id_hash(ids: np.ndarray) -> str:
    """Hash ascending source IDs as little-endian signed 64-bit integers."""
    return hashlib.sha256(np.sort(ids).astype("<i8").tobytes()).hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def verify_parent(source: Path, selection: dict) -> dict[str, str]:
    receipt_path = source / "validation_receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    _require(receipt.get("dataset") == selection.get("dataset") == "MaleCNS"
             and receipt.get("release") == selection.get("release") == "v1.0",
             "Circuit V1 requires the validated MaleCNS v1.0 parent")
    _require(selection.get("scope") == "official traced-only",
             "Circuit V1 requires the official traced-only scope")
    hashes = {}
    for name in PARENT_FILES:
        actual = sha256_file(source / name)
        _require(actual == receipt["files"][name]["sha256"],
                 f"Parent file differs from validation receipt: {name}")
        _require(actual == selection["parent_sha256"][name],
                 f"Parent file differs from pinned selection: {name}")
        hashes[name] = actual
    return hashes


def select_roles(nodes: pa.Table, selection: dict) -> tuple[np.ndarray, np.ndarray, list[dict]]:
    """Select annotated biological roles, rejecting missing or drifted members."""
    _require(selection.get("schema_version") == 1, "Unknown selection schema version")
    ids = nodes["source_id"].to_numpy()
    runtime = nodes["runtime_index"].to_numpy()
    _require(np.array_equal(runtime, np.arange(len(nodes))),
             "Parent runtime indices must be contiguous and row aligned")
    _require(len(np.unique(ids)) == len(ids), "Parent source IDs are not unique")
    _require(len(selection.get("roles", [])) > 0, "Selection contains no roles")
    node_rows = nodes.to_pylist()
    role_index = np.full(len(nodes), -1, dtype=np.int16)
    roles: list[dict] = []
    names: set[str] = set()
    for role_no, spec in enumerate(selection["roles"]):
        name = spec["name"]
        _require(name not in names, f"Duplicate role name: {name}")
        names.add(name)
        match = spec["match"]
        _require(bool(match) and set(match) <= MATCH_FIELDS,
                 f"Unsupported or empty role match: {name}")
        _require(bool(spec.get("reason")), f"Missing biological rationale: {name}")
        found = [i for i, row in enumerate(node_rows)
                 if all(row[key] == value for key, value in match.items())]
        _require(len(found) == spec["expected_count"],
                 f"Role {name}: expected {spec['expected_count']} annotated bodies, found {len(found)}")
        found_indices = np.asarray(found, dtype=np.int64)
        _require(bool(np.all(role_index[found_indices] == -1)),
                 f"Role {name} overlaps another selected role")
        _require(all(node_rows[i]["status"] == "Traced" for i in found),
                 f"Role {name} includes a non-Traced body")
        role_ids = ids[found_indices]
        if "source_id_sha256" in spec:
            _require(source_id_hash(role_ids) == spec["source_id_sha256"],
                     f"Role {name} source-ID membership drifted")
        role_index[found_indices] = role_no
        roles.append({"name": name, "reason": spec["reason"],
                      "match": match, "source_ids": sorted(map(int, role_ids))})
    selected_indices = np.flatnonzero(role_index >= 0)
    _require(source_id_hash(ids[selected_indices]) == selection["selected_source_id_sha256"],
             "Overall Circuit V1 source-ID membership drifted")
    return selected_indices, role_index, roles


def _boundary_by_role(role_index: np.ndarray, pre: np.ndarray, post: np.ndarray,
                      count: np.ndarray, inside: np.ndarray,
                      incoming: np.ndarray, outgoing: np.ndarray,
                      roles: list[dict]) -> list[dict]:
    role_count = len(roles)

    def pairs_and_contacts(targets: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        indices = role_index[targets[mask]]
        return (np.bincount(indices, minlength=role_count),
                np.bincount(indices, weights=count[mask], minlength=role_count))

    incoming_pairs, incoming_contacts = pairs_and_contacts(post, incoming)
    retained_pairs, retained_contacts = pairs_and_contacts(post, inside)
    outgoing_pairs, outgoing_contacts = pairs_and_contacts(pre, outgoing)
    return [{"role": role["name"],
             "incoming_cut_pairs": int(incoming_pairs[i]),
             "incoming_cut_contacts": int(incoming_contacts[i]),
             "retained_incoming_pairs": int(retained_pairs[i]),
             "retained_incoming_contacts": int(retained_contacts[i]),
             "outgoing_cut_pairs": int(outgoing_pairs[i]),
             "outgoing_cut_contacts": int(outgoing_contacts[i])}
            for i, role in enumerate(roles)]


def build_circuit_v1(source: Path, selection_path: Path, output: Path) -> dict:
    """Materialize exact neurons, all induced edges, candidate plastic rows and manifest."""
    source, selection_path, output = Path(source), Path(selection_path), Path(output)
    _require(source.resolve() != output.resolve(), "Output may not overwrite the parent")
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    parent_hashes = verify_parent(source, selection)
    nodes = pq.read_table(source / "neurons.parquet")
    selected_indices, role_index, roles = select_roles(nodes, selection)
    ids = nodes["source_id"].to_numpy()
    selected = role_index >= 0
    local_index = np.full(len(nodes), -1, dtype=np.int32)
    local_index[selected_indices] = np.arange(len(selected_indices), dtype=np.int32)

    parent_edges = pq.read_table(source / "connections.parquet")
    pre = parent_edges["pre_index"].to_numpy()
    post = parent_edges["post_index"].to_numpy()
    count = parent_edges["synapse_count"].to_numpy()
    _require(bool(np.all(pre < len(nodes)) and np.all(post < len(nodes))),
             "Parent edge endpoint exceeds neuron table")
    _require(bool(np.all(count > 0)), "Parent contains nonpositive contact count")
    inside = selected[pre] & selected[post]
    incoming = ~selected[pre] & selected[post]
    outgoing = selected[pre] & ~selected[post]
    inside_indices = np.flatnonzero(inside)

    out_nodes = nodes.take(pa.array(selected_indices))
    out_nodes = out_nodes.append_column("local_index",
                                        pa.array(np.arange(len(selected_indices), dtype=np.uint32)))
    out_edges = parent_edges.take(pa.array(inside_indices))
    out_edges = out_edges.append_column("pre_source_id", pa.array(ids[pre[inside_indices]]))
    out_edges = out_edges.append_column("post_source_id", pa.array(ids[post[inside_indices]]))
    out_edges = out_edges.append_column("pre_local_index", pa.array(local_index[pre[inside_indices]]))
    out_edges = out_edges.append_column("post_local_index", pa.array(local_index[post[inside_indices]]))

    role_lookup = {role["name"]: i for i, role in enumerate(roles)}
    plastic_rows: list[np.ndarray] = []
    plastic_compartments: list[str] = []
    plastic_teaching_roles: list[str] = []
    for rule in selection["plastic_candidates"]:
        pre_role, post_role, teaching = (rule["pre_role"], rule["post_role"], rule["teaching_role"])
        _require(all(name in role_lookup for name in (pre_role, post_role, teaching)),
                 "Plastic rule refers to an absent biological role")
        _require(bool(rule["compartment_candidate"]), "Plastic rule lacks a compartment label")
        positions = np.flatnonzero(inside & (role_index[pre] == role_lookup[pre_role])
                                    & (role_index[post] == role_lookup[post_role]))
        _require(len(positions) > 0, "Plastic rule has no source connections")
        plastic_rows.append(positions)
        plastic_compartments.extend([rule["compartment_candidate"]] * len(positions))
        plastic_teaching_roles.extend([teaching] * len(positions))
    plastic_indices = np.concatenate(plastic_rows) if plastic_rows else np.empty(0, dtype=np.int64)
    _require(len(np.unique(plastic_indices)) == len(plastic_indices),
             "Plastic candidate rules overlap")
    order = np.argsort(plastic_indices)
    plastic_indices = plastic_indices[order]
    plastic_compartments = [plastic_compartments[i] for i in order]
    plastic_teaching_roles = [plastic_teaching_roles[i] for i in order]
    out_plastic = pa.table({
        "source_row": pa.array(parent_edges["source_row"].to_numpy()[plastic_indices]),
        "pre_source_id": pa.array(ids[pre[plastic_indices]]),
        "post_source_id": pa.array(ids[post[plastic_indices]]),
        "pre_local_index": pa.array(local_index[pre[plastic_indices]]),
        "post_local_index": pa.array(local_index[post[plastic_indices]]),
        "synapse_count": pa.array(count[plastic_indices]),
        "compartment_candidate": pa.array(plastic_compartments, type=pa.string()),
        "teaching_role": pa.array(plastic_teaching_roles, type=pa.string()),
        "status": pa.array(["candidate_pending_synapse_location"] * len(plastic_indices)),
    })
    boundaries = _boundary_by_role(role_index, pre, post, count, inside,
                                   incoming, outgoing, roles)

    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "manifest.json"
    if manifest_path.exists():
        manifest_path.unlink()  # A failed rebuild must not retain a stale valid manifest.
    pq.write_table(out_nodes, output / "neurons.parquet", compression="zstd")
    pq.write_table(out_edges, output / "connections.parquet", compression="zstd")
    pq.write_table(out_plastic, output / "plastic_candidates.parquet", compression="zstd")
    manifest = {
        "dataset": "MaleCNS", "release": "v1.0", "scope": "official traced-only",
        "selector_version": SELECTOR_VERSION,
        "selection_file": selection_path.name,
        "selection_sha256": sha256_file(selection_path),
        "validation_receipt_sha256": sha256_file(source / "validation_receipt.json"),
        "parent_sha256": parent_hashes,
        "source_id_sha256": source_id_hash(ids[selected_indices]),
        "selection_basis": "biological roles and annotations; no edge-strength ranking",
        "roles": roles,
        "neurons": len(selected_indices),
        "directed_pairs": len(inside_indices),
        "internal_contacts": int(count[inside].sum(dtype=np.int64)),
        "plastic_candidate_pairs": len(plastic_indices),
        "plastic_candidate_contacts": int(count[plastic_indices].sum(dtype=np.int64)),
        "plastic_mask_status": "candidate only; synapse locations and compartment overlap unverified",
        "boundary_scope": "official traced-only parent; untraced fragments excluded",
        "incoming_cut_pairs": int(incoming.sum()),
        "incoming_cut_contacts": int(count[incoming].sum(dtype=np.int64)),
        "outgoing_cut_pairs": int(outgoing.sum()),
        "outgoing_cut_contacts": int(count[outgoing].sum(dtype=np.int64)),
        "boundary_by_role": boundaries,
        "artifact_sha256": {name: sha256_file(output / name) for name in OUTPUT_FILES},
        "electrical_effects": None,
        "dynamics": None,
        "training": None,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                             encoding="utf-8")
    return manifest
