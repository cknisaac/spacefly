"""Materialize the pinned, data-only MaleCNS Circuit V1 subset."""

from __future__ import annotations

import argparse
from pathlib import Path

from project_b.connectome.circuit_v1 import build_circuit_v1


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path,
                        default=ROOT / "data/processed/malecns_v1_traced")
    parser.add_argument("--selection", type=Path,
                        default=ROOT / "configs/circuit_v1_selection.json")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "data/processed/malecns_v1_circuit_v1")
    args = parser.parse_args()
    result = build_circuit_v1(args.source, args.selection, args.output)
    print(f"{result['neurons']} neurons, {result['directed_pairs']} exact source pairs, "
          f"{result['plastic_candidate_pairs']} plastic candidates; "
          f"manifest: {args.output / 'manifest.json'}")


if __name__ == "__main__":
    main()
