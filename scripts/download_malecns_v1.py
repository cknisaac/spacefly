"""Download unmodified, generation-pinned official MaleCNS v1.0 flat files."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen


BUCKET = "flyem-male-cns"
PREFIX = "v1.0/connectome-data/flat-connectome/"
OBJECTS = (
    ("body-annotations-male-cns-v1.0-minconf-0.5.feather", "1780494878811468", 14483314, "UKdxh3DFciDxYLpPQxq4ng=="),
    ("body-neurotransmitters-male-cns-v1.0.feather", "1780894899156750", 43282834, "PYQrEv5cSe763lKNfdJKHw=="),
    ("body-stats-male-cns-v1.0-minconf-0.5.feather", "1780494888472305", 778062826, "QEwzScKFgBSOFoFeuZ84Kg=="),
    ("connectome-weights-male-cns-v1.0-minconf-0.5.feather", "1780494887545976", 1051241946, "8w6dzKJc/QIb8eez2XVZng=="),
    ("connectome-weights-male-cns-v1.0-minconf-0.5-traced-only.feather", "1780494884279095", 508025642, "ZgHUrQr6mf0D6wh5Ze8kIw=="),
)


def digest(path: Path) -> tuple[int, str, str]:
    sha = hashlib.sha256()
    md5 = hashlib.md5(usedforsecurity=False)
    size = 0
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            size += len(chunk)
            sha.update(chunk)
            md5.update(chunk)
    return size, sha.hexdigest(), base64.b64encode(md5.digest()).decode("ascii")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path("data/raw/malecns_v1"))
    args = parser.parse_args()
    destination = args.directory
    destination.mkdir(parents=True, exist_ok=True)
    manifest = {"dataset": "MaleCNS", "release": "v1.0", "source": "official public GCS object generations", "objects": []}
    for name, generation, expected_size, expected_md5 in OBJECTS:
        path = destination / name
        url = f"https://storage.googleapis.com/{BUCKET}/{PREFIX}{name}?{urlencode({'generation': generation})}"
        if not path.exists():
            temp = path.with_suffix(path.suffix + ".part")
            if temp.exists():
                temp.unlink()
            with urlopen(url, timeout=120) as response, temp.open("wb") as output:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
            size, sha256, md5 = digest(temp)
            if (size, md5) != (expected_size, expected_md5):
                temp.unlink()
                raise ValueError(f"Downloaded source failed size/MD5 validation: {name}")
            temp.replace(path)
        size, sha256, md5 = digest(path)
        if (size, md5) != (expected_size, expected_md5):
            raise ValueError(f"Cached source failed size/MD5 validation: {name}")
        manifest["objects"].append({"name": name, "url": url, "generation": generation, "bytes": size, "md5_base64": md5, "sha256": sha256})
        print(f"validated {name}: {size:,} bytes SHA256 {sha256}", flush=True)
    (destination / "source_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
