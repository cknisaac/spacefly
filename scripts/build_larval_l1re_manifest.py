"""Build the immutable anatomy manifest for the L1R-E engineering variant.

L1R-E preserves measured KC -> MBON-m1 anatomy while exposing teaching and
action only as non-anatomical engineering ports.  It deliberately contains no
DAN node or dopamine-labelled edge.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "data/raw/larval_l1em/supplementary_data_s1.zip"
ADMISSION = ROOT / "data/raw/larval_l1em/l1r_admission_audit.json"
OUTPUT = ROOT / "configs/larval_l1re_manifest_v1.json"
MBON_M1_IDS = {4_022_539, 17_016_974}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def read_annotations() -> dict[int, dict[str, str]]:
    with zipfile.ZipFile(ARCHIVE) as archive:
        raw = archive.open("Supplementary-Data-S1/annotations.csv")
        rows = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""))
        result: dict[int, dict[str, str]] = {}
        for row in rows:
            for side, field in (("L", "left_id"), ("R", "right_id")):
                if row[field] != "no pair":
                    result[int(row[field])] = {
                        "hemisphere": side,
                        "celltype": row["celltype"],
                        "additional_annotations": row["additional_annotations"],
                        "level_7_cluster": row["level_7_cluster"],
                    }
        return result


def main() -> None:
    admission = json.loads(ADMISSION.read_text(encoding="utf-8"))
    frozen = admission["frozen_source"]
    archive_hash = sha256(ARCHIVE)
    if archive_hash != frozen["sha256"]:
        raise RuntimeError(f"pinned archive hash mismatch: {archive_hash}")
    if admission["decision"] != "FAIL":
        raise RuntimeError("literal L1R admission result changed unexpectedly")

    anatomy = admission["anatomy"]["KC_to_MBON-m1"]
    source_rows = sorted(
        ({"pre_id": int(row["pre_id"]), "post_id": int(row["post_id"]),
          "contacts": int(row["contacts"])} for row in anatomy["edges"]),
        key=lambda row: (row["post_id"], row["pre_id"]),
    )
    if len(source_rows) != 88 or sum(row["contacts"] for row in source_rows) != 437:
        raise RuntimeError("KC -> MBON-m1 source totals no longer match the admitted facts")
    if {row["post_id"] for row in source_rows} != MBON_M1_IDS:
        raise RuntimeError("unexpected MBON-m1 endpoint")
    if any(row["contacts"] <= 0 for row in source_rows):
        raise RuntimeError("non-positive source contact count")
    if len({(row["pre_id"], row["post_id"]) for row in source_rows}) != len(source_rows):
        raise RuntimeError("duplicate KC -> MBON-m1 source pair")

    annotations = read_annotations()
    kc_ids = sorted({row["pre_id"] for row in source_rows})
    node_ids = kc_ids + sorted(MBON_M1_IDS)
    if len(set(node_ids)) != len(node_ids):
        raise RuntimeError("node identity overlap")

    nodes: list[dict] = []
    for source_id in node_ids:
        ann = annotations.get(source_id)
        if ann is None:
            raise RuntimeError(f"source ID {source_id} is absent from pinned annotations")
        role = "MBON-m1" if source_id in MBON_M1_IDS else "KC"
        if role == "MBON-m1" and ann["celltype"] != "MBON":
            raise RuntimeError(f"MBON-m1 source ID {source_id} has unexpected annotation")
        if role == "KC" and ann["celltype"] != "KC":
            raise RuntimeError(f"KC source ID {source_id} has unexpected annotation")
        nodes.append({
            "source_id": source_id,
            "role": role,
            "celltype": ann["celltype"],
            "source_annotation": ann["additional_annotations"],
            "hemisphere": ann["hemisphere"],
            "level_7_cluster": ann["level_7_cluster"],
            "transmitter": "UNKNOWN",
            "physiological_output_sign": "UNKNOWN",
            "anatomical_status": "MEASURED",
            "source": "Winding et al. 2023 Supplementary Data S1 annotations.csv",
        })

    edges = [{
        **row,
        "direction": "KC_to_MBON-m1",
        "connection_class": "axon_to_dendrite",
        "anatomical_status": "MEASURED",
        "candidate_plasticity_mask": (
            "INFERRED: all measured whole-cell KC -> MBON-m1 contact rows; "
            "a compartment-local plastic locus is not established"
        ),
        "synaptic_sign": "UNKNOWN; positive effect used later is an ENGINEERING ASSUMPTION",
        "source": "Supplementary-Data-S1/ad_connectivity_matrix.csv via l1r_admission_audit.json",
    } for row in source_rows]

    manifest = {
        "manifest_id": "larval_l1re_kc_mbon-m1_engineering_teacher_v1",
        "variant": "L1R-E",
        "status": "anatomy_manifest_only",
        "dataset": frozen["dataset"],
        "organism_stage": "first-instar larva; source EM volume 6-hour-old larva",
        "scientific_boundary": (
            "Measured KC -> MBON-m1 anatomy with an artificial local teaching port and "
            "a fixed inverse MBON-m1 -> action interface. No biological DAN pathway is claimed."
        ),
        "source_inputs": {
            str(ARCHIVE.relative_to(ROOT)).replace("/", "\\"): archive_hash,
            str(ADMISSION.relative_to(ROOT)).replace("/", "\\"): sha256(ADMISSION),
        },
        "nodes": nodes,
        "edges": edges,
        "boundary_overlays": [
            {
                "name": "current_position_to_KC_drive",
                "category": "ENGINEERING ASSUMPTION",
                "topology_edit": False,
                "trainable": False,
                "description": "Fixed causal encoding of current position only; no future timing or answer data.",
            },
            {
                "name": "artificial_local_teaching_port",
                "category": "ENGINEERING ASSUMPTION",
                "topology_edit": False,
                "trainable": False,
                "biological_cell_identity": None,
                "description": (
                    "A scalar event may gate local KC -> MBON-m1 plasticity in later stages. "
                    "It is not DAN-c1, a reconstructed neuron, or a measured dopamine pathway."
                ),
            },
            {
                "name": "inverse_MBON-m1_to_KEY_DOWN",
                "category": "ENGINEERING OVERLAY",
                "topology_edit": False,
                "trainable": False,
                "description": "While a valid cue arms the interface, lower bilateral MBON-m1 spike count maps to action.",
            },
        ],
        "validation": {
            "unique_node_count": len(nodes),
            "kc_node_count": len(kc_ids),
            "mbon_m1_node_count": 2,
            "edge_row_count": len(edges),
            "contact_count": sum(row["contacts"] for row in edges),
            "all_endpoints_present": all(
                row["pre_id"] in set(node_ids) and row["post_id"] in set(node_ids)
                for row in edges
            ),
            "all_contacts_positive": all(row["contacts"] > 0 for row in edges),
            "duplicate_edge_rows": len(edges) - len({(row["pre_id"], row["post_id"]) for row in edges}),
            "included_contact_reason_coverage": "100%",
            "excluded_candidate_contacts": [],
            "excluded_contact_reason_coverage": "vacuous: whole-cell rule includes every measured KC -> MBON-m1 row",
            "contains_DAN_nodes": False,
            "contains_motor_neurons": False,
        },
        "limits": [
            "The whole-cell plastic mask is INFERRED and is not a measured compartment-specific locus.",
            "The teaching port is an ENGINEERING ASSUMPTION without a biological neuron identity.",
            "The action mapping is an ENGINEERING OVERLAY and is not reconstructed larval motor anatomy.",
            "Exact connection sign, efficacy, membrane values, and learning rule remain UNKNOWN until separately declared.",
            "Literal DAN-c1-gated KC -> MBON-m1 L1R remains rejected by L1R-0.",
        ],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(OUTPUT.relative_to(ROOT)),
        "nodes": len(nodes),
        "kcs": len(kc_ids),
        "edges": len(edges),
        "contacts": sum(row["contacts"] for row in edges),
        "sha256": sha256(OUTPUT),
    }, indent=2))


if __name__ == "__main__":
    main()
