"""Independent exact endpoint/count/provenance audit of scale samples."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/processed/malecns_v1_traced"
OUTPUT = ROOT / "runs/malecns_v1_scale"
STAGES = ("n100", "n1000", "n10000", "mb_subcircuit", "larger_network")


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    receipt = json.loads((SOURCE / "validation_receipt.json").read_text(encoding="utf-8"))
    assert receipt["dataset"] == "MaleCNS" and receipt["release"] == "v1.0"
    for name in ("neurons.parquet", "connections.parquet"):
        assert sha(SOURCE / name) == receipt["files"][name]["sha256"]
    parent_nodes = pq.read_table(SOURCE / "neurons.parquet", columns=["source_id"])["source_id"].to_numpy()
    parent_edges = pq.read_table(SOURCE / "connections.parquet")
    source_rows = parent_edges["source_row"].to_numpy()
    assert np.array_equal(np.sort(source_rows), np.arange(len(source_rows)))
    pre = parent_edges["pre_index"].to_numpy()
    post = parent_edges["post_index"].to_numpy()
    count = parent_edges["synapse_count"].to_numpy()
    row_lookup = np.empty(len(source_rows), dtype=np.int32)
    row_lookup[source_rows] = np.arange(len(source_rows), dtype=np.int32)
    previous = set()
    result = {}
    for stage in STAGES:
        path = OUTPUT / stage
        manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
        for name in ("neurons.parquet", "connections.parquet"):
            assert sha(path / name) == manifest["sample_sha256"][name]
        nodes = pq.read_table(path / "neurons.parquet")
        edges = pq.read_table(path / "connections.parquet")
        parent_index = nodes["runtime_index"].to_numpy()
        local = nodes["local_index"].to_numpy()
        ids = nodes["source_id"].to_numpy()
        assert np.array_equal(local, np.arange(len(local)))
        assert np.array_equal(ids, parent_nodes[parent_index])
        assert hashlib.sha256(ids.tobytes()).hexdigest() == manifest["source_id_sha256"]
        assert previous.issubset(set(map(int, parent_index)))
        previous = set(map(int, parent_index))
        source_row = edges["parent_source_row"].to_numpy()
        edge_pos = row_lookup[source_row]
        edge_pre = edges["pre_local"].to_numpy()
        edge_post = edges["post_local"].to_numpy()
        edge_count = edges["synapse_count"].to_numpy()
        assert np.array_equal(parent_index[edge_pre], pre[edge_pos])
        assert np.array_equal(parent_index[edge_post], post[edge_pos])
        assert np.array_equal(edge_count, count[edge_pos])
        inside = np.zeros(len(parent_nodes), dtype=bool)
        inside[parent_index] = True
        expected = inside[pre] & inside[post]
        assert len(source_row) == int(expected.sum())
        assert np.array_equal(np.sort(source_row), np.sort(source_rows[expected]))
        assert int(edge_count.sum()) == manifest["internal_synapse_count"]
        result[stage] = {"neurons": len(parent_index), "pairs": len(source_row),
                         "exact_rows_verified": True, "nested": True}
        print(stage, result[stage], flush=True)
    (OUTPUT / "audit.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
