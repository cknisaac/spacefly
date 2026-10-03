"""Compare the 4K tap model with the pinned osu!lazer ReplayPlayer and scorer."""

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
PINNED_COMMIT = "da27300fcbfa246f87c3ba1a14cbd00b68c7e9a9"
SOURCE_ROOT = ROOT / "work" / "osu_lazer_reference"
TEST_PROJECT = SOURCE_ROOT / "osu.Game.Rulesets.Mania.Tests" / "osu.Game.Rulesets.Mania.Tests.csproj"
TEST_SOURCE = ROOT / "scripts" / "lazer_4k_probe" / "L0FourKScoreProbe.cs"
INJECTED_SOURCE = TEST_PROJECT.parent / "L0FourKScoreProbe.cs"
CORPUS = ROOT / "tests" / "fixtures" / "lazer_mvp_4k_score_scenarios.json"
FIXTURE = ROOT / "tests" / "fixtures" / "lazer_mvp_4k_score_reference.json"
OUTPUT = ROOT / "work" / "lazer_4k_score_probe.jsonl"
REPEAT_OUTPUT = ROOT / "work" / "lazer_4k_score_probe_repeat.jsonl"
DOTNET = shutil.which("dotnet") or "C:/Program Files/dotnet/dotnet.exe"

sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
from run_lazer_runtime_probe import (  # noqa: E402
    _normalize_scenario_trace,
    _without_observed_times,
)
from project_b.osu import ManiaHitWindows  # noqa: E402


def _run_once(path: Path, base_environment: dict[str, str]) -> tuple[int, list[dict[str, Any]]]:
    path.unlink(missing_ok=True)
    environment = base_environment.copy()
    environment["LAZER_4K_SCORE_OUTPUT"] = str(path.resolve())
    command = [
        DOTNET, "test", str(TEST_PROJECT), "-c", "Release", "--no-restore",
        "--filter", "FullyQualifiedName~L0FourKScoreProbe.RunFourKScoreScenariosThroughReplayPlayer",
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
        return completed.returncode, []
    if not path.is_file():
        print(f"4K probe did not create {path}.", file=sys.stderr)
        return 1, []
    return 0, [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _project_output(rows: list[dict[str, Any]], corpus: dict[str, Any]) -> dict[str, Any]:
    observed = {row["Id"]: row for row in rows}
    if set(observed) != {scenario["id"] for scenario in corpus["scenarios"]}:
        raise ValueError(f"unexpected 4K runtime rows: {sorted(observed)}")
    expiry = ManiaHitWindows.from_od(corpus["reference"]["od"], "lazer").expiry_offset_us
    scenarios = []
    for scenario in corpus["scenarios"]:
        runtime = observed[scenario["id"]]
        actions = [
            {"time_us": action["TimeUs"], "lane": action["Lane"], "kind": action["Kind"]}
            for action in sorted(runtime["Actions"], key=lambda action: action["Sequence"])
        ]
        if actions != scenario["actions"]:
            raise ValueError(
                f"captured Lazer key transitions differ for {scenario['id']}: "
                f"expected {scenario['actions']}, got {actions}"
            )
        trace = _normalize_scenario_trace(
            runtime, scenario, expiry, include_score=True,
        )
        scenarios.append({
            "id": scenario["id"],
            "notes": scenario["notes"],
            "actions": actions,
            "events": trace["events"],
        })
    return {
        "schema_version": 1,
        "reference": corpus["reference"],
        "scenarios": scenarios,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write-fixture", action="store_true",
        help="freeze the verified pinned-runtime output as a reference fixture",
    )
    args = parser.parse_args()
    if not TEST_PROJECT.is_file() or not TEST_SOURCE.is_file() or not CORPUS.is_file():
        print("Pinned source, scenario corpus, or 4K probe is missing.", file=sys.stderr)
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
    work.mkdir(parents=True, exist_ok=True)
    (work / "tmp").mkdir(parents=True, exist_ok=True)
    INJECTED_SOURCE.write_bytes(TEST_SOURCE.read_bytes())
    environment = os.environ.copy()
    environment.update({
        "DOTNET_CLI_HOME": str(work / "dotnet_cli_home"),
        "NUGET_PACKAGES": str(work / "nuget_packages_online"),
        "APPDATA": str(work / "dotnet_appdata"),
        "TEMP": str(work / "tmp"),
        "TMP": str(work / "tmp"),
        "DOTNET_SKIP_FIRST_TIME_EXPERIENCE": "1",
        "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
        "DOTNET_PROCESSOR_COUNT": "2",
        "LAZER_4K_SCORE_CORPUS": str(CORPUS.resolve()),
    })

    try:
        code, first_rows = _run_once(OUTPUT, environment)
        if code != 0:
            return code
        code, repeat_rows = _run_once(REPEAT_OUTPUT, environment)
        if code != 0:
            return code
        if _without_observed_times(first_rows) != _without_observed_times(repeat_rows):
            print("Pinned 4K action, judgement, or score output changed across repeated runs.",
                  file=sys.stderr)
            return 1

        corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
        projected = _project_output(first_rows, corpus)
        if args.write_fixture:
            FIXTURE.write_text(json.dumps(projected, indent=2, sort_keys=True) + "\n",
                               encoding="utf-8")
            print(f"Wrote pinned 4K replay and score reference to {FIXTURE}.")
            return 0

        if not FIXTURE.is_file():
            print(f"Pinned 4K reference fixture is missing: {FIXTURE}", file=sys.stderr)
            return 2
        expected = json.loads(FIXTURE.read_text(encoding="utf-8"))
        if _without_observed_times(projected) != _without_observed_times(expected):
            print("Pinned 4K event or score output differs from the frozen fixture.",
                  file=sys.stderr)
            return 1
        print(f"PASS: pinned 4K replay and Score V2 output repeat identically and match {FIXTURE}.")
        return 0
    except (KeyError, ValueError) as exc:
        print(f"4K probe validation failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if not injected_before:
            INJECTED_SOURCE.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
