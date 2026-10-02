"""MaleCNS source-scope, validation, and exact directed-edge mapping tests."""

import base64
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
    from project_b.connectome import malecns
except ImportError:
    pa = None


@unittest.skipIf(pa is None, "MaleCNS import requires optional pyarrow")
class MaleCNSImportTests(unittest.TestCase):
    def make_source(self, root: Path, duplicate: bool = False):
        source = root / "raw"
        source.mkdir()
        annotations = {field: [None, None, None] for field in malecns.ANNOTATION_FIELDS}
        annotations.update({
            "bodyId": [9, 4, 7], "status": ["Traced", "Traced", "Glia"],
            "superclass": ["cb_intrinsic", "vnc_motor", None],
            "class": ["CX", "motor", None], "type": ["A", "B", None],
            "somaNeuromere": [None, "T1", None],
        })
        feather.write_feather(pa.table(annotations), source / malecns.ANNOTATIONS)
        transmitter = {field: [None, None, None] for field in malecns.NT_FIELDS}
        transmitter.update({
            "body": [9, 4, 7], "predicted_nt": ["acetylcholine", "gaba", "unclear"],
            "predicted_nt_confidence": [0.8, 0.9, None],
            "consensus_nt": ["acetylcholine", "gaba", "unclear"],
        })
        feather.write_feather(pa.table(transmitter), source / malecns.TRANSMITTERS)
        full = {"body_pre": [9, 4, 7], "body_post": [4, 4, 4], "weight": [2, 1, 3]}
        feather.write_feather(pa.table(full), source / malecns.FULL_EDGES)
        traced = {"body_pre": [9, 4], "body_post": [4, 4], "weight": [2, 1], "type_pre": ["A", "B"], "type_post": ["B", "B"]}
        if duplicate:
            traced["body_pre"][1] = 9
        feather.write_feather(pa.table(traced), source / malecns.TRACED_EDGES)
        stats = {"body": [9, 4, 7], "pre": [2, 1, 3], "post": [0, 6, 0], "downstream": [2, 1, 3], "synweight": [2, 7, 3]}
        feather.write_feather(pa.table(stats), source / malecns.BODY_STATS)
        pinned = []
        entries = []
        for name in (malecns.ANNOTATIONS, malecns.TRANSMITTERS, malecns.BODY_STATS, malecns.FULL_EDGES, malecns.TRACED_EDGES):
            data = (source / name).read_bytes()
            md5 = base64.b64encode(hashlib.md5(data, usedforsecurity=False).digest()).decode("ascii")
            pinned.append((name, "1", len(data), md5))
            entries.append({"name": name, "generation": "1", "sha256": hashlib.sha256(data).hexdigest()})
        (source / "source_manifest.json").write_text(json.dumps({"dataset": "MaleCNS", "release": "v1.0", "objects": entries}), encoding="utf-8")
        return source, tuple(pinned)

    def test_traced_only_import_preserves_pair_direction_count_and_row(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, pinned = self.make_source(root)
            with patch.object(malecns, "PINNED_OBJECTS", pinned):
                report = malecns.import_malecns(source, root / "processed")
            nodes = parquet.read_table(root / "processed/neurons.parquet").to_pylist()
            edges = parquet.read_table(root / "processed/connections.parquet").to_pylist()
            self.assertEqual([node["source_id"] for node in nodes], [4, 9])
            self.assertEqual([(edge["pre_index"], edge["post_index"], edge["synapse_count"], edge["source_row"]) for edge in edges], [(1, 0, 2, 0), (0, 0, 1, 1)])
            self.assertEqual(report["statistics"]["full_segment_graph_synapse_count_sum"], 6)
            self.assertEqual(report["statistics"]["traced_graph_synapse_count_sum"], 3)
            self.assertEqual(nodes[0]["soma_neuromere"], "T1")
            self.assertEqual(nodes[0]["region"], "T1")
            self.assertEqual(nodes[0]["region_basis"], "soma_neuromere")

    def test_duplicate_traced_pair_rejected_before_materialization(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, pinned = self.make_source(root, duplicate=True)
            with patch.object(malecns, "PINNED_OBJECTS", pinned):
                with self.assertRaisesRegex(ValueError, "Duplicate directed pair"):
                    malecns.import_malecns(source, root / "processed")
            self.assertFalse((root / "processed").exists())


if __name__ == "__main__":
    unittest.main()
