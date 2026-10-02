"""Materialize the frozen V1.1 two-cell visual-boundary hypothesis; no simulation."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from project_b.electrical_v1 import build_circuit
from project_b.electrical_v1.source import ADDED_VISUAL_IDS, V1_CONFIG_SHA, file_sha


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/processed/malecns_v1_electrical_v1_1"
CONFIG = ROOT / "configs/electrical_model_v1_1.json"
V1_OUT = ROOT / "data/processed/malecns_v1_electrical_v1"


def row(circuit, edge):
    return {"source_row": edge.source_row,
            "pre_source_id": circuit.cells[edge.pre].source_id,
            "post_source_id": circuit.cells[edge.post].source_id,
            "pre_local_index": edge.pre, "post_local_index": edge.post,
            "source_contacts": edge.contacts, "effect_state": edge.effect_state,
            "effect_evidence": edge.effect_evidence, "model_weight_pa": edge.weight_pa,
            "candidate_contacts": edge.candidate_contacts,
            "remaining_fixed_contacts": edge.contacts - edge.candidate_contacts}


def main() -> None:
    old = build_circuit()
    new = build_circuit(CONFIG)
    if old.config_sha256 != V1_CONFIG_SHA:
        raise AssertionError("Frozen V1 hash changed")
    old_by_row = {e.source_row: row(old, e) for e in old.connections}
    new_by_row = {e.source_row: row(new, e) for e in new.connections}
    if not set(old_by_row) <= set(new_by_row):
        raise AssertionError("V1 source rows removed")
    for source_row, before in old_by_row.items():
        after = new_by_row[source_row]
        for field in ("pre_source_id", "post_source_id", "source_contacts", "effect_state",
                      "effect_evidence", "model_weight_pa", "candidate_contacts",
                      "remaining_fixed_contacts"):
            if before[field] != after[field]:
                raise AssertionError(f"Old effect changed: row {source_row}/{field}")
    added = [new_by_row[i] for i in sorted(set(new_by_row) - set(old_by_row))]
    if len(added) != 62 or sum(x["source_contacts"] for x in added) != 603:
        raise AssertionError("Induced source-row addition differs from 117-body audit")
    if any(x["pre_source_id"] not in ADDED_VISUAL_IDS and
           x["post_source_id"] not in ADDED_VISUAL_IDS for x in added):
        raise AssertionError("New topology outside two added visual bodies")
    active = [x for x in added if x["effect_state"] == "ACTIVE_FAST"]
    if (len(active), sum(x["source_contacts"] for x in active)) != (48, 569):
        raise AssertionError("Added aMe12→KC fast block differs from B5.2")
    if any(x["pre_source_id"] not in ADDED_VISUAL_IDS or
           next(c.kind for c in new.cells if c.source_id == x["post_source_id"]) != "KC" or
           x["effect_evidence"] != "INFERRED" or
           x["model_weight_pa"] != .03*x["source_contacts"] for x in active):
        raise AssertionError("Unexpected added fast effect")
    inactive = [x for x in added if x["effect_state"] == "UNKNOWN"]
    if len(inactive) != 14 or sum(x["source_contacts"] for x in inactive) != 34 or any(
            x["model_weight_pa"] is not None for x in inactive):
        raise AssertionError("Unexpected added non-KC effect")
    kcs = {x.source_id for x in old.cells if x.kind == "KC"}
    old_targets = {x["post_source_id"] for x in old_by_row.values() if
                   x["pre_source_id"] in {13285, 13707, 13874} and x["post_source_id"] in kcs}
    new_targets = {x["post_source_id"] for x in active}
    if (len(old_targets), len(new_targets), len(new_targets - old_targets),
            len(old_targets | new_targets)) != (59, 37, 20, 79):
        raise AssertionError("Visual KC coverage differs from B5.2")
    OUT.mkdir(parents=True, exist_ok=True)
    nodes = [{"local_index": i, "source_id": cell.source_id, "kind": cell.kind,
              "source_runtime_index": cell.source_runtime_index,
              "transmitter_consensus": cell.transmitter} for i, cell in enumerate(new.cells)]
    pq.write_table(pa.Table.from_pylist(nodes), OUT / "neurons.parquet", compression="zstd")
    pq.write_table(pa.Table.from_pylist([row(new, e) for e in new.connections]),
                   OUT / "connections.parquet", compression="zstd")
    pq.write_table(pa.Table.from_pylist([{"source_partner_row": i} for i in new.candidate_partner_rows]),
                   OUT / "plastic_contact_mask_anatomy_only.parquet", compression="zstd")
    names = ("neurons.parquet", "connections.parquet", "plastic_contact_mask_anatomy_only.parquet")
    old_artifact_hashes = {name: file_sha(V1_OUT / name) for name in names}
    old_manifest = json.loads((V1_OUT / "manifest.json").read_text(encoding="utf-8"))
    if old_artifact_hashes != old_manifest["artifact_sha256"]:
        raise AssertionError("V1 artifacts changed")
    manifest = {"schema_version": 2, "model_id": new.config["model_id"],
                "anatomy_status": "pinned source immutable; all 117-body induced rows retained",
                "config_sha256": new.config_sha256, "v1_config_sha256": old.config_sha256,
                "source_id_sha256": new.config["source_id_sha256"],
                "parent_sha256": new.parent_hashes,
                "candidate_source_sha256": new.config["plastic_candidates_sha256"],
                "unknown_edge_policy": new.config["unknown_edge_policy"],
                "plasticity_enabled": False,
                "added_source_ids": list(ADDED_VISUAL_IDS),
                "added_source_rows": [x["source_row"] for x in added],
                "added_pairs": len(added), "added_contacts": sum(x["source_contacts"] for x in added),
                "added_effect_pairs": dict(Counter(x["effect_state"] for x in added)),
                "added_visual_to_KC_pairs": len(active),
                "added_visual_to_KC_contacts": sum(x["source_contacts"] for x in active),
                "newly_contacted_KC_ids": sorted(new_targets - old_targets),
                "visual_KC_coverage_v1": len(old_targets),
                "visual_KC_coverage_v1_1": len(old_targets | new_targets),
                "visual_boundary_hypothesis": new.config["visual_boundary_hypothesis"],
                "v1_artifact_sha256": old_artifact_hashes,
                "artifact_sha256": {name: file_sha(OUT / name) for name in names},
                **new.counts()}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    print(json.dumps({key: manifest[key] for key in
                      ("neurons", "source_pairs", "source_contacts", "added_pairs", "added_contacts",
                       "added_visual_to_KC_pairs", "added_visual_to_KC_contacts",
                       "visual_KC_coverage_v1_1")}, sort_keys=True))


if __name__ == "__main__":
    main()
