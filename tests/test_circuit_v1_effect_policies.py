"""Unknown-state, evidence, class-dynamics and exact policy-product tests."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

try:
    import pyarrow.parquet as pq
    from project_b.connectome.effect_policies import (
        BoundaryInputPolicy, ConnectionEffectPolicy, DelayPolicy,
        NeuronParameterPolicy, build_policy_product, require_runtime_ready,
    )
    from scripts.audit_circuit_v1_policies import audit
except ImportError:
    pq = None


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs/circuit_v1_effect_policies.json"
SUBSET = ROOT / "data/processed/malecns_v1_circuit_v1"
PRODUCT = ROOT / "data/processed/malecns_v1_circuit_v1_policy_v1"


@unittest.skipIf(pq is None, "Circuit V1 policies require optional pyarrow")
class CircuitV1EffectPolicyTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    def test_unknown_never_inherits_excitation_from_transmitter_or_count(self):
        policy = ConnectionEffectPolicy(self.config)
        edge = {"source_row": 999, "synapse_count": 500}
        unknown = policy.resolve(edge, "mbon01_gamma5_learning_output",
                                 "mbon26_output_relay", "glutamate")
        self.assertEqual(unknown["effect_state"], "UNKNOWN")
        self.assertIsNone(unknown["weight_mv"])
        gaba_unknown = policy.resolve(edge, "mbon32_competing_output",
                                      "dna02_action_boundary", "gaba")
        self.assertEqual(gaba_unknown["effect_state"], "UNKNOWN")
        self.assertIsNone(gaba_unknown["weight_mv"])
        ach_unknown = policy.resolve(edge, "mbon27_visual_output",
                                     "dna03_descending_relay", "acetylcholine")
        self.assertEqual(ach_unknown["effect_state"], "UNKNOWN")
        self.assertIsNone(ach_unknown["weight_mv"])
        known = policy.resolve(edge, "visual_kenyon_cells",
                               "mbon01_gamma5_learning_output", "acetylcholine")
        self.assertEqual((known["effect_state"], known["effect_evidence"]),
                         ("EXCITATORY", "LITERATURE-CONSTRAINED"))
        self.assertIsNone(known["weight_mv"])
        mod = policy.resolve(edge, "pam_gamma5_teaching_cohort",
                             "mbon01_gamma5_learning_output", "dopamine")
        self.assertEqual(mod["effect_state"], "MODULATORY")
        self.assertIsNone(mod["weight_mv"])

    def test_transmitter_guard_and_numeric_provenance_are_enforced(self):
        policy = ConnectionEffectPolicy(self.config)
        with self.assertRaisesRegex(ValueError, "Transmitter annotation conflicts"):
            policy.resolve({"source_row": 1}, "visual_kenyon_cells",
                           "mbon01_gamma5_learning_output", "glutamate")
        config = copy.deepcopy(self.config)
        config["connection_rules"][0]["weight_mv"] = 0.1
        with self.assertRaisesRegex(ValueError, "needs a provenance object"):
            ConnectionEffectPolicy(config)
        config["connection_rules"][0]["weight_mv"] = {
            "value": -0.1, "evidence": "ENGINEERING ASSUMPTION", "source": "test fixture"}
        with self.assertRaisesRegex(ValueError, "weight sign conflicts"):
            ConnectionEffectPolicy(config)
        config["connection_rules"][0]["weight_mv"]["value"] = 0.1
        resolved = ConnectionEffectPolicy(config).resolve(
            {"source_row": 1}, "visual_kenyon_cells",
            "mbon11_gamma1_learning_output", "acetylcholine")
        self.assertEqual(resolved["weight_mv"], 0.1)
        self.assertEqual(json.loads(resolved["weight_provenance"])["evidence"],
                         "ENGINEERING ASSUMPTION")

    def test_nonspiking_apl_unknown_parameters_and_delays(self):
        names = set(self.config["neuron_parameter_policy"]["role_families"])
        neurons = NeuronParameterPolicy(self.config, names)
        apl = neurons.resolve(10540, "apl_local_feedback", "gaba")
        kc = neurons.resolve(19102, "visual_kenyon_cells", "acetylcholine")
        self.assertIn("GRADED_LOCAL_NON_SPIKING", apl["model_kind"])
        self.assertNotEqual(apl["model_family"], kc["model_family"])
        self.assertEqual(apl["numeric_parameters_state"], "UNKNOWN")
        self.assertIsNone(apl["numeric_parameters_json"])
        delays = DelayPolicy(self.config, set(neurons.families))
        self.assertEqual(delays.resolve("APL")["delay_kind"], "GRADED_LOCAL")
        self.assertEqual(delays.resolve("DAN")["delay_kind"], "DOPAMINE_RELEASE")
        self.assertEqual(delays.resolve("KC")["delay_state"], "UNKNOWN")
        self.assertIsNone(delays.resolve("KC")["delay_us"])
        bad = copy.deepcopy(self.config)
        bad["neuron_parameter_policy"]["numeric_parameters"]["KC"] = {"tau_m_us": 10000}
        with self.assertRaisesRegex(ValueError, "needs a provenance object"):
            NeuronParameterPolicy(bad, names)
        bad = copy.deepcopy(self.config)
        bad["delay_policy"]["by_presynaptic_family"]["KC"] = {
            "kind": "CHEMICAL", "delay_state": "DECLARED", "delay_us": 2000,
            "evidence": "ENGINEERING ASSUMPTION"}
        with self.assertRaisesRegex(ValueError, "needs a provenance object"):
            DelayPolicy(bad, set(neurons.families))

    def test_boundary_cut_is_unknown_and_overlays_have_no_hidden_drive(self):
        roles = set(self.config["neuron_parameter_policy"]["role_families"])
        policy = BoundaryInputPolicy(self.config, roles)
        resolved = policy.resolve({"role": "dna02_action_boundary",
                                   "incoming_cut_pairs": 1135,
                                   "incoming_cut_contacts": 23643})
        self.assertEqual(resolved["missing_neural_drive_state"], "UNKNOWN")
        self.assertIsNone(resolved["missing_neural_drive_mv"])
        self.assertIsNone(resolved["interface_amplitude_mv"])
        self.assertEqual(resolved["interface_state"], "ARTIFICIAL_ACTION_READOUT_PENDING")
        bad = copy.deepcopy(self.config)
        bad["boundary_input_policy"]["missing_neural_drive_mv"] = 0.8
        with self.assertRaisesRegex(ValueError, "Omitted-neuron drive must remain UNKNOWN"):
            BoundaryInputPolicy(bad, roles)

    @unittest.skipUnless((SUBSET / "manifest.json").exists(), "Pinned MaleCNS subset unavailable")
    def test_production_product_is_deterministic_exact_and_not_runtime_ready(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "policy"
            manifest = build_policy_product(SUBSET, CONFIG_PATH, output)
            self.assertFalse(manifest["runtime_ready"])
            self.assertEqual(manifest["source_pairs"], 12153)
            self.assertEqual(manifest["effect_pairs"]["UNKNOWN"], 10960)
            self.assertEqual(manifest["numeric_edge_weights_assigned"], 0)
            self.assertEqual(manifest["numeric_delays_assigned"], 0)
            self.assertEqual(audit(SUBSET, CONFIG_PATH, output)["status"], "passed")
            current = json.loads((PRODUCT / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest, current)
            with self.assertRaisesRegex(ValueError, "UNKNOWN effects"):
                require_runtime_ready(
                    pq.read_table(output / "neuron_policy.parquet"),
                    pq.read_table(output / "connection_policy.parquet"),
                    json.loads((output / "boundary_policy.json").read_text(encoding="utf-8")),
                )


if __name__ == "__main__":
    unittest.main()
