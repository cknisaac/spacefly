"""Data-only γ4 contact audit against pinned MaleCNS partners and ROI cache.

Missing ROI chunks stay unknown. This never creates a simulator/plasticity mask.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np
import pyarrow as pa

from audit_route_closure_roi import sample_chunk, decoder_check

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/raw/malecns_v1/route_closure_roi"
VOLUME = "rois/malecns-subcompartments-v3"
OUT = ROOT / "docs/figures/b2_candidate_design"


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def main():
    decoder_check()
    prior = json.loads((ROOT / "docs/figures/b1_mvp_pathway_rule_selection/selected_anatomy.json").read_text())
    kcs = np.array(prior["kc_source_ids"], dtype=np.int64)
    dans = np.array(prior["dan_source_ids"], dtype=np.int64)
    source = ROOT / "data/raw/malecns_v1/syn-partners-male-cns-v1.0-minconf-0.5-traced-only.feather"
    receipt = json.loads((source.with_name(source.name + ".receipt.json")).read_text())
    assert digest(source) == receipt["sha256"]
    reader = pa.ipc.open_file(pa.memory_map(str(source)))
    rows = []
    offset = 0
    for i in range(reader.num_record_batches):
        b = reader.get_batch(i)
        pre, post = b["body_pre"].to_numpy(), b["body_post"].to_numpy()
        take = ((np.isin(pre, kcs) & (post == 10495)) |
                (np.isin(pre, dans) & (np.isin(post, kcs) | (post == 10495))))
        if take.any():
            t = pa.Table.from_batches([b]).filter(pa.array(take))
            t = t.append_column("source_partner_row", pa.array(np.flatnonzero(take) + offset))
            rows.extend(t.to_pylist())
        offset += len(b)
    assert offset == 124025046
    groups = {
        "KC_to_MBON05": [r for r in rows if r["body_post"] == 10495 and r["body_pre"] in kcs],
        "PAM08_to_KC": [r for r in rows if r["body_pre"] in dans and r["body_post"] in kcs],
        "PAM08_to_MBON05": [r for r in rows if r["body_pre"] in dans and r["body_post"] == 10495],
    }
    for name, expected in [("KC_to_MBON05", 16398), ("PAM08_to_KC", 10601), ("PAM08_to_MBON05", 918)]:
        assert len(groups[name]) == expected, (name, len(groups[name]))
    raw = json.loads((BASE / VOLUME / "info").read_text())
    props = json.loads((BASE / VOLUME / "segment_properties/info").read_text())["inline"]
    labels = {0: "<unspecified>", 2**64 - 1: "UNKNOWN_MISSING_CHUNK"}
    labels.update({int(k): v for k, v in zip(props["ids"], props["properties"][0]["values"])})
    scale = raw["scales"][0]
    assert scale["resolution"] == [256.0] * 3
    size = np.array(scale["size"])
    chunk = np.array(scale["chunk_sizes"][0])
    block = np.array(scale["compressed_segmentation_block_size"])
    coords = np.array([[r[f"{a}_{side}"] for a in "xyz"] for side in ("pre", "post") for r in rows])
    voxels = coords // 32
    assert ((voxels >= 0) & (voxels < size)).all()
    keys, inverse = np.unique(voxels // chunk, axis=0, return_inverse=True)
    mapped = np.full(len(coords), 2**64 - 1, dtype=np.uint64)
    missing = []
    used = []
    for i, key in enumerate(keys):
        start = key * chunk
        end = np.minimum(start + chunk, size)
        name = VOLUME + "/" + scale["key"] + "/" + "_".join(f"{a}-{b}" for a, b in zip(start, end))
        path = BASE / name
        ix = np.flatnonzero(inverse == i)
        if not path.exists():
            missing.append({"name": name, "endpoints": len(ix)})
            continue
        rec = json.loads(path.with_name(path.name + ".receipt.json").read_text())
        assert digest(path) == rec["sha256"]
        used.append({"name": name, "sha256": rec["sha256"]})
        data = path.read_bytes()
        if data[:2] == b"\x1f\x8b":
            import gzip
            data = gzip.decompress(data)
        mapped[ix] = sample_chunk(data, voxels[ix] - start, end - start, block)
    for i, row in enumerate(rows):
        row["roi_pre"] = labels[int(mapped[i])]
        row["roi_post"] = labels[int(mapped[i + len(rows)])]
    selected = {}
    summaries = {}
    for name, rs in groups.items():
        good = [r for r in rs if r["roi_pre"] == r["roi_post"] == "g4(L)"]
        selected[name] = good
        summaries[name] = {"all_contacts": len(rs), "both_g4_left_contacts": len(good),
                           "both_g4_left_pairs": len({(r["body_pre"], r["body_post"]) for r in good}),
                           "unknown_roi_contacts": sum("UNKNOWN_MISSING_CHUNK" in (r["roi_pre"], r["roi_post"]) for r in rs),
                           "joint_roi_counts": dict(Counter(r["roi_pre"] + " -> " + r["roi_post"] for r in rs))}
    active_kcs = {r["body_post"] for r in selected["PAM08_to_KC"]}
    candidate = [r for r in selected["KC_to_MBON05"] if r["body_pre"] in active_kcs]
    OUT.mkdir(parents=True, exist_ok=True)
    result = {"status": "complete_cache" if not missing else "partial_cache_missing_roi",
              "source_partner_sha256": receipt["sha256"], "rows_scanned": offset,
              "coordinate_conversion": "floor(source_xyz_8nm / 32)", "roi": VOLUME,
              "roi_chunks_used": used, "roi_chunks_missing": missing,
              "groups": summaries,
              "same_kc_screen": {"rule": "KC→MBON05 contact both endpoints g4(L) and same KC receives ≥1 PAM08→KC contact both endpoints g4(L)",
                                 "candidate_contacts": len(candidate),
                                 "candidate_pairs": len({(r["body_pre"], r["body_post"]) for r in candidate}),
                                 "candidate_kc_ids": sorted({r["body_pre"] for r in candidate}),
                                 "candidate_source_partner_rows": [r["source_partner_row"] for r in candidate]},
              "interpretation": "Anatomical candidacy only; no receptor, dopamine diffusion, efficacy or active runtime mask is inferred."}
    (OUT / "gamma4_contact_audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "groups": summaries, "missing_roi_chunks": len(missing),
                      "screen_contacts": len(candidate), "screen_pairs": result["same_kc_screen"]["candidate_pairs"]}, indent=2))


if __name__ == "__main__":
    main()
