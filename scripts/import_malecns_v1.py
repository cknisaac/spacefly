"""Validate official MaleCNS v1.0 and import its traced-neuron graph only."""

import argparse
from pathlib import Path

from project_b.connectome.malecns import import_malecns


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("data/raw/malecns_v1"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/malecns_v1_traced"))
    args = parser.parse_args()
    report = import_malecns(args.source, args.output)
    stats = report["statistics"]
    print(f"Validated MaleCNS v1.0: {stats['traced_neurons']:,} traced neurons and {stats['traced_graph_connections']:,} directed connections")
    print(args.output / "import_report.json")


if __name__ == "__main__":
    main()
