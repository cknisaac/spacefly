"""Fetch checksum-pinned public synapse source data for the route evidence audit."""
import argparse
import base64
import hashlib
import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/malecns_v1"
OBJECTS = {
    "partners": ("syn-partners-male-cns-v1.0-minconf-0.5-traced-only.feather", "1780494912394119", 2965367002, "9bwcXONKAbaJVkFLUw7dqA=="),
    "points": ("syn-points-male-cns-v1.0-minconf-0.5.feather", "1780494991007477", 13061489098, "xp0IdY3gdYIDXMiENXRJOg=="),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("product", choices=OBJECTS)
    args = parser.parse_args()
    name, generation, size, md5 = OBJECTS[args.product]
    target = RAW / name
    receipt = RAW / (name + ".receipt.json")
    url = f"https://storage.googleapis.com/flyem-male-cns/v1.0/connectome-data/flat-connectome/{name}?generation={generation}"
    sha = hashlib.sha256()
    checksum = hashlib.md5(usedforsecurity=False)
    count = 0
    start = time.monotonic()
    if target.exists():
        source = target.open("rb")
        output = None
    else:
        partial = target.with_suffix(target.suffix + ".part")
        if partial.exists():
            raise RuntimeError(f"Inspect existing partial before retry: {partial}")
        source = urllib.request.urlopen(url, timeout=60)
        output = partial.open("wb")
    try:
        report_at = 256 * 1024**2
        while chunk := source.read(4 * 1024**2):
            sha.update(chunk)
            checksum.update(chunk)
            count += len(chunk)
            if output:
                output.write(chunk)
            if count >= report_at:
                print(f"{name}: {count / size:.1%}; {count / 1024**2:.0f} MiB; {time.monotonic()-start:.1f}s", flush=True)
                report_at += 256 * 1024**2
    finally:
        source.close()
        if output:
            output.close()
    assert count == size and base64.b64encode(checksum.digest()).decode() == md5, "Source checksum/size mismatch"
    if output:
        partial.replace(target)
    receipt.write_text(json.dumps({"url": url, "generation": generation, "bytes": count,
                                  "md5_base64": md5, "sha256": sha.hexdigest()}, indent=2) + "\n")
    print(f"Verified {target.name}; SHA256 {sha.hexdigest()}", flush=True)


if __name__ == "__main__":
    main()
