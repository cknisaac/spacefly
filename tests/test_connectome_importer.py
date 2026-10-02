"""Data-only checks for BANC import boundaries and directed edge provenance."""

import base64
import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    import pyarrow as pa
    import pyarrow.feather as feather
    import pyarrow.parquet as parquet
    from project_b.connectome import importer
except ImportError:
    pa = None


@unittest.skipIf(pa is None, "connectome import requires the optional pyarrow dependency")
class ConnectomeImportTests(unittest.TestCase):
    def make_source(self, root: Path, duplicate_edge: bool = False):
        source = root / "raw"
        source.mkdir()
        columns = {field: [None, None] for field in importer.NEURON_FIELDS}
        columns.update({
            "banc_888_id": ["9", "4"],
            "region": ["central_brain", "ventral_nerve_cord"],
            "cell_type": ["A", "B"],
            "neurotransmitter_predicted": ["acetylcholine", "gaba"],
            "neurotransmitter_score": [0.8, 0.9],
        })
        feather.write_feather(pa.table(columns), source / importer.META)
        edge_columns = {
            "pre": ["9", "4"], "post": ["4", "4"],
            "count": pa.array([2, 1], type=pa.int32()),
            "norm": [0.5, 0.25],
            "post_count": pa.array([4, 4], type=pa.int32()),
            "pre_count": pa.array([2, 1], type=pa.int32()),
        }
        if duplicate_edge:
            edge_columns["pre"][1] = "9"
            edge_columns["post"][1] = "4"
        feather.write_feather(pa.table(edge_columns), source / importer.EDGES)
        with (source / importer.NT).open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["root_id", "neurotransmitter_predicted", "neurotransmitter_score"])
            writer.writeheader()
            writer.writerows([
                {"root_id": "9", "neurotransmitter_predicted": "acetylcholine", "neurotransmitter_score": "0.8"},
                {"root_id": "9", "neurotransmitter_predicted": "acetylcholine", "neurotransmitter_score": "0.8"},
                {"root_id": "4", "neurotransmitter_predicted": "gaba", "neurotransmitter_score": "0.9"},
            ])
        pinned = []
        entries = []
        for name in (importer.META, importer.EDGES, importer.NT):
            data = (source / name).read_bytes()
            md5 = base64.b64encode(hashlib.md5(data, usedforsecurity=False).digest()).decode("ascii")
            pinned.append((name, "1", len(data), md5))
            entries.append({"name": name, "generation": "1", "sha256": hashlib.sha256(data).hexdigest()})
        (source / "source_manifest.json").write_text(json.dumps({"objects": entries}), encoding="utf-8")
        return source, tuple(pinned)

    def test_import_preserves_direction_count_and_source_row(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, pinned = self.make_source(root)
            with patch.object(importer, "PINNED_OBJECTS", pinned):
                report = importer.import_banc(source, root / "processed")
            neurons = parquet.read_table(root / "processed/neurons.parquet").to_pylist()
            edges = parquet.read_table(root / "processed/connections.parquet").to_pylist()
            self.assertEqual([node["source_id"] for node in neurons], [4, 9])
            self.assertEqual([(edge["pre_index"], edge["post_index"], edge["synapse_count"], edge["source_row"]) for edge in edges], [(1, 0, 2, 0), (0, 0, 1, 1)])
            self.assertEqual(report["validation"]["source_nt_duplicate_ids_with_matching_calls"], 1)
            self.assertEqual(report["validation"]["self_connection_rows"], 1)

    def test_duplicate_directed_pair_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, pinned = self.make_source(root, duplicate_edge=True)
            with patch.object(importer, "PINNED_OBJECTS", pinned):
                with self.assertRaisesRegex(ValueError, "duplicate_directed_edge_pairs"):
                    importer.import_banc(source, root / "processed")
            self.assertFalse((root / "processed").exists())


if __name__ == "__main__":
    unittest.main()
