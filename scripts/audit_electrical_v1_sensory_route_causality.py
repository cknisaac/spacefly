"""Independent saved-data audit and predeclared B5 stage classification."""

from __future__ import annotations

from collections import Counter, defaultdict
import gzip
import hashlib
import json
import math
from pathlib import Path

from project_b.electrical_v1 import DNBoundary, build_circuit


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/figures/electrical_v1_sensory_route_causality"
PROTOCOL = ROOT / "configs/electrical_v1_sensory_route_causality.json"
MODEL_CONFIG = ROOT / "configs/electrical_model_v1.json"
VISUAL = {13285, 13707, 13874}
DN = {519624, 523769}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_gz(path: Path) -> dict:
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+"\n", encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def close(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=1e-11, abs_tol=1e-9)


def grouped_spikes(trial: dict, kc_ids: set[int], *, pre: bool = False) -> dict:
    key = "pre_spikes_time_us_source_id" if pre else "post_spikes_time_us_source_id"
    out = {"visual": [], "KC": [], "MBON32": [], "DNa03": [], "DNa02": []}
    for t, sid in trial[key]:
        if sid in VISUAL:
            out["visual"].append([t, sid])
        elif sid in kc_ids:
            out["KC"].append([t, sid])
        elif sid == 519131:
            out["MBON32"].append([t, sid])
        elif sid == 519624:
            out["DNa03"].append([t, sid])
        elif sid == 523769:
            out["DNa02"].append([t, sid])
        else:
            raise AssertionError(f"Unexpected B5 spike source {sid}")
    return out


def expected_lesions(circuit) -> dict[str, set[int]]:
    out = {"none": set(), "visual_to_KC": set(), "KC_to_MBON32": set(),
           "MBON32_to_DNs": set()}
    for edge in circuit.connections:
        pre = circuit.cells[edge.pre]
        post = circuit.cells[edge.post]
        if edge.effect_state != "ACTIVE_FAST":
            continue
        if pre.source_id in VISUAL and post.kind == "KC":
            out["visual_to_KC"].add(edge.source_row)
        if pre.kind == "KC" and post.source_id == 519131:
            out["KC_to_MBON32"].add(edge.source_row)
        if pre.source_id == 519131 and post.source_id in DN:
            out["MBON32_to_DNs"].add(edge.source_row)
    require([len(out[k]) for k in ("visual_to_KC", "KC_to_MBON32", "MBON32_to_DNs")] ==
            [76, 105, 2], "Expected functional lesion source rows drifted")
    return out


def audit_trial(trial: dict, protocol: dict, circuit, kc_ids: set[int],
                lesions: dict[str, set[int]], by_row: dict) -> dict:
    t0 = trial["onset_us"]
    t1 = t0 + protocol["post_window_us"]
    pulse_end = t0 + protocol["pulse_duration_us"]
    arm = trial["arm"]
    expected_lesion = protocol["arms"][arm]["functional_disconnection"]
    require(trial["functional_disconnection"] == expected_lesion,
            f"Functional lesion name: {arm}@{t0}")
    require(set(trial["removed_source_rows"]) == lesions[expected_lesion],
            f"Functional lesion exact source rows: {arm}@{t0}")
    require(trial["source_anatomical_pairs_retained"] == 10009,
            f"Anatomical source pairs: {arm}@{t0}")
    require(trial["final_plasticity_enabled"] is False and trial["final_dan_state"] == 0,
            f"Learning/DA exclusion: {arm}@{t0}")
    require(trial["final_scheduled_events"]-trial["final_delivered_events"] ==
            trial["final_queued_events"], f"Queue accounting: {arm}@{t0}")
    stimulus = trial["stimulus"]
    require(stimulus["start_us"] == t0 and stimulus["end_us"] == pulse_end and
            stimulus["evidence"] == "ENGINEERING ASSUMPTION", f"Stimulus interval: {arm}@{t0}")
    if arm in {"A", "B", "C", "D"}:
        ids = VISUAL
        ref = 15.0
        multiplier = protocol["current_policy"]["visual_levels"][trial["level"]]
    elif arm in {"E", "E_off"}:
        ids = kc_ids
        ref = 7.0
        multiplier = protocol["current_policy"]["direct_KC_multiplier"]
    else:
        ids = {519131}
        ref = 15.0
        multiplier = protocol["current_policy"]["direct_MBON32_multiplier"]
    require(set(stimulus["source_ids"]) == ids and
            close(stimulus["amplitude_pa_per_cell"], ref*multiplier),
            f"Exact stimulus target/current: {arm}@{t0}")
    require(not (set(trial) & set(protocol["prohibited"])),
            f"Prohibited task field: {arm}@{t0}")
    trace = trial["trace"]
    require(trial["trace_columns"] == ["time_us", "DNa03_voltage_mv", "DNa02_voltage_mv",
               "DNa03_synaptic_pa", "DNa02_synaptic_pa", "DNa03_boundary_pa",
               "DNa02_boundary_pa", "APL_local_sum", "APL_local_max", "queue_length"],
            f"Trace schema: {arm}@{t0}")
    require(len(trace) == protocol["post_window_us"]//protocol["trace_interval_us"]+1 and
            all(len(row) == 10 and row[0] == t0+i*protocol["trace_interval_us"] and
                all(math.isfinite(value) for value in row) for i, row in enumerate(trace)),
            f"Trace times/finiteness: {arm}@{t0}")
    boundary = DNBoundary(seed=trial["seed"], level="nominal", control="shared")
    for row in trace:
        boundary.advance_to(row[0])
        expected = boundary.currents_pa(22.5, 30.0)
        require(close(row[5], expected[0]) and close(row[6], expected[1]),
                f"Frozen boundary current: {arm}@{row[0]}")
        require(row[7] >= 0 and row[8] >= 0 and row[9] >= 0,
                f"APL/queue state: {arm}@{row[0]}")
    grouped = grouped_spikes(trial, kc_ids)
    pre = grouped_spikes(trial, kc_ids, pre=True)
    require(all(t0 <= t < t1 for t, _ in trial["post_spikes_time_us_source_id"]),
            f"Post spike timing: {arm}@{t0}")
    require(all(t0-protocol["pre_window_us"] <= t < t0
                for t, _ in trial["pre_spikes_time_us_source_id"]),
            f"Pre spike timing: {arm}@{t0}")
    require(all(not pre[k] for k in ("visual", "KC", "MBON32")),
            f"Unexpected baseline route activity: {arm}@{t0}")
    all_spike_set = {(t, sid) for t, sid in (trial["pre_spikes_time_us_source_id"]+
                                           trial["post_spikes_time_us_source_id"])}
    for at, pre_id, post_id, source_row, kind, amplitude in trial[
            "delivered_events_time_us_pre_post_source_row_kind_amplitude"]:
        require(t0 <= at < t1 and (at-1000, pre_id) in all_spike_set,
                f"Delivered event lacks timed presynaptic spike: {arm}@{at}")
        edge = by_row[source_row]
        source_post_id = circuit.cells[edge.post].source_id
        delivered_target_valid = (post_id == pre_id and source_post_id == 10540
                                  if kind == "APL_INPUT" else post_id == source_post_id)
        require(circuit.cells[edge.pre].source_id == pre_id and delivered_target_valid and
                source_row not in lesions[expected_lesion],
                f"Delivered source row/lesion: {arm}@{at}")
        if kind == "FAST":
            require(edge.effect_state == "ACTIVE_FAST" and close(amplitude, edge.weight_pa),
                    f"Fast amplitude: {arm}@{at}")
        elif kind == "APL_INPUT":
            require(edge.effect_state == "GRADED_INPUT" and close(amplitude, edge.contacts*.002),
                    f"APL event amplitude: {arm}@{at}")
        else:
            raise AssertionError(f"Unapproved queued effect {kind}")
    return {"visual_spikes": len(grouped["visual"]),
            "KC_spikes": len(grouped["KC"]),
            "KC_recruited": len({sid for _, sid in grouped["KC"]}),
            "KC_fraction": len({sid for _, sid in grouped["KC"]})/107,
            "MBON32_spikes": len(grouped["MBON32"]),
            "APL_local_peak": max(row[8] for row in trace),
            "DNa03_pre_spikes": len(pre["DNa03"]),
            "DNa03_post_spikes": len(grouped["DNa03"]),
            "DNa02_pre_spikes": len(pre["DNa02"]),
            "DNa02_post_spikes": len(grouped["DNa02"]),
            "delivered_events": len(trial["delivered_events_time_us_pre_post_source_row_kind_amplitude"])}


def first_inhibitory_difference(active: list[int], disconnected: list[int],
                                first_arrival: int) -> tuple[bool, bool]:
    before_a = [t for t in active if t < first_arrival]
    before_b = [t for t in disconnected if t < first_arrival]
    if before_a != before_b:
        return False, False
    after_a = [t for t in active if t >= first_arrival]
    after_b = [t for t in disconnected if t >= first_arrival]
    if after_a == after_b:
        return True, False
    for a, b in zip(after_a, after_b):
        if a != b:
            return True, a-b >= 500
    return True, len(after_a) < len(after_b)


def pair_dn_effect(full: dict, disconnected: dict, kc_ids: set[int]) -> dict:
    f = grouped_spikes(full, kc_ids)
    d = grouped_spikes(disconnected, kc_ids)
    mb = f["MBON32"]
    if not mb:
        return {"MBON32_spikes": 0, "timing_clean": f["DNa03"] == d["DNa03"] and
                f["DNa02"] == d["DNa02"], "inhibitory": {"DNa03": False, "DNa02": False},
                "post_count_difference": {name: len(f[name])-len(d[name]) for name in ("DNa03", "DNa02")}}
    first_arrival = mb[0][0]+1000
    outcome = {}
    timing = []
    for name in ("DNa03", "DNa02"):
        clean, inhibition = first_inhibitory_difference(
            [t for t, _ in f[name]], [t for t, _ in d[name]], first_arrival)
        timing.append(clean)
        outcome[name] = inhibition
    return {"MBON32_spikes": len(mb), "first_MBON_arrival_us": first_arrival,
            "timing_clean": all(timing), "inhibitory": outcome,
            "post_count_difference": {name: len(f[name])-len(d[name]) for name in outcome}}


def stage_analysis(trials: list[dict], protocol: dict, kc_ids: set[int]) -> dict:
    by_key = {(t["seed"], t["onset_us"], t["arm"], t["level"]): t for t in trials}
    require(len(by_key) == len(trials), "Duplicate trial key")
    seeds = protocol["boundary_seeds"]
    pulse_times = protocol["pulse_onsets_us"]
    levels = protocol["primary_levels"]
    min_pulses = protocol["stage_criteria"]["minimum_responding_pulses_per_seed"]
    min_dn = protocol["stage_criteria"]["minimum_DN_modulated_pulses_per_seed"]
    stage = {}
    pair_data = []
    direct_pair_data = []
    for seed in seeds:
        for level in levels:
            visual_good = kc_good = mbon_good = 0
            dn_effects = {"DNa03": [], "DNa02": []}
            total_dn_diff = {"DNa03": 0, "DNa02": 0}
            for onset in pulse_times:
                a, b, c, d = (by_key[(seed, onset, arm, level)] for arm in ("A", "B", "C", "D"))
                ga, gb, gc, gd = (grouped_spikes(t, kc_ids) for t in (a, b, c, d))
                require(ga["visual"] == gb["visual"] == gc["visual"] == gd["visual"],
                        f"Matched visual response differs by lesion: {seed}/{level}/{onset}")
                require(ga["KC"] == gc["KC"] == gd["KC"],
                        f"KC response differs outside visual lesion: {seed}/{level}/{onset}")
                require(ga["MBON32"] == gd["MBON32"],
                        f"MBON spike response differs under output lesion: {seed}/{level}/{onset}")
                visual = bool(ga["visual"])
                kc = bool(ga["KC"]) and not gb["KC"] and visual and (
                    ga["KC"][0][0] >= ga["visual"][0][0]+1000)
                mbon = bool(ga["MBON32"]) and not gc["MBON32"] and kc and (
                    ga["MBON32"][0][0] >= ga["KC"][0][0]+1000)
                visual_good += visual
                kc_good += kc
                mbon_good += mbon
                dn = pair_dn_effect(a, d, kc_ids)
                require(dn["timing_clean"], f"DN divergence before MBON arrival: {seed}/{level}/{onset}")
                for name in ("DNa03", "DNa02"):
                    dn_effects[name].append(bool(mbon and dn["inhibitory"][name]))
                    total_dn_diff[name] += dn["post_count_difference"][name]
                pair_data.append({"seed": seed, "level": level, "onset_us": onset,
                                  "visual_response": visual, "KC_stage_response": kc,
                                  "MBON_stage_response": mbon,
                                  "KC_spike_difference_A_minus_B": len(ga["KC"])-len(gb["KC"]),
                                  "MBON_spike_difference_A_minus_C":
                                      len(ga["MBON32"])-len(gc["MBON32"]),
                                  "DN_pair": dn})
            dn_pass = {name: sum(values) >= min_dn and total_dn_diff[name] <= 0
                       for name, values in dn_effects.items()}
            stage[f"{seed}_{level}"] = {"visual_responding_pulses": visual_good,
                                        "KC_stage_pulses": kc_good,
                                        "MBON_stage_pulses": mbon_good,
                                        "DN_inhibitory_pulses": {k: sum(v) for k, v in dn_effects.items()},
                                        "DN_post_count_difference": total_dn_diff,
                                        "visual_pass": visual_good >= min_pulses,
                                        "KC_entry_pass": kc_good >= min_pulses,
                                        "KC_to_MBON_pass": mbon_good >= min_pulses,
                                        "MBON_to_DN_pass": any(dn_pass.values())}
    direct = {}
    for seed in seeds:
        e_count = 0
        f_count = {"DNa03": 0, "DNa02": 0}
        f_total = {"DNa03": 0, "DNa02": 0}
        for onset in pulse_times:
            e, e_off, f, f_off = (by_key[(seed, onset, arm, protocol["direct_probe_level"])]
                                  for arm in ("E", "E_off", "F", "F_off"))
            ge, geoff, gf, gfoff = (grouped_spikes(t, kc_ids) for t in (e, e_off, f, f_off))
            require(ge["KC"] == geoff["KC"] and gf["MBON32"] == gfoff["MBON32"],
                    f"Direct probe input differs under output lesion: {seed}/{onset}")
            if ge["KC"] and ge["MBON32"] and not geoff["MBON32"] and (
                    ge["MBON32"][0][0] >= ge["KC"][0][0]+1000):
                e_count += 1
            effect = pair_dn_effect(f, f_off, kc_ids)
            require(effect["timing_clean"], f"Direct MBON DN effect precedes arrival: {seed}/{onset}")
            direct_pair_data.append({"seed": seed, "onset_us": onset,
                                     "KC_spikes_E": len(ge["KC"]),
                                     "MBON_spikes_E": len(ge["MBON32"]),
                                     "MBON_spikes_E_off": len(geoff["MBON32"]),
                                     "MBON_spikes_F": len(gf["MBON32"]),
                                     "DN_pair_F_vs_F_off": effect})
            for name in ("DNa03", "DNa02"):
                f_count[name] += effect["inhibitory"][name]
                f_total[name] += effect["post_count_difference"][name]
        direct[str(seed)] = {"direct_KC_to_MBON_responding_pulses": e_count,
                             "direct_KC_to_MBON_pass": e_count >= min_pulses,
                             "direct_MBON_to_DN_inhibitory_pulses": f_count,
                             "direct_MBON_to_DN_post_count_difference": f_total,
                             "direct_MBON_to_DN_pass": any(f_count[name] >= min_dn and
                                                           f_total[name] <= 0 for name in f_count)}
    nominal = [stage[f"{seed}_nominal"] for seed in seeds]
    overall = {"visual_response": all(x["visual_pass"] for x in nominal),
               "visual_to_KC": all(x["KC_entry_pass"] for x in nominal),
               "KC_to_MBON32": all(x["KC_to_MBON_pass"] for x in nominal),
               "MBON32_to_DN": all(x["MBON_to_DN_pass"] for x in nominal)}
    overall["full_route"] = all(overall.values())
    if not overall["visual_response"]:
        failure = "visual-cell stimulus response"
    elif not overall["visual_to_KC"]:
        failure = "sensory entry: visual→KC"
    elif not overall["KC_to_MBON32"]:
        failure = "feedforward mushroom-body: KC→MBON32"
    elif not overall["MBON32_to_DN"]:
        failure = "descending effect: MBON32→DN"
    else:
        failure = None
    return {"stage_by_seed_level": stage, "direct_probes_by_seed": direct,
            "paired_pulses": pair_data, "direct_paired_pulses": direct_pair_data,
            "nominal_stage_pass": overall,
            "first_failed_stage": failure,
            "criteria": protocol["stage_criteria"]}


def main() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    meta = json.loads((OUT / "meta.json").read_text(encoding="utf-8"))
    result = json.loads((OUT / "result.json").read_text(encoding="utf-8"))
    require(sha(PROTOCOL) == meta["protocol_sha256"] == result["protocol_sha256"],
            "B5 predeclared protocol identity")
    require(sha(MODEL_CONFIG) == protocol["electrical_model_config_sha256"] ==
            meta["model_config_sha256"] == result["model_config_sha256"],
            "Frozen Electrical V1 identity")
    require(result["complete"] and result["trial_count"] == 480 and
            result["replay_checks"] == 48, "Expected three-seed 480-trial panel")
    circuit = build_circuit()
    kc_ids = {c.source_id for c in circuit.cells if c.kind == "KC"}
    require(len(kc_ids) == 107, "KC class identity")
    lesions = expected_lesions(circuit)
    by_row = {e.source_row: e for e in circuit.connections}
    all_trials = []
    audit_rows = []
    for row in result["rows"]:
        path = OUT / row["file"]
        require(path.exists() and sha(path) == row["file_sha256"],
                f"Seed raw file/hash {row['seed']}")
        raw = read_gz(path)
        require(raw["status"] == "complete" and raw["trial_count"] == 160 and
                raw["deterministic_replay_checks"] == 16 and
                raw["protocol_sha256"] == sha(PROTOCOL) and
                raw["model_config_sha256"] == sha(MODEL_CONFIG) and
                raw["code_sha256"] == meta["code_sha256"],
                f"Seed record/provenance/replay {row['seed']}")
        require(all(t["seed"] == row["seed"] for t in raw["trials"]),
                f"Seed trial identity {row['seed']}")
        all_trials.extend(raw["trials"])
    by_checkpoint = defaultdict(list)
    for trial in all_trials:
        by_checkpoint[(trial["seed"], trial["onset_us"])].append(trial)
        audit_rows.append(audit_trial(trial, protocol, circuit, kc_ids, lesions, by_row))
    require(len(by_checkpoint) == 30 and all(len(v) == 16 for v in by_checkpoint.values()),
            "Exactly 16 paired arms per seed/pulse")
    for (seed, onset), group in by_checkpoint.items():
        require(len({t["initial_state_sha256"] for t in group}) == 1 and
                len({t["initial_boundary_sha256"] for t in group}) == 1 and
                len({t["terminal_boundary_sha256"] for t in group}) == 1,
                f"Matched initial neural state/boundary clock {seed}/{onset}")
        for level in protocol["primary_levels"]:
            visual = [t for t in group if t["level"] == level]
            require(len(visual) == 4 and
                    len({json.dumps(t["stimulus"], sort_keys=True) for t in visual}) == 1,
                    f"Matched visual stimulus {seed}/{onset}/{level}")
        for arms in (("E", "E_off"), ("F", "F_off")):
            pair = [t for t in group if t["arm"] in arms]
            require(len(pair) == 2 and pair[0]["stimulus"] == pair[1]["stimulus"],
                    f"Matched direct stimulus {seed}/{onset}/{arms}")
    analysis = stage_analysis(all_trials, protocol, kc_ids)
    rollup = defaultdict(list)
    for trial, measured in zip(all_trials, audit_rows):
        rollup[f"{trial['seed']}_{trial['arm']}_{trial['level']}"].append(measured)
    analysis["activity_by_seed_arm_level"] = {
        key: {"trials": len(items),
              "visual_spikes": sum(x["visual_spikes"] for x in items),
              "KC_spikes": sum(x["KC_spikes"] for x in items),
              "mean_distinct_KCs_per_trial": sum(x["KC_recruited"] for x in items)/len(items),
              "MBON32_spikes": sum(x["MBON32_spikes"] for x in items),
              "maximum_APL_local_state": max(x["APL_local_peak"] for x in items),
              "DNa03_pre_spikes": sum(x["DNa03_pre_spikes"] for x in items),
              "DNa03_post_spikes": sum(x["DNa03_post_spikes"] for x in items),
              "DNa02_pre_spikes": sum(x["DNa02_pre_spikes"] for x in items),
              "DNa02_post_spikes": sum(x["DNa02_post_spikes"] for x in items),
              "delivered_events": sum(x["delivered_events"] for x in items)}
        for key, items in sorted(rollup.items())}
    write_json(OUT / "analysis.json", analysis)
    receipt = {"status": "passed", "seed_files": 3, "trials": len(all_trials),
               "deterministic_replay_checks": result["replay_checks"],
               "matched_checkpoints": len(by_checkpoint),
               "trace_samples_checked": sum(len(t["trace"]) for t in all_trials),
               "spikes_checked": sum(len(t["pre_spikes_time_us_source_id"])+
                                     len(t["post_spikes_time_us_source_id"]) for t in all_trials),
               "delivered_events_checked": sum(x["delivered_events"] for x in audit_rows),
               "lesion_source_row_counts": {k: len(v) for k, v in lesions.items()},
               "raw_sha256": {row["file"]: row["file_sha256"] for row in result["rows"]},
               "analysis_sha256": sha(OUT / "analysis.json"),
               "result_sha256": sha(OUT / "result.json"),
               "limit": "Saved-record audit verifies timing/source rows and boundary samples; it does not measure biological receptor effects or independently re-integrate membrane ODEs."}
    write_json(OUT / "audit.json", receipt)
    print(json.dumps({"audit": "passed", "trials": len(all_trials),
                      "full_route": analysis["nominal_stage_pass"]["full_route"],
                      "first_failed_stage": analysis["first_failed_stage"],
                      "direct_probes": analysis["direct_probes_by_seed"],
                      "events_checked": receipt["delivered_events_checked"]}, indent=2))


if __name__ == "__main__":
    main()
