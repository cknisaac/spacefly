"""Run a long-note replay comparison on the pinned osu!lazer test host."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from project_b.osu.config import OsuConfig  # noqa: E402
from project_b.osu.mania_game import ManiaGame, ManiaScore  # noqa: E402
from project_b.osu.types import HoldNote, KeyAction, KeyActionKind  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "work/osu_lazer_reference"
TEST_PROJECT = SOURCE / "osu.Game.Rulesets.Mania.Tests/osu.Game.Rulesets.Mania.Tests.csproj"
PROBE = ROOT / "scripts/lazer_hold_probe/L0HoldProbe.cs"
INJECTED = TEST_PROJECT.parent / PROBE.name
OUTPUT = ROOT / "work/lazer_hold_probe.jsonl"
PINNED = "da27300fcbfa246f87c3ba1a14cbd00b68c7e9a9"
DOTNET = shutil.which("dotnet") or "C:/Program Files/dotnet/dotnet.exe"
CASES = {
    "correct": [(1500, "down"), (4000, "up")],
    "no_input": [],
    "early_break_repress": [(1500, "down"), (1510, "up"),
                            (2500, "down"), (4000, "up")],
    "early_break": [(1500, "down"), (1510, "up")],
    "late_release": [(1500, "down"), (5250, "up")],
    "head_miss_tail_meh": [(4000, "down"), (4010, "up")],
}


def _compare(rows: list[dict]) -> None:
    if {row["id"] for row in rows} != set(CASES):
        raise AssertionError("pinned host returned unexpected scenarios")
    for row in rows:
        note = HoldNote("hold", 0, 1_500_000, 4_000_000)
        game = ManiaGame([note], OsuConfig(od=8, ruleset="lazer"))
        for ms, kind in CASES[row["id"]]:
            game.apply_action(KeyAction(ms * 1000, 0, KeyActionKind(kind)))
        final = game.finish()
        scorer = ManiaScore([note])
        actual = []
        for event in game.results:
            scorer.add(event)
            snapshot = scorer.snapshot()
            actual.append((event.component, event.result.replace("_", ""),
                           snapshot.combo, snapshot.score, snapshot.accuracy))
        expected = [(event["component"], event["result"], event["combo_after"],
                     event["score"], event["accuracy"])
                    for event in row["results"]]
        if len(actual) != len(expected):
            raise AssertionError(f"{row['id']}: event count {len(actual)} != {len(expected)}")
        for index, (one, two) in enumerate(zip(actual, expected)):
            if one[:4] != two[:4] or abs(one[4] - two[4]) > 1e-12:
                raise AssertionError(f"{row['id']} event {index}: Python {one} != lazer {two}")
        if (final.score, final.combo) != (row["score"], row["combo"]):
            raise AssertionError(f"{row['id']}: final score/combo mismatch")


def main() -> int:
    revision = subprocess.run(["git", "-C", str(SOURCE), "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
    if revision != PINNED:
        raise ValueError(f"wrong osu!lazer reference revision: {revision}")
    if INJECTED.exists() and INJECTED.read_bytes() != PROBE.read_bytes():
        raise ValueError(f"refusing to overwrite {INJECTED}")
    already_present = INJECTED.exists()
    INJECTED.write_bytes(PROBE.read_bytes())
    OUTPUT.unlink(missing_ok=True)
    environment = os.environ.copy()
    work = ROOT / "work"
    environment.update({
        "DOTNET_CLI_HOME": str(work / "dotnet_cli_home"),
        "NUGET_PACKAGES": str(work / "nuget_packages_online"),
        "APPDATA": str(work / "dotnet_appdata"),
        "TEMP": str(work / "tmp"),
        "TMP": str(work / "tmp"),
        "DOTNET_SKIP_FIRST_TIME_EXPERIENCE": "1",
        "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
        "DOTNET_PROCESSOR_COUNT": "2",
        "LAZER_HOLD_OUTPUT": str(OUTPUT),
    })
    try:
        completed = subprocess.run(
            [DOTNET, "test", str(TEST_PROJECT), "-c", "Release", "--no-restore",
             "--filter", "FullyQualifiedName~L0HoldProbe.RunLongNoteScenariosThroughReplayPlayer",
             "-m:1", "/nodeReuse:false", "-p:BuildInParallel=false",
             "-p:RunAnalyzers=false", "--logger", "console;verbosity=normal",
             "-clp:ErrorsOnly"],
            cwd=TEST_PROJECT.parent, env=environment, capture_output=True, text=True,
        )
        print(completed.stdout)
        print(completed.stderr, file=sys.stderr)
        if completed.returncode != 0:
            return completed.returncode
        rows = [json.loads(line) for line in OUTPUT.read_text(encoding="utf-8").splitlines()]
        _compare(rows)
        for row in rows:
            print(f"PASS: {row['id']} matched {len(row['results'])} results, score {row['score']}")
        return 0
    finally:
        if not already_present:
            INJECTED.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
