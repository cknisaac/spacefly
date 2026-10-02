"""Build the immutable, provenance-linked anatomy manifest for Candidate L2."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "data/raw/larval_l1em/supplementary_data_s1.zip"
EDGE_AUDIT = ROOT / "data/raw/larval_l1em/edge_audit.json"
CATMAID_AUDIT = ROOT / "data/raw/larval_l1em/catmaid_route_audit.json"
OUTPUT = ROOT / "configs/larval_l2_subgraph_manifest_v1.json"
ROLES = {
    "DAN-d1": {3_886_356, 5_966_099},
    "MBON-d1": {4_241_237, 7_055_857},
    "Ipsigoro": {3_979_181, 5_794_678},
    "Goro": {3_720_037, 5_206_247},
}


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
                        "annotation_level_7_cluster": row["level_7_cluster"],
                    }
        return result


def main() -> None:
    edge_audit = json.loads(EDGE_AUDIT.read_text(encoding="utf-8"))
    catmaid = json.loads(CATMAID_AUDIT.read_text(encoding="utf-8"))
    annotations = read_annotations()
    kc_rows = edge_audit["KC_to_MBON_d1"]["edge_rows"]
    node_ids = set(ROLES["DAN-d1"] | ROLES["MBON-d1"] | ROLES["Ipsigoro"] | ROLES["Goro"])
    node_ids.update(row["pre_id"] for row in kc_rows)
    catmaid_names = catmaid["catmaid_neuron_names"]

    nodes: list[dict] = []
    for neuron_id in sorted(node_ids):
        if neuron_id in ROLES["DAN-d1"]:
            role = "DAN-d1"
        elif neuron_id in ROLES["MBON-d1"]:
            role = "MBON-d1"
        elif neuron_id in ROLES["Ipsigoro"]:
            role = "Ipsigoro"
        elif neuron_id in ROLES["Goro"]:
            role = "Goro"
        else:
            role = "KC"
        ann = annotations.get(neuron_id, {})
        nodes.append(
            {
                "source_id": neuron_id,
                "role": role,
                "celltype": ann.get("celltype", role),
                "source_annotation": ann.get("additional_annotations", "VFB/CATMAID crosswalk"),
                "hemisphere": ann.get("hemisphere", "from_VFB_pair_crosswalk"),
                "level_7_cluster": ann.get("annotation_level_7_cluster"),
                "catmaid_neuron_name": catmaid_names.get(str(neuron_id)),
                "transmitter": "UNKNOWN",
                "physiological_output_sign": "UNKNOWN",
                "evidence_provenance": "Winding et al. (2023) Supplementary Data S1 and/or VFB CATMAID L1EM project 1",
            }
        )

    edges: list[dict] = []
    for row in kc_rows:
        edges.append(
            {
                "pre_id": row["pre_id"],
                "post_id": row["post_id"],
                "contacts": row["contacts"],
                "direction": "KC_to_MBON-d1",
                "connection_class": "axon_to_dendrite",
                "anatomical_status": "MEASURED",
                "candidate_plasticity_mask": "INFERRED: all measured annotated KC inputs to MBON-d1; compartment-local contacts are not resolved in S1",
                "synaptic_sign": "UNKNOWN",
                "source": "Supplementary-Data-S1/ad_connectivity_matrix.csv",
            }
        )

    selected_pairs = edge_audit["selected_pair_edges"]
    for pre, post, count in (
        (int(k.split("->")[0]), int(k.split("->")[1]), v)
        for pre_role, targets in selected_pairs.items()
        for post_role, pair_edges in targets.items()
        for k, v in pair_edges.items()
        if (pre_role, post_role) == ("DAN-d1", "MBON-d1")
    ):
        edges.append(
            {
                "pre_id": pre,
                "post_id": post,
                "contacts": count,
                "direction": "DAN-d1_to_MBON-d1",
                "connection_class": "axon_to_dendrite",
                "anatomical_status": "MEASURED",
                "candidate_plasticity_mask": "not_plastic; teaching/modulatory input",
                "synaptic_sign": "UNKNOWN",
                "source": "Supplementary-Data-S1/ad_connectivity_matrix.csv",
            }
        )

    for source_name, route_name in (("L2_MBONd1_to_Ipsigoro", "MBON-d1_to_Ipsigoro"), ("L2_Ipsigoro_to_Goro", "Ipsigoro_to_Goro")):
        for path in catmaid["routes"][source_name]["paths_at_shortest_depth"]:
            edges.append(
                {
                    "pre_id": path["path_ids"][0],
                    "post_id": path["path_ids"][1],
                    "contacts": path["contacts_per_edge"][0],
                    "direction": route_name,
                    "connection_class": "chemical_synapse_count_CATMAID",
                    "anatomical_status": "MEASURED",
                    "candidate_plasticity_mask": "fixed",
                    "synaptic_sign": "UNKNOWN",
                    "source": "VFB CATMAID pass-through; L1EM project 1; catmaid_route_audit.json",
                }
            )

    manifest = {
        "manifest_id": "larval_l2_dan-d1_mbon-d1_v1",
        "candidate_status": "admitted_to_anatomy_and_model_design_only",
        "dataset": "L1 Larval CNS / Winding et al. 2023",
        "organism_stage": "first-instar larva; source EM volume 6-hour-old larva",
        "source_inputs": {
            str(ARCHIVE.relative_to(ROOT)): sha256(ARCHIVE),
            str(EDGE_AUDIT.relative_to(ROOT)): sha256(EDGE_AUDIT),
            str(CATMAID_AUDIT.relative_to(ROOT)): sha256(CATMAID_AUDIT),
        },
        "nodes": nodes,
        "edges": edges,
        "boundary_overlays": [
            {
                "name": "current_visible_position_to_KC_drive",
                "category": "ENGINEERING ASSUMPTION",
                "topology_edit": False,
                "description": "Fixed causal sensory drive into the retained KC population; no future timing information.",
            },
            {
                "name": "Goro_to_game_KEY_DOWN",
                "category": "ENGINEERING OVERLAY",
                "topology_edit": False,
                "description": "A fixed threshold maps Goro output to the task action; this is not a measured fly-to-key correspondence.",
            },
            {
                "name": "game_outcome_to_DAN-d1_teaching",
                "category": "ENGINEERING ASSUMPTION",
                "topology_edit": False,
                "description": "A fixed task teaching interface drives DAN-d1; utility, DAN drive, and local synaptic change remain separately logged.",
            },
        ],
        "limits": [
            "Candidate L1 is rejected; this manifest is the distinct DAN-d1 / MBON-d1 hypothesis.",
            "KC-to-MBON-d1 contacts are whole-cell totals; compartment-specific bouton localization is unresolved.",
            "The exact larval KC-to-MBON-d1 learning-storage locus is an INFERRED hypothesis, not measured by this connectome.",
            "All transmitter/sign and physiological efficacy entries remain UNKNOWN.",
            "The key-action interface is an engineering overlay.",
        ],
    }
    OUTPUT.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(ROOT)} with {len(nodes)} nodes and {len(edges)} directed edge rows")


if __name__ == "__main__":
    main()
