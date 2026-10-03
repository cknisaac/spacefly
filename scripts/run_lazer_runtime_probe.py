"""Run the frozen L0.9a corpus through osu!'s pinned mania replay test host."""

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
TEST_SOURCE = ROOT / "scripts" / "lazer_runtime_probe" / "L0ParityProbe.cs"
INJECTED_SOURCE = TEST_PROJECT.parent / "L0ParityProbe.cs"
CORPUS = ROOT / "tests" / "fixtures" / "lazer_od8_parity_corpus.json"
OUTPUT = ROOT / "work" / "lazer_runtime_reference_probe.jsonl"
REPEAT_OUTPUT = ROOT / "work" / "lazer_runtime_reference_probe_repeat.jsonl"
NORMALIZED_OUTPUT = ROOT / "work" / "lazer_runtime_normalized_trace.json"
DOTNET = shutil.which("dotnet") or "C:/Program Files/dotnet/dotnet.exe"
sys.path.insert(0, str(ROOT / "src"))
from project_b.osu import ManiaHitWindows  # noqa: E402


def _run_once(output_path: Path, environment: dict[str, str]) -> tuple[int, list[dict[str, Any]]]:
    output_path.unlink(missing_ok=True)
    run_environment = environment.copy()
    run_environment["LAZER_PARITY_OUTPUT"] = str(output_path.resolve())
    command = [
        DOTNET, "test", str(TEST_PROJECT), "-c", "Release", "--no-restore",
        "--filter", "FullyQualifiedName~L0ParityProbe",
        "-m:1", "/nodeReuse:false", "-p:BuildInParallel=false",
        "-p:RunAnalyzers=false", "--logger", "console;verbosity=normal",
        "-clp:ErrorsOnly",
    ]
    completed = subprocess.run(
        command, cwd=TEST_PROJECT.parent, env=run_environment,
        capture_output=True, text=True,
    )
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    if completed.returncode != 0:
        return completed.returncode, []
    rows = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
    return 0, rows


def _without_observed_times(value: Any) -> Any:
    if isinstance(value, dict):
        if (value.get("Result") == "MISS" and type(value.get("OffsetUs")) is int
                and value["OffsetUs"] > 127_500):
            value = {**value, "OffsetUs": None}
        return {key: _without_observed_times(item)
                for key, item in value.items()
                if key not in {"ObservedGameTimeUs", "observed_game_time_us"}}
    if isinstance(value, list):
        return [_without_observed_times(item) for item in value]
    return value


def _normalize_scenario_trace(
    runtime: dict[str, Any], scenario: dict[str, Any], expiry_offset_us: int,
    *, include_score: bool = False,
) -> dict[str, Any]:
    """Separate deterministic event causes from raw frame-observation times."""
    notes = {row["id"]: row for row in scenario["notes"]}
    actions = sorted(runtime["Actions"], key=lambda row: row["Sequence"])
    windows = ManiaHitWindows.from_od(8, "lazer")
    direct_by_note: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    assigned_actions: set[int] = set()

    for judgement in runtime["Judgements"]:
        note = notes[judgement["NoteId"]]
        for action in actions:
            if (action["Sequence"] in assigned_actions or action["Kind"] != "down"
                    or action["Lane"] != judgement["Lane"]):
                continue
            error_us = action["TimeUs"] - note["time_us"]
            if (error_us == judgement["OffsetUs"]
                    and error_us < expiry_offset_us
                    and windows.press_judgement(error_us) is not None):
                direct_by_note[judgement["NoteId"]] = (judgement, action)
                assigned_actions.add(action["Sequence"])
                break

    force_by_hit_note: dict[str, list[dict[str, Any]]] = {}
    normalized_judgements: dict[str, dict[str, Any]] = {}
    for judgement in runtime["Judgements"]:
        note = notes[judgement["NoteId"]]
        direct = direct_by_note.get(judgement["NoteId"])
        if direct is not None:
            logical_time_us = direct[1]["TimeUs"]
            hit_error_us: int | None = judgement["OffsetUs"]
        else:
            forced_by = next((
                (hit, action) for hit_id, (hit, action) in direct_by_note.items()
                if hit["Result"] != "MISS"
                and hit["Lane"] == judgement["Lane"]
                and notes[hit_id]["time_us"] > note["time_us"]
                and action["TimeUs"] < note["time_us"] + expiry_offset_us
            ), None)
            if forced_by is not None:
                forced_hit, forced_action = forced_by
                logical_time_us = forced_action["TimeUs"]
                hit_error_us = None
                force_by_hit_note.setdefault(forced_hit["NoteId"], []).append(judgement)
            else:
                logical_time_us = note["time_us"] + expiry_offset_us
                hit_error_us = None
        normalized_judgements[judgement["NoteId"]] = {
            "kind": "judgement",
            "logical_event_time_us": logical_time_us,
            "observed_game_time_us": judgement["ObservedGameTimeUs"],
            "note_id": judgement["NoteId"],
            "lane": judgement["Lane"],
            "note_time_us": judgement["NoteTimeUs"],
            "result": judgement["Result"],
            "hit_error_us": hit_error_us,
        }
        if include_score and judgement.get("Score") is not None:
            normalized_judgements[judgement["NoteId"]]["score"] = judgement["Score"]

    unresolved = set(notes)
    held: set[int] = set()
    emitted: set[str] = set()
    events: list[dict[str, Any]] = []

    def emit_expiries(through_us: int) -> None:
        expired = sorted(
            (note_id for note_id in unresolved
             if notes[note_id]["time_us"] + expiry_offset_us <= through_us),
            key=lambda note_id: (notes[note_id]["time_us"] + expiry_offset_us,
                                 notes[note_id]["lane"], note_id),
        )
        for note_id in expired:
            if note_id in normalized_judgements and note_id not in emitted:
                events.append(normalized_judgements[note_id])
                emitted.add(note_id)
                unresolved.remove(note_id)

    for action in actions:
        time_us, lane, kind = action["TimeUs"], action["Lane"], action["Kind"]
        emit_expiries(time_us)
        note_id = None
        if kind == "up":
            disposition = "release" if lane in held else "repeat_up"
            held.discard(lane)
        elif lane in held:
            disposition = "repeat_down"
        else:
            held.add(lane)
            note_id = next((
                candidate_id for candidate_id, (_, down_action) in direct_by_note.items()
                if down_action["Sequence"] == action["Sequence"]
            ), None)
            if note_id is None:
                disposition = "null_press"
            else:
                record = normalized_judgements[note_id]
                events.append(record)
                emitted.add(note_id)
                unresolved.discard(note_id)
                disposition = "early_miss" if record["result"] == "MISS" else "hit"
                for forced in sorted(
                    force_by_hit_note.get(note_id, []),
                    key=lambda row: (row["NoteTimeUs"], row["NoteId"]),
                ):
                    forced_id = forced["NoteId"]
                    if forced_id not in emitted:
                        events.append(normalized_judgements[forced_id])
                        emitted.add(forced_id)
                        unresolved.discard(forced_id)
        events.append({
            "kind": "action", "event_time_us": time_us, "lane": lane,
            "action": kind, "disposition": disposition, "note_id": note_id,
        })

    emit_expiries(2**63 - 1)
    if emitted != set(normalized_judgements):
        missing = sorted(set(normalized_judgements) - emitted)
        raise ValueError(f"could not order observed runtime judgements: {missing}")
    return {"id": scenario["id"], "events": events}


def main() -> int:
    if not TEST_PROJECT.is_file() or not TEST_SOURCE.is_file():
        print("Pinned source or runtime probe is missing; see the L0.9a report.", file=sys.stderr)
        return 2

    revision = subprocess.run(
        ["git", "-C", str(SOURCE_ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if revision != PINNED_COMMIT:
        print(f"Expected pinned lazer commit {PINNED_COMMIT}, got {revision}.", file=sys.stderr)
        return 2

    output_path = OUTPUT.resolve()
    repeat_path = REPEAT_OUTPUT.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    injected_before = INJECTED_SOURCE.exists()
    if injected_before and INJECTED_SOURCE.read_bytes() != TEST_SOURCE.read_bytes():
        print(f"Refusing to overwrite a different file: {INJECTED_SOURCE}", file=sys.stderr)
        return 2

    INJECTED_SOURCE.write_bytes(TEST_SOURCE.read_bytes())
    environment = os.environ.copy()
    work = ROOT / "work"
    appdata = work / "dotnet_appdata"
    environment.update({
        "DOTNET_CLI_HOME": str(work / "dotnet_cli_home"),
        "NUGET_PACKAGES": str(work / "nuget_packages_online"),
        "APPDATA": str(appdata),
        "TEMP": str(work / "tmp"),
        "TMP": str(work / "tmp"),
        "DOTNET_SKIP_FIRST_TIME_EXPERIENCE": "1",
        "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
        "DOTNET_PROCESSOR_COUNT": "2",
        "LAZER_PARITY_CORPUS": str(CORPUS.resolve()),
    })
    (work / "tmp").mkdir(parents=True, exist_ok=True)
    try:
        code, rows = _run_once(output_path, environment)
        if code != 0:
            return code
        code, repeated_rows = _run_once(repeat_path, environment)
        if code != 0:
            return code
        ids = {row["Id"] for row in rows}
        expected = {
            "OD8_timing_boundaries", "early_judged_miss",
            "too_early_null_then_automatic_miss", "late_meh_at_last_successful_microsecond",
            "expiry_precedes_action_at_expiry_timestamp", "no_press_automatic_miss",
            "same_lane_earliest_note_and_key_transition_order",
            "same_lane_note_lock_at_next_note_start", "simultaneous_four_lane_chord",
        }
        if ids != expected or len(rows) != len(expected):
            print(f"Unexpected probe rows: {sorted(ids)}", file=sys.stderr)
            return 1
        if _without_observed_times(rows) != _without_observed_times(repeated_rows):
            print("FAIL: normalized action/judgement trace changed across repeated runs; "
                  "raw game timestamps are retained in both JSONL files.", file=sys.stderr)
            return 1

        corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
        observed_scenarios = {row["Id"]: row for row in rows if row["Id"] != "OD8_timing_boundaries"}
        windows = ManiaHitWindows.from_od(corpus["reference"]["od"], "lazer")
        normalized_scenarios = []
        for scenario in corpus["scenarios"]:
            observed = observed_scenarios[scenario["id"]]
            actual_actions = [
                {"time_us": action["TimeUs"], "lane": action["Lane"], "kind": action["Kind"]}
                for action in sorted(observed["Actions"], key=lambda action: action["Sequence"])
            ]
            if actual_actions != scenario["actions"]:
                print(f"FAIL: captured Lazer key transitions differ for {scenario['id']}: "
                      f"expected {scenario['actions']}, got {actual_actions}", file=sys.stderr)
                return 1
            normalized = _normalize_scenario_trace(
                observed, scenario, windows.expiry_offset_us)
            expected_events = scenario["expected_events"]
            if _without_observed_times(normalized["events"]) != _without_observed_times(expected_events):
                print(f"FAIL: normalized pinned-runtime event trace differs for {scenario['id']}",
                      file=sys.stderr)
                print("Expected: " + json.dumps(expected_events, sort_keys=True), file=sys.stderr)
                print("Observed: " + json.dumps(normalized["events"], sort_keys=True), file=sys.stderr)
                return 1
            normalized_scenarios.append(normalized)

        normalized_output = {
            "schema_version": corpus["schema_version"],
            "reference": corpus["reference"],
            "scenarios": normalized_scenarios,
            "raw_observation_sources": [str(output_path), str(repeat_path)],
        }
        NORMALIZED_OUTPUT.write_text(
            json.dumps(normalized_output, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"PASS: {len(rows)} runtime traces repeat with stable normalized ordering; "
              f"all captured DOWN/UP transitions and normalized events match the frozen corpus. "
              f"Normalized trace: {NORMALIZED_OUTPUT}; raw runs: {output_path} and {repeat_path}")
        return 0
    finally:
        if not injected_before:
            INJECTED_SOURCE.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())

