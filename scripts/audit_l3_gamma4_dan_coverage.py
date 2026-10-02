"""Read-only all-annotated-DAN γ4 coverage audit for the frozen Level 2 cohort."""

from __future__ import annotations

import gzip
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_route_closure_roi import fetch as fetch_roi, sample_chunk  # noqa: E402

CONFIG = ROOT / "configs/malecns_continuous_position_learning_v2_5.json"
PARTNERS = ROOT / "data/raw/malecns_v1/syn-partners-male-cns-v1.0-minconf-0.5-traced-only.feather"
NEURONS = ROOT / "data/processed/malecns_v1_traced/neurons.parquet"
SELECTED_ANATOMY = ROOT / "docs/figures/b1_mvp_pathway_rule_selection/selected_anatomy.json"
VOLUME = "rois/malecns-subcompartments-v3"
VOLUME_ROOT = ROOT / "data/raw/malecns_v1/route_closure_roi" / VOLUME
OUTPUT = ROOT / "docs/figures/l3_gamma4_dan_cohort_coverage_audit.json"
MBON_ID = 10495
EXPECTED_PARTNER_SHA = "3db100d3b4c7cfdc9b34506b3eb8b5ead2d9760b38952e5656285bb362327efc"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def minimum_cover(masks: list[tuple[int, int]], universe: int) -> list[int]:
    """Exact minimum set cover for the union of the candidate KC masks."""
    if not universe:
        return []
    # Seed branch-and-bound with a greedy complete cover.
    greedy: list[int] = []
    covered = 0
    remaining = set(range(len(masks)))
    while covered != universe:
        best = max(remaining, key=lambda i: ((masks[i][1] & ~covered).bit_count(),
                                             -masks[i][0]))
        gain = masks[best][1] & ~covered
        if not gain:
            raise ValueError("candidate union is not coverable")
        greedy.append(best)
        covered |= masks[best][1]
        remaining.remove(best)
    best_solution = list(greedy)
    by_bit: dict[int, list[int]] = defaultdict(list)
    for i, (_, mask) in enumerate(masks):
        bits = mask
        while bits:
            low = bits & -bits
            by_bit[low].append(i)
            bits ^= low
    seen_depth: dict[int, int] = {}

    def search(covered_mask: int, chosen: list[int]) -> None:
        nonlocal best_solution
        if covered_mask == universe:
            if len(chosen) < len(best_solution):
                best_solution = chosen.copy()
            return
        if len(chosen) >= len(best_solution):
            return
        prior = seen_depth.get(covered_mask)
        if prior is not None and prior <= len(chosen):
            return
        seen_depth[covered_mask] = len(chosen)
        uncovered = universe & ~covered_mask
        options_by_bit = []
        bits = uncovered
        while bits:
            low = bits & -bits
            options = [i for i in by_bit[low]
                       if masks[i][1] & ~covered_mask]
            if not options:
                return
            options_by_bit.append((len(options), low, options))
            bits ^= low
        _, _, options = min(options_by_bit, key=lambda row: row[0])
        options.sort(key=lambda i: (-(masks[i][1] & uncovered).bit_count(),
                                    masks[i][0]))
        for i in options:
            search(covered_mask | masks[i][1], chosen + [i])

    search(0, [])
    return best_solution


def audit() -> dict:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    cohort = [int(row["source_id"]) for row in config["circuit"]["selected_kcs"]]
    if len(cohort) != 32 or config["circuit"]["mbon_source_id"] != MBON_ID:
        raise ValueError("frozen cohort identity differs")
    partner_receipt = json.loads(
        PARTNERS.with_name(PARTNERS.name + ".receipt.json").read_text(encoding="utf-8"))
    partner_sha = sha256(PARTNERS)
    if partner_sha != EXPECTED_PARTNER_SHA or partner_sha != partner_receipt["sha256"]:
        raise ValueError("pinned traced-only syn-partner checksum differs")

    annotation = pq.read_table(NEURONS).to_pandas().set_index("source_id")
    dan_rows = annotation[annotation["cell_class"] == "DAN"]
    dan_ids = np.asarray(dan_rows.index.to_numpy(), dtype=np.int64)
    cohort_array = np.asarray(cohort, dtype=np.int64)
    reader = pa.ipc.open_file(pa.memory_map(str(PARTNERS)))
    rows: list[dict] = []
    offset = 0
    for batch_index in range(reader.num_record_batches):
        batch = reader.get_batch(batch_index)
        pre = batch["body_pre"].to_numpy()
        post = batch["body_post"].to_numpy()
        take = ((np.isin(pre, dan_ids) & np.isin(post, cohort_array))
                | (np.isin(pre, cohort_array) & (post == MBON_ID)))
        if take.any():
            selected = pa.Table.from_batches([batch]).filter(pa.array(take))
            selected = selected.append_column(
                "source_partner_row", pa.array(np.flatnonzero(take) + offset))
            rows.extend(selected.to_pylist())
        offset += len(batch)
    if offset != 124_025_046:
        raise ValueError("syn-partner row count differs from source receipt")

    volume_info = json.loads((VOLUME_ROOT / "info").read_text(encoding="utf-8"))
    segment = json.loads(
        (VOLUME_ROOT / "segment_properties/info").read_text(encoding="utf-8"))["inline"]
    labels = {0: "<unspecified>", 2**64 - 1: "UNKNOWN_MISSING_CHUNK"}
    labels.update({int(k): v for k, v in zip(segment["ids"], segment["properties"][0]["values"])})
    scale = volume_info["scales"][0]
    size = np.asarray(scale["size"])
    chunk_shape = np.asarray(scale["chunk_sizes"][0])
    block_shape = np.asarray(scale["compressed_segmentation_block_size"])
    xyz = np.asarray([[row[f"{axis}_{side}"] for axis in "xyz"]
                      for side in ("pre", "post") for row in rows])
    voxels = xyz // 32
    keys, inverse = np.unique(voxels // chunk_shape, axis=0, return_inverse=True)
    roi_ids = np.full(len(voxels), 2**64 - 1, dtype=np.uint64)
    used, missing = [], []
    for ki, key in enumerate(keys):
        start = key * chunk_shape
        end = np.minimum(start + chunk_shape, size)
        relative = (VOLUME + "/" + scale["key"] + "/" +
                    "_".join(f"{lo}-{hi}" for lo, hi in zip(start, end)))
        path = ROOT / "data/raw/malecns_v1/route_closure_roi" / relative
        indices = np.flatnonzero(inverse == ki)
        if not path.exists():
            # Reuse the project's pinned, checksum-validating read-only ROI fetcher.
            try:
                data, receipt = fetch_roi(relative)
            except Exception:
                missing.append(relative)
                continue
        else:
            data = path.read_bytes()
            receipt_path = path.with_name(path.name + ".receipt.json")
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if sha256(path) != receipt["sha256"]:
            raise ValueError(f"ROI chunk checksum differs: {relative}")
        if data[:2] == b"\x1f\x8b":
            data = gzip.decompress(data)
        roi_ids[indices] = sample_chunk(data, voxels[indices] - start, end - start, block_shape)
        used.append({"name": relative, "sha256": receipt["sha256"]})
    for i, row in enumerate(rows):
        row["roi_pre"] = labels[int(roi_ids[i])]
        row["roi_post"] = labels[int(roi_ids[i + len(rows)])]

    g4_target_kcs = {int(r["body_pre"]) for r in rows
                     if r["body_post"] == MBON_ID
                     and r["roi_pre"] == r["roi_post"] == "g4(L)"}
    def summarize(scope_ids: set[int]) -> dict:
        coverage: dict[int, set[int]] = defaultdict(set)
        contacts: dict[int, int] = defaultdict(int)
        for row in rows:
            dan_id, kc_id = int(row["body_pre"]), int(row["body_post"])
            if (dan_id in scope_ids and kc_id in g4_target_kcs
                    and row["roi_pre"] == row["roi_post"] == "g4(L)"):
                coverage[dan_id].add(kc_id)
                contacts[dan_id] += 1
        indexed = [(dan_id, set(kcs)) for dan_id, kcs in coverage.items() if kcs]
        union = set().union(*(kcs for _, kcs in indexed)) if indexed else set()
        kc_bit = {kc: 1 << i for i, kc in enumerate(cohort)}
        masks = [(dan_id, sum(kc_bit[kc] for kc in kcs)) for dan_id, kcs in indexed]
        universe = 0
        for kc in union:
            universe |= kc_bit[kc]
        chosen_indices = minimum_cover(masks, universe)
        chosen_ids = [masks[i][0] for i in chosen_indices]
        ranking = []
        for dan_id, kcs in indexed:
            ann = dan_rows.loc[dan_id]
            ranking.append({"source_id": dan_id, "cell_type": str(ann["cell_type"]),
                            "instance": str(ann["instance"]),
                            "annotation_status": str(ann["status_label"]),
                            "transmitter_consensus": str(ann["transmitter_consensus"]),
                            "gamma4_kc_count": len(kcs),
                            "gamma4_dan_to_kc_contacts": contacts[dan_id],
                            "gamma4_kc_source_ids": sorted(kcs)})
        ranking.sort(key=lambda r: (-r["gamma4_kc_count"],
                                    -r["gamma4_dan_to_kc_contacts"], r["source_id"]))
        return {"candidate_count_with_gamma4_overlap": len(ranking),
                "maximum_anatomical_coverage_kc_ids": sorted(union),
                "maximum_anatomical_coverage_count": len(union),
                "minimum_cardinality_set_for_maximum_coverage": [
                    next(row for row in ranking if row["source_id"] == dan_id)
                    for dan_id in chosen_ids],
                "candidate_ranking": ranking}

    all_scope = set(int(x) for x in dan_rows.index)
    roster_ids = set(int(x) for x in
                     json.loads(SELECTED_ANATOMY.read_text(encoding="utf-8"))["dan_source_ids"])
    unknown_rows_by_scope = {
        "all_annotated_dan": sum(1 for row in rows
            if int(row["body_pre"]) in all_scope
            and "UNKNOWN_MISSING_CHUNK" in (row["roi_pre"], row["roi_post"])),
        "audited_pam08_roster": sum(1 for row in rows
            if int(row["body_pre"]) in roster_ids
            and "UNKNOWN_MISSING_CHUNK" in (row["roi_pre"], row["roi_post"])),
        "frozen_kc_to_mbon05_pairs": sum(1 for row in rows
            if int(row["body_pre"]) in set(cohort) and row["body_post"] == MBON_ID
            and "UNKNOWN_MISSING_CHUNK" in (row["roi_pre"], row["roi_post"])),
    }
    all_summary = summarize(all_scope)
    pam08_summary = summarize(roster_ids)
    return {
        "status": "PASS" if not missing else "INCONCLUSIVE_MISSING_ROI",
        "scope": "All annotated MaleCNS DAN bodies with traced-only presynaptic contacts to the frozen cohort; both DAN presynaptic and KC postsynaptic endpoints must map to g4(L). KC coverage is counted only for KCs with a strict g4(L) KC→MBON05 pair.",
        "sources": {"partner_sha256": partner_sha, "partner_rows_scanned": offset,
                    "neuron_annotations": str(NEURONS.relative_to(ROOT)),
                    "roi_volume": VOLUME, "roi_chunks_used": used,
                    "roi_chunks_missing": missing},
        "frozen_cohort": cohort, "frozen_mbon05": MBON_ID,
        "kc_with_strict_gamma4_kc_to_mbon05_pair": sorted(g4_target_kcs),
        "strict_gamma4_kc_to_mbon05_kc_count": len(g4_target_kcs),
        "all_annotated_dan_scope": all_summary,
        "previously_audited_pam08_roster_scope": pam08_summary,
        "unknown_roi_candidate_rows_by_scope": unknown_rows_by_scope,
        "pam08_roster_and_frozen_kc_mbon_roi_complete": (
            not missing or (unknown_rows_by_scope["audited_pam08_roster"] == 0
                            and unknown_rows_by_scope["frozen_kc_to_mbon05_pairs"] == 0)),
    }


if __name__ == "__main__":
    result = audit()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "all_annotated_dan": {
            "candidate_count": result["all_annotated_dan_scope"]["candidate_count_with_gamma4_overlap"],
            "coverage": result["all_annotated_dan_scope"]["maximum_anatomical_coverage_count"],
            "minimum_set": [row["source_id"] for row in
                result["all_annotated_dan_scope"]["minimum_cardinality_set_for_maximum_coverage"]]},
        "audited_pam08_roster": {
            "candidate_count": result["previously_audited_pam08_roster_scope"]["candidate_count_with_gamma4_overlap"],
            "coverage": result["previously_audited_pam08_roster_scope"]["maximum_anatomical_coverage_count"],
            "minimum_set": [row["source_id"] for row in
                result["previously_audited_pam08_roster_scope"]["minimum_cardinality_set_for_maximum_coverage"]]},
        "roi_chunks_missing": len(result["sources"]["roi_chunks_missing"]),
        "unknown_rows": result["unknown_roi_candidate_rows_by_scope"],
    }, indent=2))
