"""Two predeclared positive-RPE checkpoint contrasts using one fixed cohort."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from project_b.experiments import TinyLaneSession
from scripts.cue_300ms_necessity_diagnostic import probe_with_readout_trace
from scripts.cue_300ms_threshold_cohort_diagnostic import (
    assert_same_state_except_weights, digest, weights, window_count,
)
from scripts.exploration_map_diagnostic import load_long_rows, load_rows
from scripts.long_continuation import atomic_json, event_record, sha
from scripts.successive_update_interference_diagnostic import (
    LONG_LEDGER, LONG_META, LONG_PROTOCOL, ORIGINAL_LEDGER, make_config,
    timing_summary,
)
from scripts.update_direction_magnitude_diagnostic import geometry


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/cue_300ms_saturation_contrast_diagnostic.json"
A3_LEDGER = ROOT / "docs/figures/successive_update_interference/runs.jsonl"
A5 = ROOT / "docs/figures/cue_300ms_necessity"
OUT = ROOT / "docs/figures/cue_300ms_saturation_contrast"
BRANCHES = ("no_update", "real_full", "real_except_300ms_targets_97_105")
TARGETS = (372, 377)


def first_note(probe: dict, trace: dict) -> dict:
    rise = next((x for x in trace["threshold_crossings"]
                 if x["threshold"] == "on" and x["direction"] == "rise"), None)
    t = rise["time_us"] if rise is not None else None
    downs = probe["down_actions"]
    dt = trace["initial"]["dt_us"]
    return {
        "first_on_threshold_rise_us": t,
        "readout_window_count_previous_tick": window_count(trace, t-dt) if t else None,
        "readout_window_count_at_crossing": window_count(trace, t) if t else None,
        "on_threshold": trace["initial"]["on_threshold"],
        "first_down_us": downs[0]["time_us"] if downs else None,
        "first_down_disposition": downs[0]["disposition"] if downs else None,
        "first_scored_down_us": next((a["time_us"] for a in downs
                                       if a["note_id"] == "probe-0"), None),
        "first_judgement": probe["events"][0]["judgement"],
        "first_scored_error_us": probe["events"][0]["hit_error_us"],
    }


def main() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert [(x["seed"], x["one_based_outcome"])
            for x in protocol["checkpoint_selection"]] == [(2002, 372), (2002, 377)]
    assert protocol["branches_per_checkpoint"] == list(BRANCHES)
    a3 = next(json.loads(line) for line in A3_LEDGER.read_text(encoding="utf-8").splitlines()
              if json.loads(line)["seed"] == 2002)
    a5 = json.loads((A5 / "result.json").read_text(encoding="utf-8"))
    assert sha(A5 / "result.json") == json.loads((A5 / "status.json").read_text())["result_sha256"]
    long_rows = load_long_rows()
    originals = load_rows(ORIGINAL_LEDGER)
    long_protocol = json.loads(LONG_PROTOCOL.read_text(encoding="utf-8"))
    long_meta = json.loads(LONG_META.read_text(encoding="utf-8"))
    common = (tuple(long_meta["probe_relative_note_offsets_us"]),
              tuple(long_meta["probe_cue_gains"]))
    session = TinyLaneSession(make_config(2002, originals, long_rows, long_protocol))
    source = long_rows[2002]
    captured = {}
    real_apply = session.simulator.apply_dopamine

    def intercept(dopamine: float):
        outcome = session.resolved_count + 1
        if outcome not in TARGETS:
            return real_apply(dopamine)
        del session.simulator.apply_dopamine
        try:
            pre_bytes = session.checkpoint_bytes()
            geo = geometry(session, dopamine)
            changes = real_apply(dopamine)
        finally:
            session.simulator.apply_dopamine = intercept
        captured[outcome] = {"pre_checkpoint_bytes": pre_bytes, "geometry": geo,
                             "changes": len(changes)}
        return changes

    session.simulator.apply_dopamine = intercept
    for outcome in range(1, max(TARGETS)+1):
        while session.resolved_count < outcome:
            session.step()
        assert event_record(session, outcome-1) == source["training_events"][outcome-1]
    del session.simulator.apply_dopamine
    assert set(captured) == set(TARGETS)
    edge_meta = a5["source_pathway_structure"]["edge_metadata"]
    selected = [i for i, edge in enumerate(edge_meta)
                if edge["preferred_time_to_contact_us"] == 300_000
                and edge["post_motor_id"] in range(97, 106)]
    selected_slots = [a5["pre_update_geometry"]["edge_slots"][i] for i in selected]
    assert len(selected) == 36 and selected_slots == [
        slot for slot in range(139, 184) if slot not in (148,149,150,160,161,162,172,173,174)]
    OUT.mkdir(parents=True, exist_ok=True)
    atomic_json(OUT / "status.json", {"status": "running", "protocol_sha256": sha(PROTOCOL)})
    cases = {}
    for outcome in TARGETS:
        prior = next(c for c in a3["checkpoints"] if c["after_outcomes"] == outcome)
        prior_before = next(c for c in a3["checkpoints"] if c["after_outcomes"] == outcome-1)
        assert prior["training_event"] == source["training_events"][outcome-1]
        pre_bytes = captured[outcome]["pre_checkpoint_bytes"]
        pre = TinyLaneSession.from_trusted_checkpoint_bytes(pre_bytes)
        geo = captured[outcome]["geometry"]
        assert weights(pre) == geo["weights_before_mv"]
        assert pre.simulator.current_time_us == geo["time_us"]
        assert geo["dopamine"] == prior["training_event"]["rpe"]
        # A3's pickle memoization can differ across an in-memory and loaded
        # clone even when all behavior-relevant fields agree. Keep this hash
        # as an observed serialization diagnostic; verify the full geometry,
        # event replay and historical frozen probe below instead.
        historical_pickle_match = (hashlib.sha256(pre.checkpoint_bytes()).hexdigest()
                                   == prior["pre_update_canonical_sha256"])
        assert all(geo[k] == prior["update"][k] for k in geo)
        assert captured[outcome]["changes"] == prior["update"]["changed_edges"]
        for i, slot in enumerate(geo["edge_slots"]):
            e = pre.plasticity.eligibility_at(slot, geo["time_us"])
            assert math.isclose(e, geo["eligibility"][i], abs_tol=1e-12)
        assert [geo["edge_slots"][i] for i in selected] == selected_slots
        zero = TinyLaneSession.from_trusted_checkpoint_bytes(pre_bytes)
        zero.simulator.apply_dopamine(0.0)
        full = TinyLaneSession.from_trusted_checkpoint_bytes(pre_bytes)
        full.simulator.apply_dopamine(geo["dopamine"])
        assert weights(zero) == geo["weights_before_mv"]
        assert weights(full) == prior["update"]["weights_after_mv"]
        cut = TinyLaneSession.from_trusted_checkpoint_bytes(full.checkpoint_bytes())
        for i in selected:
            cut.plasticity._weights[geo["edge_slots"][i]] = geo["weights_before_mv"][i]
        assert_same_state_except_weights(cut, full)
        full_w, cut_w, before = weights(full), weights(cut), geo["weights_before_mv"]
        assert all(cut_w[i] == (before[i] if i in selected else full_w[i])
                   for i in range(480))
        sessions = dict(zip(BRANCHES, (zero, full, cut)))
        checkpoints = {name: s.checkpoint_bytes() for name, s in sessions.items()}
        (OUT / f"{outcome}_pre_update_checkpoint.pkl").write_bytes(pre_bytes)
        for name, value in checkpoints.items():
            (OUT / f"{outcome}_{name}_checkpoint.pkl").write_bytes(value)
        note_times = tuple(geo["time_us"] + x for x in common[0])
        records = {}
        for name in BRANCHES:
            probe, trace = probe_with_readout_trace(checkpoints[name], note_times, common[1])
            if name == "real_full":
                assert probe == prior["probe"]
            records[name] = {
                "checkpoint_sha256": hashlib.sha256(checkpoints[name]).hexdigest(),
                "weights_after_mv": weights(sessions[name]),
                "probe": probe, "readout_trace": trace,
                "first_note": first_note(probe, trace),
                "timing": timing_summary(probe),
            }
            print(json.dumps({"outcome": outcome, "branch": name,
                              "first": records[name]["first_note"],
                              "good": probe["metrics"]["good_or_better_count"],
                              "utility": probe["metrics"]["mean_utility"]}), flush=True)
        no_t = records["no_update"]["first_note"]["first_on_threshold_rise_us"]
        full_t = records["real_full"]["first_note"]["first_on_threshold_rise_us"]
        cut_t = records[BRANCHES[2]]["first_note"]["first_on_threshold_rise_us"]
        cases[str(outcome)] = {
            "source_training_event": prior["training_event"],
            "pre_update_geometry": geo,
            "pre_update_checkpoint_sha256": hashlib.sha256(pre_bytes).hexdigest(),
            "source_pre_update_canonical_sha256": prior["pre_update_canonical_sha256"],
            "historical_pickle_match": historical_pickle_match,
            "source_previous_probe_metrics": prior_before["probe"]["metrics"],
            "selected_edge_slots": selected_slots,
            "removed_applied_l1_mv": sum(abs(full_w[i]-before[i]) for i in selected),
            "retained_applied_l1_mv": sum(abs(a-b) for a,b in zip(cut_w,before)),
            "branches": records,
            "first_crossing_us": {"no_update": no_t, "real_full": full_t,
                                  BRANCHES[2]: cut_t},
            "full_minus_no_us": full_t-no_t if no_t is not None and full_t is not None else None,
            "omit_minus_full_us": cut_t-full_t if cut_t is not None and full_t is not None else None,
        }
    result = {
        "study_id": protocol["study_id"], "status": "complete",
        "protocol_sha256": sha(PROTOCOL), "source_a3_ledger_sha256": sha(A3_LEDGER),
        "source_long_ledger_sha256": sha(LONG_LEDGER),
        "source_original_ledger_sha256": sha(ORIGINAL_LEDGER),
        "a5_result_sha256": sha(A5 / "result.json"),
        "checkpoint_selection": protocol["checkpoint_selection"],
        "selected_edge_slots": selected_slots,
        "cases": cases, "completed_utc": datetime.now(timezone.utc).isoformat(),
    }
    atomic_json(OUT / "result.json", result)
    atomic_json(OUT / "status.json", {"status": "complete",
                                       "protocol_sha256": sha(PROTOCOL),
                                       "result_sha256": sha(OUT / "result.json")})
    print(json.dumps({"status": "complete", "first_crossings": {
        k: v["first_crossing_us"] for k,v in cases.items()}}, indent=2), flush=True)


if __name__ == "__main__":
    main()
