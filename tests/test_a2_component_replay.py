"""Exact local continuation for existing motor/game owners."""

import unittest
import json
import tempfile
from pathlib import Path

from project_b.checkpoint import load_checkpoint, save_checkpoint
from project_b.motor import FixedMotorReadout
from project_b.mvp_c1 import CurrentPositionKCEncoder
from project_b.osu.environment import GameEnvironment
from project_b.osu.types import KeyAction, KeyActionKind, TapNote


class ComponentReplayTests(unittest.TestCase):
    def test_delayed_position_drive_and_cancellation_resume(self):
        first = CurrentPositionKCEncoder((10, 11, 12))
        first.observe(1000, "n1", 0.5)
        first.observe(2000, "n1", 0.6)
        state = first.state()
        resumed = CurrentPositionKCEncoder((10, 11, 12))
        resumed.restore(state)
        self.assertEqual(first.due_drive(26_000), resumed.due_drive(26_000))
        self.assertGreater(max(first.current_drive), 0)
        first.cancel(26_000, "n1")
        resumed.cancel(26_000, "n1")
        self.assertEqual(first.due_drive(27_000), resumed.due_drive(27_000))
        self.assertTrue(all(x == 0.0 for x in first.current_drive))
        self.assertEqual(first.state(), resumed.state())

    def test_canonical_bundle_rejects_identity_or_payload_drift(self):
        identity = {"candidate": "MVP-C1", "graph_sha256": "abc"}
        state = {"phase": "COMMITTED_TICK_AFTER_FEEDBACK_AND_LEDGER_FLUSH",
                 "time_us": 1000, "values": [0.1, -0.0, 2**53 + 1]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkpoint"
            save_checkpoint(path, identity, state)
            loaded = load_checkpoint(path, identity)
            self.assertEqual(loaded, state)
            self.assertEqual(loaded["values"][1].hex(), (-0.0).hex())
            with self.assertRaises(ValueError):
                load_checkpoint(path, {"candidate": "other"})
            payload = path / "state.json"
            tampered = json.loads(payload.read_text(encoding="utf-8"))
            tampered["time_us"] = 2000
            payload.write_text(json.dumps(tampered), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_checkpoint(path, identity)
    def test_motor_deque_and_cooldown_resume(self):
        original = FixedMotorReadout((0,), on_threshold=2, off_threshold=0)
        original.observe(1000, (0,))
        original.observe(2000, (0,))
        state = original.state()
        restored = FixedMotorReadout((0,), on_threshold=2, off_threshold=0)
        restored.restore(state)
        self.assertEqual(restored.state(), state)
        for t in (3000, 12000, 22000, 32000):
            self.assertEqual(original.observe(t, ()), restored.observe(t, ()))
        self.assertEqual(original.state(), restored.state())

    def test_game_expiry_and_action_ledger_resume(self):
        notes = (TapNote("n1", 0, 900_000), TapNote("n2", 0, 2_100_000))
        original = GameEnvironment(notes)
        original.advance_to(100_000)
        original.apply_action(KeyAction(800_000, 0, KeyActionKind.DOWN))
        state = original.state()
        restored = GameEnvironment(notes)
        restored.restore(state)
        self.assertEqual(restored.state(), state)
        actions = (KeyAction(820_000, 0, KeyActionKind.UP),
                   KeyAction(2_100_000, 0, KeyActionKind.DOWN))
        for action in actions:
            self.assertEqual(original.apply_action(action), restored.apply_action(action))
        self.assertEqual(original.finish(), restored.finish())
        bad = restored.state()
        bad["resolved_note_ids"] = ["unknown"]
        before = restored.state()
        with self.assertRaises(ValueError):
            restored.restore(bad)
        self.assertEqual(restored.state(), before)


if __name__ == "__main__":
    unittest.main()
