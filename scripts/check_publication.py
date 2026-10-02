"""Check the curated GitHub entry points and compact Level 4D evidence."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
CURATED = [
    ROOT / "README.md",
    ROOT / "docs" / "catalog.md",
    *sorted((ROOT / "docs").glob("*.md")),
    *sorted((ROOT / "docs" / "tracks").rglob("*.md")),
    *sorted((ROOT / "docs" / "history").rglob("*.md")),
    *sorted((ROOT / "research").rglob("*.md")),
    ROOT / "data" / "README.md",
    ROOT / "results" / "index.md",
    ROOT / "results" / "malecns-level4d" / "summary.md",
    ROOT / "visualization" / "README.md",
]
NEW_GUIDES = [
    path for path in CURATED if path != ROOT / "README.md" and
    (path.parent != ROOT / "docs" or path.name in {
        "index.md", "catalog.md", "project-status.md", "architecture.md", "reproducibility.md"
    })
]
LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_links(errors: list[str]) -> None:
    for path in dict.fromkeys(NEW_GUIDES):
        if not path.is_file():
            errors.append(f"Missing guide: {path.relative_to(ROOT)}")
            continue
        for raw in LINK.findall(path.read_text(encoding="utf-8")):
            target = unquote(raw.split("#", 1)[0].split("?", 1)[0])
            if not target or target.startswith(("http:", "https:", "mailto:")):
                continue
            if target.startswith("<") and target.endswith(">"):
                target = target[1:-1]
            resolved = (path.parent / target).resolve()
            if not resolved.is_relative_to(ROOT) or not resolved.exists():
                errors.append(f"Broken link in {path.relative_to(ROOT)}: {raw}")


def check_git_candidates(errors: list[str]) -> None:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT, capture_output=True, check=True,
    )
    candidates = [ROOT / name.decode("utf-8") for name in result.stdout.split(b"\0") if name]
    prohibited = ("runs/", "data/raw/", "data/processed/")
    for path in candidates:
        relative = path.relative_to(ROOT).as_posix()
        if relative.startswith(prohibited) or path.name == ".env":
            errors.append(f"Local-only file would be published: {relative}")
        if path.is_file() and path.stat().st_size > 10_000_000:
            errors.append(f"Large file would be published: {relative} ({path.stat().st_size} bytes)")
    print(f"Git candidate files: {len(candidates)}")


def check_level4d(errors: list[str]) -> None:
    bundle = ROOT / "results" / "malecns-level4d"
    metrics = json.loads((bundle / "metrics.json").read_text(encoding="utf-8"))
    artifacts = json.loads((bundle / "artifacts.json").read_text(encoding="utf-8"))
    if metrics["contract_result"] != "FAIL" or metrics["branch_classification"] != "Mechanistic success / behavioral robustness incomplete":
        errors.append("Level 4D judgment does not match the frozen branch classification")
    if metrics["arms"]["target"]["first_action"] is not None or metrics["arms"]["wrong"]["first_action"]["position"] != 0.2:
        errors.append("Level 4D compact first-action result does not match the frozen result")
    if metrics["arms"]["baseline"]["first_action"] is not None or metrics["arms"]["plasticity_off"]["first_action"] is not None:
        errors.append("Level 4D control first-action results changed")
    for name, record in artifacts.items():
        if name == "schema_version":
            continue
        path = ROOT / record["path"]
        if not path.is_file():
            if name != "source_receipt":
                errors.append(f"Missing bundled artifact: {record['path']}")
            continue
        if path.stat().st_size != record["bytes"] or sha256(path) != record["sha256"]:
            errors.append(f"Artifact size/hash mismatch: {record['path']}")
    if artifacts["source_receipt"]["sha256"] != metrics["source_receipt_sha256"]:
        errors.append("Full receipt hash differs between compact records")
    with (bundle / "position-map.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 84:
        errors.append(f"Expected 84 position-map rows, found {len(rows)}")
    print(f"Level 4D position-map rows: {len(rows)}")


def main() -> int:
    errors: list[str] = []
    check_links(errors)
    check_git_candidates(errors)
    check_level4d(errors)
    for message in errors:
        print(f"ERROR: {message}")
    if errors:
        print(f"Publication check failed: {len(errors)} problem(s)")
        return 1
    print("Publication check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
