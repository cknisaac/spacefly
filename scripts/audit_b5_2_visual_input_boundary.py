"""Read-only MaleCNS v1.0 direct-parent ledger for 107 right KCg-d cells."""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT / "data/processed/malecns_v1_traced"
PROTOCOL = ROOT / "configs/b5_2_visual_input_boundary_audit.json"
OUT = ROOT / "docs/figures/b5_2_visual_input_boundary"
SELECTED = (13285, 13707, 13874)


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n", encoding="utf-8")


def main():
    protocol = json.loads(PROTOCOL.read_text())
    assert protocol["stage_id"] == "B5.2"
    receipt = json.loads((PARENT / "validation_receipt.json").read_text())
    assert receipt["dataset"] == "MaleCNS" and receipt["release"] == "v1.0"
    for name in ("neurons.parquet", "connections.parquet"):
        assert sha(PARENT / name) == receipt["files"][name]["sha256"]
    ncols = ("runtime_index", "source_id", "status", "superclass", "cell_class", "cell_subclass",
             "cell_type", "instance", "region", "soma_side", "transmitter_consensus")
    neurons = pq.read_table(PARENT / "neurons.parquet", columns=list(ncols)).to_pylist()
    by_index = {n["runtime_index"]: n for n in neurons}
    by_id = {n["source_id"]: n for n in neurons}
    kcs = {n["runtime_index"] for n in neurons if n["cell_type"] == "KCg-d" and n["soma_side"] == "R"}
    assert len(kcs) == 107
    kc_ids = {by_index[i]["source_id"] for i in kcs}
    assert all(s in by_id for s in SELECTED)
    ledger = []
    scanned_rows = 0
    for batch in pq.ParquetFile(PARENT / "connections.parquet").iter_batches(
            batch_size=1_000_000, columns=["source_row", "pre_index", "post_index", "synapse_count"]):
        rows, pre, post, contacts = [batch.column(i).to_numpy() for i in range(4)]
        mask = np.isin(post, list(kcs))
        for row, p, q, n in zip(rows[mask], pre[mask], post[mask], contacts[mask]):
            node = by_index[int(p)]
            target = by_index[int(q)]
            ledger.append({"source_row": int(row), "pre_id": int(node["source_id"]),
                           "post_id": int(target["source_id"]), "contacts": int(n)})
        scanned_rows += len(rows)
    assert scanned_rows == receipt["all_traced_connection_rows_compared"]
    ledger.sort(key=lambda e: e["source_row"])
    assert len({e["source_row"] for e in ledger}) == len(ledger)
    pre_ids = sorted({e["pre_id"] for e in ledger})
    parents = [{k: by_id[sid].get(k) for k in ncols if k != "runtime_index"} for sid in pre_ids]
    by_parent = defaultdict(list)
    for e in ledger:
        by_parent[e["pre_id"]].append(e)
    parent_summary = []
    for n in parents:
        sid = n["source_id"]
        edges = by_parent[sid]
        parent_summary.append({**n, "kc_pairs": len(edges),
                               "kc_contacts": sum(e["contacts"] for e in edges),
                               "kc_targets": sorted(e["post_id"] for e in edges),
                               "selected_visual": sid in SELECTED,
                               "selected_KC": sid in kc_ids})
    selected_target_set = {e["post_id"] for e in ledger if e["pre_id"] in SELECTED}
    assert len(selected_target_set) == 59
    assert sum(e["contacts"] for e in ledger if e["pre_id"] in SELECTED) == 1427
    outside = {s for s in pre_ids if s not in kc_ids}
    all_outside_targets = {e["post_id"] for e in ledger if e["pre_id"] in outside}
    fields = ("superclass", "cell_class", "cell_subclass", "cell_type", "region", "transmitter_consensus")
    annotation_counts = {field: dict(Counter(str(n.get(field)) for n in parent_summary if not n["selected_KC"]))
                         for field in fields}
    top = sorted((n for n in parent_summary if not n["selected_KC"]),
                 key=lambda x: (-x["kc_contacts"], -x["kc_pairs"], x["source_id"]))
    OUT.mkdir(parents=True, exist_ok=True)
    ledger_payload = {"parent_validation_receipt_sha256": sha(PARENT / "validation_receipt.json"),
                      "parent_neurons_sha256": sha(PARENT / "neurons.parquet"),
                      "parent_connections_sha256": sha(PARENT / "connections.parquet"),
                      "protocol_sha256": sha(PROTOCOL), "scanned_connection_rows": scanned_rows,
                      "selected_kc_ids": sorted(kc_ids), "selected_visual_ids": list(SELECTED),
                      "direct_parent_rows": ledger, "parent_annotations": parent_summary}
    save(OUT / "parent_ledger.json", ledger_payload)
    summary = {"protocol_sha256": sha(PROTOCOL), "parent_ledger_sha256": sha(OUT / "parent_ledger.json"),
               "kc_count": len(kcs), "all_direct_parent_ids": len(pre_ids),
               "all_direct_pairs": len(ledger), "all_direct_contacts": sum(e["contacts"] for e in ledger),
               "outside_KC_parent_ids": len(outside), "outside_KC_target_count": len(all_outside_targets),
               "selected_visual_target_count": len(selected_target_set),
               "selected_visual_contact_count": 1427,
               "currently_unreached_KC_ids": sorted(kc_ids - selected_target_set),
               "annotation_counts_outside_KC": annotation_counts,
               "top_40_outside_KC_parents_by_contacts": top[:40]}
    save(OUT / "summary.json", summary)
    print("scan", scanned_rows, "parent_ids", len(pre_ids), "outside", len(outside),
          "pairs", len(ledger), "contacts", summary["all_direct_contacts"],
          "outside_targets", len(all_outside_targets), flush=True)
    for n in top[:25]:
        print(n["source_id"], n["cell_type"], n["cell_class"], n["cell_subclass"],
              n["region"], n["kc_pairs"], n["kc_contacts"],
              len(set(n["kc_targets"]) - selected_target_set), flush=True)


if __name__ == "__main__":
    main()
