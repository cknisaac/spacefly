"""Read-only anatomy audit for the Level 3 PAM08→KC→MBON05 bridge."""

from __future__ import annotations

import gzip
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from audit_route_closure_roi import sample_chunk


ROOT = Path(__file__).resolve().parents[1]
PARTNERS = ROOT / "data/raw/malecns_v1/syn-partners-male-cns-v1.0-minconf-0.5-traced-only.feather"
VOLUME = "rois/malecns-subcompartments-v3"
SELECTED_ANATOMY = ROOT / "docs/figures/b1_mvp_pathway_rule_selection/selected_anatomy.json"
RUNTIME_MASK = ROOT / "configs/b2_candidate1_runtime_mask.json"
LEVEL2_CONFIG = ROOT / "configs/malecns_continuous_position_learning_v2_5.json"
OUTPUT = ROOT / "docs/figures/l3_dan_bridge_anatomy_audit.json"
MBON_ID = 10495
SELECTED_DAN_ID = 87177


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def audit() -> dict:
    mask = json.loads(RUNTIME_MASK.read_text(encoding="utf-8"))
    cohort = [int(item["kc_source_id"]) for item in mask["kc_pairs"][16:48]
              if item["plastic_contact_rows"]]
    level2 = json.loads(LEVEL2_CONFIG.read_text(encoding="utf-8"))
    level2_ids = [int(cell["source_id"]) for cell in level2["circuit"]["selected_kcs"]]
    if cohort != level2_ids or len(cohort) != 32:
        raise ValueError("Level 2 v2.5 cohort differs from the pinned B2 source-order slice")

    identities = json.loads(SELECTED_ANATOMY.read_text(encoding="utf-8"))
    dan_ids = [int(value) for value in identities["dan_source_ids"]]
    if SELECTED_DAN_ID not in dan_ids:
        raise ValueError("selected PAM08 body is outside the pre-audited B1 PAM08 roster")
    annotations = pq.read_table(
        ROOT / "data/processed/malecns_v1_traced/neurons.parquet").to_pandas()
    annotations = annotations.set_index("source_id")
    dan = annotations.loc[SELECTED_DAN_ID]
    if (dan["cell_class"] != "DAN" or dan["cell_type"] != "PAM08"
            or dan["instance"] != "PAM08(y4)_L"
            or dan["transmitter_consensus"] != "dopamine"):
        raise ValueError("selected DAN annotation no longer matches the pinned identity")

    source_receipt = json.loads(PARTNERS.with_name(PARTNERS.name + ".receipt.json").read_text())
    source_sha = _sha256(PARTNERS)
    if source_sha != source_receipt["sha256"]:
        raise ValueError("pinned syn-partner source checksum changed")

    reader = pa.ipc.open_file(pa.memory_map(str(PARTNERS)))
    rows: list[dict] = []
    offset = 0
    kc_array = np.asarray(cohort, dtype=np.int64)
    dan_array = np.asarray(dan_ids, dtype=np.int64)
    for batch_index in range(reader.num_record_batches):
        batch = reader.get_batch(batch_index)
        pre = batch["body_pre"].to_numpy()
        post = batch["body_post"].to_numpy()
        take = ((np.isin(pre, kc_array) & (post == MBON_ID))
                | (np.isin(pre, dan_array) &
                   (np.isin(post, kc_array) | (post == MBON_ID))))
        if take.any():
            selected = pa.Table.from_batches([batch]).filter(pa.array(take))
            selected = selected.append_column(
                "source_partner_row", pa.array(np.flatnonzero(take) + offset))
            rows.extend(selected.to_pylist())
        offset += len(batch)
    if offset != 124_025_046:
        raise ValueError("syn-partner row count does not match its receipt")

    volume_root = ROOT / "data/raw/malecns_v1/route_closure_roi" / VOLUME
    volume_info = json.loads((volume_root / "info").read_text(encoding="utf-8"))
    segment_info = json.loads(
        (volume_root / "segment_properties/info").read_text(encoding="utf-8"))["inline"]
    labels = {0: "<unspecified>", 2**64 - 1: "UNKNOWN_MISSING_CHUNK"}
    labels.update({int(key): value for key, value in zip(
        segment_info["ids"], segment_info["properties"][0]["values"])})
    scale = volume_info["scales"][0]
    size = np.asarray(scale["size"])
    chunk_shape = np.asarray(scale["chunk_sizes"][0])
    block_shape = np.asarray(scale["compressed_segmentation_block_size"])
    coordinates = np.asarray(
        [[row[f"{axis}_{side}"] for axis in "xyz"]
         for side in ("pre", "post") for row in rows])
    voxels = coordinates // 32
    chunk_keys, inverse = np.unique(voxels // chunk_shape, axis=0, return_inverse=True)
    mapped = np.full(len(coordinates), 2**64 - 1, dtype=np.uint64)
    chunks_used = []
    missing_chunks = []
    for key_index, key in enumerate(chunk_keys):
        start = key * chunk_shape
        end = np.minimum(start + chunk_shape, size)
        relative = (VOLUME + "/" + scale["key"] + "/" +
                    "_".join(f"{low}-{high}" for low, high in zip(start, end)))
        chunk_path = ROOT / "data/raw/malecns_v1/route_closure_roi" / relative
        indices = np.flatnonzero(inverse == key_index)
        if not chunk_path.exists():
            missing_chunks.append(relative)
            continue
        chunk_receipt = json.loads(
            chunk_path.with_name(chunk_path.name + ".receipt.json").read_text())
        chunk_sha = _sha256(chunk_path)
        if chunk_sha != chunk_receipt["sha256"]:
            raise ValueError(f"ROI chunk checksum changed: {relative}")
        data = chunk_path.read_bytes()
        if data[:2] == b"\x1f\x8b":
            data = gzip.decompress(data)
        mapped[indices] = sample_chunk(
            data, voxels[indices] - start, end - start, block_shape)
        chunks_used.append({"name": relative, "sha256": chunk_sha})

    for index, row in enumerate(rows):
        row["roi_pre"] = labels[int(mapped[index])]
        row["roi_post"] = labels[int(mapped[index + len(rows)])]

    target_contacts: Counter = Counter()
    dan_contacts: dict[int, Counter] = defaultdict(Counter)
    dan_pair_counts: Counter = Counter()
    dan_total_contacts: Counter = Counter()
    dan_to_mbon = Counter()
    for row in rows:
        if row["body_post"] == MBON_ID and row["body_pre"] in cohort:
            if row["roi_pre"] == row["roi_post"] == "g4(L)":
                target_contacts[int(row["body_pre"])] += 1
        if row["body_pre"] in dan_ids and row["body_post"] in cohort:
            body = int(row["body_pre"])
            dan_total_contacts[body] += 1
            if row["roi_pre"] == row["roi_post"] == "g4(L)":
                dan_contacts[body][int(row["body_post"])] += 1
        if row["body_pre"] in dan_ids and row["body_post"] == MBON_ID:
            dan_to_mbon[int(row["body_pre"])] += 1

    # Candidate ranking is restricted to the 25 PAM08 bodies already in the B1/B2 audit.
    ranking = []
    for body in dan_ids:
        matched = set(dan_contacts[body]) & set(target_contacts)
        contacts = sum(dan_contacts[body][kc] for kc in matched)
        ann = annotations.loc[body]
        ranking.append({
            "source_id": body,
            "cell_type": ann["cell_type"],
            "instance": ann["instance"],
            "same_g4_kc_count": len(matched),
            "same_g4_dan_to_kc_contacts": contacts,
            "same_g4_kc_to_mbon05_contacts_on_those_kcs": sum(
                target_contacts[kc] for kc in matched),
        })
    ranking.sort(key=lambda item: (item["same_g4_kc_count"],
                                   item["same_g4_dan_to_kc_contacts"],
                                   -item["source_id"]), reverse=True)
    selected_matched_kcs = sorted(set(dan_contacts[SELECTED_DAN_ID]) & set(target_contacts))

    return {
        "status": "PASS" if not missing_chunks else "INCONCLUSIVE_MISSING_ROI",
        "audit_scope": "Read-only; compares the 25 PAM08 bodies in the existing B1/B2 roster against the exact frozen Level 2 v2.5 32-KC cohort. It is not a census of every MaleCNS DAN.",
        "source": {
            "dataset": "MaleCNS v1.0 traced-only minconf-0.5",
            "syn_partner_sha256": source_sha,
            "syn_partner_rows_scanned": offset,
            "roi_volume": VOLUME,
            "coordinate_conversion": "floor(source_xyz_8nm / 32)",
            "roi_chunks_used": chunks_used,
            "roi_chunks_missing": missing_chunks,
        },
        "level2_status_record": {
            "cohort_1_v2_5": "PASS",
            "fresh_cohort_2_level2r": "FAIL strict 3/3 target-core replication; partial learning effect replicated",
            "level2_tuning": "none further authorized or performed",
            "artifacts_modified": False,
        },
        "fixed_cohort": {
            "parent_config": "configs/malecns_continuous_position_learning_v2_5.json",
            "parent_config_sha256": _sha256(LEVEL2_CONFIG),
            "mbon_source_id": MBON_ID,
            "kc_source_ids": cohort,
            "kc_to_mbon05_same_g4_pairs": len(target_contacts),
            "kc_to_mbon05_same_g4_contacts": sum(target_contacts.values()),
        },
        "candidate_ranking_within_audited_pam08_roster": ranking,
        "selected_dan": {
            "source_id": SELECTED_DAN_ID,
            "cell_class": dan["cell_class"],
            "cell_type": dan["cell_type"],
            "instance": dan["instance"],
            "annotation_status": dan["status_label"],
            "transmitter_consensus": dan["transmitter_consensus"],
            "transmitter_confidence": float(dan["transmitter_confidence"]),
            "whole_cohort_direct_dan_to_kc_graph_pairs": len({
                int(row["body_post"]) for row in rows
                if row["body_pre"] == SELECTED_DAN_ID and row["body_post"] in cohort}),
            "whole_cohort_direct_dan_to_kc_contacts": int(dan_total_contacts[SELECTED_DAN_ID]),
            "same_g4_dan_to_kc_pairs": len(dan_contacts[SELECTED_DAN_ID]),
            "same_g4_dan_to_kc_contacts": int(sum(dan_contacts[SELECTED_DAN_ID].values())),
            "same_g4_overlap_kc_source_ids": selected_matched_kcs,
            "same_g4_overlap_count": len(selected_matched_kcs),
            "direct_dan_to_mbon05_graph_contacts": int(dan_to_mbon[SELECTED_DAN_ID]),
            "direct_dan_to_mbon05_synaptic_current_modeled": False,
            "direct_dan_to_mbon05_exclusion_reason": "The minimal bridge uses DAN activity only at the local teaching gate; pair-specific physiological effect is unknown and was not added to Level 2 electrical readout.",
        },
        "evidence_limit": "Same-KC and same-g4 structural overlap supports an anatomical association only. Dopamine release at individual terminals, receptor action, functional modulation and the local LTD rule remain unverified; the LTD gate is an engineering assumption.",
    }


if __name__ == "__main__":
    result = audit()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "candidate": result["selected_dan"],
        "top_candidates": result["candidate_ranking_within_audited_pam08_roster"][:5],
        "missing_roi_chunks": result["source"]["roi_chunks_missing"],
    }, indent=2, ensure_ascii=False))
