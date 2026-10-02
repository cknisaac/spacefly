"""Read-only sign-direction replay over the frozen L3 C1 simulator."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run_larval_l3_c1_controllability import (  # noqa: E402
    MANIFEST_PATH, MODEL_PATH, NEUTRAL_PATH, run_one,
)

EXPECTED = {
    "manifest": "b54a8a7ec9e3b18f21f8df91584c33f875c3302c8e534b6020dec7290f004895",
    "model": "5e32171707409a5dffc66f0c93d48bec307d442a01ace8b8554fa82e23c91f6e",
    "neutral": "8fa83febee7812f5ba3435592a9a4dc390f156ccd9ba929e25486bbf9b4ce7bc",
    "controllability": "f3d224242f6dd0b7c526acdbf905fa43eda3d16182736473be359551e4c6f340",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    paths = {
        "manifest": MANIFEST_PATH,
        "model": MODEL_PATH,
        "neutral": NEUTRAL_PATH,
        "controllability": ROOT / "runs/larval_l3_c1_controllability_v1.json",
    }
    hashes = {name: sha(path) for name, path in paths.items()}
    if hashes != EXPECTED:
        raise RuntimeError(f"frozen input hash mismatch: {hashes}")
    # The frozen v1 weight is factor 1. A smaller factor represents Δw < 0;
    # a larger factor represents Δw > 0. Only KC→MBON-c1 weights are changed.
    factors = {"decrease": 0.5, "reference": 1.0, "increase": 2.0}
    rows = []
    for direction, factor in factors.items():
        for state in range(8):
            a = run_one(factor, state)
            b = run_one(factor, state)
            rows.append({
                "direction": direction,
                "factor": factor,
                "state": state,
                "action": a["action"],
                "dn_spikes": sum(a["action_readout_spikes_by_source_id"].values()),
                "mbon_spikes": a["spikes_by_role"]["MBON-c1"],
                "replay_match": a["replay_digest"] == b["replay_digest"],
            })
    result = {
        "experiment_id": "larval_l3_c1_rule_direction_audit_v1",
        "status": "READ_ONLY_DIRECTION_AUDIT",
        "frozen_input_hashes": hashes,
        "method": "Replay the frozen eight states at KC→MBON-c1 weight factors 0.5, 1, and 2; every other parameter and input remains fixed. No learning or teaching signal is active.",
        "rows": rows,
        "summary": {
            direction: {
                "factor": factor,
                "action_states": [r["state"] for r in rows if r["direction"] == direction and r["action"]],
                "action_count": sum(r["action"] for r in rows if r["direction"] == direction),
                "mbon_spikes_by_state": [r["mbon_spikes"] for r in rows if r["direction"] == direction],
            }
            for direction, factor in factors.items()
        },
        "all_replays_deterministic": all(row["replay_match"] for row in rows),
        "interpretation": "Simulator direction only: positive KC→MBON-c1 weight change moves toward the model's fixed DN action boundary; negative change moves away. This does not identify a biological plasticity sign or validate the DN action mapping.",
    }
    out = ROOT / "runs/larval_l3_c1_rule_direction_audit_v1.json"
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"result": str(out), "sha256": sha(out), "summary": result["summary"],
                      "all_replays_deterministic": result["all_replays_deterministic"]}, indent=2))


if __name__ == "__main__":
    main()
