"""Compare every 4K Normal object with pinned osu!lazer's .osu decoder."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from project_b.osu.beatmap import extract_osz, load_mania_beatmap  # noqa: E402
from project_b.osu.types import HoldNote  # noqa: E402
from project_b.osu.types import KeyAction, KeyActionKind  # noqa: E402
from project_b.osu.config import OsuConfig  # noqa: E402
from project_b.osu.mania_game import ManiaGame  # noqa: E402

SOURCE = ROOT / "work/osu_lazer_reference"
PROJECT = SOURCE / "osu.Game.Rulesets.Mania.Tests/osu.Game.Rulesets.Mania.Tests.csproj"
PROBE = ROOT / "scripts/lazer_map_probe/FreedomDiveMapProbe.cs"
INJECTED = PROJECT.parent / PROBE.name
OUTPUT = ROOT / "work/freedom_dive_lazer_map.json"
REPLAY_OUTPUT = ROOT / "work/freedom_dive_lazer_replay.json"
ARCHIVE = Path(r"C:\Users\imdef\AppData\Roaming\osu\exports\xi - FREEDOM DiVE (razlteh).osz")
PINNED = "da27300fcbfa246f87c3ba1a14cbd00b68c7e9a9"
DOTNET = shutil.which("dotnet") or "C:/Program Files/dotnet/dotnet.exe"


def main() -> int:
    revision = subprocess.run(["git", "-C", str(SOURCE), "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
    if revision != PINNED:
        raise ValueError(f"wrong osu!lazer reference revision: {revision}")
    matches = [path for path in extract_osz(ARCHIVE) if "4K Normal" in path.name]
    if len(matches) != 1:
        raise ValueError(f"expected one 4K Normal map, got {len(matches)}")
    chart = load_mania_beatmap(matches[0])
    if INJECTED.exists() and INJECTED.read_bytes() != PROBE.read_bytes():
        raise ValueError(f"refusing to overwrite {INJECTED}")
    present = INJECTED.exists()
    INJECTED.write_bytes(PROBE.read_bytes())
    OUTPUT.unlink(missing_ok=True)
    REPLAY_OUTPUT.unlink(missing_ok=True)
    work = ROOT / "work"
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
        "FREEDOM_OSU_PATH": str(chart.path),
        "FREEDOM_LAZER_OUTPUT": str(OUTPUT),
        "FREEDOM_LAZER_REPLAY_OUTPUT": str(REPLAY_OUTPUT),
    })
    try:
        completed = subprocess.run(
            [DOTNET, "test", str(PROJECT), "-c", "Release", "--no-restore",
             "--filter", "FullyQualifiedName~FreedomDiveMapProbe.DecodeRealFourKeyChart",
             "-m:1", "/nodeReuse:false", "-p:BuildInParallel=false",
             "-p:RunAnalyzers=false", "--logger", "console;verbosity=normal",
             "-clp:ErrorsOnly"], cwd=PROJECT.parent, env=environment,
            capture_output=True, text=True,
        )
        print(completed.stdout)
        print(completed.stderr, file=sys.stderr)
        if completed.returncode != 0:
            return completed.returncode
        reference = json.loads(OUTPUT.read_text(encoding="utf-8"))
        expected = sorted(({"kind": "hold" if isinstance(note, HoldNote) else "tap",
                            "lane": note.lane, "start_us": note.time_us,
                            "end_us": note.end_time_us if isinstance(note, HoldNote)
                            else note.time_us} for note in chart.notes),
                          key=lambda row: (row["start_us"], row["lane"], row["end_us"]))
        if reference["notes"] != expected:
            for index, (lazer, recreated) in enumerate(zip(reference["notes"], expected)):
                if lazer != recreated:
                    raise AssertionError(f"first object difference at {index}: {lazer} != {recreated}")
            raise AssertionError(f"object count mismatch: {len(reference['notes'])} != {len(expected)}")
        if str(reference["od"]) != str(chart.od):
            raise AssertionError(f"OD differs: {reference['od']} != {chart.od}")
        print(f"PASS: all {len(expected)} map objects and OD match pinned lazer decoder")

        replay = subprocess.run(
            [DOTNET, "test", str(PROJECT), "-c", "Release", "--no-build", "--no-restore",
             "--filter", "FullyQualifiedName~FreedomDiveReplayProbe.ReplayEveryObjectInRealFourKeyChart",
             "-m:1", "/nodeReuse:false", "-p:BuildInParallel=false",
             "-p:RunAnalyzers=false", "--logger", "console;verbosity=normal",
             "-clp:ErrorsOnly"], cwd=PROJECT.parent, env=environment,
            capture_output=True, text=True, timeout=360,
        )
        print(replay.stdout)
        print(replay.stderr, file=sys.stderr)
        if replay.returncode != 0:
            return replay.returncode
        lazer = json.loads(REPLAY_OUTPUT.read_text(encoding="utf-8"))
        game = ManiaGame(chart.notes, OsuConfig(od=chart.od, ruleset="lazer"))
        transitions = []
        for note in chart.notes:
            transitions.append((note.time_us, 1, note.lane, KeyActionKind.DOWN))
            end = note.end_time_us if isinstance(note, HoldNote) else note.time_us + 1000
            transitions.append((end, 0, note.lane, KeyActionKind.UP))
        for at_us, _, lane, kind in sorted(transitions):
            game.apply_action(KeyAction(at_us, lane, kind))
        final = game.finish()
        expected_counts = {key.replace("_", ""): count
                           for key, count in final.result_counts.items()}
        if (lazer["score"] != final.score or lazer["combo"] != final.combo or
                abs(lazer["accuracy"] - final.accuracy) > 1e-12 or
                lazer["counts"] != expected_counts):
            raise AssertionError(f"full replay differs: lazer={lazer}; recreation={final}")
        print(f"PASS: full perfect replay score {final.score}, combo {final.combo}, "
              f"accuracy {final.accuracy}, result counts {expected_counts}")
        return 0
    finally:
        if not present:
            INJECTED.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
