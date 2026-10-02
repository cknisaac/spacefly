"""Independent B5.2 source-row, candidate-coverage and ROI-count audit."""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/figures/b5_2_visual_input_boundary"
EXTRACT = ROOT / "data/processed/malecns_v1_b5_2_visual_partner_contacts.parquet"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    protocol = ROOT / "configs/b5_2_visual_input_boundary_audit.json"
    ledger = json.loads((OUT / "parent_ledger.json").read_text())
    summary = json.loads((OUT / "summary.json").read_text())
    cohort = json.loads((OUT / "candidate_sets.json").read_text())
    roi = json.loads((OUT / "partner_roi_summary.json").read_text())
    assert ledger["protocol_sha256"] == summary["protocol_sha256"] == sha(protocol)
    assert summary["parent_ledger_sha256"] == cohort["source_ledger_sha256"] == sha(OUT / "parent_ledger.json")
    assert cohort["partner_roi_summary_sha256"] == sha(OUT / "partner_roi_summary.json")
    assert roi["extract_sha256"] == sha(EXTRACT)
    kc = set(ledger["selected_kc_ids"])
    assert len(kc) == 107
    rows = ledger["direct_parent_rows"]
    annotations = {n["source_id"]: n for n in ledger["parent_annotations"]}
    assert len(rows) == summary["all_direct_pairs"] == 19692
    assert sum(e["contacts"] for e in rows) == summary["all_direct_contacts"] == 60502
    assert {e["post_id"] for e in rows} == kc
    assert len({e["source_row"] for e in rows}) == len(rows)
    by_source = defaultdict(list)
    for edge in rows:
        by_source[edge["pre_id"]].append(edge)
    for sid, node in annotations.items():
        rr = by_source[sid]
        assert node["kc_pairs"] == len(rr)
        assert node["kc_contacts"] == sum(e["contacts"] for e in rr)
        assert node["kc_targets"] == sorted(e["post_id"] for e in rr)
    current = {e["post_id"] for e in rows if e["pre_id"] in {13285, 13707, 13874}}
    assert len(current) == 59 and sorted(kc-current) == summary["currently_unreached_KC_ids"]
    assert sum(e["contacts"] for e in rows if e["pre_id"] in {13285,13707,13874}) == 1427
    for label, group in cohort["cohorts"].items():
        ids = set(group["source_ids"])
        rr = [e for e in rows if e["pre_id"] in ids]
        targets = {e["post_id"] for e in rr}
        assert group["kc_pairs"] == len(rr)
        assert group["kc_contacts"] == sum(e["contacts"] for e in rr)
        assert group["direct_kc_ids"] == sorted(targets)
        assert group["new_vs_current_kc_ids"] == sorted(targets-current)
        assert group["union_with_current_kc_count"] == len(targets|current)
        if label == "aMe12_R":
            assert ids == {12740, 13190} and all(annotations[i]["cell_type"] == "aMe12" and annotations[i]["soma_side"] == "R" for i in ids)
        if label == "aMe12_all_traced":
            assert len(ids) == 6 and all(annotations[i]["cell_type"] == "aMe12" for i in ids)
    partner = pq.read_table(EXTRACT, columns=["body_pre", "body_post", "primary_post"]).to_pylist()
    assert len(partner) == roi["extracted_contact_count"] == 3183
    partner_counts = Counter((e["body_pre"],e["body_post"]) for e in partner)
    expected = {(e["pre_id"],e["post_id"]): e["contacts"] for e in rows if e["pre_id"] in roi["candidate_source_ids"]}
    assert dict(partner_counts) == expected
    by_id_roi = defaultdict(Counter)
    for e in partner:
        by_id_roi[e["body_pre"]][e["primary_post"]] += 1
    assert {str(k): dict(v) for k,v in by_id_roi.items()} == roi["id_primary_post"]
    audit = {"status": "pass", "protocol_sha256": sha(protocol),
             "parent_ledger_sha256": sha(OUT / "parent_ledger.json"),
             "summary_sha256": sha(OUT / "summary.json"),
             "candidate_sets_sha256": sha(OUT / "candidate_sets.json"),
             "partner_roi_summary_sha256": sha(OUT / "partner_roi_summary.json"),
             "direct_parent_pairs_checked": len(rows), "source_contacts_checked": sum(e["contacts"] for e in rows),
             "source_partner_contacts_checked": len(partner), "candidate_groups_checked": len(cohort["cohorts"])}
    (OUT / "audit.json").write_text(json.dumps(audit, sort_keys=True, indent=2) + "\n")
    print(audit)


if __name__ == "__main__":
    main()
