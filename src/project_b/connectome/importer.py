"""Validate BANC source products, then materialize a sparse, typed graph schema."""

from __future__ import annotations

import csv
import base64
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.feather as feather
import pyarrow.parquet as parquet


SCHEMA_VERSION = 1
META = "banc_888_meta.feather"
EDGES = "banc_888_edgelist_simple_v2.feather"
NT = "banc_888_neurotransmitter_prediction_v2.csv"
PINNED_OBJECTS = (
    (META, "1787336614757441", 57503026, "jCuTpgjHFj7J2U1o4HVv9A=="),
    (EDGES, "1780396134870867", 305250378, "OUQG+Km98JPIlfla/09sSQ=="),
    (NT, "1778713090033523", 21107592, "TrvR1uBdQZKtDG2ydzmo4w=="),
)
NEURON_FIELDS = (
    "region", "root_region", "side", "flow", "super_class", "cell_class",
    "cell_sub_class", "cell_type", "neuromere", "proofread", "roughly_proofread",
    "status", "neurotransmitter_predicted", "neurotransmitter_verified",
)
NT_FIELDS = ("neurotransmitter_predicted", "neurotransmitter_score")


def label(value: object) -> str | None:
    """Normalize missing annotations; source files remain unchanged."""
    if value is None:
        return None
    result = str(value).strip()
    return None if result.lower() in {"", "na", "nan", "null", "none"} else result


def ids(column: pa.Array) -> np.ndarray:
    if column.null_count:
        raise ValueError("Null source ID")
    return pc.cast(column, pa.uint64(), safe=True).to_numpy(zero_copy_only=True)


def _required(actual: list[str], required: set[str], product: str) -> None:
    missing = sorted(required.difference(actual))
    if missing:
        raise ValueError(f"{product}: missing required columns {missing}")


def _source_manifest(source: Path) -> dict:
    observed = json.loads((source / "source_manifest.json").read_text(encoding="utf-8"))
    entries = {item["name"]: item for item in observed["objects"]}
    for name, generation, expected_size, expected_md5 in PINNED_OBJECTS:
        item = entries[name]
        sha = hashlib.sha256()
        md5_hash = hashlib.md5(usedforsecurity=False)
        size = 0
        with (source / name).open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                sha.update(chunk)
                md5_hash.update(chunk)
                size += len(chunk)
        sha256 = sha.hexdigest()
        md5 = base64.b64encode(md5_hash.digest()).decode("ascii")
        if (size, sha256, md5, item["generation"]) != (
            expected_size, item["sha256"], expected_md5, generation
        ):
            raise ValueError(f"Source checksum/generation mismatch: {name}")
    return observed


def _read_nt(path: Path) -> tuple[dict[int, dict], dict]:
    predictions: dict[int, dict] = {}
    scores_out_of_range = 0
    row_count = 0
    duplicate_ids: set[int] = set()
    duplicate_rows = 0
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        _required(reader.fieldnames or [], {"root_id", *NT_FIELDS}, NT)
        for row in reader:
            row_count += 1
            source_id = int(row["root_id"])
            score = label(row["neurotransmitter_score"])
            score = None if score is None else float(score)
            if score is not None and not 0 <= score <= 1:
                scores_out_of_range += 1
            prediction = {
                "predicted": label(row["neurotransmitter_predicted"]),
                "score": score,
            }
            if source_id in predictions:
                duplicate_ids.add(source_id)
                duplicate_rows += 1
                if predictions[source_id] != prediction:
                    raise ValueError(f"Conflicting NT calls for source ID: {source_id}")
            else:
                predictions[source_id] = prediction
    if scores_out_of_range:
        raise ValueError(f"NT scores outside [0,1]: {scores_out_of_range}")
    return predictions, {
        "rows": row_count, "unique_ids": len(predictions),
        "duplicate_ids_with_matching_calls": len(duplicate_ids),
        "extra_duplicate_rows": duplicate_rows,
        "scores_out_of_range": scores_out_of_range,
    }


def _counts(values: list[str | None]) -> dict[str, int]:
    return dict(sorted(Counter(value if value is not None else "UNKNOWN" for value in values).items(), key=lambda x: (-x[1], x[0])))


def import_banc(source: Path, output: Path) -> dict:
    """Audit complete source tables before writing any internal tables.

    Raw source is immutable. The edge table stays directed and sparse; runtime
    indices are stable for this materialization and are never biological IDs.
    """
    source = Path(source)
    output = Path(output)
    manifest = _source_manifest(source)
    meta = feather.read_table(source / META, memory_map=True)
    edge_source = feather.read_table(source / EDGES, memory_map=True)
    _required(meta.column_names, {"banc_888_id", *NEURON_FIELDS, "neurotransmitter_score"}, META)
    _required(edge_source.column_names, {"pre", "post", "count", "norm", "post_count", "pre_count"}, EDGES)
    meta_ids = ids(meta["banc_888_id"].combine_chunks())
    if len(np.unique(meta_ids)) != len(meta_ids):
        raise ValueError("Duplicate metadata neuron ID")
    if np.any(meta_ids == 0):
        raise ValueError("Zero metadata neuron ID")
    predictions, nt_stats = _read_nt(source / NT)
    id_order = np.argsort(meta_ids)
    sorted_ids = meta_ids[id_order]
    source_index = {int(key): i for i, key in enumerate(meta_ids)}
    missing_nt = sum(int(key) not in predictions for key in meta_ids)
    nt_without_meta = sum(key not in source_index for key in predictions)

    annotations: dict[str, list[str | None]] = {}
    for field in NEURON_FIELDS:
        raw = meta[field].to_pylist()
        annotations[field] = [label(raw[int(i)]) for i in id_order]
    scores = meta["neurotransmitter_score"].to_pylist()
    meta_scores = [None if scores[int(i)] is None or np.isnan(scores[int(i)]) else scores[int(i)] for i in id_order]
    missing_meta_scores = sum(x is None for x in meta_scores)
    invalid_meta_scores = sum(x is not None and not 0 <= x <= 1 for x in meta_scores)
    if invalid_meta_scores:
        raise ValueError(f"Metadata NT scores outside [0,1]: {invalid_meta_scores}")

    nt_calls = [predictions.get(int(key), {}).get("predicted") for key in sorted_ids]
    nt_scores = [predictions.get(int(key), {}).get("score") for key in sorted_ids]
    explicit_non_neuron = np.array(
        [value in {"glia", "trachea", "not_a_neuron"} for value in annotations["super_class"]],
        dtype=np.bool_,
    )
    unknown_super_class = np.array([value is None for value in annotations["super_class"]], dtype=np.bool_)
    nt_disagreements = sum(
        a is not None and b is not None and a != b
        for a, b in zip(annotations["neurotransmitter_predicted"], nt_calls)
    )

    # Preflight the full edge product. Keep bounded batch allocations; no NxN matrix.
    endpoints: set[int] = set()
    pre_parts: list[np.ndarray] = []
    post_parts: list[np.ndarray] = []
    row_count = 0
    count_sum = 0
    count_min = None
    count_max = 0
    self_loops = 0
    invalid_counts = 0
    bad_norm = 0
    bad_totals = 0
    count_histogram = Counter()
    for batch in edge_source.to_batches(max_chunksize=262144):
        pre = ids(batch.column(batch.schema.get_field_index("pre")))
        post = ids(batch.column(batch.schema.get_field_index("post")))
        counts = batch.column(batch.schema.get_field_index("count")).to_numpy(zero_copy_only=True)
        norm = batch.column(batch.schema.get_field_index("norm")).to_numpy(zero_copy_only=True)
        post_total = batch.column(batch.schema.get_field_index("post_count")).to_numpy(zero_copy_only=True)
        pre_total = batch.column(batch.schema.get_field_index("pre_count")).to_numpy(zero_copy_only=True)
        invalid_counts += int(np.count_nonzero(counts <= 0))
        bad_totals += int(np.count_nonzero((post_total < counts) | (pre_total < counts)))
        expected_norm = counts / np.maximum(post_total, 1)
        bad_norm += int(np.count_nonzero(~np.isfinite(norm) | (np.abs(norm - expected_norm) > 1e-5)))
        self_loops += int(np.count_nonzero(pre == post))
        count_sum += int(np.sum(counts, dtype=np.int64))
        count_min = int(min(count_min if count_min is not None else counts.min(), counts.min()))
        count_max = max(count_max, int(counts.max()))
        row_count += len(batch)
        count_histogram["1"] += int(np.count_nonzero(counts == 1))
        count_histogram["2"] += int(np.count_nonzero(counts == 2))
        count_histogram["3-5"] += int(np.count_nonzero((counts >= 3) & (counts <= 5)))
        count_histogram["6-10"] += int(np.count_nonzero((counts >= 6) & (counts <= 10)))
        count_histogram["11-50"] += int(np.count_nonzero((counts >= 11) & (counts <= 50)))
        count_histogram[">50"] += int(np.count_nonzero(counts > 50))
        pre_parts.append(pre.copy())
        post_parts.append(post.copy())
        endpoints.update(map(int, np.unique(pre)))
        endpoints.update(map(int, np.unique(post)))
    pre_all = np.concatenate(pre_parts)
    post_all = np.concatenate(post_parts)
    del pre_parts, post_parts
    # Sorting pairs catches duplicate directed rows without constructing dense keys.
    pair_order = np.lexsort((post_all, pre_all))
    duplicate_pairs = int(np.count_nonzero(
        (pre_all[pair_order[1:]] == pre_all[pair_order[:-1]])
        & (post_all[pair_order[1:]] == post_all[pair_order[:-1]])
    ))
    del pair_order
    unknown_endpoints = sorted(endpoints.difference(source_index))
    validation = {
        "source_neuron_rows": meta.num_rows,
        "source_edge_rows": edge_source.num_rows,
        "source_nt_rows": nt_stats["rows"],
        "source_nt_unique_ids": nt_stats["unique_ids"],
        "source_nt_duplicate_ids_with_matching_calls": nt_stats["duplicate_ids_with_matching_calls"],
        "source_nt_extra_duplicate_rows": nt_stats["extra_duplicate_rows"],
        "unique_metadata_ids": len(source_index),
        "unique_edge_endpoint_ids": len(endpoints),
        "edge_endpoint_ids_without_metadata": len(unknown_endpoints),
        "edge_endpoint_examples_without_metadata": unknown_endpoints[:10],
        "duplicate_directed_edge_pairs": duplicate_pairs,
        "nonpositive_synapse_counts": invalid_counts,
        "edge_count_exceeds_source_total": bad_totals,
        "norm_inconsistent_with_count_over_post_count": bad_norm,
        "self_connection_rows": self_loops,
        "metadata_ids_without_nt_csv": missing_nt,
        "nt_csv_ids_without_metadata": nt_without_meta,
        "metadata_vs_csv_nonnull_nt_call_disagreements": nt_disagreements,
        "metadata_missing_or_nan_nt_scores": missing_meta_scores,
    }
    fatal = {key: validation[key] for key in (
        "edge_endpoint_ids_without_metadata", "duplicate_directed_edge_pairs",
        "nonpositive_synapse_counts", "edge_count_exceeds_source_total",
        "norm_inconsistent_with_count_over_post_count",
    ) if validation[key]}
    if fatal:
        raise ValueError(f"Source preflight failed: {fatal}")

    output.mkdir(parents=True, exist_ok=True)
    neuron_columns = {
        "runtime_index": pa.array(np.arange(len(sorted_ids), dtype=np.uint32)),
        "source_id": pa.array(sorted_ids),
        "explicit_non_neuron": pa.array(explicit_non_neuron),
        **{field: pa.array(values, type=pa.string()) for field, values in annotations.items()},
        "neurotransmitter_score": pa.array(meta_scores, type=pa.float64()),
        "nt_v2_predicted": pa.array(nt_calls, type=pa.string()),
        "nt_v2_score": pa.array(nt_scores, type=pa.float64()),
    }
    parquet.write_table(pa.table(neuron_columns), output / "neurons.parquet", compression="zstd")
    del neuron_columns

    writer = None
    edge_row = 0
    in_degree = np.zeros(len(sorted_ids), dtype=np.int64)
    out_degree = np.zeros(len(sorted_ids), dtype=np.int64)
    in_synapses = np.zeros(len(sorted_ids), dtype=np.int64)
    out_synapses = np.zeros(len(sorted_ids), dtype=np.int64)
    edges_incident_to_explicit_non_neuron = 0
    edges_incident_to_unknown_super_class = 0
    for batch in edge_source.to_batches(max_chunksize=262144):
        count = batch.column(batch.schema.get_field_index("count")).to_numpy(zero_copy_only=True)
        end = edge_row + len(batch)
        pre_idx = np.searchsorted(sorted_ids, pre_all[edge_row:end]).astype(np.uint32)
        post_idx = np.searchsorted(sorted_ids, post_all[edge_row:end]).astype(np.uint32)
        edges_incident_to_explicit_non_neuron += int(np.count_nonzero(explicit_non_neuron[pre_idx] | explicit_non_neuron[post_idx]))
        edges_incident_to_unknown_super_class += int(np.count_nonzero(unknown_super_class[pre_idx] | unknown_super_class[post_idx]))
        np.add.at(out_degree, pre_idx, 1)
        np.add.at(in_degree, post_idx, 1)
        np.add.at(out_synapses, pre_idx, count)
        np.add.at(in_synapses, post_idx, count)
        table = pa.table({
            "source_row": pa.array(np.arange(edge_row, end, dtype=np.uint32)),
            "pre_index": pa.array(pre_idx),
            "post_index": pa.array(post_idx),
            "synapse_count": pa.array(count, type=pa.int32()),
        })
        if writer is None:
            writer = parquet.ParquetWriter(output / "connections.parquet", table.schema, compression="zstd")
        writer.write_table(table)
        edge_row = end
    if writer is not None:
        writer.close()
    del pre_all, post_all

    region_counts = _counts(annotations["region"])
    cell_type_counts = _counts(annotations["cell_type"])
    report = {
        "schema_version": SCHEMA_VERSION,
        "source_manifest": manifest,
        "validation": validation,
        "statistics": {
            "source_nodes": len(sorted_ids), "connections": row_count,
            "explicit_non_neuron_source_nodes": int(np.count_nonzero(explicit_non_neuron)),
            "unknown_super_class_source_nodes": int(np.count_nonzero(unknown_super_class)),
            "connections_incident_to_explicit_non_neuron_source_nodes": edges_incident_to_explicit_non_neuron,
            "connections_incident_to_unknown_super_class_source_nodes": edges_incident_to_unknown_super_class,
            "synapse_count_sum_in_edge_product": count_sum,
            "synapse_count_min": count_min, "synapse_count_max": count_max,
            "synapse_count_buckets": dict(count_histogram),
            "region_counts": region_counts,
            "super_class_counts": _counts(annotations["super_class"]),
            "cell_class_counts": _counts(annotations["cell_class"]),
            "cell_type_count_distinct_nonmissing": len(cell_type_counts) - ("UNKNOWN" in cell_type_counts),
            "cell_type_counts_top20": dict(list(cell_type_counts.items())[:20]),
            "predicted_transmitter_counts": _counts(annotations["neurotransmitter_predicted"]),
            "verified_transmitter_counts": _counts(annotations["neurotransmitter_verified"]),
            "nt_v2_predicted_counts": _counts(nt_calls),
            "zero_in_degree_neurons": int(np.count_nonzero(in_degree == 0)),
            "zero_out_degree_neurons": int(np.count_nonzero(out_degree == 0)),
            "max_in_degree": int(in_degree.max()), "max_out_degree": int(out_degree.max()),
            "max_in_synapse_count": int(in_synapses.max()),
            "max_out_synapse_count": int(out_synapses.max()),
        },
        "schema": {
            "neurons": "runtime_index:uint32, source_id:uint64, explicit_non_neuron:bool, source annotation fields, nt_v2_*",
            "neuron_table_scope": "all metadata IDs, including explicitly non-neuronal and unclassified IDs; no biological neuron filter applied",
            "connections": "source_row:uint32, pre_index:uint32, post_index:uint32, synapse_count:int32",
            "source_row_meaning": "zero-based row in the immutable v2 simple edgelist; source IDs join via neurons.runtime_index",
            "edge_direction": "pre_index -> post_index",
            "region_meaning": "neuron-level metadata region, not synapse location",
            "transmitter_meaning": "neuron-level prediction/verification only; no synaptic sign or receptor model inferred",
        },
    }
    (output / "import_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report
