"""Role selection, exact source topology, metadata and reproducibility tests."""

import json
import tempfile
import unittest
from pathlib import Path

try:
    import numpy as np
    import pyarrow as pa
    import pyarrow.parquet as pq
    from project_b.connectome.circuit_v1 import build_circuit_v1, sha256_file, source_id_hash
    from scripts.audit_circuit_v1 import audit
except ImportError:
    pa = None


@unittest.skipIf(pa is None, "Circuit V1 selection requires optional numpy and pyarrow")
class CircuitV1SubsetTests(unittest.TestCase):
    def make_fixture(self, root: Path) -> tuple[Path, Path]:
        source = root / "parent"
        source.mkdir()
        nodes = pa.table({
            "runtime_index": pa.array([0, 1, 2, 3, 4], type=pa.uint32()),
            "source_id": pa.array([10, 20, 30, 40, 50], type=pa.int64()),
            "status": ["Traced"] * 5,
            "cell_type": ["other", "KC", "MBON", "DAN", "KC"],
            "instance": ["outside", "KC_R", "MBON_R", "DAN_R", "KC_R"],
            "soma_side": ["R"] * 5,
            "transmitter_predicted": ["gaba", "acetylcholine", "glutamate", "dopamine", "acetylcholine"],
            "transmitter_consensus": ["gaba", "acetylcholine", "glutamate", "dopamine", "acetylcholine"],
            "transmitter_ground_truth": [None, None, "glutamate", "dopamine", None],
            "transmitter_confidence": [0.5, 0.8, 0.9, 0.7, 0.6],
        })
        edges = pa.table({
            "source_row": pa.array(list(range(8)), type=pa.uint32()),
            "pre_index": pa.array([0, 1, 4, 1, 2, 3, 2, 4], type=pa.uint32()),
            "post_index": pa.array([1, 2, 2, 4, 3, 0, 1, 3], type=pa.uint32()),
            "synapse_count": pa.array([7, 2, 1, 3, 5, 11, 1, 1], type=pa.int64()),
        })
        pq.write_table(nodes, source / "neurons.parquet")
        pq.write_table(edges, source / "connections.parquet")
        file_info = {name: {"sha256": sha256_file(source / name)}
                     for name in ("neurons.parquet", "connections.parquet")}
        (source / "validation_receipt.json").write_text(
            json.dumps({"dataset": "MaleCNS", "release": "v1.0", "files": file_info}),
            encoding="utf-8")
        config = {
            "schema_version": 1, "dataset": "MaleCNS", "release": "v1.0",
            "scope": "official traced-only",
            "parent_sha256": {name: values["sha256"] for name, values in file_info.items()},
            "selected_source_id_sha256": source_id_hash(np.array([20, 30, 40, 50])),
            "roles": [
                {"name": "KC", "reason": "Complete input class", "match": {"cell_type": "KC", "soma_side": "R"},
                 "expected_count": 2, "source_id_sha256": source_id_hash(np.array([20, 50]))},
                {"name": "MBON", "reason": "Learning output", "match": {"source_id": 30, "cell_type": "MBON"},
                 "expected_count": 1},
                {"name": "DAN", "reason": "Teaching candidate", "match": {"source_id": 40, "cell_type": "DAN"},
                 "expected_count": 1},
            ],
            "plastic_candidates": [
                {"pre_role": "KC", "post_role": "MBON", "teaching_role": "DAN",
                 "compartment_candidate": "test_compartment"},
            ],
        }
        selection = root / "selection.json"
        selection.write_text(json.dumps(config), encoding="utf-8")
        return source, selection

    def test_exact_subset_mask_boundary_metadata_and_independent_audit(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, selection = self.make_fixture(root)
            output = root / "subset"
            manifest = build_circuit_v1(source, selection, output)
            self.assertEqual((manifest["neurons"], manifest["directed_pairs"],
                              manifest["internal_contacts"]), (4, 6, 13))
            self.assertEqual((manifest["plastic_candidate_pairs"],
                              manifest["plastic_candidate_contacts"]), (2, 3))
            self.assertEqual((manifest["incoming_cut_pairs"], manifest["incoming_cut_contacts"],
                              manifest["outgoing_cut_pairs"], manifest["outgoing_cut_contacts"]),
                             (1, 7, 1, 11))
            nodes = pq.read_table(output / "neurons.parquet")
            parent = pq.read_table(source / "neurons.parquet")
            self.assertTrue(nodes.drop(["local_index"]).equals(parent.take(pa.array([1, 2, 3, 4]))))
            self.assertEqual(nodes["transmitter_predicted"].to_pylist(),
                             ["acetylcholine", "glutamate", "dopamine", "acetylcholine"])
            edges = pq.read_table(output / "connections.parquet")
            self.assertEqual(edges["source_row"].to_pylist(), [1, 2, 3, 4, 6, 7])
            self.assertEqual(edges["synapse_count"].to_pylist(), [2, 1, 3, 5, 1, 1])
            plastic = pq.read_table(output / "plastic_candidates.parquet")
            self.assertEqual(plastic["source_row"].to_pylist(), [1, 2])
            self.assertEqual(set(plastic["status"].to_pylist()),
                             {"candidate_pending_synapse_location"})
            self.assertEqual(audit(source, selection, output)["status"], "passed")

    def test_repeat_build_has_identical_bytes_and_selection(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, selection = self.make_fixture(root)
            first = build_circuit_v1(source, selection, root / "first")
            second = build_circuit_v1(source, selection, root / "second")
            self.assertEqual(first, second)
            self.assertEqual((root / "first/manifest.json").read_bytes(),
                             (root / "second/manifest.json").read_bytes())
            for name in ("neurons.parquet", "connections.parquet", "plastic_candidates.parquet"):
                self.assertEqual(sha256_file(root / "first" / name),
                                 sha256_file(root / "second" / name))

    def test_missing_id_or_annotation_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, selection = self.make_fixture(root)
            config = json.loads(selection.read_text(encoding="utf-8"))
            config["roles"][1]["match"]["source_id"] = 999
            selection.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "expected 1 annotated bodies, found 0"):
                build_circuit_v1(source, selection, root / "missing")
            self.assertFalse((root / "missing").exists())

            config["roles"][1]["match"]["source_id"] = 30
            selection.write_text(json.dumps(config), encoding="utf-8")
            nodes = pq.read_table(source / "neurons.parquet")
            types = nodes["cell_type"].to_pylist()
            types[0], types[4] = "KC", "other"  # Same role size, different members.
            changed = nodes.set_column(nodes.schema.get_field_index("cell_type"),
                                       "cell_type", pa.array(types))
            pq.write_table(changed, source / "neurons.parquet")
            digest = sha256_file(source / "neurons.parquet")
            receipt_path = source / "validation_receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["files"]["neurons.parquet"]["sha256"] = digest
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            config["parent_sha256"]["neurons.parquet"] = digest
            selection.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "source-ID membership drifted"):
                build_circuit_v1(source, selection, root / "drift")
            self.assertFalse((root / "drift").exists())

    def test_parent_file_corruption_is_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, selection = self.make_fixture(root)
            with (source / "connections.parquet").open("ab") as stream:
                stream.write(b"tamper")
            with self.assertRaisesRegex(ValueError, "validation receipt"):
                build_circuit_v1(source, selection, root / "bad")
            self.assertFalse((root / "bad").exists())


if __name__ == "__main__":
    unittest.main()
