"""Independent parent-to-output audit of the MaleCNS Circuit V1 subset."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
PRODUCTS = ("neurons.parquet", "connections.parquet", "plastic_candidates.parquet")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def audit(source: Path, selection_path: Path, output: Path) -> dict:
    source, selection_path, output = Path(source), Path(selection_path), Path(output)
    config = json.loads(selection_path.read_text(encoding="utf-8"))
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    receipt = json.loads((source / "validation_receipt.json").read_text(encoding="utf-8"))
    require((manifest["dataset"], manifest["release"], manifest["scope"]) ==
            ("MaleCNS", "v1.0", "official traced-only"), "Wrong output source identity")
    require(sha(selection_path) == manifest["selection_sha256"], "Selection file changed")
    require(sha(source / "validation_receipt.json") == manifest["validation_receipt_sha256"],
            "Parent validation receipt changed")
    for filename in ("neurons.parquet", "connections.parquet"):
        digest = sha(source / filename)
        require(digest == manifest["parent_sha256"][filename] ==
                receipt["files"][filename]["sha256"] == config["parent_sha256"][filename],
                f"Parent checksum mismatch: {filename}")
    for filename in PRODUCTS:
        require(sha(output / filename) == manifest["artifact_sha256"][filename],
                f"Output checksum mismatch: {filename}")

    parent_nodes = pq.read_table(source / "neurons.parquet")
    out_nodes = pq.read_table(output / "neurons.parquet")
    parent_ids = parent_nodes["source_id"].to_numpy()
    parent_runtime = out_nodes["runtime_index"].to_numpy()
    local = out_nodes["local_index"].to_numpy()
    ids = out_nodes["source_id"].to_numpy()
    require(np.array_equal(local, np.arange(len(ids))), "Local node index is not contiguous")
    require(np.array_equal(ids, np.sort(ids)), "Selected IDs are not ascending")
    require(np.array_equal(ids, parent_ids[parent_runtime]), "Source body ID mismatch")
    require(out_nodes.drop(["local_index"]).equals(parent_nodes.take(pa.array(parent_runtime))),
            "Node annotations or transmitter metadata differ from parent")
    id_hash = hashlib.sha256(np.asarray(ids, dtype="<i8").tobytes()).hexdigest()
    require(id_hash == config["selected_source_id_sha256"] == manifest["source_id_sha256"],
            "Selected ID set differs from the design")
    require(len(ids) == manifest["neurons"], "Node count mismatch")

    # Independently reconstruct every role from the complete annotation table.
    parent_rows = parent_nodes.to_pylist()
    selected_set = set(map(int, ids))
    role_ids: dict[str, set[int]] = {}
    role_of_id: dict[int, str] = {}
    for spec in config["roles"]:
        name = spec["name"]
        found = {int(row["source_id"]) for row in parent_rows
                 if all(row[key] == value for key, value in spec["match"].items())}
        require(len(found) == spec["expected_count"], f"Role membership count drifted: {name}")
        if "source_id_sha256" in spec:
            encoded = np.asarray(sorted(found), dtype="<i8").tobytes()
            require(hashlib.sha256(encoded).hexdigest() == spec["source_id_sha256"],
                    f"Role source IDs drifted: {name}")
        require(all(parent_rows[int(np.searchsorted(parent_ids, body))]["status"] == "Traced"
                    for body in found), f"Non-Traced body in role: {name}")
        require(not (set(role_of_id) & found), f"Roles overlap: {name}")
        require(next(role for role in manifest["roles"] if role["name"] == name)["source_ids"] ==
                sorted(found), f"Manifest role IDs differ: {name}")
        role_ids[name] = found
        role_of_id.update({body: name for body in found})
    require(set(role_of_id) == selected_set, "Selected nodes differ from the role union")

    parent_edges = pq.read_table(source / "connections.parquet")
    out_edges = pq.read_table(output / "connections.parquet")
    pre = parent_edges["pre_index"].to_numpy()
    post = parent_edges["post_index"].to_numpy()
    count = parent_edges["synapse_count"].to_numpy()
    selected = np.zeros(len(parent_ids), dtype=np.bool_)
    selected[parent_runtime] = True
    internal = selected[pre] & selected[post]
    inbound = ~selected[pre] & selected[post]
    outbound = selected[pre] & ~selected[post]
    internal_rows = np.flatnonzero(internal)
    original_columns = parent_edges.column_names
    require(out_edges.select(original_columns).equals(parent_edges.take(pa.array(internal_rows))),
            "Internal edge set/order, source rows, endpoints or counts differ from parent")
    require(np.array_equal(out_edges["pre_source_id"].to_numpy(), parent_ids[pre[internal_rows]])
            and np.array_equal(out_edges["post_source_id"].to_numpy(), parent_ids[post[internal_rows]]),
            "Stored edge source endpoints differ from parent")
    expected_local = np.full(len(parent_ids), -1, dtype=np.int32)
    expected_local[parent_runtime] = np.arange(len(ids), dtype=np.int32)
    require(np.array_equal(out_edges["pre_local_index"].to_numpy(), expected_local[pre[internal_rows]])
            and np.array_equal(out_edges["post_local_index"].to_numpy(), expected_local[post[internal_rows]]),
            "Stored edge local endpoints differ from parent")
    require(len(out_edges) == manifest["directed_pairs"]
            and int(count[internal].sum(dtype=np.int64)) == manifest["internal_contacts"],
            "Internal edge totals differ")

    # Audit each plastic candidate from the independent parent/role construction.
    expected_plastic = {}
    for rule in config["plastic_candidates"]:
        for index in internal_rows:
            if (int(parent_ids[pre[index]]) in role_ids[rule["pre_role"]]
                    and int(parent_ids[post[index]]) in role_ids[rule["post_role"]]):
                require(int(index) not in expected_plastic, "Plastic rules overlap")
                expected_plastic[int(index)] = (rule["compartment_candidate"], rule["teaching_role"])
    plastic = pq.read_table(output / "plastic_candidates.parquet").to_pylist()
    require(len(plastic) == len(expected_plastic) == manifest["plastic_candidate_pairs"],
            "Plastic candidate set size differs")
    for saved, index in zip(plastic, sorted(expected_plastic)):
        compartment, teaching = expected_plastic[index]
        require(saved == {
            "source_row": int(parent_edges["source_row"][index].as_py()),
            "pre_source_id": int(parent_ids[pre[index]]),
            "post_source_id": int(parent_ids[post[index]]),
            "pre_local_index": int(expected_local[pre[index]]),
            "post_local_index": int(expected_local[post[index]]),
            "synapse_count": int(count[index]),
            "compartment_candidate": compartment,
            "teaching_role": teaching,
            "status": "candidate_pending_synapse_location",
        }, f"Plastic candidate differs at parent row {index}")
    require(sum(row["synapse_count"] for row in plastic) ==
            manifest["plastic_candidate_contacts"], "Plastic contact total differs")

    require((int(inbound.sum()), int(count[inbound].sum(dtype=np.int64)),
             int(outbound.sum()), int(count[outbound].sum(dtype=np.int64))) ==
            (manifest["incoming_cut_pairs"], manifest["incoming_cut_contacts"],
             manifest["outgoing_cut_pairs"], manifest["outgoing_cut_contacts"]),
            "Boundary totals differ")
    boundary = defaultdict(lambda: defaultdict(int))
    for label, rows, selected_endpoint in (("incoming_cut", np.flatnonzero(inbound), post),
                                            ("outgoing_cut", np.flatnonzero(outbound), pre),
                                            ("retained_incoming", internal_rows, post)):
        for index in rows:
            role = role_of_id[int(parent_ids[selected_endpoint[index]])]
            boundary[role][f"{label}_pairs"] += 1
            boundary[role][f"{label}_contacts"] += int(count[index])
    for entry in manifest["boundary_by_role"]:
        name = entry["role"]
        for field, value in entry.items():
            if field != "role":
                require(boundary[name][field] == value,
                        f"Boundary role mismatch: {name}/{field}")

    return {"status": "passed", "source_ids": len(ids),
            "exact_source_edges": len(out_edges),
            "plastic_candidates": len(plastic),
            "incoming_cut_pairs": int(inbound.sum()),
            "outgoing_cut_pairs": int(outbound.sum()),
            "metadata_equal_to_parent": True,
            "boundary_by_role_verified": True,
            "artifact_sha256": manifest["artifact_sha256"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path,
                        default=ROOT / "data/processed/malecns_v1_traced")
    parser.add_argument("--selection", type=Path,
                        default=ROOT / "configs/circuit_v1_selection.json")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "data/processed/malecns_v1_circuit_v1")
    args = parser.parse_args()
    result = audit(args.source, args.selection, args.output)
    (args.output / "audit.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                                           encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
