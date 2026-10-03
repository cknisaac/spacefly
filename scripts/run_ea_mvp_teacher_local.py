"""Run frozen EA-4 one-pulse controls; this is not task training."""

from __future__ import annotations

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
from project_b.osu.types import TapNote


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/ea_mvp_teacher_local_protocol.json"
OUTPUT = ROOT / "runs/ea_mvp/teacher_local_result.json"


def verify_source(path: Path, lf_hash: str, legacy_crlf_hash: str) -> None:
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != lf_hash or b"\r" in content:
        raise RuntimeError(f"current LF source does not match EA pin: {path}")
    crlf = content.replace(b"\n", b"\r\n")
    if hashlib.sha256(crlf).hexdigest() != legacy_crlf_hash:
        raise RuntimeError(f"normalized source does not match historical pin: {path}")


def main() -> None:
    p = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    verify_source(ROOT / p["source_config"], p["source_config_lf_sha256"],
                  p["source_config_legacy_crlf_sha256"])
    verify_source(ROOT / p["anatomy_audit"], p["anatomy_audit_lf_sha256"],
                  p["anatomy_audit_legacy_crlf_sha256"])
    config = load_position_config(ROOT, p["source_config"])
    audit = json.loads((ROOT / p["anatomy_audit"]).read_text(encoding="utf-8"))
    cells = config["circuit"]["selected_kcs"]
    kc_ids = tuple(int(row["source_id"]) for row in cells)
    roster = audit["previously_audited_pam08_roster_scope"][
        "minimum_cardinality_set_for_maximum_coverage"]
    coverage = {int(row["source_id"]): set(row["gamma4_kc_source_ids"]) for row in roster}
    assert set(coverage) == set(p["dan_source_ids"])
    assert set().union(*coverage.values()) == set(kc_ids) == set(audit["frozen_cohort"])
    assert audit["pam08_roster_and_frozen_kc_mbon_roi_complete"]
    assert audit["unknown_roi_candidate_rows_by_scope"]["audited_pam08_roster"] == 0
    total = sum(row["plastic_contact_rows"] for row in cells)
    originals = [row["plastic_contact_rows"] / total for row in cells]

    mapping = p["judgement_to_dan"]
    assert set(mapping) == {"PERFECT", "GREAT", "GOOD", "OK", "MEH", "MISS"}
    adapter = JudgementDanAdapter(
        dt_us=p["dt_us"], dan_source_ids=tuple(p["dan_source_ids"]),
        amplitude_mv_equivalent=p["dan_pulse"]["amplitude_mv_equivalent"],
        duration_us=p["dan_pulse"]["duration_us"],
        pulse_labels=frozenset(label for label, action in mapping.items() if action == "pulse"))
    assert all(action in {"pulse", "silent"} for action in mapping.values())

    note = TapNote("ea4-note", 0, p["fixture_note"]["time_us"])
    game = OsuConfig(od=p["fixture_note"]["od"], ruleset="lazer")
    bridge = StreamingTapBridge(note, game, visible_lead_us=p["fixture_note"]["visible_lead_us"],
                                dt_us=p["dt_us"])
    policy = FrozenFlyTapPolicy(config)
    trace = bridge.run(policy)
    assert not trace.actions and len(trace.feedback) == 1
    delivered = trace.feedback[0]
    assert delivered.event.judgement_label == "MISS"
    kc_spikes = policy.fly._sim.snapshot().spikes

    early_rejected = False
    try:
        adapter.translate(delivered.event, observed_at_us=delivered.event.available_at_us - 1)
    except ValueError:
        early_rejected = True
    assert early_rejected

    ltd = p["ltd"]
    arms = {}
    for arm in p["arms"]:
        records = []
        for _ in range(2):
            event = delivered.event
            observed = delivered.delivered_at_us
            if arm == "late_unpaired_miss":
                event = GameFeedbackEvent(900_000, "MISS")
                observed = 900_000
            elif arm == "good_no_pulse":
                event = GameFeedbackEvent(450_000, "GOOD")
                observed = 451_000
            elif arm == "no_result":
                event = None
            pulse = adapter.translate(event, observed_at_us=observed) if event else None
            dan_spikes = stimulate_dans(pulse, _lif(config), dt_us=p["dt_us"],
                                        enabled=arm != "miss_dan_off")
            result = apply_local_teaching(
                weights=list(originals), original_weights=list(originals),
                kc_source_ids=kc_ids, spikes=kc_spikes, dan_spikes=dan_spikes,
                dan_coverage=coverage, window_us=ltd["window_us"],
                tau_us=ltd["tau_us"], eta=ltd["eta"],
                minimum_fraction=ltd["minimum_fraction"],
                plasticity_on=arm != "miss_plasticity_off",
                eligibility_on=arm != "miss_eligibility_off")
            records.append({"event": asdict(event) if event else None,
                            "observed_at_us": observed if event else None,
                            "pulse": asdict(pulse) if pulse else None,
                            "local": asdict(result)})
        arms[arm] = {"record": records[0], "replay_exact": records[0] == records[1]}

    primary = arms["miss_dan_on"]["record"]
    changes = primary["local"]["changes"]
    primary_spikes = dict(primary["local"]["dan_spikes"])
    controls = [name for name in p["arms"] if name != "miss_dan_on"]
    checks = {
        "no_early_teaching": early_rejected and
            primary["pulse"]["onset_us"] >= primary["observed_at_us"] >=
            primary["event"]["available_at_us"],
        "all_three_dans_spike": set(primary_spikes) == set(p["dan_source_ids"]) and
            all(primary_spikes[source_id] for source_id in p["dan_source_ids"]),
        "selected_local_update": bool(changes) and all(
            change["eligibility"] > 0 and change["connected_active_dans"] and
            change["new_weight_mv"] >= originals[change["edge_index"]] * ltd["minimum_fraction"]
            for change in changes),
        "all_negative_controls_unchanged": all(
            not arms[name]["record"]["local"]["changes"] and
            tuple(arms[name]["record"]["local"]["weights_after"]) == tuple(originals)
            for name in controls),
        "exact_replay": all(row["replay_exact"] for row in arms.values()),
    }
    result = {"protocol_id": p["protocol_id"],
              "protocol_sha256": hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
              "source_lf_and_legacy_crlf_verified": True,
              "roster_coverage": {str(key): sorted(value) for key, value in coverage.items()},
              "observed_game_feedback": asdict(delivered),
              "baseline_kc_spikes": [asdict(row) for row in kc_spikes
                                     if row.neuron_index < len(kc_ids)],
              "arms": arms, "checks": checks,
              "status": "PASS" if all(checks.values()) else "FAIL"}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks": checks,
                      "changed_slots": len(changes)}, sort_keys=True))


if __name__ == "__main__":
    main()
