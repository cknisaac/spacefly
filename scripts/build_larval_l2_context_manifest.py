"""Extend the frozen L2 anatomy with measured noci-2nd-order-PN→Ipsigoro edges."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "data/raw/larval_l1em/supplementary_data_s1.zip"
PARENT = ROOT / "configs/larval_l2_subgraph_manifest_v1.json"
OUTPUT = ROOT / "configs/larval_l2_context_subgraph_manifest_v1.json"
PARENT_SHA256 = "84fb7af5160a405a072170466ea19e134cd12bc61ed1a7c565f301972da07c89"
EXPECTED_EDGES = {
    (11_361_875, 3_979_181): 4,
    (14_493_841, 5_794_678): 7,
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if sha256(PARENT) != PARENT_SHA256:
        raise RuntimeError("parent L2 manifest hash mismatch")
    manifest = json.loads(PARENT.read_text(encoding="utf-8"))
    with zipfile.ZipFile(ARCHIVE) as archive:
        annotations = {}
        rows = csv.DictReader(io.TextIOWrapper(
            archive.open("Supplementary-Data-S1/annotations.csv"),
            encoding="utf-8-sig", newline=""))
        for row in rows:
            for side, key in (("L", "left_id"), ("R", "right_id")):
                if row[key] != "no pair":
                    annotations[int(row[key])] = {
                        "hemisphere": side,
                        "celltype": row["celltype"],
                        "additional_annotations": row["additional_annotations"],
                        "level_7_cluster": row["level_7_cluster"],
                    }
        matrix = csv.reader(io.TextIOWrapper(
            archive.open("Supplementary-Data-S1/ad_connectivity_matrix.csv"),
            encoding="utf-8-sig", newline=""))
        header = next(matrix)
        columns = {int(value): i for i, value in enumerate(header[1:], start=1)}
        actual = {}
        for row in matrix:
            pre = int(row[0])
            if pre not in {11_361_875, 14_493_841}:
                continue
            for post in (3_979_181, 5_794_678):
                count = int(float(row[columns[post]]))
                if count:
                    actual[(pre, post)] = count
    if actual != EXPECTED_EDGES:
        raise RuntimeError(f"unexpected context edges: {actual}")

    existing = {int(node["source_id"]) for node in manifest["nodes"]}
    for neuron_id in (11_361_875, 14_493_841):
        ann = annotations[neuron_id]
        if "noci 2nd_order PN" not in ann["additional_annotations"]:
            raise RuntimeError(f"source annotation missing nociceptive identity: {neuron_id}")
        if neuron_id in existing:
            raise RuntimeError(f"context source already in parent manifest: {neuron_id}")
        manifest["nodes"].append({
            "source_id": neuron_id,
            "role": "Noci-2nd-order-PN",
            "celltype": ann["celltype"],
            "source_annotation": ann["additional_annotations"],
            "hemisphere": ann["hemisphere"],
            "level_7_cluster": ann["level_7_cluster"],
            "catmaid_neuron_name": None,
            "transmitter": "UNKNOWN",
            "physiological_output_sign": "UNKNOWN",
            "evidence_provenance": "Winding et al. (2023) Supplementary Data S1 annotations.csv",
        })
    for (pre, post), contacts in sorted(actual.items()):
        manifest["edges"].append({
            "pre_id": pre,
            "post_id": post,
            "contacts": contacts,
            "direction": "Noci-2nd-order-PN_to_Ipsigoro",
            "connection_class": "axon_to_dendrite",
            "anatomical_status": "MEASURED",
            "candidate_plasticity_mask": "fixed context input",
            "synaptic_sign": "UNKNOWN",
            "source": "Supplementary-Data-S1/ad_connectivity_matrix.csv",
        })
    manifest["manifest_id"] = "larval_l2_dan-d1_mbon-d1_nociceptive-context_v1"
    manifest["candidate_status"] = "anatomy extension for fixed context input; no electrical effect inferred"
    manifest["parent_manifest"] = {
        "path": str(PARENT.relative_to(ROOT)),
        "sha256": PARENT_SHA256,
    }
    manifest["source_inputs"][str(ARCHIVE.relative_to(ROOT))] = sha256(ARCHIVE).upper()
    manifest["limits"].append(
        "Noci-2nd-order-PN→Ipsigoro edges are measured first-instar anatomy; functional experiments support a net nociceptive effect at Ipsigoro but do not measure these exact unitary edges or a simulator gain."
    )
    OUTPUT.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(OUTPUT),
        "nodes": len(manifest["nodes"]),
        "edges": len(manifest["edges"]),
        "added_edges": [{"pre_id": pre, "post_id": post, "contacts": count}
                        for (pre, post), count in sorted(actual.items())],
        "sha256": sha256(OUTPUT),
    }, indent=2))


if __name__ == "__main__":
    main()
