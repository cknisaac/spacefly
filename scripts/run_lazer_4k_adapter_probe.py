"""Run headless 4K position episodes through the pinned in-process Lazer host."""

from __future__ import annotations

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
DOTNET = shutil.which("dotnet") or "C:/Program Files/dotnet/dotnet.exe"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
from lazer_4k_adapter_harness import build_episode, load_fixture  # noqa: E402
from project_b.osu import ManiaHitWindows  # noqa: E402
from run_lazer_runtime_probe import (  # noqa: E402
    _normalize_scenario_trace,
    _without_observed_times,
)


def _run_once(
    path: Path, episodes_path: Path, base_environment: dict[str, str],
) -> tuple[int, list[dict[str, Any]]]:
    path.unlink(missing_ok=True)
    environment = base_environment.copy()
    environment["LAZER_4K_ADAPTER_OUTPUT"] = str(path.resolve())
    command = [
        DOTNET, "test", str(TEST_PROJECT), "-c", "Release", "--no-restore",
        "--filter", "FullyQualifiedName~L0FourKScoreProbe.RunHeadlessFourKEpisodesThroughReplayPlayer",
        "-m:1", "/nodeReuse:false", "-p:BuildInParallel=false",
        "-p:RunAnalyzers=false", "--logger", "console;verbosity=normal",
        "-clp:ErrorsOnly",
    ]
    environment["LAZER_4K_ADAPTER_EPISODES"] = str(episodes_path.resolve())
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
        print(f"In-process Lazer probe did not create {path}.", file=sys.stderr)
        return 1, []
    return 0, [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _assert_reference(actual: Any, expected: Any, path: str = "root") -> None:
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(actual) != set(expected):
            raise ValueError(f"{path}: object fields differ")
        for key in expected:
            _assert_reference(actual[key], expected[key], f"{path}.{key}")
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise ValueError(f"{path}: list lengths differ")
        for index, (actual_item, expected_item) in enumerate(zip(actual, expected)):
            _assert_reference(actual_item, expected_item, f"{path}[{index}]")
    elif isinstance(expected, (int, float)) and not isinstance(expected, bool):
        if not isinstance(actual, (int, float)) or isinstance(actual, bool):
            raise ValueError(f"{path}: expected numeric value")
        if abs(actual - expected) > 1e-12:
            raise ValueError(f"{path}: expected {expected!r}, got {actual!r}")
    elif actual != expected:
        raise ValueError(f"{path}: expected {expected!r}, got {actual!r}")


def _expected_episode_events(episode: dict[str, Any]) -> list[dict[str, Any]]:
    scores = {event["note_id"]: event for event in episode["score"]["events"]}
    csharp_score_fields = {
        "base_accuracy_points", "maximum_accuracy_points", "combo_before",
        "combo_after", "highest_combo_after", "accuracy_numerator",
        "accuracy_denominator", "accuracy_judgement_count", "accuracy",
        "minimum_accuracy", "maximum_accuracy", "combo_score_portion",
        "total_score_without_mods", "total_score", "total_score_delta",
        "maximum_total_score", "maximum_combo",
    }
    expected = []
    for event in episode["events"]:
        row = dict(event)
        if row["kind"] == "judgement":
            score = scores[row["note_id"]]
            row["score"] = {field: score[field] for field in csharp_score_fields}
        expected.append(row)
    return expected


def _normalize_runtime(
    rows: list[dict[str, Any]], episodes: dict[str, dict[str, Any]], fixture: dict[str, Any],
) -> dict[str, Any]:
    observed = {row["Id"]: row for row in rows}
    if set(observed) != set(episodes):
        raise ValueError(f"unexpected runtime episode IDs: {sorted(observed)}")
    expiry = ManiaHitWindows.from_od(fixture["reference"]["od"], "lazer").expiry_offset_us
    output = []
    for scenario in fixture["scenarios"]:
        episode_id = scenario["id"]
        episode = episodes[episode_id]
        runtime = observed[episode_id]
        expected_actions = [
            {"time_us": row["time_us"], "lane": row["lane"], "kind": row["kind"]}
            for row in episode["game_actions"]
        ]
        captured_actions = [
            {"time_us": row["TimeUs"], "lane": row["Lane"], "kind": row["Kind"]}
            for row in sorted(runtime["Actions"], key=lambda item: item["Sequence"])
        ]
        if captured_actions != expected_actions:
            raise ValueError(
                f"{episode_id}: Lazer key transitions differ from headless actions: "
                f"expected {expected_actions}, got {captured_actions}"
            )
        scenario_for_normalizer = {
            "id": episode_id,
            "notes": episode["beatmap_notes"],
            "actions": expected_actions,
        }
        normalized = _normalize_scenario_trace(
            runtime, scenario_for_normalizer, expiry, include_score=True,
        )
        expected_events = _expected_episode_events(episode)
        _assert_reference(
            _without_observed_times(normalized["events"]),
            _without_observed_times(expected_events),
            f"{episode_id}.events",
        )
        output.append({"id": episode_id, "events": normalized["events"]})
    return {"schema_version": 1, "reference": fixture["reference"], "scenarios": output}


def main() -> int:
    fixture = load_fixture()
    if fixture["reference"]["commit"] != PINNED_COMMIT:
        print("Adapter scenario fixture is not pinned to the expected lazer commit.", file=sys.stderr)
        return 2
    if not TEST_PROJECT.is_file() or not TEST_SOURCE.is_file():
        print("Pinned source or 4K ReplayPlayer probe is missing.", file=sys.stderr)
        return 2
    revision = subprocess.run(
        ["git", "-C", str(SOURCE_ROOT), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    if revision != PINNED_COMMIT:
        print(f"Expected pinned lazer commit {PINNED_COMMIT}, got {revision}.", file=sys.stderr)
        return 2

    work = ROOT / "work"
    work.mkdir(parents=True, exist_ok=True)
    (work / "tmp").mkdir(parents=True, exist_ok=True)
    episodes = {
        scenario["id"]: build_episode(scenario).as_dict()
        for scenario in fixture["scenarios"]
    }
    episodes_path = work / "lazer_4k_adapter_episodes.json"
    episodes_path.write_text(json.dumps({
        "schema_version": 1,
        "reference": fixture["reference"],
        "episodes": [
            {"id": scenario_id, "episode": episode}
            for scenario_id, episode in episodes.items()
        ],
    }, separators=(",", ":")), encoding="utf-8")

    injected_before = INJECTED_SOURCE.exists()
    if injected_before and INJECTED_SOURCE.read_bytes() != TEST_SOURCE.read_bytes():
        print(f"Refusing to overwrite a different file: {INJECTED_SOURCE}", file=sys.stderr)
        return 2
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
    })
    first_path = work / "lazer_4k_adapter_probe.jsonl"
    repeat_path = work / "lazer_4k_adapter_probe_repeat.jsonl"
    try:
        code, first = _run_once(first_path, episodes_path, environment)
        if code != 0:
            return code
        code, repeated = _run_once(repeat_path, episodes_path, environment)
        if code != 0:
            return code
        if _without_observed_times(first) != _without_observed_times(repeated):
            raise ValueError("in-process Lazer output changed across identical episodes")
        normalized = _normalize_runtime(first, episodes, fixture)
        normalized_path = work / "lazer_4k_adapter_normalized.json"
        normalized_path.write_text(json.dumps(normalized, indent=2, sort_keys=True) + "\n",
                                   encoding="utf-8")
        print(
            "PASS: headless 4K position episodes match pinned in-process Lazer actions, "
            f"normalized events, and Score V2 on both runs. Raw captures: {first_path}, {repeat_path}."
        )
        return 0
    except (KeyError, ValueError) as exc:
        print(f"4K adapter parity failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if not injected_before:
            INJECTED_SOURCE.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
