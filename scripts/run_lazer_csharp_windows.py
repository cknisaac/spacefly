"""Run the exact pinned ManiaHitWindows and HitWindows source on a corpus."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
PINNED_COMMIT = "da27300fcbfa246f87c3ba1a14cbd00b68c7e9a9"
DEFAULT_SOURCE_ROOT = ROOT / "work" / "osu_lazer_reference"
DEFAULT_CORPUS = ROOT / "tests" / "fixtures" / "lazer_od8_parity_corpus.json"
PROJECT = ROOT / "scripts" / "lazer_csharp_windows" / "LazerCSharpWindowsReference.csproj"
DOTNET_EXE = (shutil.which("dotnet") or
              str(Path("C:/Program Files/dotnet/dotnet.exe")))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT,
                        help="checkout of ppy/osu at the pinned commit")
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--output", type=Path,
                        help="write C# JSON output here instead of stdout")
    args = parser.parse_args()

    source_root = args.source_root.resolve()
    revision = subprocess.run(
        ["git", "-C", str(source_root), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    if revision != PINNED_COMMIT:
        parser.error(f"source checkout must be {PINNED_COMMIT}, got {revision}")

    command = [
        DOTNET_EXE, "run", "--project", str(PROJECT), "--configuration", "Release",
        f"-p:PinnedSourceRoot={source_root}", "--", str(args.corpus.resolve()),
    ]
    environment = os.environ.copy()
    environment["DOTNET_CLI_HOME"] = str(ROOT / "work" / "dotnet_cli_home")
    environment["NUGET_PACKAGES"] = str(ROOT / "work" / "nuget_packages")
    appdata = ROOT / "work" / "dotnet_appdata"
    nuget_config = appdata / "NuGet" / "NuGet.Config"
    nuget_config.parent.mkdir(parents=True, exist_ok=True)
    nuget_config.write_text(
        "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n"
        "<configuration><packageSources><clear /></packageSources></configuration>\n",
        encoding="utf-8",
    )
    environment["APPDATA"] = str(appdata)
    environment["DOTNET_SKIP_FIRST_TIME_EXPERIENCE"] = "1"
    environment["DOTNET_CLI_TELEMETRY_OPTOUT"] = "1"
    try:
        completed = subprocess.run(command, check=True, capture_output=True, text=True,
                                   cwd=PROJECT.parent, env=environment)
    except subprocess.CalledProcessError as error:
        if error.stdout:
            sys.stdout.write(error.stdout)
        if error.stderr:
            sys.stderr.write(error.stderr)
        return error.returncode
    if args.output:
        output_path = args.output.resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(completed.stdout, encoding="utf-8")
        print(f"Wrote pinned C# source-subset output to {output_path}")
    else:
        sys.stdout.write(completed.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
