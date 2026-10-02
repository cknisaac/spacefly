"""Validate and import the pinned BANC v888 source products; no simulation."""

import argparse
from pathlib import Path

from project_b.connectome.importer import import_banc


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("data/raw/banc_v888"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/banc_v888_v2"))
    args = parser.parse_args()
    report = import_banc(args.source, args.output)
    print(f"Validated {report['statistics']['source_nodes']:,} source nodes and {report['statistics']['connections']:,} directed connections")
    print(args.output / "import_report.json")


if __name__ == "__main__":
    main()
