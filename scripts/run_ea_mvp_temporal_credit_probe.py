"""Select an eligibility-window candidate using no-game neural controllability."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from project_b.malecns_continuous_position_learning.online_policy import OnlineFlyPolicy, load_position_config
from project_b.osu.adapter import PositionObservation
from project_b.osu.types import KeyActionKind

from run_ea_mvp_teacher_local import verify_source


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/ea_mvp_temporal_credit_probe_v1.json"
OUTPUT = ROOT / "runs/ea_mvp/temporal_credit_probe_v1.json"


def traverse(config: dict, weights: list[float], span_us: int) -> tuple[OnlineFlyPolicy, list]:
    policy = OnlineFlyPolicy(config, weights=weights)
    policy.begin(PositionObservation(True, 0, 1.0))
    actions = []
    for time_us in range(policy.dt_us, span_us + policy.dt_us, policy.dt_us):
        actions.extend(policy.step(PositionObservation(True, 0,
            max(0.0, 1.0 - time_us / span_us))))
    actions.extend(policy.finish())
    return policy, actions


def main() -> None:
    p = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    teacher = json.loads((ROOT / p["source_teacher_protocol"]).read_text(encoding="utf-8"))
    verify_source(ROOT / teacher["source_config"], teacher["source_config_lf_sha256"],
                  teacher["source_config_legacy_crlf_sha256"])
    config = load_position_config(ROOT, teacher["source_config"])
    cells = config["circuit"]["selected_kcs"]
    total = sum(cell["plastic_contact_rows"] for cell in cells)
    originals = [cell["plastic_contact_rows"] / total for cell in cells]
    baseline, baseline_actions = traverse(config, originals, p["position_traversal_us"])
    spikes = baseline._sim.snapshot().spikes
    assert not any(action.kind is KeyActionKind.DOWN for action in baseline_actions)
    candidates = []
    for window in p["candidate_windows_us"]:
        eligible = sorted({spike.neuron_index for spike in spikes
                           if spike.neuron_index < len(cells)
                           and p["hypothetical_dan_gate_us"] - window <= spike.time_us
                           <= p["hypothetical_dan_gate_us"]})
        weights = [originals[i] * p["local_intervention_fraction"]
                   if i in eligible else originals[i] for i in range(len(cells))]
        replays = []
        for _ in range(p["replays_per_candidate"]):
            _, actions = traverse(config, weights, p["position_traversal_us"])
            replays.append([(a.episode_time_us, a.kind.value) for a in actions])
        first_down = next((time for time, kind in replays[0] if kind == "down"), None)
        candidates.append({"window_us": window, "eligible_source_ids":
                           [cells[i]["source_id"] for i in eligible],
                           "first_down_us": first_down,
                           "exact_replay": all(row == replays[0] for row in replays),
                           "passes": len(eligible) >= 3 and first_down is not None and
                           all(row == replays[0] for row in replays)})
    selected = next((row["window_us"] for row in candidates if row["passes"]), None)
    result = {"protocol_id": p["protocol_id"],
              "protocol_sha256": hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
              "baseline_spikes": [{"time_us": spike.time_us,
                                   "source_id": cells[spike.neuron_index]["source_id"]}
                                  for spike in spikes if spike.neuron_index < len(cells)],
              "candidates": candidates, "selected_window_us": selected,
              "status": "PASS" if selected is not None else "FAIL"}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "selected_window_us": selected,
                      "candidates": candidates}, sort_keys=True))


if __name__ == "__main__":
    main()
