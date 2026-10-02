"""Data-only MaleCNS v1.0 importer for the official traced-neuron graph.

The full segment graph is validated as a source product. The normalized graph
uses the release's official traced-only edge product and `status == Traced`
annotation rows. No dynamics, synaptic sign, or learning parameters are set.
"""

from __future__ import annotations

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
ANNOTATIONS = "body-annotations-male-cns-v1.0-minconf-0.5.feather"
TRANSMITTERS = "body-neurotransmitters-male-cns-v1.0.feather"
BODY_STATS = "body-stats-male-cns-v1.0-minconf-0.5.feather"
FULL_EDGES = "connectome-weights-male-cns-v1.0-minconf-0.5.feather"
TRACED_EDGES = "connectome-weights-male-cns-v1.0-minconf-0.5-traced-only.feather"
PINNED_OBJECTS = (
    (ANNOTATIONS, "1780494878811468", 14483314, "UKdxh3DFciDxYLpPQxq4ng=="),
    (TRANSMITTERS, "1780894899156750", 43282834, "PYQrEv5cSe763lKNfdJKHw=="),
    (BODY_STATS, "1780494888472305", 778062826, "QEwzScKFgBSOFoFeuZ84Kg=="),
    (FULL_EDGES, "1780494887545976", 1051241946, "8w6dzKJc/QIb8eez2XVZng=="),
    (TRACED_EDGES, "1780494884279095", 508025642, "ZgHUrQr6mf0D6wh5Ze8kIw=="),
)
ANNOTATION_FIELDS = (
    "bodyId", "status", "statusLabel", "superclass", "class", "subclass",
    "type", "instance", "somaNeuromere", "somaSide", "rootSide", "receptorType",
)
NT_FIELDS = ("body", "predicted_nt", "predicted_nt_confidence", "consensus_nt", "ground_truth")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _hash(path: Path) -> tuple[int, str, str]:
    sha = hashlib.sha256()
    md5 = hashlib.md5(usedforsecurity=False)
    size = 0
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            size += len(chunk)
            sha.update(chunk)
            md5.update(chunk)
    return size, sha.hexdigest(), base64.b64encode(md5.digest()).decode("ascii")


def verify_source(source: Path) -> dict:
    manifest = json.loads((source / "source_manifest.json").read_text(encoding="utf-8"))
    _require(manifest.get("dataset") == "MaleCNS" and manifest.get("release") == "v1.0", "Wrong dataset/release manifest")
    entries = {item["name"]: item for item in manifest["objects"]}
    for name, generation, expected_size, expected_md5 in PINNED_OBJECTS:
        item = entries[name]
        size, sha256, md5 = _hash(source / name)
        _require(
            (size, sha256, md5, item["generation"]) ==
            (expected_size, item["sha256"], expected_md5, generation),
            f"Source checksum/generation mismatch: {name}",
        )
    return manifest


def _open_feather(path: Path):
    mapped = pa.memory_map(str(path))
    return mapped, pa.ipc.open_file(mapped)


def _counts(values: list[str | None]) -> dict[str, int]:
    return dict(sorted(Counter(v if v not in (None, "") else "UNKNOWN" for v in values).items(), key=lambda x: (-x[1], x[0])))


def _matching(sorted_ids: np.ndarray, candidates: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    loc = np.searchsorted(sorted_ids, candidates)
    match = (loc < len(sorted_ids)) & (sorted_ids[np.minimum(loc, len(sorted_ids) - 1)] == candidates)
    return loc, match


def import_malecns(source: Path, output: Path) -> dict:
    source, output = Path(source), Path(output)
    manifest = verify_source(source)

    annotations = feather.read_table(source / ANNOTATIONS, columns=list(ANNOTATION_FIELDS), memory_map=True)
    a_ids = annotations["bodyId"].to_numpy()
    _require(len(np.unique(a_ids)) == len(a_ids), "Duplicate annotation body ID")
    a_status = annotations["status"].to_pylist()
    traced_rows = np.flatnonzero(np.array([x == "Traced" for x in a_status], dtype=np.bool_))
    traced_ids = np.sort(a_ids[traced_rows])
    _require(len(traced_ids) > 0 and np.all(traced_ids > 0), "No valid traced bodies")
    _require(int(traced_ids[-1]) < 2**32, "Body IDs exceed packed-pair validation limit")
    annotation_row_for_node = np.argsort(a_ids[traced_rows])
    ordered_rows = traced_rows[annotation_row_for_node]
    node_fields: dict[str, list[str | None]] = {}
    for field in ANNOTATION_FIELDS[1:]:
        values = annotations[field].to_pylist()
        node_fields[field] = [values[int(i)] for i in ordered_rows]
    literal_na_soma_regions = sum(value == "NA" for value in node_fields["somaNeuromere"])
    node_fields["somaNeuromere"] = [None if value == "NA" else value for value in node_fields["somaNeuromere"]]

    nt = feather.read_table(source / TRANSMITTERS, columns=list(NT_FIELDS), memory_map=True)
    nt_ids = nt["body"].to_numpy()
    _require(len(np.unique(nt_ids)) == len(nt_ids), "Duplicate neurotransmitter body ID")
    _require(np.all(nt_ids > 0), "Nonpositive neurotransmitter body ID")
    nt_order = np.argsort(nt_ids)
    nt_loc, nt_match = _matching(nt_ids[nt_order], traced_ids)
    node_nt_rows = nt_order[nt_loc[nt_match]]
    nt_field_values: dict[str, list] = {}
    for field in NT_FIELDS[1:]:
        selected = pc.take(nt[field], pa.array(node_nt_rows)).to_pylist()
        result = [None] * len(traced_ids)
        for node_i, value in zip(np.flatnonzero(nt_match), selected):
            if isinstance(value, float) and not np.isfinite(value):
                value = None
            result[int(node_i)] = value
        nt_field_values[field] = result
    invalid_nt_scores = sum(
        value is not None and not 0 <= value <= 1
        for value in nt_field_values["predicted_nt_confidence"]
    )
    _require(invalid_nt_scores == 0, "Predicted transmitter confidence outside [0,1]")

    traced_map, traced_reader = _open_feather(source / TRACED_EDGES)
    _require(set(traced_reader.schema.names) >= {"body_pre", "body_post", "weight", "type_pre", "type_post"}, "Traced edge schema changed")
    packed_parts: list[np.ndarray] = []
    weight_parts: list[np.ndarray] = []
    endpoints: set[int] = set()
    traced_rows_count = 0
    traced_weight_sum = 0
    traced_self = 0
    traced_nonpositive = 0
    count_buckets = Counter()
    for i in range(traced_reader.num_record_batches):
        batch = traced_reader.get_batch(i)
        pre = batch.column(0).to_numpy(zero_copy_only=True)
        post = batch.column(1).to_numpy(zero_copy_only=True)
        weight = batch.column(2).to_numpy(zero_copy_only=True)
        _require(np.all((pre > 0) & (post > 0) & (pre < 2**32) & (post < 2**32)), f"Invalid traced endpoint ID in batch {i}")
        packed_parts.append((pre.astype(np.uint64) << np.uint64(32)) | post.astype(np.uint64))
        weight_parts.append(weight.copy())
        endpoints.update(map(int, np.unique(pre)))
        endpoints.update(map(int, np.unique(post)))
        traced_rows_count += len(batch)
        traced_weight_sum += int(weight.sum(dtype=np.int64))
        traced_self += int(np.count_nonzero(pre == post))
        traced_nonpositive += int(np.count_nonzero(weight <= 0))
        count_buckets["1"] += int(np.count_nonzero(weight == 1))
        count_buckets["2-4"] += int(np.count_nonzero((weight >= 2) & (weight <= 4)))
        count_buckets["5-9"] += int(np.count_nonzero((weight >= 5) & (weight <= 9)))
        count_buckets["10-49"] += int(np.count_nonzero((weight >= 10) & (weight <= 49)))
        count_buckets[">=50"] += int(np.count_nonzero(weight >= 50))
    _require(traced_nonpositive == 0, "Nonpositive traced edge count")
    missing_endpoints = sorted(endpoints.difference(map(int, traced_ids)))
    _require(not missing_endpoints, f"Traced graph endpoints without Traced annotation: {missing_endpoints[:10]}")
    packed = np.concatenate(packed_parts)
    weights = np.concatenate(weight_parts)
    del packed_parts, weight_parts
    pair_order = np.argsort(packed)
    sorted_keys = packed[pair_order]
    sorted_weights = weights[pair_order]
    duplicate_pairs = int(np.count_nonzero(sorted_keys[1:] == sorted_keys[:-1]))
    _require(duplicate_pairs == 0, "Duplicate directed pair in traced graph")
    del packed, weights, pair_order

    # Verify every traced-only edge is exactly the full source graph restricted
    # to Traced annotation IDs. This is a source-product reconciliation, not a
    # model choice based on task performance.
    full_map, full_reader = _open_feather(source / FULL_EDGES)
    _require(set(full_reader.schema.names) >= {"body_pre", "body_post", "weight"}, "Full edge schema changed")
    seen = np.zeros(len(sorted_keys), dtype=np.bool_)
    full_rows = 0
    full_weight_sum = 0
    full_self = 0
    full_nonpositive = 0
    full_traced_pair_rows = 0
    for i in range(full_reader.num_record_batches):
        batch = full_reader.get_batch(i)
        pre = batch.column(0).to_numpy(zero_copy_only=True)
        post = batch.column(1).to_numpy(zero_copy_only=True)
        weight = batch.column(2).to_numpy(zero_copy_only=True)
        full_rows += len(batch)
        full_weight_sum += int(weight.sum(dtype=np.int64))
        full_self += int(np.count_nonzero(pre == post))
        full_nonpositive += int(np.count_nonzero(weight <= 0))
        pre_loc, pre_match = _matching(traced_ids, pre)
        post_loc, post_match = _matching(traced_ids, post)
        keep = pre_match & post_match
        if np.any(keep):
            keys = (pre[keep].astype(np.uint64) << np.uint64(32)) | post[keep].astype(np.uint64)
            loc = np.searchsorted(sorted_keys, keys)
            _require(bool(np.all(loc < len(sorted_keys))), f"Traced pair absent from traced-only file, full batch {i}")
            _require(bool(np.all(sorted_keys[loc] == keys)), f"Traced pair absent from traced-only file, full batch {i}")
            _require(bool(np.array_equal(sorted_weights[loc], weight[keep])), f"Traced pair weight mismatch, full batch {i}")
            _require(not bool(np.any(seen[loc])), f"Duplicate traced pair in full graph, batch {i}")
            seen[loc] = True
            full_traced_pair_rows += int(np.count_nonzero(keep))
    _require(full_nonpositive == 0, "Nonpositive full edge count")
    _require(full_traced_pair_rows == traced_rows_count and bool(np.all(seen)), "Traced-only graph differs from full graph Traced-ID restriction")
    del sorted_keys, sorted_weights, seen
    full_map.close()

    stats_map, stats_reader = _open_feather(source / BODY_STATS)
    _require(set(stats_reader.schema.names) >= {"body", "pre", "post", "downstream", "synweight"}, "Body stats schema changed")
    stats_rows = 0
    stats_pre_sum = 0
    stats_post_sum = 0
    stats_downstream_sum = 0
    stats_synweight_sum = 0
    for i in range(stats_reader.num_record_batches):
        batch = stats_reader.get_batch(i)
        stats_rows += len(batch)
        stats_pre_sum += int(batch.column(batch.schema.get_field_index("pre")).to_numpy().sum(dtype=np.int64))
        stats_post_sum += int(batch.column(batch.schema.get_field_index("post")).to_numpy().sum(dtype=np.int64))
        stats_downstream_sum += int(batch.column(batch.schema.get_field_index("downstream")).to_numpy().sum(dtype=np.int64))
        stats_synweight_sum += int(batch.column(batch.schema.get_field_index("synweight")).to_numpy().sum(dtype=np.int64))
    _require(stats_post_sum == full_weight_sum, "Full edge count sum disagrees with body-stats post sum")
    _require(stats_synweight_sum == stats_post_sum + stats_downstream_sum, "Body-stats synweight formula is inconsistent")
    stats_map.close()

    # Only after the source products reconcile, materialize the traced graph.
    output.mkdir(parents=True, exist_ok=True)
    nodes = pa.table({
        "runtime_index": pa.array(np.arange(len(traced_ids), dtype=np.uint32)),
        "source_id": pa.array(traced_ids, type=pa.int64()),
        "status": pa.array(node_fields["status"], type=pa.string()),
        "status_label": pa.array(node_fields["statusLabel"], type=pa.string()),
        "superclass": pa.array(node_fields["superclass"], type=pa.string()),
        "cell_class": pa.array(node_fields["class"], type=pa.string()),
        "cell_subclass": pa.array(node_fields["subclass"], type=pa.string()),
        "cell_type": pa.array(node_fields["type"], type=pa.string()),
        "instance": pa.array(node_fields["instance"], type=pa.string()),
        "region": pa.array(node_fields["somaNeuromere"], type=pa.string()),
        "region_basis": pa.array(["soma_neuromere" if value is not None else None for value in node_fields["somaNeuromere"]], type=pa.string()),
        "soma_neuromere": pa.array(node_fields["somaNeuromere"], type=pa.string()),
        "soma_side": pa.array(node_fields["somaSide"], type=pa.string()),
        "root_side": pa.array(node_fields["rootSide"], type=pa.string()),
        "receptor_type_annotation": pa.array(node_fields["receptorType"], type=pa.string()),
        "transmitter_predicted": pa.array(nt_field_values["predicted_nt"], type=pa.string()),
        "transmitter_confidence": pa.array(nt_field_values["predicted_nt_confidence"], type=pa.float64()),
        "transmitter_consensus": pa.array(nt_field_values["consensus_nt"], type=pa.string()),
        "transmitter_ground_truth": pa.array(nt_field_values["ground_truth"], type=pa.string()),
    })
    parquet.write_table(nodes, output / "neurons.parquet", compression="zstd")

    writer = None
    offset = 0
    in_degree = np.zeros(len(traced_ids), dtype=np.int64)
    out_degree = np.zeros(len(traced_ids), dtype=np.int64)
    for i in range(traced_reader.num_record_batches):
        batch = traced_reader.get_batch(i)
        pre = batch.column(0).to_numpy(zero_copy_only=True)
        post = batch.column(1).to_numpy(zero_copy_only=True)
        weight = batch.column(2).to_numpy(zero_copy_only=True)
        pre_idx = np.searchsorted(traced_ids, pre).astype(np.uint32)
        post_idx = np.searchsorted(traced_ids, post).astype(np.uint32)
        in_degree += np.bincount(post_idx, minlength=len(traced_ids))
        out_degree += np.bincount(pre_idx, minlength=len(traced_ids))
        end = offset + len(batch)
        table = pa.table({
            "source_row": pa.array(np.arange(offset, end, dtype=np.uint32)),
            "pre_index": pa.array(pre_idx),
            "post_index": pa.array(post_idx),
            "synapse_count": pa.array(weight, type=pa.int64()),
        })
        if writer is None:
            writer = parquet.ParquetWriter(output / "connections.parquet", table.schema, compression="zstd")
        writer.write_table(table)
        offset = end
    if writer is not None:
        writer.close()
    traced_map.close()

    report = {
        "schema_version": SCHEMA_VERSION,
        "dataset": "MaleCNS", "release": "v1.0", "graph_scope": "official traced-only product",
        "source_manifest": manifest,
        "validation": {
            "annotation_rows": len(a_ids), "unique_annotation_ids": len(a_ids),
            "transmitter_rows": len(nt_ids), "unique_transmitter_ids": len(nt_ids),
            "traced_annotation_rows": len(traced_ids),
            "traced_edge_endpoints_without_traced_annotation": len(missing_endpoints),
            "duplicate_traced_directed_pairs": duplicate_pairs,
            "nonpositive_traced_edge_counts": traced_nonpositive,
            "nonpositive_full_edge_counts": full_nonpositive,
            "traced_edges_matched_to_full_graph": full_traced_pair_rows,
            "full_graph_weight_sum_matches_body_stats_post": True,
            "body_stats_synweight_equals_post_plus_downstream": True,
            "traced_neurons_without_transmitter_row": int(np.count_nonzero(~nt_match)),
            "invalid_traced_transmitter_confidences": invalid_nt_scores,
            "literal_NA_soma_regions_normalized_to_unknown": literal_na_soma_regions,
        },
        "statistics": {
            "source_annotation_rows": len(a_ids),
            "source_transmitter_rows": len(nt_ids),
            "source_body_stats_rows": stats_rows,
            "full_segment_graph_connections": full_rows,
            "full_segment_graph_synapse_count_sum": full_weight_sum,
            "full_segment_graph_self_connections": full_self,
            "body_stats_pre_site_sum": stats_pre_sum,
            "body_stats_downstream_sum": stats_downstream_sum,
            "body_stats_synweight_sum": stats_synweight_sum,
            "traced_neurons": len(traced_ids),
            "traced_graph_active_neurons": len(endpoints),
            "traced_graph_connections": traced_rows_count,
            "traced_graph_synapse_count_sum": traced_weight_sum,
            "traced_graph_self_connections": traced_self,
            "traced_graph_count_buckets": dict(count_buckets),
            "zero_in_degree_traced_neurons": int(np.count_nonzero(in_degree == 0)),
            "zero_out_degree_traced_neurons": int(np.count_nonzero(out_degree == 0)),
            "max_in_degree": int(in_degree.max()),
            "max_out_degree": int(out_degree.max()),
            "superclass_counts": _counts(node_fields["superclass"]),
            "cell_class_counts": _counts(node_fields["class"]),
            "cell_type_distinct_nonmissing": len(set(x for x in node_fields["type"] if x not in (None, ""))),
            "cell_type_missing": sum(x in (None, "") for x in node_fields["type"]),
            "soma_neuromere_counts": _counts(node_fields["somaNeuromere"]),
            "transmitter_predicted_counts": _counts(nt_field_values["predicted_nt"]),
            "transmitter_consensus_counts": _counts(nt_field_values["consensus_nt"]),
            "transmitter_ground_truth_counts": _counts(nt_field_values["ground_truth"]),
            "transmitter_confidence_missing": sum(value is None for value in nt_field_values["predicted_nt_confidence"]),
        },
        "schema": {
            "neurons": "runtime_index:uint32, source_id:int64, source annotations, region/region_basis, and neuron-level transmitter fields",
            "connections": "source_row:uint32, pre_index:uint32, post_index:uint32, synapse_count:int64",
            "source_row": "zero-based row in the immutable official traced-only Feather product",
            "direction": "pre_index -> post_index",
            "region": "soma_neuromere is the released soma-region field; missing for most traced neurons. No global brain/VNC region or per-synapse ROI is inferred.",
            "transmitter": "neuron-level predictions/consensus only; unclear and missing remain distinct; no synaptic sign inferred",
        },
    }
    (output / "import_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report
