"""Predeclared EA-5 repeated-note development; only KC→MBON weights persist."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from project_b.ea_mvp.bridge import StreamingTapBridge
from project_b.ea_mvp.frozen_policy import FrozenFlyTapPolicy
from project_b.ea_mvp.local_learning import apply_local_teaching, stimulate_dans
from project_b.ea_mvp.teacher import JudgementDanAdapter
from project_b.malecns_continuous_position_learning.online_policy import load_position_config
from project_b.malecns_continuous_position_learning.probe import _lif
from project_b.osu.config import OsuConfig
from project_b.osu.feedback import GameFeedbackEvent
from project_b.osu.types import KeyActionKind, TapNote

from run_ea_mvp_teacher_local import verify_source


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = ROOT / "configs/ea_mvp_development_v1.json"


def run_episode(config: dict, teacher: dict, dev: dict, coverage: dict[int, set[int]],
                kc_ids: tuple[int, ...], originals: list[float], weights: list[float],
                arm: str, index: int, *,
                teaching_label_override: str | None = None) -> tuple[list[float], dict]:
    game = OsuConfig(od=dev["od"], ruleset="lazer")
    bridge = StreamingTapBridge(TapNote(f"development-{index}", 0, dev["note_time_us"]),
                                game, visible_lead_us=dev["visible_lead_us"],
                                dt_us=teacher["dt_us"])
    policy = FrozenFlyTapPolicy(config, weights=weights)
    before = tuple(weights)
    trace = bridge.run(policy)
    feedback = tuple(trace.feedback)
    adapter = JudgementDanAdapter(
        dt_us=teacher["dt_us"], dan_source_ids=tuple(teacher["dan_source_ids"]),
        amplitude_mv_equivalent=teacher["dan_pulse"]["amplitude_mv_equivalent"],
        duration_us=teacher["dan_pulse"]["duration_us"],
        pulse_labels=frozenset(label for label, choice in teacher["judgement_to_dan"].items()
                               if choice == "pulse"))
    local_rows = []
    for delivery in feedback:
        teaching_event = (delivery.event if teaching_label_override is None else
                          GameFeedbackEvent(delivery.event.available_at_us,
                                            teaching_label_override))
        pulse = adapter.translate(teaching_event, observed_at_us=delivery.delivered_at_us)
        dan_spikes = stimulate_dans(pulse, _lif(config), dt_us=teacher["dt_us"],
                                    enabled=arm != "dan_off")
        local = apply_local_teaching(
            weights=weights, original_weights=originals, kc_source_ids=kc_ids,
            spikes=policy.fly._sim.snapshot().spikes, dan_spikes=dan_spikes,
            dan_coverage=coverage, window_us=teacher["ltd"]["window_us"],
            tau_us=teacher["ltd"]["tau_us"], eta=teacher["ltd"]["eta"],
            minimum_fraction=teacher["ltd"]["minimum_fraction"],
            plasticity_on=arm != "plasticity_off")
        weights = list(local.weights_after)
        local_rows.append({"teaching_event": asdict(teaching_event),
                           "pulse": asdict(pulse) if pulse else None,
                           "result": asdict(local)})
    first_down = next((action.time_us for action in trace.actions
                       if action.kind is KeyActionKind.DOWN), None)
    hit_error = None if first_down is None else first_down - dev["note_time_us"]
    good_or_better = hit_error is not None and abs(hit_error) <= 73500
    record = {"episode": index, "arm": arm,
              "first_down_us": first_down, "first_down_error_us": hit_error,
              "first_down_good_or_better": good_or_better,
              "game_results": [asdict(row) for row in trace.results],
              "feedback": [asdict(row) for row in feedback],
              "actions": [asdict(row) for row in trace.actions],
              "local_teaching": local_rows,
              "weights_before": before, "weights_after": tuple(weights)}
    return weights, record


def main(protocol_path: Path = DEFAULT_PROTOCOL) -> None:
    protocol_path = protocol_path.resolve()
    if protocol_path.parent != ROOT / "configs":
        raise ValueError("development protocol must be in this repository's configs")
    output = ROOT / "runs/ea_mvp" / (protocol_path.stem.replace("ea_mvp_", "") + ".json")
    dev = json.loads(protocol_path.read_text(encoding="utf-8"))
    teacher_path = ROOT / dev["teacher_protocol"]
    teacher = json.loads(teacher_path.read_text(encoding="utf-8"))
    verify_source(ROOT / teacher["source_config"], teacher["source_config_lf_sha256"],
                  teacher["source_config_legacy_crlf_sha256"])
    verify_source(ROOT / teacher["anatomy_audit"], teacher["anatomy_audit_lf_sha256"],
                  teacher["anatomy_audit_legacy_crlf_sha256"])
    config = load_position_config(ROOT, teacher["source_config"])
    audit = json.loads((ROOT / teacher["anatomy_audit"]).read_text(encoding="utf-8"))
    roster = audit["previously_audited_pam08_roster_scope"][
        "minimum_cardinality_set_for_maximum_coverage"]
    coverage = {int(row["source_id"]): set(row["gamma4_kc_source_ids"]) for row in roster}
    cells = config["circuit"]["selected_kcs"]
    kc_ids = tuple(int(row["source_id"]) for row in cells)
    assert set().union(*coverage.values()) == set(kc_ids)
    total = sum(row["plastic_contact_rows"] for row in cells)
    originals = [row["plastic_contact_rows"] / total for row in cells]
    assert dev["checkpoints"][0] == 0 and dev["checkpoints"][-1] == dev["episodes"]
    assert set(dev["arms"]) == {"learning_on", "dan_off", "plasticity_off"}
    result = {"protocol_id": dev["protocol_id"],
              "protocol_sha256": hashlib.sha256(protocol_path.read_bytes()).hexdigest(),
              "teacher_protocol_sha256": hashlib.sha256(teacher_path.read_bytes()).hexdigest(),
              "arms": {}, "status": "RUNNING"}
    output.parent.mkdir(parents=True, exist_ok=True)
    for arm in dev["arms"]:
        weights = list(originals)
        episodes = []
        checkpoints = {"0": list(weights)}
        for index in range(1, dev["episodes"] + 1):
            weights, record = run_episode(config, teacher, dev, coverage, kc_ids,
                                          originals, weights, arm, index)
            episodes.append(record)
            if index in dev["checkpoints"]:
                checkpoints[str(index)] = list(weights)
                print(json.dumps({"arm": arm, "episode": index,
                                  "first_down_error_us": record["first_down_error_us"],
                                  "changed_weights": sum(a != b for a, b in zip(weights, originals))}),
                      flush=True)
        result["arms"][arm] = {"checkpoints": checkpoints, "episodes": episodes}
        output.write_text(json.dumps(result, indent=2, sort_keys=True, default=str) + "\n",
                          encoding="utf-8")
    result["status"] = "COMPLETED"
    output.write_text(json.dumps(result, indent=2, sort_keys=True, default=str) + "\n",
                      encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    main(parser.parse_args().protocol)
