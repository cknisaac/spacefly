"""Run the frozen OD8 corpus locally or compare it with a pinned C# output.

The reference runner must emit JSON with the same schema as
``build_python_output``. This tool never calls the Python profile a lazer
runtime result: parity is established only when ``--reference-output`` is
provided and the full output matches.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from project_b.osu import KeyAction, KeyActionKind, ManiaHitWindows, OsuConfig, TapNote, play  # noqa: E402


CORPUS_PATH = ROOT / "tests" / "fixtures" / "lazer_od8_parity_corpus.json"
RESULT_LABELS = {
    "MAX_320": "PERFECT",
    "GREAT_300": "GREAT",
    "GOOD_200": "GOOD",
    "OK_100": "OK",
    "MEH_50": "MEH",
    "MISS": "MISS",
}


def _normalized_event(event: Any) -> dict[str, Any]:
    if hasattr(event, "judgement"):
        return {
            "kind": "judgement",
            "logical_event_time_us": event.logical_event_time_us,
            "observed_game_time_us": event.observed_game_time_us,
            "note_id": event.note_id,
            "lane": event.lane,
            "note_time_us": event.note_time_us,
            "result": event.result_name,
            "hit_error_us": event.hit_error_us,
        }
    action = event.action
    return {
        "kind": "action",
        "event_time_us": action.time_us,
        "lane": action.lane,
        "action": action.kind.value,
        "disposition": event.disposition.value,
        "note_id": event.note_id,
    }


def build_python_output(corpus: dict[str, Any]) -> dict[str, Any]:
    """Return canonical outputs for the Python profile and game scenarios."""
    reference = corpus["reference"]
    config = OsuConfig(od=reference["od"], ruleset="lazer")
    windows = ManiaHitWindows.from_od(reference["od"], "lazer")

    vector_results = []
    for vector in corpus["judgement_vectors"]:
        result = windows.press_judgement(vector["offset_us"])
        result_name = "NO_PRESS_JUDGEMENT" if result is None else RESULT_LABELS[result.name]
        vector_results.append({"id": vector["id"], "result": result_name})

    scenario_results = []
    for scenario in corpus["scenarios"]:
        notes = [TapNote(row["id"], row["lane"], row["time_us"])
                 for row in scenario["notes"]]
        actions = [KeyAction(row["time_us"], row["lane"], KeyActionKind(row["kind"]))
                   for row in scenario["actions"]]
        result = play(notes, actions, config)
        scenario_results.append({
            "id": scenario["id"],
            "events": [_normalized_event(event) for event in result.events],
        })

    return {
        "schema_version": corpus["schema_version"],
        "reference": reference,
        "judgement_vectors": vector_results,
        "scenarios": scenario_results,
    }


def _differences(expected: Any, actual: Any, path: str = "$") -> list[str]:
    if type(expected) is not type(actual):
        return [f"{path}: expected {expected!r}, got {actual!r}"]
    if isinstance(expected, dict):
        differences = []
        for key in sorted(expected.keys() | actual.keys()):
            if key not in expected:
                differences.append(f"{path}.{key}: unexpected {actual[key]!r}")
            elif key not in actual:
                differences.append(f"{path}.{key}: missing (expected {expected[key]!r})")
            else:
                differences.extend(_differences(expected[key], actual[key], f"{path}.{key}"))
        return differences
    if isinstance(expected, list):
        differences = []
        if len(expected) != len(actual):
            differences.append(f"{path}: expected {len(expected)} items, got {len(actual)}")
        for index, (left, right) in enumerate(zip(expected, actual)):
            differences.extend(_differences(left, right, f"{path}[{index}]"))
        return differences
    if expected != actual:
        return [f"{path}: expected {expected!r}, got {actual!r}"]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=CORPUS_PATH,
                        help="frozen JSON inputs and expected source-derived outputs")
    parser.add_argument("--python-output", type=Path,
                        help="write canonical Python-profile output to this path")
    reference_group = parser.add_mutually_exclusive_group()
    reference_group.add_argument("--reference-output", type=Path,
                                 help="compare full pinned C# output, including game events")
    reference_group.add_argument("--windows-reference-output", type=Path,
                                 help="compare pinned C# hit-window-class output only")
    reference_group.add_argument("--source-policy-reference-output", type=Path,
                                 help="compare pinned C# timing classes and OrderedHitPolicy output")
    args = parser.parse_args()

    corpus = json.loads(args.corpus.read_text(encoding="utf-8"))
    python_output = build_python_output(corpus)

    # The fixture's expected values are a frozen regression contract for the
    # Python implementation; the separate C# comparison is still required.
    expected_python = {
        "schema_version": corpus["schema_version"],
        "reference": corpus["reference"],
        "judgement_vectors": [
            {"id": row["id"], "result": row["expected"]}
            for row in corpus["judgement_vectors"]
        ],
        "scenarios": [
            {"id": row["id"], "events": row["expected_events"]}
            for row in corpus["scenarios"]
        ],
    }
    python_differences = _differences(expected_python, python_output)
    if python_differences:
        print("Python profile disagrees with the frozen corpus:", file=sys.stderr)
        print("\n".join(python_differences), file=sys.stderr)
        return 1

    serialized = json.dumps(python_output, indent=2, sort_keys=True) + "\n"
    if args.python_output:
        args.python_output.parent.mkdir(parents=True, exist_ok=True)
        args.python_output.write_text(serialized, encoding="utf-8")
    elif not args.reference_output and not args.windows_reference_output and not args.source_policy_reference_output:
        sys.stdout.write(serialized)

    if args.reference_output:
        reference_output = json.loads(args.reference_output.read_text(encoding="utf-8"))
        differences = _differences(python_output, reference_output)
        if differences:
            print(f"FAIL: {len(differences)} pinned-reference mismatches", file=sys.stderr)
            print("\n".join(differences), file=sys.stderr)
            return 1
        print("PASS: zero differences for the frozen OD8 corpus")
    elif args.windows_reference_output:
        reference_output = json.loads(args.windows_reference_output.read_text(encoding="utf-8"))
        if reference_output.get("scope") not in {"hit-windows-only", "pinned-source-subset"}:
            print("FAIL: C# output does not declare a supported pinned-source scope", file=sys.stderr)
            return 1
        expected_windows = {
            "schema_version": python_output["schema_version"],
            "reference": python_output["reference"],
            "judgement_vectors": python_output["judgement_vectors"],
        }
        observed_windows = {key: reference_output.get(key)
                            for key in expected_windows}
        differences = _differences(expected_windows, observed_windows)
        if differences:
            print(f"FAIL: {len(differences)} pinned C# timing-window mismatches", file=sys.stderr)
            print("\n".join(differences), file=sys.stderr)
            return 1
        print("PASS: pinned C# hit-window classes match all timing vectors; "
              "game event parity remains unverified")
    elif args.source_policy_reference_output:
        reference_output = json.loads(args.source_policy_reference_output.read_text(encoding="utf-8"))
        if reference_output.get("scope") != "pinned-source-subset":
            print("FAIL: C# output does not declare pinned-source-subset scope", file=sys.stderr)
            return 1
        expected_subset = {
            "schema_version": python_output["schema_version"],
            "reference": python_output["reference"],
            "judgement_vectors": python_output["judgement_vectors"],
            "source_policy_vectors": [
                {"id": row["id"], **row["expected"]}
                for row in corpus["source_policy_vectors"]
            ],
        }
        observed_subset = {key: reference_output.get(key)
                           for key in expected_subset}
        differences = _differences(expected_subset, observed_subset)
        if differences:
            print(f"FAIL: {len(differences)} pinned source-policy mismatches", file=sys.stderr)
            print("\n".join(differences), file=sys.stderr)
            return 1
        print("PASS: pinned timing classes and OrderedHitPolicy match; "
              "full playfield event parity remains unverified")
    elif args.python_output:
        print("Wrote source-derived Python output; pinned-runtime parity is unverified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
