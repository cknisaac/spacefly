"""Compare every normalized MaleCNS traced-neuron edge with its source row."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.feather as feather
import pyarrow.parquet as parquet

from project_b.connectome.malecns import ANNOTATIONS, TRACED_EDGES, verify_source


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
    verify_source(source)
    report = json.loads((output / "import_report.json").read_text(encoding="utf-8"))
    raw_annotations = feather.read_table(source / ANNOTATIONS, columns=["bodyId", "status"], memory_map=True)
    traced_ids = np.sort(raw_annotations["bodyId"].to_numpy()[np.array([x == "Traced" for x in raw_annotations["status"].to_pylist()])])
    nodes = parquet.read_table(output / "neurons.parquet", columns=["runtime_index", "source_id", "status"])
    source_ids = nodes["source_id"].to_numpy()
    runtime = nodes["runtime_index"].to_numpy()
    require(np.array_equal(runtime, np.arange(len(runtime), dtype=np.uint32)), "Noncontiguous runtime indices")
    require(np.array_equal(source_ids, traced_ids), "Traced source IDs differ")
    require(all(value == "Traced" for value in nodes["status"].to_pylist()), "Non-traced node entered internal graph")
    require(len(source_ids) == report["statistics"]["traced_neurons"], "Traced node count differs")

    with pa.memory_map(str(source / TRACED_EDGES)) as mapped:
        original = pa.ipc.open_file(mapped)
        result = parquet.ParquetFile(output / "connections.parquet")
        require(result.metadata.num_rows == report["statistics"]["traced_graph_connections"], "Connection count differs")
        require(original.num_record_batches == result.metadata.num_row_groups, "Row-group/source-batch count differs")
        offset = 0
        count_sum = 0
        for i in range(original.num_record_batches):
            source_batch = original.get_batch(i)
            derived = result.read_row_group(i)
            length = source_batch.num_rows
            require(derived.num_rows == length, f"Row-group size differs at {i}")
            source_row = derived["source_row"].to_numpy()
            pre_idx = derived["pre_index"].to_numpy()
            post_idx = derived["post_index"].to_numpy()
            count = derived["synapse_count"].to_numpy()
            require(np.array_equal(source_row, np.arange(offset, offset + length, dtype=np.uint32)), f"Source-row sequence differs at {i}")
            require(bool(np.all(pre_idx < len(source_ids)) and np.all(post_idx < len(source_ids))), f"Out-of-range endpoint at {i}")
            require(np.array_equal(source_ids[pre_idx], source_batch.column(0).to_numpy()), f"Presynaptic ID differs at {i}")
            require(np.array_equal(source_ids[post_idx], source_batch.column(1).to_numpy()), f"Postsynaptic ID differs at {i}")
            require(np.array_equal(count, source_batch.column(2).to_numpy()), f"Synapse count differs at {i}")
            count_sum += int(count.sum(dtype=np.int64))
            offset += length
    require(count_sum == report["statistics"]["traced_graph_synapse_count_sum"], "Synapse-count sum differs")
    receipt = {
        "dataset": "MaleCNS", "release": "v1.0",
        "all_traced_neuron_ids_compared": len(source_ids),
        "all_traced_connection_rows_compared": offset,
        "synapse_count_sum": count_sum,
        "files": {
            name: {"bytes": (output / name).stat().st_size, "sha256": sha256(output / name)}
            for name in ("neurons.parquet", "connections.parquet", "import_report.json")
        },
    }
    (output / "validation_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("data/raw/malecns_v1"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/malecns_v1_traced"))
    args = parser.parse_args()
    result = validate(args.source, args.output)
    print(f"Matched all {result['all_traced_neuron_ids_compared']:,} traced IDs and {result['all_traced_connection_rows_compared']:,} edges to source")


if __name__ == "__main__":
    main()
