"""Check source synapse-region labels for literature-named visual KC parents."""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/raw/malecns_v1/syn-partners-male-cns-v1.0-minconf-0.5-traced-only.feather"
OUT = ROOT / "docs/figures/b5_2_visual_input_boundary"
EXTRACT = ROOT / "data/processed/malecns_v1_b5_2_visual_partner_contacts.parquet"
TYPES = {"aMe12", "aMe20", "aMe26", "PLP095", "MeVP41", "LoVP97", "LoVP42"}


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main():
    ledger = json.loads((OUT / "parent_ledger.json").read_text())
    parents = {p["source_id"]: p for p in ledger["parent_annotations"]}
    ids = sorted(sid for sid, p in parents.items() if p["cell_type"] in TYPES)
    kcs = set(ledger["selected_kc_ids"])
    expected = {(e["pre_id"], e["post_id"]): e["contacts"]
                for e in ledger["direct_parent_rows"] if e["pre_id"] in ids}
    receipt = json.loads(SOURCE.with_name(SOURCE.name + ".receipt.json").read_text())
    assert SOURCE.stat().st_size == receipt["bytes"]
    assert sha(SOURCE) == receipt["sha256"]
    reader = pa.ipc.open_file(pa.memory_map(str(SOURCE)))
    selected = []
    offset = 0
    for i in range(reader.num_record_batches):
        batch = reader.get_batch(i)
        pre = batch["body_pre"].to_numpy()
        post = batch["body_post"].to_numpy()
        keep = np.isin(pre, ids) & np.isin(post, list(kcs))
        if keep.any():
            part = pa.Table.from_batches([batch]).filter(pa.array(keep))
            part = part.append_column("source_partner_row", pa.array(np.flatnonzero(keep) + offset))
            selected.append(part)
        offset += len(batch)
    assert offset == 124025046
    table = pa.concat_tables(selected)
    counts = Counter((r["body_pre"], r["body_post"]) for r in table.select(["body_pre", "body_post"]).to_pylist())
    assert dict(counts) == expected
    EXTRACT.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, EXTRACT, compression="zstd")
    rows = table.select(["body_pre", "body_post", "primary_post"]).to_pylist()
    by_type = defaultdict(list)
    by_id = defaultdict(list)
    for r in rows:
        sid = r["body_pre"]
        by_type[parents[sid]["cell_type"]].append(r["primary_post"])
        by_id[sid].append(r["primary_post"])
    summary = {
        "source_sha256": receipt["sha256"],
        "parent_ledger_sha256": sha(OUT / "parent_ledger.json"),
        "source_partner_rows_scanned": offset,
        "candidate_source_ids": ids,
        "candidate_types": sorted(TYPES),
        "extracted_contact_count": len(rows),
        "extract_sha256": sha(EXTRACT),
        "type_primary_post": {t: dict(Counter(v)) for t, v in by_type.items()},
        "id_primary_post": {str(sid): dict(Counter(v)) for sid, v in by_id.items()},
    }
    (OUT / "partner_roi_summary.json").write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n")
    print("scanned", offset, "extracted", len(rows), "type ROIs", summary["type_primary_post"], flush=True)


if __name__ == "__main__":
    main()
