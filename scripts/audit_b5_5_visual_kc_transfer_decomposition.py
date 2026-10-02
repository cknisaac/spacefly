"""Independent B5.5 provenance, conservation, and scalar first-spike audit."""

from __future__ import annotations

from collections import Counter, defaultdict
import gzip
import json
import math
from pathlib import Path
import statistics

from project_b.electrical_v1 import build_circuit
from project_b.electrical_v1.source import file_sha


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/figures/b5_5_visual_kc_transfer_decomposition"
B54 = ROOT / "docs/figures/electrical_v1_1_visual_boundary_validation"
PROTOCOL = ROOT / "configs/b5_5_visual_kc_transfer_decomposition.json"
CONFIG = ROOT / "configs/electrical_model_v1_1.json"


def read(path: Path) -> dict:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            return json.load(stream)
    return json.loads(path.read_text(encoding="utf-8"))


def need(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def independently_remap(events: list[list], family: str) -> list[list]:
    if family == "observed" or not events:
        return events
    center = (min(e[0] for e in events) + max(e[0] for e in events)) / 2
    factor = None if family == "synchronous" else int(family.split("_")[1])
    return [[int(round((center if factor is None else center + (e[0]-center)/factor)/500)*500),
             e[1], e[2], e[3]] for e in events]


def scalar_series(events: list[list], onset: int, cap: float, leak: float,
                  rest: float) -> list[float]:
    dt = 0.5
    a = math.exp(-dt * leak / cap)
    d = math.exp(-dt / 5)
    difference = leak/cap - 1/5
    factor = dt*a/cap if abs(difference) < 1e-12 else (d-a)/(cap*difference)
    impulses = defaultdict(float)
    for t, _, _, amp in events:
        impulses[(t-onset)//500] += amp
    voltage = rest
    syn = 0.0
    trace = []
    for step in range(1000):
        if step:
            voltage = rest + (voltage-rest)*a + syn*factor
            syn *= d
        trace.append(voltage)
        syn += impulses[step]
    return trace


def scalar_result(trace: list[float], onset: int, rest: float,
                  threshold: float, multiplier: int) -> tuple[int | None, float, float]:
    peak = rest
    first = None
    for step, base in enumerate(trace):
        value = rest + multiplier*(base-rest)
        peak = max(peak, value)
        if value >= threshold - 1e-12:
            first = onset + step*500
            break
    return first, peak, max(0.0, threshold-peak)


def distribution(values: list[float]) -> dict:
    ordered = sorted(values)
    return {"n": len(ordered), "min": ordered[0] if ordered else None,
            "p25": statistics.quantiles(ordered, n=4, method="inclusive")[0] if len(ordered)>1 else
            (ordered[0] if ordered else None),
            "median": statistics.median(ordered) if ordered else None,
            "p75": statistics.quantiles(ordered, n=4, method="inclusive")[2] if len(ordered)>1 else
            (ordered[0] if ordered else None),
            "max": ordered[-1] if ordered else None}


def main() -> None:
    protocol = read(PROTOCOL)
    result = read(OUT / "result.json")
    meta = read(OUT / "observed_meta.json")
    manifest = read(ROOT / "data/processed/malecns_v1_electrical_v1_1/manifest.json")
    b54_audit = read(B54 / "audit.json")
    need(result["protocol_sha256"] == file_sha(PROTOCOL) and
         file_sha(CONFIG) == protocol["v1_1_config_sha256"] and
         file_sha(ROOT / "configs/electrical_model_v1.json") == protocol["v1_config_sha256"] and
         file_sha(ROOT / "configs/electrical_v1_1_visual_boundary_validation.json") ==
         protocol["b5_4_protocol_sha256"], "Locked config/protocol drift")
    need(b54_audit["status"] == "pass" and b54_audit["stage_result"] == "FAIL" and
         file_sha(B54 / "audit.json") == meta["b5_4_audit_sha256"],
         "B5.4 receipt drift")
    for name, sha in protocol["observed_before_probe_sha256"].items():
        need(file_sha(OUT/name) == sha, f"Observed pre-matrix evidence drift: {name}")
    circuit = build_circuit(CONFIG)
    need(circuit.parent_hashes == result["source_parent_hashes"] and
         file_sha(ROOT / "data/processed/malecns_v1_electrical_v1_1/manifest.json") ==
         meta["manifest_sha256"], "Parent provenance drift")
    ids = {c.source_id for c in circuit.cells if c.kind == "KC"}
    new = set(meta["new_kc_ids"])
    old = set(meta["old_kc_ids"])
    none = set(meta["no_selected_visual_contact_kc_ids"])
    need((len(new),len(old),len(none)) == (20,59,28) and
         new.isdisjoint(old) and new|old|none == ids and
         new == set(manifest["newly_contacted_KC_ids"]), "KC cohorts drifted")
    ladder = protocol["families"]["amplitude"]["multipliers"]
    compression = protocol["families"]["compression"]["factors"]
    families = ("observed", *(f"compression_{f}" for f in compression), "synchronous")
    counts_by_trial = []
    all_contact_critical = defaultdict(list)
    first_ladder_hist = defaultdict(Counter)
    first_compression_hist = defaultdict(Counter)
    scalar_cells = 0
    row_count = 0
    event_terms = 0
    for seed in protocol["seeds"]:
        diagnostic_path = OUT / f"diagnostic_seed_{seed}.json.gz"
        need(file_sha(diagnostic_path) == result["diagnostic_file_sha256"][str(seed)],
             "Diagnostic raw data hash mismatch")
        diagnostic = read(diagnostic_path)
        observed = read(OUT / f"observed_seed_{seed}.json.gz")
        source = read(B54 / f"seed_{seed}.json.gz")
        need(file_sha(B54 / f"seed_{seed}.json.gz") == meta["source_files_sha256"][str(seed)] and
             len(diagnostic["trials"]) == len(observed["trials"]) == 10 and
             diagnostic["protocol_sha256"] == result["protocol_sha256"],
             "Trial source/protocol mismatch")
        b54 = {(r["onset_us"],r["level"],r["arm"]): r for r in source["trials"]}
        for dt, ot in zip(diagnostic["trials"], observed["trials"]):
            onset = dt["onset_us"]
            need(onset == ot["onset_us"] and dt["neutral_state_sha256"] ==
                 ot["initial_shared_state_sha256"] == b54[(onset,"nominal","v1_1_connected")][
                     "initial_shared_state_sha256"], "Matched checkpoint mismatch")
            by_id = {r["source_id"]: r for r in ot["kc"]}
            rows = dt["kc"]
            need(len(rows) == 107 and {r["source_id"] for r in rows} == ids,
                 "KC row count/IDs mismatch")
            counts = {family: {cohort: 0 for cohort in ("new_20","old_59","none_28")}
                      for family in families}
            amplitude_counts = {m: {cohort: 0 for cohort in ("new_20","old_59","none_28")}
                                for m in ladder}
            for row in rows:
                sid = row["source_id"]
                observed_row = by_id[sid]
                cohort = "new_20" if sid in new else "old_59" if sid in old else "none_28"
                need(row["cohort"] == observed_row["cohort"] == cohort and
                     row["source_events"] == observed_row["event_count"], "Cohort/source count mismatch")
                original_events = observed_row["events_time_pre_source_row_amplitude"]
                need(row["families"]["observed"]["events_time_pre_source_row_amplitude"] ==
                     original_events and abs(row["infinite_horizon_charge_fc"]-
                     5*sum(e[3] for e in original_events)) < 1e-10,
                     "Observed event/charge mismatch")
                observed_peak = row["families"]["observed"]["multipliers"]["1"]
                need(observed_peak["first_spike_time_us"] is None and
                     abs(observed_peak["peak_voltage_before_first_spike_or_window_end_mv"]-
                         observed_row["peak_voltage_mv"]) < 1e-10,
                     "Observed B5.4 voltage/spiking drift")
                for family in families:
                    data = row["families"][family]
                    events = data["events_time_pre_source_row_amplitude"]
                    need(events == independently_remap(original_events, family) and
                         len(events) == len(original_events) and
                         abs(sum(e[3] for e in events)-sum(e[3] for e in original_events)) < 1e-10,
                         "Counterfactual event remap/charge mismatch")
                    event_terms += len(events)
                    for mstr, item in data["multipliers"].items():
                        m = int(mstr)
                        need(m in (ladder if family == "observed" else [1]) and
                             (item["first_spike_time_us"] is None or
                              onset <= item["first_spike_time_us"] < onset+500000) and
                             abs(item["minimum_threshold_gap_mv_clamped"]-
                                 max(0,item["signed_threshold_gap_at_peak_mv"])) < 1e-10,
                             "Spike/gap record invalid")
                    if data["multipliers"]["1"]["first_spike_time_us"] is not None:
                        counts[family][cohort] += 1
                    if (onset in (11000000,29000000) and seed in (31001,31003)):
                        # Fresh scalar recurrence, independent of runner's vectorized matrix.
                        cap = circuit.config["spiking_classes"]["KC"]["capacitance_pf"]["value"]
                        leak = circuit.config["spiking_classes"]["KC"]["leak_ns"]["value"]
                        rest = circuit.config["spiking_classes"]["KC"]["rest_mv"]["value"]
                        threshold = circuit.config["spiking_classes"]["KC"]["onset_mv"]["value"]
                        trace = scalar_series(events,onset,cap,leak,rest)
                        for mstr,item in data["multipliers"].items():
                            first,peak,gap = scalar_result(trace,onset,rest,threshold,int(mstr))
                            need(first == item["first_spike_time_us"] and
                                 abs(peak-item["peak_voltage_before_first_spike_or_window_end_mv"]) < 1e-9 and
                                 abs(gap-item["minimum_threshold_gap_mv_clamped"]) < 1e-9,
                                 f"Independent scalar first-spike mismatch {seed}/{onset}/{sid}/{family}/{mstr}")
                        scalar_cells += 1
                if cohort != "none_28":
                    critical = row["continuous_passive_critical_amplitude_multiplier"]
                    need(critical > 1, "Unexpected nominal spike threshold")
                    all_contact_critical[cohort].append(critical)
                    first_ladder_hist[cohort][str(row["minimum_tested_amplitude_multiplier_for_first_spike"])] += 1
                    first_compression_hist[cohort][str(row["minimum_finite_compression_for_first_spike"])] += 1
                first_panel = next((m for m in ladder if row["families"]["observed"][
                    "multipliers"][str(m)]["first_spike_time_us"] is not None),None)
                first_comp = next((f for f in compression if row["families"][f"compression_{f}"][
                    "multipliers"]["1"]["first_spike_time_us"] is not None),None)
                need(row["minimum_tested_amplitude_multiplier_for_first_spike"] == first_panel and
                     row["minimum_finite_compression_for_first_spike"] == first_comp and
                     row["synchronous_upper_bound_spikes"] ==
                     (row["families"]["synchronous"]["multipliers"]["1"]["first_spike_time_us"] is not None),
                     "First-spike summary mismatch")
                for m in ladder:
                    if row["families"]["observed"]["multipliers"][str(m)]["first_spike_time_us"] is not None:
                        amplitude_counts[m][cohort] += 1
                row_count += 1
            counts_by_trial.append({"seed":seed,"onset_us":onset,
                                    "spiking_by_family_and_cohort":counts,
                                    "spiking_by_amplitude_and_cohort":amplitude_counts})
    need(row_count == 3210 and len(counts_by_trial) == 30,
         "Panel incomplete")
    # The fixed neutral sensory feedforward stream is deterministic across checkpoints.
    signatures = {json.dumps({"families":r["spiking_by_family_and_cohort"],
                              "amplitude":r["spiking_by_amplitude_and_cohort"]},sort_keys=True)
                  for r in counts_by_trial}
    need(len(signatures) == 1, "Response varies across fixed nominal checkpoints")
    representative = counts_by_trial[0]
    amp = representative["spiking_by_amplitude_and_cohort"]
    family = representative["spiking_by_family_and_cohort"]
    contacted = lambda row: row["new_20"]+row["old_59"]
    finite_peak = max(contacted(family[f"compression_{f}"]) for f in compression)
    synchronous_count = contacted(family["synchronous"])
    combined_critical = all_contact_critical["new_20"]+all_contact_critical["old_59"]
    median_critical = statistics.median(combined_critical)
    rules = protocol["classification_predeclared"]
    if (finite_peak < rules["material_fixed_charge_rescue_count_of_79"] and
            synchronous_count < rules["majority_count_of_79"] and
            median_critical >= rules["gross_observed_median_critical_multiplier"] and
            contacted(amp[512]) > 0):
        classification = "AMPLITUDE-LIMITED / GROSSLY UNDERPOWERED IN THE FROZEN SURROGATE"
    elif finite_peak >= rules["majority_count_of_79"]:
        classification = "TEMPORAL-INTEGRATION-LIMITED"
    elif finite_peak >= rules["material_fixed_charge_rescue_count_of_79"]:
        # Timing may matter, but a claim of MIXED additionally needs a >=2x
        # median critical-multiplier reduction, checked from saved traces.
        classification = "UNRESOLVED (timing rescue below majority; mixed criterion requires critical-scale audit)"
    else:
        classification = "UNRESOLVED"
    audit = {"status":"pass", "stage":"B5.5", "classification":classification,
             "protocol_sha256":file_sha(PROTOCOL), "trials_checked":len(counts_by_trial),
             "kc_rows_checked":row_count,"event_terms_checked":event_terms,
             "independent_scalar_cell_families_checked":scalar_cells,
             "fixed_nominal_checkpoint_signature_count":len(signatures),
             "representative_spiking_by_amplitude_and_cohort":amp,
             "representative_spiking_by_family_and_cohort":family,
             "first_tested_amplitude_histogram_by_cohort":{k:dict(v) for k,v in first_ladder_hist.items()},
             "first_finite_compression_histogram_by_cohort":{k:dict(v) for k,v in first_compression_hist.items()},
             "critical_amplitude_distribution_by_cohort":{
                 k:distribution(v) for k,v in all_contact_critical.items()},
             "critical_amplitude_distribution_contacted_79":distribution(combined_critical),
             "finite_compression_max_contacted_spiking":finite_peak,
             "synchronous_contacted_spiking":synchronous_count,
             "all_checkpoint_counts":counts_by_trial}
    (OUT/"audit.json").write_text(json.dumps(audit,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({k:audit[k] for k in ("status","classification","trials_checked",
                                        "kc_rows_checked","independent_scalar_cell_families_checked",
                                        "finite_compression_max_contacted_spiking",
                                        "synchronous_contacted_spiking")},sort_keys=True))


if __name__ == "__main__":
    main()
