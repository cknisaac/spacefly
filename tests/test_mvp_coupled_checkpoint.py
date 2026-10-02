"""A2.2/A2.3 causal full-runner continuation and fresh frozen evaluation gates."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from project_b.checkpoint.frozen import FrozenPolicySnapshot
from project_b.mvp_c1.feedback import FirstActionOutcome, NoteWindow
from project_b.mvp_c1.runtime import MvpSession
from project_b.mvp_c1.source import load_mvp_circuit


ROOT = Path(__file__).resolve().parents[1]


class CoupledCheckpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.circuit = load_mvp_circuit(ROOT)

    def test_coupled_cut_with_chemical_apl_and_sensory_pending(self):
        circuit = self.circuit
        with tempfile.TemporaryDirectory() as directory:
            self._check_coupled(circuit, Path(directory))

    def _check_coupled(self, circuit, tmp_path):
        notes = (NoteWindow("fresh-1", 100_000, 900_000),)
        uninterrupted = MvpSession(circuit, ROOT, notes, seed=11)
        uninterrupted.run_until(139_000)
        self.assertTrue(uninterrupted.chemical_queue and uninterrupted.apl_queue)
        self.assertTrue(uninterrupted.encoder._queue)
        self.assertEqual(uninterrupted.circuit.category_counts["UNKNOWN_QUARANTINED_NO_CURRENT"], (
            7793, 13122)
        )
        cut_state = uninterrupted.state()
        path = tmp_path / "committed-cut"
        uninterrupted.save(path)
        restored = MvpSession(circuit, ROOT, notes, seed=11)
        restored.load(path)
        self.assertEqual(restored.state(), cut_state)
        uninterrupted.run_until(1_100_000)
        restored.run_until(1_100_000)
        self.assertEqual(restored.ledger_bytes(), uninterrupted.ledger_bytes())
        self.assertEqual(restored.state(), uninterrupted.state())
        self.assertTrue(any(row[0] == "motor" for row in restored.ledger))
        self.assertTrue(any(row[0] == "game_event" for row in restored.ledger))
        self.assertTrue(any(row[0] == "feedback_decision" for row in restored.ledger))
        self.assertGreater(restored.delivered_chemical, cut_state["neural_diagnostic_counters"][0])
        self.assertGreater(restored.delivered_apl, cut_state["neural_diagnostic_counters"][1])

        wrong_seed = MvpSession(circuit, ROOT, notes, seed=12)
        with self.assertRaisesRegex(ValueError, "identity"):
            wrong_seed.load(path)
        self.assertEqual(wrong_seed.time_us, 0)
        corrupt = deepcopy(cut_state)
        corrupt["apl_graded_state"] = float("nan")
        before = restored.state()
        with self.assertRaisesRegex(ValueError, "invalid MVP"):
            restored.restore(corrupt)
        self.assertEqual(restored.state(), before)


    def test_frozen_policy_starts_fresh_and_runs_two_notes(self):
        circuit = self.circuit
        self._check_frozen(circuit)

    def test_controlled_pending_feedback_continues_through_pam_current(self):
        """A controlled outcome probes the pending owner without claiming task success."""
        notes = (NoteWindow("fresh-1", 100_000, 900_000),)
        left = MvpSession(self.circuit, ROOT, notes, seed=11)
        left.run_until(139_000)
        left.task.feedback.resolve(FirstActionOutcome(
            "fresh-1", 139_000, -90_000, "early_judged", "early_miss", 0), 139_000)
        left._flush_task_events()
        self.assertIsNotNone(left.task.feedback.pending_early)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pending-feedback-cut"
            left.save(path)
            right = MvpSession(self.circuit, ROOT, notes, seed=11)
            right.load(path)
            left.run_until(170_000)
            right.run_until(170_000)
            self.assertEqual(left.ledger_bytes(), right.ledger_bytes())
            self.assertEqual(left.state(), right.state())
            self.assertEqual(len(left.task.feedback.pulse_records), 1)
            self.assertEqual(left.task.feedback.pulse_records[0].start_us, 164_000)

    def test_post_action_cut_preserves_game_and_first_action_owner(self):
        notes = (NoteWindow("fresh-1", 100_000, 900_000),)
        left = MvpSession(self.circuit, ROOT, notes, seed=11)
        left.run_until(191_000)
        self.assertTrue(left.task.game.result().actions)
        self.assertTrue(left.task.feedback.decisions)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "post-action-cut"
            left.save(path)
            right = MvpSession(self.circuit, ROOT, notes, seed=11)
            right.load(path)
            self.assertEqual(left.state(), right.state())
            left.run_until(220_000)
            right.run_until(220_000)
            self.assertEqual(left.ledger_bytes(), right.ledger_bytes())
            self.assertEqual(left.state(), right.state())

    def _check_frozen(self, circuit):
        template_notes = (NoteWindow("template", 100_000, 900_000),)
        donor = MvpSession(circuit, ROOT, template_notes, seed=11)
        selected_kc = next(iter(sorted(donor.rule.mask.by_kc)))
        original = donor.rule.state()["selected_plastic_weights_by_kc_source_id"][str(selected_kc)]
        donor.rule.observe_spikes(1_000, [donor.index[selected_kc]])
        donor.rule.observe_spikes(2_000, [donor.index[circuit.pam_ids[0]]])
        policy = FrozenPolicySnapshot.capture(donor.rule)
        changed = dict(policy.selected_weights)[selected_kc]
        self.assertNotEqual(changed, original)

        fresh_notes = (NoteWindow("new-1", 100_000, 900_000),
                       NoteWindow("new-2", 1_300_000, 2_100_000))
        run = MvpSession(circuit, ROOT, fresh_notes, seed=11, frozen_policy=policy)
        clean = MvpSession(circuit, ROOT, fresh_notes, seed=11, frozen_policy=policy)
        self.assertEqual(run.state(), clean.state())
        self.assertTrue(all(value == [0.0, 0] for value in
                            run.rule.state()["kc_trace_value_and_last_update_us"].values()))
        self.assertEqual(run.task.feedback.pam_current(0), 0)
        self.assertFalse(run.rule.enabled or run.task.teaching_enabled)
        initial_weights = run.rule.state()["selected_plastic_weights_by_kc_source_id"]
        run.run_until(2_200_000)
        self.assertEqual(run.rule.state()["selected_plastic_weights_by_kc_source_id"],
                         initial_weights)
        self.assertEqual(len(run.task.game.result().judgements), 2)
        self.assertGreaterEqual(len(run.task.first_action.outcomes), 1)
        self.assertTrue(all(d.pam_request == 0 for d in run.task.feedback.decisions))
        self.assertFalse(run.task.feedback.pulse_records)
        self.assertEqual(clean.time_us, 0)
        self.assertEqual(clean.spike_counts.sum(), 0)


if __name__ == "__main__":
    unittest.main()
