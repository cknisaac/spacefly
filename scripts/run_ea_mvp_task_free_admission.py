"""Run one predeclared non-learning EA-MVP position/readout admission panel."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from project_b.malecns_continuous_position_learning.online_policy import (
    OnlineFlyPolicy,
    load_position_config,
)
from project_b.osu.adapter import PositionObservation
from project_b.osu.types import KeyActionKind


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/ea_mvp_task_free_admission.json"
OUTPUT = ROOT / "runs/ea_mvp/task_free_admission.json"


def run_arm(config: dict, protocol: dict, center: float | None) -> dict:
    cells = config["circuit"]["selected_kcs"]
    total = sum(cell["plastic_contact_rows"] for cell in cells)
    weights = [cell["plastic_contact_rows"] / total for cell in cells]
    if center is not None:
        width = protocol["local_preferred_position_half_width"]
        factor = protocol["local_weight_multiplier"]
        weights = [weight * factor if abs(cell["preferred_position"] - center) <= width
                   else weight for cell, weight in zip(cells, weights)]
    policy = OnlineFlyPolicy(config, weights=weights)
    policy.begin(PositionObservation(True, 0, 1.0))
    actions = []
    dt = protocol["observation_dt_us"]
    span = protocol["traversal_us"]
    for time_us in range(dt, span + dt, dt):
        position = max(0.0, 1.0 - time_us / span)
        actions.extend(policy.step(PositionObservation(True, 0, position)))
    actions.extend(policy.finish())
    downs = [action for action in actions if action.kind is KeyActionKind.DOWN]
    return {
        "center": center,
        "changed_source_ids": [cell["source_id"] for cell, weight in zip(cells, weights)
                               if weight != cell["plastic_contact_rows"] / total],
        "actions": [{"time_us": action.episode_time_us, "lane": action.lane,
                     "kind": action.kind.value} for action in actions],
        "first_down_us": downs[0].episode_time_us if downs else None,
        "first_down_position": (1.0 - downs[0].episode_time_us / span) if downs else None,
        "policy_metadata": policy.reproducibility_metadata(),
    }


def main() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    source_path = ROOT / protocol["source_config"]
    source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
    if source_hash != protocol["source_config_sha256"]:
        raise RuntimeError("frozen source config hash mismatch")
    config = load_position_config(ROOT, protocol["source_config"])
    arms = [("initial_weights", None)] + [
        (f"local_{center}", center) for center in protocol["probe_centers"]]
    records = {}
    repeat_ok = True
    for name, center in arms:
        repeats = [run_arm(config, protocol, center)
                   for _ in range(protocol["replays_per_arm"])]
        repeat_ok &= all(row == repeats[0] for row in repeats[1:])
        records[name] = repeats[0]
    baseline_quiet = records["initial_weights"]["first_down_us"] is None
    local_pass = []
    for center in protocol["probe_centers"]:
        row = records[f"local_{center}"]
        position = row["first_down_position"]
        local_pass.append(position is not None and abs(position - center) <= 0.1)
    result = {
        "protocol_id": protocol["protocol_id"],
        "protocol_sha256": hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
        "source_config_sha256": source_hash,
        "arms": records,
        "baseline_quiet": baseline_quiet,
        "local_pass": local_pass,
        "repeat_ok": repeat_ok,
        "status": "PASS" if baseline_quiet and sum(local_pass) >= 2 and repeat_ok else "FAIL",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")
    print(json.dumps({key: result[key] for key in
                      ("status", "baseline_quiet", "local_pass", "repeat_ok")},
                     sort_keys=True))


if __name__ == "__main__":
    main()
