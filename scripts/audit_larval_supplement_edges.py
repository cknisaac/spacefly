"""Audit selected axon-to-dendrite edges in Winding et al. (2023) Supplementary Data S1.

This script reads the published axon-to-dendrite synapse-count matrix directly
from the small compressed supplement archive. Rows are presynaptic neuron IDs
and columns are postsynaptic neuron IDs. It does not assign synaptic sign or
infer physiology from anatomical contact counts.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import zipfile
from collections import defaultdict
from pathlib import Path


DEFAULT_ARCHIVE = Path("data/raw/larval_l1em/supplementary_data_s1.zip")
DAN_D1 = {5_966_099, 3_886_356}
DAN_C1 = {15_592_096, 16_240_569}
MBON_D1 = {4_241_237, 7_055_857}
MBON_M1 = {17_016_974, 4_022_539}
IPSIGORO = {5_794_678, 3_979_181}
GORO = {3_720_037, 5_206_247}


def parse_annotations(archive: zipfile.ZipFile) -> list[dict[str, str]]:
    with archive.open("Supplementary-Data-S1/annotations.csv") as raw:
        text = io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")
        return list(csv.DictReader(text))


def read_matrix_edges(
    archive: zipfile.ZipFile,
    id_sets: dict[str, set[int]],
) -> tuple[set[int], dict[str, dict[str, dict[str, int]]]]:
    """Return all matrix IDs and contacts among named identity sets."""
    interesting = set().union(*id_sets.values())
    label_by_id = {
        neuron_id: label
        for label, neuron_ids in id_sets.items()
        for neuron_id in neuron_ids
    }
    edges: dict[str, dict[str, dict[str, int]]] = defaultdict(
        lambda: defaultdict(dict)
    )
    with archive.open("Supplementary-Data-S1/ad_connectivity_matrix.csv") as raw:
        text = io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")
        reader = csv.reader(text)
        header = next(reader)
        target_ids = [int(value) for value in header[1:]]
        matrix_ids = set(target_ids)
        for row in reader:
            source_id = int(row[0])
            if source_id not in interesting:
                continue
            source_label = label_by_id[source_id]
            for index, value in enumerate(row[1:]):
                target_id = target_ids[index]
                if target_id in interesting and float(value) > 0:
                    edges[source_label][label_by_id[target_id]][
                        f"{source_id}->{target_id}"
                    ] = int(float(value))
    return matrix_ids, edges


def kc_edges_to(archive: zipfile.ZipFile, targets: set[int]) -> list[dict[str, int]]:
    annotations = parse_annotations(archive)
    kc_ids: set[int] = set()
    for row in annotations:
        if row["celltype"] != "KC":
            continue
        for field in ("left_id", "right_id"):
            if row[field] != "no pair":
                kc_ids.add(int(row[field]))

    result: list[dict[str, int]] = []
    with archive.open("Supplementary-Data-S1/ad_connectivity_matrix.csv") as raw:
        text = io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")
        reader = csv.reader(text)
        header = next(reader)
        target_indexes = {
            int(neuron_id): index
            for index, neuron_id in enumerate(header[1:])
            if int(neuron_id) in targets
        }
        for row in reader:
            source_id = int(row[0])
            if source_id not in kc_ids:
                continue
            for target_id, index in target_indexes.items():
                contacts = int(float(row[index + 1]))
                if contacts:
                    result.append(
                        {"pre_id": source_id, "post_id": target_id, "contacts": contacts}
                    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    args = parser.parse_args()
    id_sets = {
        "DAN-d1": DAN_D1,
        "DAN-c1": DAN_C1,
        "MBON-d1": MBON_D1,
        "MBON-m1": MBON_M1,
        "Ipsigoro": IPSIGORO,
        "Goro": GORO,
    }
    with zipfile.ZipFile(args.archive) as archive:
        matrix_ids, edges = read_matrix_edges(archive, id_sets)
        kc_to_d1 = kc_edges_to(archive, MBON_D1)
        kc_to_m1 = kc_edges_to(archive, MBON_M1)
        annotations = parse_annotations(archive)
    annotation_text = " ".join(
        row["celltype"] + " " + row["additional_annotations"] for row in annotations
    ).lower()
    result = {
        "dataset": "Winding et al. 2023, Supplementary Data S1",
        "matrix": "ad_connectivity_matrix.csv",
        "matrix_direction": "row/presynaptic -> column/postsynaptic",
        "matrix_neuron_count": len(matrix_ids),
        "anatomical_contacts_are_not_synaptic_sign": True,
        "KC_to_MBON_d1": {
            "annotated_KC_edges": len(kc_to_d1),
            "total_contacts": sum(row["contacts"] for row in kc_to_d1),
            "edge_rows": kc_to_d1,
        },
        "KC_to_MBON_m1": {
            "annotated_KC_edges": len(kc_to_m1),
            "total_contacts": sum(row["contacts"] for row in kc_to_m1),
            "edge_rows": kc_to_m1,
        },
        "selected_pair_edges": edges,
        "all_goro_ids_in_matrix": GORO.issubset(matrix_ids),
        "basin4_mentioned_in_published_annotation_table": "basin-4" in annotation_text,
        "limits": [
            "This graph matrix does not establish synaptic sign or physiological efficacy.",
            "The published annotation table does not label Basin-4.",
            "Both Goro IDs are outside this matrix; no complete MBON-to-Goro path is asserted.",
        ],
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
