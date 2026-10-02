"""Evidence-class cohorts for B5.2; anatomy only, no electrical selection."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/figures/b5_2_visual_input_boundary"
CLASSES = ("aMe12", "aMe20", "aMe26", "PLP095")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    raw = json.loads((OUT / "parent_ledger.json").read_text())
    rois = json.loads((OUT / "partner_roi_summary.json").read_text())
    assert rois["parent_ledger_sha256"] == sha(OUT / "parent_ledger.json")
    nodes = raw["parent_annotations"]
    kcs = set(raw["selected_kc_ids"])
    current = {target for n in nodes if n["selected_visual"] for target in n["kc_targets"]}
    assert len(current) == 59
    cohorts = {}
    definitions = {
        "current_three": lambda n: n["selected_visual"],
        "aMe12_R": lambda n: n["cell_type"] == "aMe12" and n["soma_side"] == "R",
        "aMe12_all_traced": lambda n: n["cell_type"] == "aMe12",
        "aMe20_all_traced": lambda n: n["cell_type"] == "aMe20",
        "aMe26_all_traced": lambda n: n["cell_type"] == "aMe26",
        "PLP095_all_traced": lambda n: n["cell_type"] == "PLP095",
        "literature_named_aMe12_aMe20_aMe26": lambda n: n["cell_type"] in {"aMe12", "aMe20", "aMe26"},
    }
    for label, include in definitions.items():
        group = sorted((n for n in nodes if include(n)), key=lambda n: n["source_id"])
        targets = {sid for n in group for sid in n["kc_targets"]}
        assert targets <= kcs
        cohorts[label] = {
            "source_ids": [n["source_id"] for n in group],
            "cell_types": dict(Counter(n["cell_type"] for n in group)),
            "kc_pairs": sum(n["kc_pairs"] for n in group),
            "kc_contacts": sum(n["kc_contacts"] for n in group),
            "direct_kc_ids": sorted(targets), "direct_kc_count": len(targets),
            "new_vs_current_kc_ids": sorted(targets-current),
            "new_vs_current_kc_count": len(targets-current),
            "union_with_current_kc_count": len(targets|current),
            "still_unreached_with_current_ids": sorted(kcs-(targets|current)),
            "post_primary_region_counts": dict(sum((Counter(rois["id_primary_post"].get(str(n["source_id"]), {}))
                                                  for n in group), Counter())),
        }
    result = {"source_ledger_sha256": sha(OUT / "parent_ledger.json"),
              "partner_roi_summary_sha256": sha(OUT / "partner_roi_summary.json"),
              "selected_kc_count": len(kcs), "current_visual_kc_count": len(current),
              "cohorts": cohorts,
              "evidence_scope": "Cohorts use source cell_type/soma_side and literature-named classes; no electrical effect or stimulus tuning is inferred from counts."}
    (OUT / "candidate_sets.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    for name, row in cohorts.items():
        print(name, "cells", len(row["source_ids"]), "pairs", row["kc_pairs"],
              "contacts", row["kc_contacts"], "new", row["new_vs_current_kc_count"],
              "union", row["union_with_current_kc_count"])


if __name__ == "__main__":
    main()
