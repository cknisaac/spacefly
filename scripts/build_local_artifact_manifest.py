"""Record hashes for ignored historical docs/figures files kept locally."""

from __future__ import annotations

import argparse
import csv
import hashlib
from io import StringIO
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "results" / "local-artifact-manifest.csv"


def render() -> str:
    found = subprocess.run(
        ["git", "ls-files", "--others", "--ignored", "--exclude-standard", "-z", "--", "docs/figures"],
        cwd=ROOT, capture_output=True, check=True,
    )
    names = sorted(part.decode("utf-8") for part in found.stdout.split(b"\0") if part)
    buffer = StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(("local_path", "bytes", "sha256"))
    for name in names:
        path = ROOT / name
        if not path.is_file():
            continue
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        writer.writerow((Path(name).as_posix(), path.stat().st_size, digest.hexdigest()))
    return buffer.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if the manifest is stale")
    args = parser.parse_args()
    expected = render()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != expected:
            print("results/local-artifact-manifest.csv is missing or stale")
            return 1
        print("Local artifact manifest is current")
        return 0
    OUTPUT.write_text(expected, encoding="utf-8", newline="")
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
