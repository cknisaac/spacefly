"""Independent source/event/state audit of the complete B5.4 matched panel."""

from __future__ import annotations

from collections import Counter, defaultdict
import gzip
import json
import math
from pathlib import Path
import statistics

from project_b.electrical_v1 import build_circuit
from project_b.electrical_v1.source import ADDED_VISUAL_IDS, file_sha
from project_b.electrical_v1.visual_boundary_probe import VisualBoundaryProbe


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/figures/electrical_v1_1_visual_boundary_validation"
PROTOCOL = ROOT / "configs/electrical_v1_1_visual_boundary_validation.json"
V11_CONFIG = ROOT / "configs/electrical_model_v1_1.json"
MANIFEST = ROOT / "data/processed/malecns_v1_electrical_v1_1/manifest.json"
OLD_VISUAL = (13285, 13707, 13874)
ARMS = ("v1_reference", "v1_1_connected", "v1_1_disconnected")
LEVELS = ("low", "nominal", "high")


def require(ok: bool, message: str) -> None:
    if not ok:
        raise AssertionError(message)


def read_seed(seed: int) -> dict:
    with gzip.open(OUT / f"seed_{seed}.json.gz", "rt", encoding="utf-8") as stream:
        return json.load(stream)


def replay_first_nominal(seed: int, circuit, arm: str, saved: dict) -> None:
    """Reintegrate from t=0 independently of the B5.4 runner's trial function."""
    model = VisualBoundaryProbe(circuit, seed=seed)
    model.run_until(11_000_000)
    if arm == "v1_1_disconnected":
        require(len(model.apply_disconnection("aMe12_to_KC")) == 48, "Replay lesion count")
    source_ids = OLD_VISUAL if arm == "v1_reference" else tuple(sorted(OLD_VISUAL+ADDED_VISUAL_IDS))
    model.set_current(source_ids, 22.5)
    model.run_until(11_200_000)
    model.clear_current()
    model.run_until(11_500_000)
    post_spikes = [x for x in model.spikes if 11_000_000 <= x[0] < 11_500_000]
    post_events = [x for x in model.delivered_event_log if 11_000_000 <= x[0] < 11_500_000]
    require(post_spikes == [tuple(x) for x in saved["post_spikes_time_us_source_id"]],
            "Independent spike replay mismatch")
    require(post_events == [tuple(x) for x in saved[
        "delivered_events_time_us_pre_post_source_row_kind_amplitude"]],
        "Independent delivered-event replay mismatch")
    for k in saved["KC"]:
        i = model.dynamic_of_source[k["source_id"]]
        require(abs(float(model.peak_voltage_mv[i])-k["peak_voltage_mv"]) < 1e-11,
                "Independent KC voltage replay mismatch")
        require(abs(float(model.peak_synaptic_pa[i])-k["peak_synaptic_pa"]) < 1e-11,
                "Independent KC synaptic-current replay mismatch")
    i = model.dynamic_of_source[519131]
    require(abs(float(model.peak_voltage_mv[i])-saved["MBON32_peak_voltage_mv"]) < 1e-11,
            "Independent MBON voltage replay mismatch")


def main() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    result = json.loads((OUT / "result.json").read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    require(result["complete"] and result["trial_count"] == 270 and
            result["reference_checks"] == 90 and result["replay_checks"] == 27,
            "Incomplete locked panel")
    require(file_sha(PROTOCOL) == result["protocol_sha256"], "Protocol hash mismatch")
    require(file_sha(V11_CONFIG) == protocol["v1_1_config_sha256"] == manifest["config_sha256"],
            "V1.1 config hash mismatch")
    require(file_sha(ROOT / "configs/electrical_model_v1.json") ==
            protocol["v1_config_sha256"] == manifest["v1_config_sha256"],
            "V1 frozen hash mismatch")
    for name, sha in manifest["artifact_sha256"].items():
        require(file_sha(MANIFEST.parent / name) == sha, f"V1.1 artifact changed: {name}")
    old, new = build_circuit(), build_circuit(V11_CONFIG)
    old_edges = {e.source_row: e for e in old.connections}
    new_edges = {e.source_row: e for e in new.connections}
    require((len(new_edges)-len(old_edges), new.counts()["source_contacts"]-
             old.counts()["source_contacts"]) == (62, 603), "Unexpected topology delta")
    for row, before in old_edges.items():
        after = new_edges[row]
        require((old.cells[before.pre].source_id, old.cells[before.post].source_id,
                 before.contacts, before.effect_state, before.effect_evidence,
                 before.weight_pa, before.candidate_contacts) ==
                (new.cells[after.pre].source_id, new.cells[after.post].source_id,
                 after.contacts, after.effect_state, after.effect_evidence,
                 after.weight_pa, after.candidate_contacts),
                f"V1 source row changed: {row}")
    added = [new_edges[row] for row in set(new_edges)-set(old_edges)]
    added_fast = [e for e in added if e.effect_state == "ACTIVE_FAST"]
    require((len(added_fast), sum(e.contacts for e in added_fast)) == (48, 569),
            "Added fast source block changed")
    require(all(new.cells[e.pre].source_id in ADDED_VISUAL_IDS and
                new.cells[e.post].kind == "KC" and e.effect_evidence == "INFERRED" and
                e.weight_pa == e.contacts*.03 for e in added_fast),
            "Unapproved added fast effect")
    require(all(e.effect_state == "UNKNOWN" and e.weight_pa is None for e in added
                if e not in added_fast), "New non-KC effect activated")
    kc_ids = {c.source_id for c in new.cells if c.kind == "KC"}
    new_kcs = set(manifest["newly_contacted_KC_ids"])
    require(len(kc_ids) == 107 and len(new_kcs) == 20, "KC cohort changed")
    edge_by_pre = defaultdict(list)
    for e in new.connections:
        if e.effect_state == "ACTIVE_FAST" and new.cells[e.pre].kind == "sensory" and new.cells[e.post].kind == "KC":
            edge_by_pre[new.cells[e.pre].source_id].append(
                (new.cells[e.post].source_id, e.source_row, e.weight_pa))
    grouped = defaultdict(list)
    event_terms = 0
    replay_count = 0
    for seed in protocol["boundary_seeds"]:
        payload = read_seed(seed)
        require(payload["status"] == "complete" and len(payload["trials"]) == 90,
                f"Seed {seed} incomplete")
        require(file_sha(OUT / f"seed_{seed}.json.gz") == next(x["file_sha256"] for x in
                result["rows"] if x["seed"] == seed), "Seed file hash mismatch")
        require(payload["protocol_sha256"] == result["protocol_sha256"], "Seed protocol mismatch")
        for trial in payload["trials"]:
            key = (seed, trial["onset_us"], trial["level"])
            grouped[key].append(trial)
            arm = trial["arm"]
            require(arm in ARMS and trial["level"] in LEVELS, "Unexpected arm/level")
            ids = set(OLD_VISUAL if arm == "v1_reference" else OLD_VISUAL+ADDED_VISUAL_IDS)
            require(set(trial["stimulus"]["source_ids"]) == ids and
                    trial["stimulus"]["amplitude_pa_per_cell"] ==
                    15*protocol["visual_levels"][trial["level"]],
                    "Stimulus mismatch")
            require(trial["final_dan_state"] == 0 and not trial["final_plasticity_enabled"] and
                    trial["peak_queued_events"] < 100000,
                    "Learning/safety violation")
            removed = set(trial["removed_source_rows"])
            require(removed == ({e.source_row for e in added_fast}
                                if arm == "v1_1_disconnected" else set()),
                    "Added-source lesion mismatch")
            visual_spikes = trial["visual_spike_times_us_by_source_id"]
            require(set(map(int, visual_spikes)) == set(OLD_VISUAL+ADDED_VISUAL_IDS),
                    "Visual spike IDs incomplete")
            expected = []
            for sid in ids:
                for t in visual_spikes[str(sid)]:
                    for post, row, amplitude in edge_by_pre[sid]:
                        if row not in removed and t+1000 < trial["onset_us"]+500000:
                            expected.append((t+1000, sid, post, row, "FAST", amplitude))
            actual = [tuple(e) for e in trial[
                "delivered_events_time_us_pre_post_source_row_kind_amplitude"]
                if e[4] == "FAST" and e[1] in ids and e[2] in kc_ids]
            require(Counter(actual) == Counter(expected), "Visual source spike/event arithmetic mismatch")
            event_terms += len(actual)
            events_by_kc = defaultdict(list)
            for event in actual:
                events_by_kc[event[2]].append(event)
            kc = trial["KC"]
            require(len(kc) == 107 and {r["source_id"] for r in kc} == kc_ids,
                    "KC detail cohort incomplete")
            require(trial["KC_receiving_visual_count"] ==
                    sum(bool(events_by_kc[r["source_id"]]) for r in kc),
                    "KC received-input count mismatch")
            spike_by_id = defaultdict(list)
            for t, sid in trial["post_spikes_time_us_source_id"]:
                spike_by_id[sid].append(t)
            require(trial["KC_spiking_count"] == sum(bool(spike_by_id[sid]) for sid in kc_ids),
                    "KC spike-count mismatch")
            for r in kc:
                sid = r["source_id"]
                require(r["visual_event_count"] == len(events_by_kc[sid]) and
                        r["spike_times_us"] == spike_by_id[sid] and
                        abs(r["closest_onset_margin_mv"] - (-48-r["peak_voltage_mv"])) < 1e-11,
                        "KC row mismatch")
                charge = sum(e[5]*5*(1-math.exp(-(trial["onset_us"]+500000-e[0])/5000))
                             for e in events_by_kc[sid])
                require(abs(charge-r["visual_charge_fc"]) < 1e-10,
                        "KC integrated-charge mismatch")
            require(trial["MBON32_spike_times_us"] == spike_by_id[519131] and
                    abs(trial["MBON32_closest_onset_margin_mv"] -
                        (-43-trial["MBON32_peak_voltage_mv"])) < 1e-11,
                    "MBON32 row mismatch")
            require(trial["DN_spike_times_us_by_id"] ==
                    {str(sid): spike_by_id[sid] for sid in (519624, 523769)},
                    "DN row mismatch")
            require(all(len(row) == len(trial["trace_columns"]) for row in trial["trace"]),
                    "Trace width mismatch")
            if trial["onset_us"] == 11_000_000 and trial["level"] == "nominal":
                replay_first_nominal(seed, old if arm == "v1_reference" else new, arm, trial)
                replay_count += 1
    require(len(grouped) == 90, "Expected 90 matched seed/onset/level groups")
    summaries = {}
    for level in LEVELS:
        summaries[level] = {}
        for arm in ARMS:
            group = [r for key, rows in grouped.items() if key[2] == level
                     for r in rows if r["arm"] == arm]
            require(len(group) == 30, "Expected 30 trials per arm/level")
            rows = [[x for x in r["KC"] if x["source_id"] in new_kcs] for r in group]
            margins = [x["closest_onset_margin_mv"] for group_rows in rows for x in group_rows]
            summaries[level][arm] = {
                "trials": 30,
                "visual_spikes_per_trial": sorted({sum(len(v) for v in r[
                    "visual_spike_times_us_by_source_id"].values()) for r in group}),
                "added_visual_fast_events_per_trial": sorted({sum(e[4] == "FAST" and
                    e[1] in ADDED_VISUAL_IDS for e in r[
                    "delivered_events_time_us_pre_post_source_row_kind_amplitude"]) for r in group}),
                "KC_receiving_count_per_trial": sorted({r["KC_receiving_visual_count"] for r in group}),
                "KC_spiking_count_per_trial": sorted({r["KC_spiking_count"] for r in group}),
                "newly_contacted_KC_spiking_per_trial": sorted({sum(bool(x["spike_times_us"])
                    for x in group_rows) for group_rows in rows}),
                "new_KC_min_onset_gap_mv": min(margins),
                "new_KC_median_onset_gap_mv": statistics.median(margins),
                "MBON32_spikes_per_trial": sorted({len(r["MBON32_spike_times_us"]) for r in group}),
                "MBON32_min_onset_gap_mv": min(r["MBON32_closest_onset_margin_mv"] for r in group),
                "APL_peak_local_state": sorted({r["APL_peak_local_state"] for r in group}),
            }
    for key, rows in grouped.items():
        by_arm = {r["arm"]: r for r in rows}
        require(set(by_arm) == set(ARMS), "Missing matched arm")
        v1, connected, disconnected = (by_arm[a] for a in ARMS)
        require(len({r["initial_shared_state_sha256"] for r in rows}) == 1 and
                len({r["initial_boundary_sha256"] for r in rows}) == 1 and
                len({r["terminal_boundary_sha256"] for r in rows}) == 1,
                "Initial/final boundary or shared-state mismatch")
        require(v1["KC"] == disconnected["KC"] and
                v1["MBON32_peak_voltage_mv"] == disconnected["MBON32_peak_voltage_mv"] and
                v1["MBON32_spike_times_us"] == disconnected["MBON32_spike_times_us"] and
                v1["DN_spike_times_us_by_id"] == disconnected["DN_spike_times_us_by_id"],
                "Disconnected arm perturbed the old functional circuit")
        for sid in OLD_VISUAL:
            require(v1["visual_spike_times_us_by_source_id"][str(sid)] ==
                    connected["visual_spike_times_us_by_source_id"][str(sid)] ==
                    disconnected["visual_spike_times_us_by_source_id"][str(sid)],
                    "Old visual source mismatch")
        for sid in ADDED_VISUAL_IDS:
            require(connected["visual_spike_times_us_by_source_id"][str(sid)] ==
                    disconnected["visual_spike_times_us_by_source_id"][str(sid)],
                    "Added source spike mismatch")
    nominal_groups = [rows for key, rows in grouped.items() if key[2] == "nominal"]
    pass_primary = all(
        sum(bool(k["spike_times_us"]) for k in next(r for r in rows if r["arm"] ==
            "v1_1_connected")["KC"] if k["source_id"] in new_kcs) >= 1 and
        sum(bool(k["spike_times_us"]) for k in next(r for r in rows if r["arm"] ==
            "v1_1_disconnected")["KC"] if k["source_id"] in new_kcs) == 0
        for rows in nominal_groups)
    audit = {"status": "pass", "stage_result": "PASS" if pass_primary else "FAIL",
             "v1_1_visual_boundary_pass": pass_primary,
             "protocol_sha256": file_sha(PROTOCOL),
             "v1_config_sha256": protocol["v1_config_sha256"],
             "v1_1_config_sha256": protocol["v1_1_config_sha256"],
             "matched_groups": len(grouped), "trials_checked": sum(len(x) for x in grouped.values()),
             "visual_event_terms_checked": event_terms,
             "independent_nominal_first_pulse_replays": replay_count,
             "v1_source_rows_preserved": len(old_edges),
             "added_source_rows": len(added),
             "added_active_fast_rows": len(added_fast),
             "summaries": summaries}
    (OUT / "audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    print(json.dumps({key: audit[key] for key in
                      ("status", "stage_result", "matched_groups", "trials_checked",
                       "visual_event_terms_checked", "independent_nominal_first_pulse_replays")},
                     sort_keys=True))


if __name__ == "__main__":
    main()
