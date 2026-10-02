"""Read-only anatomical evidence for candidate Circuit V1 route revisions.

Streams parent edges; no electrical parameters, topology edits or neural runs.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.feather as feather
import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT / "data/processed/malecns_v1_traced"
RAW = ROOT / "data/raw/malecns_v1"
OUT = ROOT / "docs/figures/circuit_v1_critical_route_anatomy.json"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    table = pq.read_table(PARENT / "neurons.parquet")
    nodes = table.to_pylist()
    ids = table["source_id"].to_numpy()
    node_by_id = {n["source_id"]: n for n in nodes}
    kc_ids = {n["source_id"] for n in nodes
              if n["cell_type"] == "KCg-d" and n["soma_side"] == "R"}
    focal_ids = {10013, 10540, 11176, 11327, 11402, 13285, 13707, 13874,
                 515034, 519131, 519624, 523769, 14182, 519368, 521086,
                 10360, 10975, 11455, 10971, 11233, 14986, 519129,
                 12910, 14192, 14830, 18956}
    pam_ids = {n["source_id"] for n in nodes if n["instance"] == "PAM01(y5)_R"}
    selected = kc_ids | focal_ids | pam_ids
    assert len(kc_ids) == 107 and len(pam_ids) == 21
    assert selected <= node_by_id.keys()
    proposal_roles = {
        "candidate_visual_input": {13285, 13707, 13874},
        "KCg-d_R": kc_ids, "APL_R": {10540}, "PPL103_R": {14182},
        "MBON32_R": {519131}, "DNa03_L": {519624}, "DNa02_L": {523769},
    }
    proposal = set().union(*proposal_roles.values())
    assert len(proposal) == 115 and proposal <= selected
    proposal_mask = np.array([i in proposal for i in ids], dtype=bool)
    proposal_in = np.zeros(len(ids), dtype=np.int64)
    proposal_out = np.zeros(len(ids), dtype=np.int64)
    proposal_totals = {k: {"pairs": 0, "contacts": 0}
                       for k in ("internal", "incoming_cut", "outgoing_cut")}
    selected_mask = np.array([i in selected for i in ids], dtype=bool)
    kc_mask = np.array([i in kc_ids for i in ids], dtype=bool)
    edges = []
    incoming = np.zeros(len(ids), dtype=np.int64)
    outgoing = np.zeros(len(ids), dtype=np.int64)
    retained_incoming = np.zeros(len(ids), dtype=np.int64)
    retained_outgoing = np.zeros(len(ids), dtype=np.int64)
    internal_pairs = internal_contacts = 0
    for batch in pq.ParquetFile(PARENT / "connections.parquet").iter_batches(
            batch_size=500_000,
            columns=["pre_index", "post_index", "synapse_count", "source_row"]):
        pre = batch["pre_index"].to_numpy()
        post = batch["post_index"].to_numpy()
        count = batch["synapse_count"].to_numpy()
        source_row = batch["source_row"].to_numpy()
        ppre, ppost = proposal_mask[pre], proposal_mask[post]
        pboth = ppre & ppost
        for name, mask in (("internal", pboth), ("incoming_cut", ~ppre & ppost),
                           ("outgoing_cut", ppre & ~ppost)):
            proposal_totals[name]["pairs"] += int(mask.sum())
            proposal_totals[name]["contacts"] += int(count[mask].sum(dtype=np.int64))
        np.add.at(proposal_in, post[pboth], count[pboth])
        np.add.at(proposal_out, pre[pboth], count[pboth])
        both = selected_mask[pre] & selected_mask[post]
        internal_pairs += int(both.sum())
        internal_contacts += int(count[both].sum(dtype=np.int64))
        for target, endpoint, mask in (
                (incoming, post, selected_mask[post]),
                (outgoing, pre, selected_mask[pre]),
                (retained_incoming, post, both),
                (retained_outgoing, pre, both)):
            np.add.at(target, endpoint[mask], count[mask])
        # Preserve every comparison edge except the unchanged KC recurrent block.
        keep = both & (~(kc_mask[pre] & kc_mask[post]))
        for row in np.flatnonzero(keep):
            edges.append({"pre": int(ids[pre[row]]), "post": int(ids[post[row]]),
                          "contacts": int(count[row]), "source_row": int(source_row[row])})
    edges.sort(key=lambda e: (e["pre"], e["post"]))
    assert len({(e["pre"], e["post"]) for e in edges}) == len(edges)
    proposal_edges = [e for e in edges if e["pre"] in proposal and e["post"] in proposal]
    expected_parent_hashes = {
        "neurons.parquet": "7d9a410d61d4caa934fa3639f9d204291ff0d18c445b2384054b95286d6350eb",
        "connections.parquet": "da21af867d4e8e4c627c9916e55af4332302b611a296de1d0a8bc7dd6ebcff7a",
    }
    for name, expected in expected_parent_hashes.items():
        assert sha(PARENT / name) == expected, f"Parent drift: {name}"

    annotation_file = RAW / "body-annotations-male-cns-v1.0-minconf-0.5.feather"
    annotation = feather.read_table(annotation_file, memory_map=True)
    receptor_values = Counter(v for v in annotation["receptorType"].to_pylist() if v is not None)
    a = annotation.filter(pc.is_in(annotation["bodyId"], pa.array(sorted(selected))))
    a = a.select(["bodyId", "type", "instance", "superclass", "class", "somaSide",
                  "hemibrainType", "flywireType", "matchingNotes", "receptorType"])
    nt_file = RAW / "body-neurotransmitters-male-cns-v1.0.feather"
    nt = feather.read_table(nt_file, memory_map=True)
    nt = nt.filter(pc.is_in(nt["body"], pa.array(sorted(selected))))
    stats_map = pa.memory_map(str(RAW / "body-stats-male-cns-v1.0-minconf-0.5.feather"))
    stats_schema = str(pa.ipc.open_file(stats_map).schema)
    report = {
        "dataset": "MaleCNS v1.0 traced parent",
        "purpose": "candidate comparison only; this union is not a new selected circuit",
        "sha256": {str(p.relative_to(ROOT)): sha(p) for p in
                   (PARENT / "neurons.parquet", PARENT / "connections.parquet",
                    annotation_file, nt_file)},
        "kc_ids": sorted(kc_ids), "pam_ids": sorted(pam_ids), "focal_ids": sorted(focal_ids),
        "comparison_union_pairs": internal_pairs,
        "comparison_union_contacts": internal_contacts,
        "proposed_115_anatomy_only": {
            "status": "evidence proposal only; no selected-product or policy replacement",
            "ids": sorted(proposal),
            "id_hash_le_int64": hashlib.sha256(np.array(sorted(proposal), dtype="<i8").tobytes()).hexdigest(),
            "roles": {k: sorted(v) for k, v in proposal_roles.items()},
            "totals": proposal_totals,
            "boundary_by_role": {
                role: {
                    "all_in_contacts": sum(int(incoming[node_by_id[i]["runtime_index"]]) for i in members),
                    "retained_in_contacts": sum(int(proposal_in[node_by_id[i]["runtime_index"]]) for i in members),
                    "all_out_contacts": sum(int(outgoing[node_by_id[i]["runtime_index"]]) for i in members),
                    "retained_out_contacts": sum(int(proposal_out[node_by_id[i]["runtime_index"]]) for i in members),
                } for role, members in proposal_roles.items()
            },
            "block_totals": {
                f"{a}->{b}": {
                    "pairs": sum(e["pre"] in pre_ids and e["post"] in post_ids for e in proposal_edges),
                    "contacts": sum(e["contacts"] for e in proposal_edges if e["pre"] in pre_ids and e["post"] in post_ids),
                }
                for a, pre_ids in proposal_roles.items() for b, post_ids in proposal_roles.items()
                if not (a == b == "KCg-d_R")
            },
        },
        "focal_non_kc_recurrent_edges": edges,
        "source_annotations": a.to_pylist(), "source_transmitter_fields": nt.to_pylist(),
        "receptor_type_nonnull_values_whole_source": dict(receptor_values),
        "body_stats_schema": stats_schema,
        "comparison_union_boundary_by_id": {
            str(i): {"all_in_contacts": int(incoming[node_by_id[i]["runtime_index"]]),
                     "all_out_contacts": int(outgoing[node_by_id[i]["runtime_index"]]),
                     "union_in_contacts": int(retained_incoming[node_by_id[i]["runtime_index"]]),
                     "union_out_contacts": int(retained_outgoing[node_by_id[i]["runtime_index"]])}
            for i in sorted(selected)},
    }
    OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Saved {len(edges)} focal source edges; {len(selected)} comparison bodies; no simulation")


if __name__ == "__main__":
    main()
