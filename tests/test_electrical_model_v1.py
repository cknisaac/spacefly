"""Electrical Model V1 contract tests; no neutral gate or task training."""

from collections import Counter
from dataclasses import replace
import inspect
import itertools
import unittest

from project_b.electrical_v1 import DNBoundary, NeutralCircuit, UnknownEdgePolicy, build_circuit
from project_b.electrical_v1.boundary import STREAM_NAMES
from project_b.electrical_v1.source import parameter


class ElectricalModelV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.circuit = build_circuit()

    def test_source_identity_and_fail_closed_effects(self):
        c = self.circuit
        counts = c.counts()
        self.assertEqual((counts["neurons"], counts["source_pairs"], counts["source_contacts"]),
                         (115, 10009, 45010))
        self.assertEqual(counts["effect_pairs"], {
            "UNKNOWN": 9505, "ACTIVE_FAST": 184, "GRADED_INPUT": 106,
            "GRADED_OUTPUT": 106, "MODULATORY": 108})
        self.assertEqual(sum(e.contacts for e in c.connections if e.effect_state == "UNKNOWN"), 30168)
        self.assertTrue(all(e.weight_pa is None and e.effect_evidence == "UNKNOWN"
                            for e in c.connections if e.effect_state == "UNKNOWN"))
        unknown = next(e for e in c.connections if e.effect_state == "UNKNOWN")
        self.assertIsNone(UnknownEdgePolicy.electrical_weight(unknown))
        with self.assertRaises(ValueError):
            UnknownEdgePolicy.electrical_weight(replace(unknown, weight_pa=1.0))

    def test_plastic_contact_identity_is_anatomical_only(self):
        c = self.circuit
        candidates = [e for e in c.connections if e.candidate_contacts]
        self.assertEqual((len(candidates), sum(e.candidate_contacts for e in candidates)), (100, 796))
        self.assertEqual(len(c.candidate_partner_rows), 796)
        self.assertEqual(len(set(c.candidate_partner_rows)), 796)
        self.assertTrue(all(c.cells[e.pre].kind == "KC" and c.cells[e.post].kind == "MBON32"
                            and e.candidate_contacts <= e.contacts for e in candidates))
        self.assertFalse(NeutralCircuit(c, condition="B").plasticity_enabled)

    def test_cell_class_dispatch_and_dn_reference(self):
        model = NeutralCircuit(self.circuit, condition="A")
        self.assertEqual(Counter(model.kind), Counter({"KC": 107, "sensory": 3,
                                                        "MBON32": 1, "DNa03": 1, "DNa02": 1}))
        self.assertEqual(model.dn_reference_pa, (22.5, 30.0))
        self.assertEqual(float(model.cap_pf[model.dn3]), 30.0)
        self.assertEqual(float(model.cap_pf[model.dn2]), 40.0)
        self.assertNotEqual(float(model.cap_pf[model.dn3]), float(model.cap_pf[model.dn2]))
        for klass in model.circuit.config["spiking_classes"].values():
            for entry in klass.values():
                self.assertEqual(entry["evidence"], "ENGINEERING ASSUMPTION")
                parameter(entry)

    def test_effect_dispatch_and_mbon_disconnection(self):
        a = NeutralCircuit(self.circuit, condition="A")
        c = NeutralCircuit(self.circuit, condition="C")
        self.assertEqual(a.modulatory_pair_count, 108)
        self.assertEqual(c.modulatory_pair_count, 108)
        self.assertTrue(any(x < 0 for x in a.apl_out_coefficient))
        self.assertEqual(sum(len(x) for x in a.outgoing), 184 + 106)
        mbon = a.dynamic_of_source[519131]
        self.assertEqual({a.source_ids[x[0]] for x in a.outgoing[mbon]}, {519624, 523769})
        self.assertFalse(c.outgoing[mbon])
        self.assertEqual(len(a.circuit.connections), len(c.circuit.connections))

    def test_boundary_levels_support_and_normalization(self):
        for level, scale in (("low", .5), ("nominal", 1), ("high", 1.5)):
            b = DNBoundary(seed=31001, level=level)
            for signs in itertools.product((-1, 1), repeat=3):
                for name, sign in zip(STREAM_NAMES[:3], signs):
                    b.signs[name] = sign
                n3, n2 = b.normalized()
                self.assertEqual(n3, scale * (1 + .2*signs[0] + .2*signs[1]))
                self.assertEqual(n2, scale * (1 + .2*signs[0] + .2*signs[2]))
                self.assertGreaterEqual(min(n3, n2), .6*scale - 1e-12)
                self.assertLessEqual(max(n3, n2), 1.4*scale + 1e-12)
            self.assertEqual(b.currents_pa(22.5, 30.0), (n3*22.5, n2*30.0))

    def test_boundary_common_private_and_independent_marginals(self):
        shared = DNBoundary(seed=31001, level="nominal", control="shared")
        independent = DNBoundary(seed=31001, level="nominal", control="independent")
        # Enumerate fair stationary signs: same 1-D law, 0.5 versus zero
        # cross-correlation. This proves the construction without a random fit.
        def moments(mode):
            pairs = []
            for signs in itertools.product((-1, 1), repeat=5):
                b = shared if mode == "shared" else independent
                b.signs.update(dict(zip(STREAM_NAMES, signs)))
                pairs.append(b.normalized())
            mean = [sum(p[i] for p in pairs)/32 for i in (0, 1)]
            var = [sum((p[i]-mean[i])**2 for p in pairs)/32 for i in (0, 1)]
            cov = sum((p[0]-mean[0])*(p[1]-mean[1]) for p in pairs)/32
            return mean, var, cov
        ms, vs, cs = moments("shared")
        mi, vi, ci = moments("independent")
        self.assertEqual(ms, mi)
        self.assertAlmostEqual(vs[0], .08)
        self.assertAlmostEqual(vs[1], .08)
        self.assertEqual(vs, vi)
        self.assertAlmostEqual(cs / vs[0], .5)
        self.assertAlmostEqual(ci, 0)

    def test_autonomous_clock_pairing_reproducibility_and_resume(self):
        shared = DNBoundary(seed=31002, level="nominal")
        omitted = DNBoundary(seed=31002, level="nominal", control="omitted")
        independent = DNBoundary(seed=31002, level="nominal", control="independent")
        for t in (1000, 25000, 125000, 333333, 900000):
            for b in (shared, omitted, independent):
                b.advance_to(t)
            self.assertEqual(shared.checkpoint(), omitted.checkpoint())
            self.assertEqual(shared.checkpoint(), independent.checkpoint())
            self.assertEqual(omitted.normalized(), (0, 0))
        resumed = DNBoundary(seed=31002, level="nominal")
        resumed.restore(shared.checkpoint())
        shared.advance_to(2300000)
        resumed.advance_to(2300000)
        self.assertEqual(shared.checkpoint(), resumed.checkpoint())
        self.assertEqual(shared.normalized(), resumed.normalized())
        self.assertEqual(set(inspect.signature(DNBoundary).parameters), {"seed", "level", "control"})
        with self.assertRaises(TypeError):
            DNBoundary(seed=31001, level="nominal", reward=1)

    def test_tick_tie_order_and_checkpoint_replay(self):
        a = NeutralCircuit(self.circuit, condition="A", record_neurons=(519624,))
        mbon = a.dynamic_of_source[519131]
        # Force one controlled spike; exercise queue handling, not a gate run.
        a.v_mv[mbon] = 100.0
        a.boundary.next_flip_us["common"] = 1500
        first_sign = a.boundary.signs["common"]
        a.run_until(1000)
        self.assertIn((500, 519131), a.spikes)
        self.assertEqual(float(a.syn_pa[a.dn3]), 0.0)
        checkpoint = a.checkpoint()
        a.run_until(3000)
        replay = NeutralCircuit(self.circuit, condition="A", record_neurons=(519624,))
        replay.restore(checkpoint)
        replay.run_until(3000)
        self.assertEqual(a.checkpoint(), replay.checkpoint())
        self.assertEqual(a.boundary.signs["common"], -first_sign)
        self.assertGreater(a.delivered, 0)
        self.assertLess(float(a.syn_pa[a.dn3]), 0.0)
        self.assertFalse(a.plasticity_enabled)
        self.assertEqual(a.dan_state, 0.0)

    def test_apl_is_graded_and_neutral_interface_is_task_free(self):
        m = NeutralCircuit(self.circuit, condition="B")
        kc_source = next(c.source_id for c in self.circuit.cells if c.kind == "KC")
        kc = m.dynamic_of_source[kc_source]
        m.v_mv[kc] = 100.0
        m.run_until(1500)
        self.assertGreater(float(m.apl_local[kc]), 0)
        self.assertEqual(m.summary()["apl_spikes"], 0)
        self.assertEqual(m.summary()["ppl103_spikes"], 0)
        self.assertEqual(m.summary()["plasticity_enabled"], False)
        self.assertEqual(m.summary()["dn_refractory_bins_us"]["519624"], (0,))
        self.assertNotIn("reward", set(inspect.signature(NeutralCircuit).parameters))

    def test_short_numerical_refinement_without_gate_run(self):
        coarse = NeutralCircuit(self.circuit, condition="A", seed=31001)
        fine = NeutralCircuit(self.circuit, condition="A", seed=31001)
        fine.tick_us = 250  # Diagnostic refinement; does not alter frozen config.
        coarse.run_until(100_000)
        fine.run_until(100_000)
        self.assertEqual(coarse.boundary.checkpoint(), fine.boundary.checkpoint())
        self.assertEqual([sid for _, sid in coarse.spikes], [sid for _, sid in fine.spikes])
        self.assertTrue(all(abs(tc-tf) <= 500 for (tc, _), (tf, _) in zip(coarse.spikes, fine.spikes)))
        self.assertLess(max(abs(coarse.v_mv-fine.v_mv)), 0.5)

    def test_locked_controls_execute_short_implementation_steps(self):
        a = NeutralCircuit(self.circuit, condition="A", level="nominal", seed=31003)
        b = NeutralCircuit(self.circuit, condition="B", seed=31003)
        c = NeutralCircuit(self.circuit, condition="C", level="nominal", seed=31003)
        d = NeutralCircuit(self.circuit, condition="D", seed=31003)
        for model in (a, b, c, d):
            model.run_until(2000)
            self.assertEqual(model.summary()["time_us"], 2000)
        self.assertEqual(a.boundary.checkpoint(), b.boundary.checkpoint())
        self.assertEqual(a.boundary.checkpoint(), c.boundary.checkpoint())
        self.assertEqual(a.boundary.checkpoint(), d.boundary.checkpoint())
        self.assertEqual(b.boundary.normalized(), (0, 0))
        with self.assertRaises(ValueError):
            NeutralCircuit(self.circuit, condition="A", level="extra")


if __name__ == "__main__":
    unittest.main()
