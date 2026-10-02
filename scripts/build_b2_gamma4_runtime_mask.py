"""Resolve the pinned B2 contact IDs to KC pairs without changing source data."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pyarrow as pa


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "docs/figures/b2_candidate_design/gamma4_contact_audit.json"
SOURCE = ROOT / "data/raw/malecns_v1/syn-partners-male-cns-v1.0-minconf-0.5-traced-only.feather"
B1 = ROOT / "docs/figures/b1_mvp_pathway_rule_selection/selected_anatomy.json"
OUTPUT = ROOT / "configs/b2_candidate1_runtime_mask.json"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def build_mask() -> dict:
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    receipt = json.loads(SOURCE.with_name(SOURCE.name + ".receipt.json").read_text())
    if digest(SOURCE) != receipt["sha256"] != audit["source_partner_sha256"]:
        raise ValueError("MaleCNS partner source differs from pinned B2 audit")
    screen = audit["same_kc_screen"]
    selected_rows = np.asarray(screen["candidate_source_partner_rows"], dtype=np.int64)
    if (len(selected_rows) != 13957 or len(np.unique(selected_rows)) != len(selected_rows)
            or np.any(selected_rows < 0)):
        raise ValueError("B2 contact mask has invalid source rows")
    selected_rows.sort()
    by_kc: dict[int, list[int]] = defaultdict(list)
    reader = pa.ipc.open_file(pa.memory_map(str(SOURCE)))
    offset = 0
    for i in range(reader.num_record_batches):
        batch = reader.get_batch(i)
        lo = int(np.searchsorted(selected_rows, offset))
        hi = int(np.searchsorted(selected_rows, offset + len(batch)))
        if lo != hi:
            positions = selected_rows[lo:hi] - offset
            pre = batch["body_pre"].to_numpy()[positions]
            post = batch["body_post"].to_numpy()[positions]
            if np.any(post != 10495):
                raise ValueError("B2 plastic contact is outside MBON05")
            for row, kc in zip(selected_rows[lo:hi], pre):
                by_kc[int(kc)].append(int(row))
        offset += len(batch)
    if offset != audit["rows_scanned"] or sum(map(len, by_kc.values())) != 13957:
        raise ValueError("B2 source contact count drifted")
    if sorted(by_kc) != screen["candidate_kc_ids"] or len(by_kc) != 688:
        raise ValueError("B2 KC membership drifted")

    b1 = json.loads(B1.read_text(encoding="utf-8"))
    edges = b1["blocks"]["KCg-m_L_to_MBON05"]["edges"]
    all_counts = {int(edge["pre"]["source_id"]): int(edge["contacts"]) for edge in edges}
    if len(all_counts) != 689 or sum(all_counts.values()) != 16398:
        raise ValueError("Circuit V1 KC-to-MBON05 pair counts drifted")
    if any(len(rows) > all_counts[kc] for kc, rows in by_kc.items()):
        raise ValueError("Plastic contacts exceed source pair contact count")
    result = {
        "candidate_id": "MVP-C1", "compartment": "g4(L)",
        "source_partner_sha256": receipt["sha256"],
        "b2_audit_sha256": digest(AUDIT), "b1_anatomy_sha256": digest(B1),
        "mbon_source_id": 10495,
        "kc_pairs": [{"kc_source_id": kc, "total_contacts": all_counts[kc],
                      "plastic_contact_rows": by_kc.get(kc, [])}
                     for kc in sorted(all_counts)],
    }
    return result


if __name__ == "__main__":
    OUTPUT.write_text(json.dumps(build_mask(), separators=(",", ":")) + "\n", encoding="utf-8")
    print(OUTPUT)
