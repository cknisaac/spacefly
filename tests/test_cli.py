"""Config and deterministic headless CLI smoke tests."""

import json
import subprocess
import sys
import unittest
from pathlib import Path

from project_b.osu import load_config
from project_b.osu.cli import run_scenario

ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def test_base_config(self) -> None:
        config = load_config(ROOT / "configs" / "base.yaml")
        self.assertEqual(config.as_dict(),
                         {"keys": 4, "od": "8", "ruleset": "stable_native"})

    def test_chord_scenario_log_and_replay(self) -> None:
        config = ROOT / "configs" / "base.yaml"
        scenario = ROOT / "tests" / "fixtures" / "chord.json"
        first = run_scenario(config, scenario)
        second = run_scenario(config, scenario)
        self.assertEqual(first, second)
        self.assertEqual(first["total_notes"], 2)
        self.assertEqual([e["judgement"] for e in first["events"]
                          if e["type"] == "judgement"], ["MAX_320", "MAX_320"])
        command = [sys.executable, "-m", "project_b.osu.cli", str(scenario),
                   "--config", str(config)]
        output_a = subprocess.check_output(command, cwd=ROOT, text=True)
        output_b = subprocess.check_output(command, cwd=ROOT, text=True)
        self.assertEqual(output_a, output_b)
        self.assertEqual(json.loads(output_a), first)


if __name__ == "__main__":
    unittest.main()
