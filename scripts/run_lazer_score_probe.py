"""Run score vectors through the pinned osu!mania ScoreProcessor."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "work" / "osu_lazer_reference"
PINNED_COMMIT = "da27300fcbfa246f87c3ba1a14cbd00b68c7e9a9"
TEST_PROJECT = SOURCE_ROOT / "osu.Game.Rulesets.Mania.Tests" / "osu.Game.Rulesets.Mania.Tests.csproj"
TEST_SOURCE = ROOT / "scripts" / "lazer_score_probe" / "L0ScoreProbe.cs"
INJECTED_SOURCE = TEST_PROJECT.parent / "L0ScoreProbe.cs"
FIXTURE = ROOT / "tests" / "fixtures" / "lazer_score_v2_vectors.json"
OUTPUT = ROOT / "work" / "lazer_score_probe.json"
REPEAT_OUTPUT = ROOT / "work" / "lazer_score_probe_repeat.json"
DOTNET = shutil.which("dotnet") or "C:/Program Files/dotnet/dotnet.exe"


def _run_once(path: Path, base_environment: dict[str, str]) -> tuple[int, dict[str, Any] | None]:
    path.unlink(missing_ok=True)
    environment = base_environment.copy()
    environment["LAZER_SCORE_OUTPUT"] = str(path.resolve())
    command = [
        DOTNET, "test", str(TEST_PROJECT), "-c", "Release", "--no-restore",
        "--filter", "FullyQualifiedName~L0ScoreProbe.GeneratePinnedScoreVectors",
        "-m:1", "/nodeReuse:false", "-p:BuildInParallel=false",
        "-p:RunAnalyzers=false", "--logger", "console;verbosity=normal",
        "-clp:ErrorsOnly",
    ]
    completed = subprocess.run(
        command, cwd=TEST_PROJECT.parent, env=environment,
        capture_output=True, text=True,
    )
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    if completed.returncode != 0:
        return completed.returncode, None
    if not path.is_file():
        print(f"Score probe did not create {path}.", file=sys.stderr)
        return 1, None
    return 0, json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write-fixture", action="store_true",
        help="write the C# output to the frozen fixture (only for initial vector creation)",
    )
    args = parser.parse_args()
    if not TEST_PROJECT.is_file() or not TEST_SOURCE.is_file():
        print("Pinned source or score probe is missing.", file=sys.stderr)
        return 2

    revision = subprocess.run(
        ["git", "-C", str(SOURCE_ROOT), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    if revision != PINNED_COMMIT:
        print(f"Expected pinned lazer commit {PINNED_COMMIT}, got {revision}.", file=sys.stderr)
        return 2

    injected_before = INJECTED_SOURCE.exists()
    if injected_before and INJECTED_SOURCE.read_bytes() != TEST_SOURCE.read_bytes():
        print(f"Refusing to overwrite a different file: {INJECTED_SOURCE}", file=sys.stderr)
        return 2

    work = ROOT / "work"
    appdata = work / "dotnet_appdata"
    work.mkdir(parents=True, exist_ok=True)
    (work / "tmp").mkdir(parents=True, exist_ok=True)
    INJECTED_SOURCE.write_bytes(TEST_SOURCE.read_bytes())
    environment = os.environ.copy()
    environment.update({
        "DOTNET_CLI_HOME": str(work / "dotnet_cli_home"),
        "NUGET_PACKAGES": str(work / "nuget_packages_online"),
        "APPDATA": str(appdata),
        "TEMP": str(work / "tmp"),
        "TMP": str(work / "tmp"),
        "DOTNET_SKIP_FIRST_TIME_EXPERIENCE": "1",
        "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
        "DOTNET_PROCESSOR_COUNT": "2",
    })

    try:
        code, first = _run_once(OUTPUT, environment)
        if code != 0 or first is None:
            return code or 1
        code, repeated = _run_once(REPEAT_OUTPUT, environment)
        if code != 0 or repeated is None:
            return code or 1
        if first != repeated:
            print("Score vectors changed across identical pinned runs.", file=sys.stderr)
            return 1
        if first.get("reference", {}).get("commit") != PINNED_COMMIT:
            print("Score vector output identifies the wrong pinned commit.", file=sys.stderr)
            return 1

        if args.write_fixture:
            FIXTURE.write_text(json.dumps(first, indent=2) + "\n", encoding="utf-8")
            print(f"Wrote frozen C# score vectors to {FIXTURE}.")
            return 0

        if not FIXTURE.is_file():
            print(f"Frozen score vectors are missing: {FIXTURE}", file=sys.stderr)
            return 2
        expected = json.loads(FIXTURE.read_text(encoding="utf-8"))
        if first != expected:
            print("Pinned C# score output differs from the frozen fixture.", file=sys.stderr)
            return 1
        print(f"PASS: pinned score vectors repeated identically and match {FIXTURE}.")
        return 0
    finally:
        if not injected_before:
            INJECTED_SOURCE.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
