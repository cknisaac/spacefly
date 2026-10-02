"""B5 probe-overlay invariants, independent of causal panel outcomes."""

import hashlib
import math
from pathlib import Path
import unittest

import numpy as np

from project_b.electrical_v1 import NeutralCircuit, build_circuit
from project_b.electrical_v1.sensory_route_probe import SensoryRouteProbe, VISUAL_IDS


ROOT = Path(__file__).resolve().parents[1]
FROZEN_CONFIG_SHA = "fe7e0c488e5ce1beb3642cd003a19198e4f1d0758c6e6dd7ecb6c714bb935d0c"


class SensoryRouteProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.circuit = build_circuit()

    def test_frozen_config_and_zero_overlay_identity(self):
        sha = hashlib.sha256((ROOT / "configs/electrical_model_v1.json").read_bytes()).hexdigest()
        self.assertEqual(sha, FROZEN_CONFIG_SHA)
        base = NeutralCircuit(self.circuit, condition="A", level="nominal", seed=31001)
        probe = SensoryRouteProbe(self.circuit, seed=31001)
        base.run_until(100_000)
        probe.run_until(100_000)
        np.testing.assert_array_equal(base.v_mv, probe.v_mv)
        np.testing.assert_array_equal(base.syn_pa, probe.syn_pa)
        self.assertEqual(base.spikes, probe.spikes)
        self.assertEqual(base.boundary.checkpoint(), probe.boundary.checkpoint())
        self.assertEqual(self.circuit.counts()["source_pairs"], 10009)
        self.assertFalse(probe.plasticity_enabled)

    def test_declared_current_uses_class_reference_and_passive_solution(self):
        probe = SensoryRouteProbe(self.circuit, seed=31001)
        self.assertEqual([probe.reference_pa(x) for x in VISUAL_IDS], [15.0]*3)
        kc_id = next(c.source_id for c in self.circuit.cells if c.kind == "KC")
        self.assertEqual(probe.reference_pa(kc_id), 7.0)
        self.assertEqual(probe.reference_pa(519131), 15.0)
        probe.set_current(VISUAL_IDS, 15.0)
        probe.run_until(500)
        expected = -60 + 15*(1-math.exp(-.5/10))
        for source_id in VISUAL_IDS:
            self.assertAlmostEqual(probe.v_mv[probe.dynamic_of_source[source_id]], expected, places=12)
        probe.clear_current()
        self.assertFalse(np.any(probe.injected_pa))
        with self.assertRaises(ValueError):
            probe.set_current((519624,), 15)

    def test_named_disconnections_preserve_source_anatomy(self):
        for name, expected in (("visual_to_KC", 76), ("KC_to_MBON32", 105),
                               ("MBON32_to_DNs", 2)):
            probe = SensoryRouteProbe(self.circuit, seed=31001)
            before = len(probe.circuit.connections)
            removed = probe.apply_disconnection(name)
            self.assertEqual(len(removed), expected)
            self.assertEqual(len(set(removed)), expected)
            self.assertEqual(len(probe.circuit.connections), before)
            with self.assertRaises(ValueError):
                probe.apply_disconnection(name)

    def test_unperturbed_checkpoint_clone_and_event_logging(self):
        first = SensoryRouteProbe(self.circuit, seed=31002)
        first.run_until(100_000)
        state = first.checkpoint()
        second = SensoryRouteProbe(self.circuit, seed=31002)
        second.restore(state)
        first.set_current(VISUAL_IDS, 30.0)
        second.set_current(VISUAL_IDS, 30.0)
        first.run_until(200_000)
        second.run_until(200_000)
        self.assertEqual(first.spikes, second.spikes)
        self.assertEqual(first.delivered_event_log, second.delivered_event_log)
        self.assertEqual(first.boundary.checkpoint(), second.boundary.checkpoint())
        np.testing.assert_array_equal(first.v_mv, second.v_mv)


if __name__ == "__main__":
    unittest.main()
