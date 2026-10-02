"""Independently compare every normalized BANC row with its immutable source row."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pyarrow.feather as feather
import pyarrow.parquet as parquet

from project_b.connectome.importer import EDGES, META, _source_manifest, ids


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate(source: Path, output: Path) -> dict:
    _source_manifest(source)
    report = json.loads((output / "import_report.json").read_text(encoding="utf-8"))
    raw_nodes = feather.read_table(source / META, columns=["banc_888_id"], memory_map=True)
    raw_edges = feather.read_table(source / EDGES, columns=["pre", "post", "count"], memory_map=True)
    nodes = parquet.read_table(output / "neurons.parquet", columns=["runtime_index", "source_id"])
    source_ids = nodes["source_id"].to_numpy()
    runtime = nodes["runtime_index"].to_numpy()
    require(np.array_equal(runtime, np.arange(len(runtime), dtype=np.uint32)), "Runtime indices are not contiguous")
    require(np.array_equal(source_ids, np.sort(ids(raw_nodes["banc_888_id"].combine_chunks()))), "Neuron source IDs differ")
    require(report["statistics"]["source_nodes"] == len(runtime), "Source-node count differs from report")
    reader = parquet.ParquetFile(output / "connections.parquet")
    require(reader.metadata.num_rows == raw_edges.num_rows == report["statistics"]["connections"], "Connection row counts differ")
    offset = 0
    synapses = 0
    for batch in reader.iter_batches(batch_size=131072):
        length = batch.num_rows
        normalized_row = batch.column(0).to_numpy()
        pre_idx = batch.column(1).to_numpy()
        post_idx = batch.column(2).to_numpy()
        counts = batch.column(3).to_numpy()
        require(np.array_equal(normalized_row, np.arange(offset, offset + length, dtype=np.uint32)), f"Source row sequence differs at {offset}")
        require(bool(np.all(pre_idx < len(source_ids)) and np.all(post_idx < len(source_ids))), f"Out-of-range endpoint at {offset}")
        original = raw_edges.slice(offset, length)
        require(np.array_equal(source_ids[pre_idx], ids(original["pre"].combine_chunks())), f"Presynaptic ID differs at {offset}")
        require(np.array_equal(source_ids[post_idx], ids(original["post"].combine_chunks())), f"Postsynaptic ID differs at {offset}")
        require(np.array_equal(counts, original["count"].to_numpy()), f"Synapse count differs at {offset}")
        synapses += int(np.sum(counts, dtype=np.int64))
        offset += length
    require(offset == reader.metadata.num_rows, "Connection scan ended early")
    require(synapses == report["statistics"]["synapse_count_sum_in_edge_product"], "Synapse-count sum differs")
    receipt = {
        "schema_version": report["schema_version"],
        "all_neuron_source_ids_compared": len(runtime),
        "all_connection_source_rows_compared": offset,
        "all_connection_counts_compared": offset,
        "synapse_count_sum": synapses,
        "files": {
            name: {"bytes": (output / name).stat().st_size, "sha256": sha256(output / name)}
            for name in ("neurons.parquet", "connections.parquet", "import_report.json")
        },
    }
    (output / "validation_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("data/raw/banc_v888"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/banc_v888_v2"))
    args = parser.parse_args()
    receipt = validate(args.source, args.output)
    print(f"Compared all {receipt['all_neuron_source_ids_compared']:,} neuron IDs and {receipt['all_connection_source_rows_compared']:,} connections to source")


if __name__ == "__main__":
    main()
