"""Download the three pinned BANC v888 source products without altering them."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen


BUCKET = "lee-lab_brain-and-nerve-cord-fly-connectome"
PREFIX = "compiled_data/banc_888/"
OBJECTS = (
    ("banc_888_meta.feather", "1787336614757441", 57503026, "jCuTpgjHFj7J2U1o4HVv9A=="),
    ("banc_888_edgelist_simple_v2.feather", "1780396134870867", 305250378, "OUQG+Km98JPIlfla/09sSQ=="),
    ("banc_888_neurotransmitter_prediction_v2.csv", "1778713090033523", 21107592, "TrvR1uBdQZKtDG2ydzmo4w=="),
)


def hashes(path: Path) -> tuple[int, str, str]:
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
    parser.add_argument("--directory", type=Path, default=Path("data/raw/banc_v888"))
    args = parser.parse_args()
    destination = args.directory
    destination.mkdir(parents=True, exist_ok=True)
    manifest = {"dataset": "BANC", "materialization": "v888", "source": "public GCS object generations", "objects": []}
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
            size, sha256, md5 = hashes(temp)
            if (size, md5) != (expected_size, expected_md5):
                temp.unlink()
                raise ValueError(f"Downloaded source failed size/MD5 validation: {name}")
            temp.replace(path)
        size, sha256, md5 = hashes(path)
        if (size, md5) != (expected_size, expected_md5):
            raise ValueError(f"Cached source failed size/MD5 validation: {name}")
        manifest["objects"].append({"name": name, "url": url, "generation": generation, "bytes": size, "md5_base64": md5, "sha256": sha256})
        print(f"validated {name}: {size:,} bytes SHA256 {sha256}", flush=True)
    (destination / "source_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
