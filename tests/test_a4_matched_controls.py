"""A4 matched starts, declared switches and causal control-ledger invariants."""

from __future__ import annotations

import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from project_b.mvp_c1.control_manifest import create_manifest, validate_pair_start
from project_b.mvp_c1.controls import ControlPolicy, PamControlRouter
from project_b.mvp_c1.feedback import FirstActionOutcome, NoteWindow, PamPulse
from project_b.mvp_c1.runtime import MvpSession
from project_b.mvp_c1.source import load_mvp_circuit


ROOT = Path(__file__).resolve().parents[1]
NOTES = (NoteWindow("n1", 100_000, 900_000),
         NoteWindow("n2", 1_300_000, 2_100_000))
POLICIES = {
    "baseline": ControlPolicy(),
    "plasticity_off": ControlPolicy(plasticity="off"),
    "wrong_note": ControlPolicy(teaching="wrong_note"),
    "dan_disabled": ControlPolicy(dan="disabled"),
    "eligibility_disabled": ControlPolicy(eligibility="disabled"),
}


class MatchedControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.circuit = load_mvp_circuit(ROOT)

    def parent_and_arms(self, path, cut_us=139_000):
        parent = MvpSession(self.circuit, ROOT, NOTES, seed=11)
        parent.run_until(cut_us)
        sha = parent.save(path)
        arms = {}
        for name, policy in POLICIES.items():
            arm = MvpSession(self.circuit, ROOT, NOTES, seed=11)
            arm.load(path)
            arm.apply_controls(policy)
            arms[name] = arm
        manifest = create_manifest(parent, str(path), sha, POLICIES)
        return parent, arms, manifest

    def test_manifest_matched_start_and_fail_closed_mismatches(self):
        with tempfile.TemporaryDirectory() as directory:
            parent, arms, manifest = self.parent_and_arms(Path(directory) / "parent")
            for name, arm in arms.items():
                receipt = validate_pair_start(manifest, parent, name, arm)
                self.assertTrue(receipt["matched"])
                self.assertFalse(receipt["undeclared_start_differences"])
            other_seed = MvpSession(self.circuit, ROOT, NOTES, seed=12)
            other_seed.run_until(139_000)
            other_seed.apply_controls(POLICIES["dan_disabled"])
            with self.assertRaisesRegex(ValueError, "undeclared start differences"):
                validate_pair_start(manifest, parent, "dan_disabled", other_seed)
            arms["baseline"].motor.window_us += 1_000
            with self.assertRaisesRegex(ValueError, "motor.identity"):
                validate_pair_start(manifest, parent, "baseline", arms["baseline"])
            shifted_notes = (NOTES[0], NoteWindow("n2", 1_300_000, 2_101_000))
            shifted = MvpSession(self.circuit, ROOT, shifted_notes, seed=11)
            shifted.run_until(139_000)
            with self.assertRaisesRegex(ValueError, "renderer_and_note_schedule"):
                validate_pair_start(manifest, parent, "baseline", shifted)
            widened = deepcopy(manifest)
            widened["arms"]["baseline"]["allowed_start_differences"].append(
                "identity.renderer_and_note_schedule_sha256")
            with self.assertRaisesRegex(ValueError, "allowed-difference"):
                validate_pair_start(widened, parent, "baseline", parent)

    def test_controlled_request_separates_feedback_dan_and_weight_updates(self):
        with tempfile.TemporaryDirectory() as directory:
            parent, arms, manifest = self.parent_and_arms(Path(directory) / "parent")
            initial = parent.rule.state()["selected_plastic_weights_by_kc_source_id"]
            for name, arm in arms.items():
                validate_pair_start(manifest, parent, name, arm)
                # Synthetic A4 interface stimulus only: not a legal game action
                # and never interpreted as behavioral performance.
                arm.task.feedback.resolve(FirstActionOutcome(
                    "n1", 139_000, -761_000, "early_judged", "synthetic_fixture", 0),
                    139_000)
                arm._flush_task_events()
                arm.run_until(189_000)
            def kinds(name):
                return [row[0] for row in arms[name].ledger]
            self.assertIn("feedback_decision", kinds("baseline"))
            self.assertIn("pam_delivery", kinds("baseline"))
            self.assertIn("pam_actual_spikes", kinds("baseline"))
            self.assertIn("gamma4_batch", kinds("baseline"))
            self.assertNotEqual(arms["baseline"].rule.state()[
                "selected_plastic_weights_by_kc_source_id"], initial)
            self.assertEqual(arms["plasticity_off"].rule.state()[
                "selected_plastic_weights_by_kc_source_id"], initial)
            self.assertIn("pam_actual_spikes", kinds("plasticity_off"))
            self.assertEqual(arms["dan_disabled"].rule.state()[
                "selected_plastic_weights_by_kc_source_id"], initial)
            self.assertNotIn("pam_actual_spikes", kinds("dan_disabled"))
            self.assertIn("pam_delivery_suppressed", kinds("dan_disabled"))
            self.assertEqual(arms["eligibility_disabled"].rule.state()[
                "selected_plastic_weights_by_kc_source_id"], initial)
            self.assertIn("pam_actual_spikes", kinds("eligibility_disabled"))
            self.assertEqual(arms["wrong_note"].rule.state()[
                "selected_plastic_weights_by_kc_source_id"], initial)
            self.assertNotIn("pam_delivery", kinds("wrong_note"))
            self.assertTrue(arms["wrong_note"].pam_router.pending)

    def test_wrong_note_next_observed_cue_and_pending_checkpoint(self):
        pulse = PamPulse("n1", 164_000, 184_000, 1.0, "early_flush")
        router = PamControlRouter("wrong_note")
        self.assertEqual(router.advance_to(164_000, [pulse]), ())
        self.assertEqual(router.current(170_000), 0.0)
        restored = PamControlRouter("wrong_note")
        restored.restore(router.state(), [pulse])
        self.assertEqual(router.state(), restored.state())
        self.assertEqual(router.advance_to(1_200_000, [pulse], "n1"), ())
        self.assertEqual(restored.advance_to(1_200_000, [pulse], "n1"), ())
        for instance in (router, restored):
            delivered = instance.advance_to(1_300_000, [pulse], "n2")
            self.assertEqual(len(delivered), 1)
            self.assertEqual((delivered[0].origin_note_id,
                              delivered[0].recipient_note_id,
                              delivered[0].actual_start_us), ("n1", "n2", 1_300_000))
            self.assertEqual(instance.current(1_300_000), 2.0)
        self.assertEqual(router.state(), restored.state())
        with tempfile.TemporaryDirectory() as directory:
            _, arms, _ = self.parent_and_arms(Path(directory) / "parent")
            arm = arms["wrong_note"]
            arm.task.feedback.resolve(FirstActionOutcome(
                "n1", 139_000, -761_000, "early_judged", "synthetic_fixture", 0),
                139_000)
            arm._flush_task_events()
            arm.run_until(170_000)
            cut = Path(directory) / "pending_wrong_note"
            arm.save(cut)
            resumed = MvpSession(self.circuit, ROOT, NOTES, seed=11,
                                 controls=POLICIES["wrong_note"])
            resumed.load(cut)
            arm.run_until(185_000)
            resumed.run_until(185_000)
            self.assertEqual(arm.state(), resumed.state())

    def test_wrong_note_coupled_delivery_waits_for_actual_next_cue(self):
        with tempfile.TemporaryDirectory() as directory:
            _, arms, _ = self.parent_and_arms(Path(directory) / "parent")
            arm = arms["wrong_note"]
            arm.task.feedback.resolve(FirstActionOutcome(
                "a4-fixture", 139_000, -761_000, "early_judged",
                "synthetic_fixture", 0), 139_000)
            arm._flush_task_events()
            arm.run_until(1_320_000)
            routed = [row[1] for row in arm.ledger if row[0] == "pam_delivery" and
                      row[1]["origin_note_id"] == "a4-fixture"]
            self.assertEqual(len(routed), 1)
            self.assertEqual((routed[0]["source_start_us"],
                              routed[0]["actual_start_us"],
                              routed[0]["recipient_note_id"]),
                             (164_000, 1_300_000, "n2"))
            self.assertTrue(any(row[0] == "pam_actual_spikes" and row[1] >= 1_300_000
                                for row in arm.ledger))


if __name__ == "__main__":
    unittest.main()
