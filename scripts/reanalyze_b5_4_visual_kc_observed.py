"""B5.5 first step: read-only per-KC reconstruction of saved nominal B5.4."""

from __future__ import annotations

from collections import defaultdict
import gzip
import json
from pathlib import Path
import statistics

from project_b.electrical_v1 import build_circuit
from project_b.electrical_v1.source import file_sha
from run_electrical_v1_feedforward_drive_adequacy import reconstruct, describe


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/figures/electrical_v1_1_visual_boundary_validation"
OUT = ROOT / "docs/figures/b5_5_visual_kc_transfer_decomposition"
CONFIG = ROOT / "configs/electrical_model_v1_1.json"
MANIFEST = ROOT / "data/processed/malecns_v1_electrical_v1_1/manifest.json"
OLD = {13285, 13707, 13874}
VISUAL = OLD | {12740, 13190}
SEEDS = (31001, 31002, 31003)


def save_gzip(path: Path, value: object) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, separators=(",", ":"), allow_nan=False)
        stream.write("\n")


def main() -> None:
    circuit = build_circuit(CONFIG)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert file_sha(CONFIG) == manifest["config_sha256"]
    new = set(manifest["newly_contacted_KC_ids"])
    kc_ids = sorted(c.source_id for c in circuit.cells if c.kind == "KC")
    pairs = defaultdict(set)
    contacts = defaultdict(int)
    source_contacts = defaultdict(dict)
    for edge in circuit.connections:
        pre = circuit.cells[edge.pre].source_id
        post = circuit.cells[edge.post].source_id
        if pre in VISUAL and post in kc_ids:
            pairs[post].add(pre)
            contacts[post] += edge.contacts
            source_contacts[post][str(pre)] = edge.contacts
    old = {sid for sid in kc_ids if pairs[sid] & OLD}
    assert len(new) == 20 and len(old) == 59 and not (new & old)
    assert sum(bool(pairs[sid]) for sid in kc_ids) == 79
    meta = {"stage": "B5.5-observed-before-diagnostic-matrix",
            "v1_1_config_sha256": file_sha(CONFIG), "manifest_sha256": file_sha(MANIFEST),
            "b5_4_audit_sha256": file_sha(SOURCE / "audit.json"),
            "seeds": SEEDS, "new_kc_ids": sorted(new), "old_kc_ids": sorted(old),
            "no_selected_visual_contact_kc_ids": sorted(set(kc_ids) - new - old),
            "source_files_sha256": {str(seed): file_sha(SOURCE / f"seed_{seed}.json.gz")
                                    for seed in SEEDS}}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "observed_meta.json").write_text(json.dumps(meta, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    pooled = defaultdict(list)
    for seed in SEEDS:
        source = json.load(gzip.open(SOURCE / f"seed_{seed}.json.gz", "rt", encoding="utf-8"))
        trials = []
        for trial in source["trials"]:
            if trial["arm"] != "v1_1_connected" or trial["level"] != "nominal":
                continue
            if trial["KC_spiking_count"] != 0 or trial["APL_peak_local_state"] != 0:
                raise AssertionError("Observed KC/APL state no longer passive")
            by_kc = defaultdict(list)
            for e in trial["delivered_events_time_us_pre_post_source_row_kind_amplitude"]:
                if e[4] == "FAST" and e[1] in VISUAL and e[2] in kc_ids:
                    by_kc[e[2]].append(e)
            observed = reconstruct(kc_ids, by_kc, trial["onset_us"], circuit,
                                   "observed", [1.0], 500, 500000)
            saved = {r["source_id"]: r for r in trial["KC"]}
            rows = []
            for sid in kc_ids:
                result = observed[sid]
                old_row = saved[sid]
                if (abs(result["peak_voltage_mv"] - old_row["peak_voltage_mv"]) > 1e-10 or
                        abs(result["peak_fast_current_pa"] - old_row["peak_synaptic_pa"]) > 1e-10 or
                        abs(result["fast_charge_fc"] - old_row["visual_charge_fc"]) > 1e-8 or
                        result["event_count"] != old_row["visual_event_count"] or
                        old_row["spike_times_us"]):
                    raise AssertionError(f"Saved B5.4 KC reconstruction mismatch: {seed}/{sid}")
                result.update({"source_id": sid,
                               "cohort": "new_20" if sid in new else "old_59" if sid in old else "none_28",
                               "source_contacts_by_id": source_contacts[sid],
                               "anatomical_source_count": len(pairs[sid]),
                               "anatomical_contact_count": contacts[sid],
                               "event_timestamps_us": [int(e[0]) for e in by_kc[sid]],
                               "events_time_pre_source_row_amplitude":
                               [[int(e[0]), int(e[1]), int(e[3]), float(e[5])] for e in by_kc[sid]],
                               "apl_local_peak": old_row["peak_apl_local"],
                               "observed_refractory_time_us": 0})
                pooled[result["cohort"]].append(result)
                rows.append(result)
            trials.append({"seed": seed, "onset_us": trial["onset_us"],
                           "initial_shared_state_sha256": trial["initial_shared_state_sha256"],
                           "initial_boundary_sha256": trial["initial_boundary_sha256"],
                           "kc": rows})
        if len(trials) != 10:
            raise AssertionError("Missing nominal B5.4 connected trials")
        save_gzip(OUT / f"observed_seed_{seed}.json.gz", {"seed": seed, "trials": trials})
    summary = {cohort: {field: describe([r[field] for r in rows if r[field] is not None])
                        for field in ("anatomical_contact_count", "anatomical_source_count",
                                      "event_count", "arrival_span_us", "best_5ms_impulse_fraction",
                                      "peak_fast_current_pa", "fast_charge_fc", "peak_voltage_mv",
                                      "minimum_threshold_distance_mv", "fast_charge_fc_to_closest",
                                      "leak_charge_fc_to_closest")}
               for cohort, rows in pooled.items()}
    (OUT / "observed_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True)+"\n",
                                                encoding="utf-8")
    print(json.dumps({"observed_trials": 30, "kc_rows": sum(len(x) for x in pooled.values()),
                      "cohort_rows": {k: len(v) for k, v in pooled.items()},
                      "new_min_gap_mv": summary["new_20"]["minimum_threshold_distance_mv"]["min"],
                      "old_min_gap_mv": summary["old_59"]["minimum_threshold_distance_mv"]["min"]},
                     sort_keys=True))


if __name__ == "__main__":
    main()
