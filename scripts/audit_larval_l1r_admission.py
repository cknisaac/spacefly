"""Audit literal L1R (KC -> MBON-m1, DAN-c1 teaching) admission.

This is an anatomy/evidence audit. It does not construct an electrical model,
infer synaptic efficacy, or implement learning. Live CATMAID reads are public
and read-only; the pinned S1 archive remains the count/identity source.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "data/raw/larval_l1em/supplementary_data_s1.zip"
OUTPUT = ROOT / "data/raw/larval_l1em/l1r_admission_audit.json"
API = "https://v3-cached.virtualflybrain.org/catmaid/l1em/"

DAN_C1 = {15_592_096, 16_240_569}
MBON_M1 = {4_022_539, 17_016_974}
MBON_C1 = {8_980_589, 16_223_537}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def get_json(command: str, params: dict[str, str]) -> object:
    query = urllib.parse.urlencode({"project": "1", "raw": "true", **params})
    request = urllib.request.Request(API + command + "?" + query)
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)


def read_source() -> tuple[dict[int, dict[str, str]], list[dict[str, int]],
                           list[dict[str, int]], list[dict[str, int]]]:
    with zipfile.ZipFile(ARCHIVE) as archive:
        with archive.open("Supplementary-Data-S1/annotations.csv") as raw:
            annotations: dict[int, dict[str, str]] = {}
            for row in csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")):
                for side, field in (("L", "left_id"), ("R", "right_id")):
                    if row[field] != "no pair":
                        annotations[int(row[field])] = {
                            "celltype": row["celltype"],
                            "additional_annotations": row["additional_annotations"],
                            "hemisphere": side,
                        }
        kc_ids = {source_id for source_id, row in annotations.items()
                  if row["celltype"] == "KC"}
        kc_m1: list[dict[str, int]] = []
        kc_c1: list[dict[str, int]] = []
        dan_edges: list[dict[str, int]] = []
        with archive.open("Supplementary-Data-S1/ad_connectivity_matrix.csv") as raw:
            reader = csv.reader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""))
            target_ids = [int(value) for value in next(reader)[1:]]
            target_index = {source_id: index for index, source_id in enumerate(target_ids)}
            for row in reader:
                pre = int(row[0])
                if pre in kc_ids:
                    for post in sorted(MBON_M1):
                        contacts = int(float(row[target_index[post] + 1]))
                        if contacts:
                            kc_m1.append({"pre_id": pre, "post_id": post,
                                          "contacts": contacts})
                    for post in sorted(MBON_C1):
                        contacts = int(float(row[target_index[post] + 1]))
                        if contacts:
                            kc_c1.append({"pre_id": pre, "post_id": post,
                                          "contacts": contacts})
                if pre in DAN_C1:
                    for post in sorted(MBON_M1 | MBON_C1):
                        contacts = int(float(row[target_index[post] + 1]))
                        if contacts:
                            dan_edges.append({"pre_id": pre, "post_id": post,
                                              "contacts": contacts,
                                              "post_role": ("MBON-m1" if post in MBON_M1
                                                            else "MBON-c1")})
    return annotations, kc_m1, kc_c1, dan_edges


def matrix_locations(rows: set[int], columns: set[int]) -> tuple[list[tuple[float, float, float]], int]:
    response = get_json("connectivity_matrix", {
        "rows": ",".join(map(str, sorted(rows))),
        "columns": ",".join(map(str, sorted(columns))),
        "with_locations": "true",
    })
    points: list[tuple[float, float, float]] = []
    total = 0
    assert isinstance(response, dict)
    for targets in response.values():
        for details in targets.values():
            total += int(details["count"])
            for location in details.get("locations", {}).values():
                count = int(location["count"])
                point = tuple(float(value) for value in location["pos"])
                points.extend([point] * count)
    return points, total


def dan_output_locations() -> list[tuple[float, float, float]]:
    points: list[tuple[float, float, float]] = []
    for source_id in sorted(DAN_C1):
        detail = get_json("skeleton_compact_detail", {
            "id": str(source_id), "with_connectors": "true", "with_tags": "false"
        })
        # CATMAID compact connector rows:
        # [treenode_id, connector_id, relation, x, y, z], relation 0 = presynaptic.
        for row in detail[1]:
            if int(row[2]) == 0:
                points.append((float(row[3]), float(row[4]), float(row[5])))
    return points


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("percentile requires data")
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def distance_summary(query: list[tuple[float, float, float]],
                     reference: list[tuple[float, float, float]]) -> dict:
    distances_um = []
    for qx, qy, qz in query:
        nearest_nm = min(math.dist((qx, qy, qz), point) for point in reference)
        distances_um.append(nearest_nm / 1000.0)
    return {
        "query_contact_count": len(query),
        "reference_contact_count": len(reference),
        "nearest_distance_um": {
            "minimum": min(distances_um),
            "p10": percentile(distances_um, 0.10),
            "p25": percentile(distances_um, 0.25),
            "median": percentile(distances_um, 0.50),
            "p75": percentile(distances_um, 0.75),
            "p90": percentile(distances_um, 0.90),
            "maximum": max(distances_um),
        },
        "fraction_within_um": {
            str(limit): sum(value <= limit for value in distances_um) / len(distances_um)
            for limit in (1, 2, 5, 10)
        },
    }


def main() -> None:
    annotations, kc_m1, kc_c1, dan_edges = read_source()
    kc_ids_m1 = {row["pre_id"] for row in kc_m1}
    kc_ids_c1 = {row["pre_id"] for row in kc_c1}
    kc_m1_points, kc_m1_live_total = matrix_locations(kc_ids_m1, MBON_M1)
    kc_c1_points, kc_c1_live_total = matrix_locations(kc_ids_c1, MBON_C1)
    dan_c1_points, dan_c1_live_total = matrix_locations(DAN_C1, MBON_C1)
    all_dan_outputs = dan_output_locations()

    local_kc_m1_total = sum(row["contacts"] for row in kc_m1)
    local_kc_c1_total = sum(row["contacts"] for row in kc_c1)
    local_dan_c1_total = sum(row["contacts"] for row in dan_edges
                             if row["post_role"] == "MBON-c1")
    # The two critical L1R blocks must match. CATMAID is a live reconstruction
    # and can contain later edits outside those blocks; preserve any such
    # difference in the positive control rather than rewriting the pinned S1
    # source fact.
    if (local_kc_m1_total != kc_m1_live_total
            or local_dan_c1_total != dan_c1_live_total):
        raise RuntimeError("Pinned S1 and live CATMAID critical contact totals disagree")

    identities = {
        role: [{"source_id": source_id, **annotations[source_id]}
               for source_id in sorted(ids)]
        for role, ids in (("DAN-c1", DAN_C1), ("MBON-m1", MBON_M1),
                          ("MBON-c1", MBON_C1))
    }
    result = {
        "audit_id": "larval_l1r_literal_admission_v1",
        "decision": "FAIL",
        "decision_scope": "Literal KC_to_MBON-m1 plastic locus under DAN-c1 teaching",
        "frozen_source": {
            "archive": str(ARCHIVE.relative_to(ROOT)),
            "sha256": sha256(ARCHIVE),
            "dataset": "Winding et al. 2023 Supplementary Data S1 / first-instar L1EM",
        },
        "live_source": {
            "api": API,
            "project": 1,
            "method": "read-only public VFB CATMAID pass-through",
        },
        "identities": identities,
        "anatomy": {
            "KC_to_MBON-m1": {"edge_rows": len(kc_m1), "contacts": local_kc_m1_total,
                               "edges": sorted(kc_m1, key=lambda x: (x["post_id"], x["pre_id"]))},
            "KC_to_MBON-c1_positive_control": {
                "edge_rows": len(kc_c1),
                "pinned_S1_contacts": local_kc_c1_total,
                "live_CATMAID_contacts": kc_c1_live_total,
                "difference": kc_c1_live_total - local_kc_c1_total,
                "interpretation": "Descriptive positive control only; the live project has two more contacts than the pinned S1 publication matrix.",
            },
            "DAN-c1_to_MBON": sorted(dan_edges, key=lambda x: (x["post_role"], x["pre_id"], x["post_id"])),
            "DAN-c1_to_MBON-m1_direct_contacts": sum(
                row["contacts"] for row in dan_edges if row["post_role"] == "MBON-m1"),
            "DAN-c1_to_MBON-c1_direct_contacts": local_dan_c1_total,
        },
        "spatial_descriptive_check": {
            "purpose": "Compare exact KC-to-MBON contact locations with DAN-c1 output territory. Distance is descriptive anatomy, not proof of dopamine action or plasticity.",
            "KC_to_MBON-m1_vs_all_DAN-c1_presynaptic_sites": distance_summary(kc_m1_points, all_dan_outputs),
            "KC_to_MBON-c1_vs_all_DAN-c1_presynaptic_sites_positive_control": distance_summary(kc_c1_points, all_dan_outputs),
            "KC_to_MBON-m1_vs_DAN-c1_to_MBON-c1_sites": distance_summary(kc_m1_points, dan_c1_points),
            "KC_to_MBON-c1_vs_DAN-c1_to_MBON-c1_sites_positive_control": distance_summary(kc_c1_points, dan_c1_points),
        },
        "primary_evidence_ledger": [
            {
                "claim": "DAN-c1 innervates lower peduncle and causally participates in third-instar aversive learning",
                "category": "LITERATURE-CONSTRAINED",
                "source": "https://elifesciences.org/articles/100890",
                "limit": "The paper hypothesizes depression of attractive MBN-to-MBON synapses in LP but does not identify MBON-m1 as the postsynaptic LP output or measure KC-to-MBON-m1 plasticity.",
            },
            {
                "claim": "MBON-m1 odor response decreases on average after aversive conditioning in first-instar larvae",
                "category": "LITERATURE-CONSTRAINED",
                "source": "https://pmc.ncbi.nlm.nih.gov/articles/PMC8616581/",
                "limit": "The authors give DAN-g1/d1-associated direct depression or indirect MBON-network disinhibition as alternatives; the experiment does not assign the change to DAN-c1 or isolate KC-to-MBON-m1 synapses.",
            },
            {
                "claim": "DAN-c1 and MBON-c1 define the larval lower-peduncle compartment",
                "category": "LITERATURE-CONSTRAINED plus MEASURED direct anatomy",
                "source": "https://elifesciences.org/articles/80594",
                "limit": "This supports MBON-c1 as the anatomy-aligned output for DAN-c1 and contradicts substituting MBON-m1 into that compartment by adult homology.",
            },
        ],
        "gate_checks": {
            "exact_bilateral_identities_source_linked": True,
            "KC_to_MBON-m1_contacts_reproducible": True,
            "DAN-c1_teaching_supported": True,
            "MBON-m1_conditioning_response_change_supported": True,
            "same_KC_MBON-m1_learning_territory_supported_for_DAN-c1": False,
            "local_DAN-c1_gated_KC_to_MBON-m1_LTD_coherent_without_cell_substitution": False,
        },
        "interpretation": (
            "The literal L1R tuple fails its predeclared admission gate. DAN-c1 teaching and "
            "MBON-m1 conditioning effects are each supported, but the evidence does not join them "
            "at one KC-to-MBON-m1 learning locus. The source anatomy instead directly pairs DAN-c1 "
            "with MBON-c1. Do not construct or simulate literal L1R, and do not substitute MBON-c1 "
            "inside the L1R name."
        ),
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "decision": result["decision"],
        "KC_to_MBON-m1_contacts": local_kc_m1_total,
        "DAN-c1_to_MBON-m1_direct_contacts": result["anatomy"]["DAN-c1_to_MBON-m1_direct_contacts"],
        "DAN-c1_to_MBON-c1_direct_contacts": local_dan_c1_total,
        "spatial": result["spatial_descriptive_check"],
        "output": str(OUTPUT),
        "sha256": sha256(OUTPUT),
    }, indent=2))


if __name__ == "__main__":
    main()
