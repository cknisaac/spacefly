"""Pinned MaleCNS MVP-C1 source graph and B2.1 active-effect overlay."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

from project_b.connectome.runtime_graph import ArraySparseGraph


@dataclass(frozen=True, slots=True)
class MvpCircuit:
    source_ids: tuple[int, ...]          # 717 spiking cells; APL is separate
    graph: ArraySparseGraph             # declared chemical active classes only
    kc_ids: tuple[int, ...]
    pam_ids: tuple[int, ...]
    apl_input_by_kc: dict[int, tuple[int, int]]  # source KC -> (row, contacts)
    apl_target_indices: tuple[int, ...]
    all_induced_pairs: int
    all_induced_contacts: int
    category_counts: dict[str, tuple[int, int]]
    resolved_sha256: str


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _classify(pre: int, post: int, kc: set[int], pam: set[int]) -> str:
    if pre in kc:
        if post in kc:
            return "KC_to_KC"
        if post == 10495:
            return "KC_to_MBON05"
        if post == 11145:
            return "KC_to_MBON20"
        if post == 10977:
            return "KC_to_APL_graded_input"
    if pre == 10977:
        return "APL_to_measured_targets_graded_output"
    if pre in pam:
        return "PAM08_modulatory_anatomy"
    if (pre, post) == (10495, 11145):
        return "MBON05_to_MBON20"
    if (pre, post) == (11145, 10713):
        return "MBON20_to_DNp42"
    return "UNKNOWN_QUARANTINED_NO_CURRENT"


def load_mvp_circuit(root: Path) -> MvpCircuit:
    root = Path(root)
    resolved_path = root / "configs/b2_1_candidate1_resolved.json"
    resolved = json.loads(resolved_path.read_text(encoding="utf-8"))
    if resolved["candidate_id"] != "MVP-C1":
        raise ValueError("wrong candidate")
    b1 = json.loads((root / "docs/figures/b1_mvp_pathway_rule_selection/selected_anatomy.json")
                    .read_text(encoding="utf-8"))
    roster = {int(row["source_id"]) for row in b1["roster"]}
    kc = {int(x) for x in b1["kc_source_ids"]}
    pam = {int(x) for x in b1["dan_source_ids"]}
    if len(roster) != 718 or len(kc) != 689 or len(pam) != 25 or 10977 not in roster:
        raise ValueError("B1 roster differs from B2.1")
    ids = tuple(sorted(roster - {10977}))
    local = {source: i for i, source in enumerate(ids)}
    nodes_path = root / "data/processed/malecns_v1_traced/neurons.parquet"
    edges_path = root / "data/processed/malecns_v1_traced/connections.parquet"
    expected = resolved["identity"]
    if (_sha(nodes_path) != expected["source_neurons_sha256"]
            or _sha(edges_path) != expected["source_connections_sha256"]):
        raise ValueError("MaleCNS aggregate source checksum differs")
    source_ids = pq.read_table(nodes_path, columns=["source_id"])["source_id"].to_numpy()
    source_to_parent = {int(source_ids[i]): i for i in np.flatnonzero(np.isin(source_ids, list(roster)))}
    parent_indices = set(source_to_parent.values())
    parent_array = np.asarray(sorted(parent_indices), dtype=np.int64)
    if len(parent_indices) != 718:
        raise ValueError("source roster is incomplete")
    category_counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    records: list[tuple[int, int, int, int, str]] = []
    for batch in pq.ParquetFile(edges_path).iter_batches(
            columns=["source_row", "pre_index", "post_index", "synapse_count"],
            batch_size=500_000):
        rows = batch["source_row"].to_numpy()
        pre = batch["pre_index"].to_numpy()
        post = batch["post_index"].to_numpy()
        contacts = batch["synapse_count"].to_numpy()
        inside = np.flatnonzero(np.isin(pre, parent_array) & np.isin(post, parent_array))
        for j in inside:
            a, b, n = int(source_ids[pre[j]]), int(source_ids[post[j]]), int(contacts[j])
            kind = _classify(a, b, kc, pam)
            category_counts[kind][0] += 1
            category_counts[kind][1] += n
            records.append((a, b, n, int(rows[j]), kind))
    coverage = resolved["source_graph_coverage"]
    if (len(records) != coverage["induced_pairs"]
            or sum(r[2] for r in records) != coverage["induced_contacts"]
            or {k: {"pairs": v[0], "contacts": v[1]} for k, v in category_counts.items()}
            != coverage["categories"]):
        raise ValueError("source graph class coverage differs from B2.1")

    gains = resolved["B2_base_design"]["effective_weight_policy"]["class_gain"]
    denominator: dict[tuple[str, int], int] = defaultdict(int)
    for _, post, count, _, kind in records:
        if kind in ("KC_to_KC", "KC_to_MBON05", "KC_to_MBON20",
                    "MBON05_to_MBON20", "MBON20_to_DNp42"):
            denominator[kind, post] += count
    kind_gain = {"KC_to_KC": gains["kc_to_kc"],
                 "KC_to_MBON05": gains["kc_to_mbon05"],
                 "KC_to_MBON20": gains["kc_to_mbon20"],
                 "MBON05_to_MBON20": -gains["mbon05_to_mbon20"],
                 "MBON20_to_DNp42": -gains["mbon20_to_dnp42"]}
    chemical = [r for r in records if r[4] in kind_gain]
    graph = ArraySparseGraph(
        len(ids), np.asarray([local[r[0]] for r in chemical], dtype=np.int64),
        np.asarray([local[r[1]] for r in chemical], dtype=np.int64),
        np.asarray([kind_gain[r[4]] * r[2] / denominator[r[4], r[1]]
                    for r in chemical], dtype=np.float64),
        np.full(len(chemical), 2000, dtype=np.int64),
        np.asarray([r[3] for r in chemical], dtype=np.int64))
    apl_inputs = {a: (row, n) for a, b, n, row, kind in records
                  if kind == "KC_to_APL_graded_input"}
    apl_targets = tuple(sorted(local[b] for a, b, _, _, kind in records
                               if kind == "APL_to_measured_targets_graded_output"))
    if len(apl_inputs) != 689 or len(apl_targets) != 702:
        raise ValueError("APL graph coverage differs")
    return MvpCircuit(ids, graph, tuple(sorted(kc)), tuple(sorted(pam)),
                      apl_inputs, apl_targets, len(records),
                      sum(r[2] for r in records),
                      {k: tuple(v) for k, v in category_counts.items()},
                      _sha(resolved_path))
