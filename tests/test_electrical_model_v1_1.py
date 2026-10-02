"""Boundary-only V1.1 invariants; these tests do not assert a biological pass."""

from pathlib import Path
import unittest

from project_b.electrical_v1 import NeutralCircuit, build_circuit
from project_b.electrical_v1.source import ADDED_VISUAL_IDS, V1_CONFIG_SHA, file_sha
from project_b.electrical_v1.visual_boundary_probe import VisualBoundaryProbe


ROOT = Path(__file__).resolve().parents[1]


class ElectricalModelV11Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old = build_circuit()
        cls.new = build_circuit(ROOT / "configs/electrical_model_v1_1.json")

    def test_source_and_effect_delta_only(self):
        old, new = self.old, self.new
        self.assertEqual(file_sha(ROOT / "configs/electrical_model_v1.json"), V1_CONFIG_SHA)
        self.assertEqual({c.source_id for c in new.cells} - {c.source_id for c in old.cells},
                         set(ADDED_VISUAL_IDS))
        before = {e.source_row: e for e in old.connections}
        after = {e.source_row: e for e in new.connections}
        self.assertEqual(len(before), 10009)
        self.assertEqual(len(after), 10071)
        for source_row, edge in before.items():
            revised = after[source_row]
            self.assertEqual((old.cells[edge.pre].source_id, old.cells[edge.post].source_id,
                              edge.contacts, edge.effect_state, edge.effect_evidence,
                              edge.weight_pa, edge.candidate_contacts),
                             (new.cells[revised.pre].source_id, new.cells[revised.post].source_id,
                              revised.contacts, revised.effect_state, revised.effect_evidence,
                              revised.weight_pa, revised.candidate_contacts))
        added = [after[i] for i in set(after)-set(before)]
        self.assertEqual((len(added), sum(e.contacts for e in added)), (62, 603))
        active = [e for e in added if e.effect_state == "ACTIVE_FAST"]
        self.assertEqual((len(active), sum(e.contacts for e in active)), (48, 569))
        self.assertTrue(all(new.cells[e.pre].source_id in ADDED_VISUAL_IDS and
                            new.cells[e.post].kind == "KC" and
                            e.effect_evidence == "INFERRED" and
                            e.weight_pa == .03*e.contacts for e in active))
        self.assertTrue(all(e.effect_state == "UNKNOWN" and e.weight_pa is None
                            for e in added if e not in active))

    def test_unchanged_neutral_common_cell_state(self):
        old = NeutralCircuit(self.old, condition="A", seed=31001)
        new = NeutralCircuit(self.new, condition="A", seed=31001)
        old.run_until(100_000)
        new.run_until(100_000)
        self.assertEqual(old.boundary.checkpoint(), new.boundary.checkpoint())
        self.assertEqual(old.spikes, new.spikes)
        for sid in old.source_ids:
            i, j = old.dynamic_of_source[sid], new.dynamic_of_source[sid]
            self.assertEqual(float(old.v_mv[i]), float(new.v_mv[j]))
            self.assertEqual(float(old.syn_pa[i]), float(new.syn_pa[j]))
        for sid in ADDED_VISUAL_IDS:
            self.assertIn(sid, new.dynamic_of_source)
            i = new.dynamic_of_source[sid]
            self.assertEqual(float(new.v_mv[i]), float(new.rest_mv[i]))

    def test_added_effect_disconnection_keeps_anatomy(self):
        connected = VisualBoundaryProbe(self.new, seed=31001)
        control = VisualBoundaryProbe(self.new, seed=31001)
        self.assertEqual({connected.reference_pa(sid) for sid in ADDED_VISUAL_IDS}, {15.0})
        removed = control.apply_disconnection("aMe12_to_KC")
        self.assertEqual(len(removed), 48)
        self.assertEqual(len(connected.circuit.connections), len(control.circuit.connections))
        self.assertEqual(sum(len(x) for x in connected.outgoing) -
                         sum(len(x) for x in control.outgoing), 48)
        connected.set_current(ADDED_VISUAL_IDS, 30.0)
        control.set_current(ADDED_VISUAL_IDS, 30.0)
        connected.run_until(50_000)
        control.run_until(50_000)
        self.assertEqual([s for s in connected.spikes if s[1] in ADDED_VISUAL_IDS],
                         [s for s in control.spikes if s[1] in ADDED_VISUAL_IDS])
        self.assertFalse(control.plasticity_enabled)


if __name__ == "__main__":
    unittest.main()
