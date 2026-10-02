"""Resolve Circuit V1 effect, neuron, delay and boundary policies without running it."""

from __future__ import annotations

import argparse
from pathlib import Path

from project_b.connectome.effect_policies import build_policy_product


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subset", type=Path,
                        default=ROOT / "data/processed/malecns_v1_circuit_v1")
    parser.add_argument("--policy", type=Path,
                        default=ROOT / "configs/circuit_v1_effect_policies.json")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "data/processed/malecns_v1_circuit_v1_policy_v1")
    args = parser.parse_args()
    manifest = build_policy_product(args.subset, args.policy, args.output)
    print(f"{manifest['source_pairs']} source pairs classified; "
          f"{manifest['effect_pairs'].get('UNKNOWN', 0)} UNKNOWN effects; "
          f"runtime_ready={manifest['runtime_ready']}; "
          f"manifest: {args.output / 'manifest.json'}")


if __name__ == "__main__":
    main()
