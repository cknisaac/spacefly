"""Independent saved-record audit of Electrical V1 neutral gate results.

Recomputes boundary samples, spike/rate/silence/refractory metrics and the
only active neutral synaptic drive from raw event ledgers. It does not rerun or
retune the neural model.
"""

from __future__ import annotations

from collections import Counter
import gzip
import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/figures/electrical_v1_neutral_gate"
PROTOCOL = ROOT / "configs/electrical_v1_neutral_gate.json"
CONFIG = ROOT / "configs/electrical_model_v1.json"
DN_IDS = (519624, 523769)
REF_PA = (22.5, 30.0)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_gz(path: Path) -> dict:
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def close(a: float, b: float, tol: float = 1e-9) -> bool:
    return math.isclose(a, b, rel_tol=tol, abs_tol=tol)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def expected_ids(protocol: dict) -> list[str]:
    return [f"{c['name']}_{level}_{seed}" for c in protocol["conditions"]
            for level in c["levels"] for seed in protocol["seeds"]]


def refractory_us(spikes: list[int], start: int, end: int, second: bool = False):
    bins = [0] * ((end-start)//1_000_000)
    for t in spikes:
        lo, hi = max(t, start), min(t+2500, end)
        if hi <= lo:
            continue
        for i in range((lo-start)//1_000_000, (hi-start-1)//1_000_000 + 1):
            bin_start = start + i*1_000_000
            bins[i] += max(0, min(hi, bin_start+1_000_000)-max(lo, bin_start))
    return bins if second else sum(bins)


def audit_run(row: dict, protocol: dict, protocol_hash: str, ledger: dict,
              trace_columns: list[str]) -> dict:
    path = OUT / row["file"]
    require(path.exists() and sha(path) == row["file_sha256"], f"raw file/hash: {row['run_id']}")
    raw = read_gz(path)
    run_id = row["run_id"]
    require(raw["run_id"] == run_id and raw["status"] == "complete", f"run identity/status: {run_id}")
    require(raw["protocol_sha256"] == protocol_hash and raw["model_config_sha256"] == sha(CONFIG),
            f"frozen config/protocol: {run_id}")
    require(raw["trace_columns"] == trace_columns, f"trace schema: {run_id}")
    m = raw["metrics"]
    require(m == row["metrics"], f"indexed metrics differ: {run_id}")
    spec = raw["spec"]
    level_scale = {"low": .5, "nominal": 1, "high": 1.5}[spec["level"]]
    start = protocol["settling_us"]
    end = start + protocol["observation_us"]
    require(raw["final_summary"]["time_us"] == end and raw["final_summary"]["plasticity_enabled"] is False,
            f"time/learning: {run_id}")
    require(raw["final_summary"]["dan_state"] == 0 and
            raw["final_summary"]["apl_spikes"] == raw["final_summary"]["ppl103_spikes"] == 0,
            f"DAN/APL neutral state: {run_id}")
    trace = raw["trace"]
    require(len(trace) == end//protocol["trace_interval_us"]+1, f"trace length: {run_id}")
    require(all(len(t) == len(trace_columns) and t[0] == i*protocol["trace_interval_us"]
                for i, t in enumerate(trace)), f"trace clock: {run_id}")
    spikes = [(int(t), int(sid)) for t, sid in raw["all_spikes_time_us_source_id"]]
    require(all(0 < t <= end and sid in DN_IDS for t, sid in spikes), f"unexpected neutral spikes: {run_id}")
    require(spikes == sorted(spikes), f"spike order: {run_id}")
    obs = {sid: [t for t, neuron in spikes if neuron == sid and start < t <= end]
           for sid in DN_IDS}
    for sid in DN_IDS:
        d = m["dn"][str(sid)]
        times = obs[sid]
        require(len(times) == d["observation_spikes"] and
                close(len(times)/60, d["rate_hz"]), f"spike rate: {run_id}:{sid}")
        gaps = [b-a for a, b in zip([start, *times], [*times, end])]
        require(max(gaps) == d["max_silent_gap_us"], f"silent gap: {run_id}:{sid}")
        bins = refractory_us([t for t, neuron in spikes if neuron == sid], start, end, True)
        require(bins == d["refractory_bins_us"] and sum(bins) == d["refractory_time_us"],
                f"refractory bins/time: {run_id}:{sid}")
        require(close(sum(bins)/60_000_000, d["refractory_occupancy"]) and
                close(max(bins)/1_000_000, d["max_full_second_occupancy"]),
                f"refractory fractions: {run_id}:{sid}")
        counts = [0]*60
        for t in times:
            counts[(t-start-1)//1_000_000] += 1
        require(counts == d["spike_counts_by_observation_second"], f"spike bins: {run_id}:{sid}")
        if spec["condition"] in {"A", "C"} and spec["level"] == "nominal":
            require(len(times) >= 60 and max(gaps) <= 30_000_000, f"nominal activity: {run_id}:{sid}")
        require(d["rate_hz"] <= 100 and d["refractory_occupancy"] <= .25 and
                max(bins) <= 500_000, f"DN saturation: {run_id}:{sid}")
    require(raw["final_summary"]["spikes_by_class"].get("KC", -1) == 0 and
            raw["final_summary"]["spikes_by_class"].get("MBON32", -1) == 0 and
            raw["final_summary"]["spikes_by_class"].get("sensory", -1) == 0,
            f"silent neutral route: {run_id}")
    require(m["max_outer_voltage_fraction_all_cells"] == 0 and not m["outer_voltage_violators"]
            and not m["extreme_voltage_violators"], f"voltage counter: {run_id}")
    require(all(m["checks"].values()) and m["base_gate_pass"], f"declared gate checks: {run_id}")
    require(raw["final_summary"]["scheduled_events"] - raw["final_summary"]["delivered_events"] ==
            raw["final_summary"]["queued_events"], f"event accounting: {run_id}")

    # Independent boundary reconstruction from the saved autonomous sign ledger.
    events = ledger["events"]
    require(events[0][0] == 0 and events[-1][0] <= end, f"boundary event times: {run_id}")
    require(m["boundary_checkpoint_sha256"] == ledger["checkpoint_sha256"],
            f"boundary checkpoint pairing: {run_id}")
    event_index = 0
    arrivals = sorted((t+1000, 10.2) for t, sid in spikes if sid == 519624 and t+1000 <= end)
    arrival_index = 0
    syn_current = 0.0
    syn_time = 0
    max_syn_error = 0.0
    for sample in trace:
        t = sample[0]
        while event_index+1 < len(events) and events[event_index+1][0] <= t:
            event_index += 1
        signs = events[event_index][1:]
        if spec["condition"] == "B":
            expected3 = expected2 = 0.0
        else:
            c3, c2 = (signs[3], signs[4]) if spec["condition"] == "D" else (signs[0], signs[0])
            expected3 = REF_PA[0]*level_scale*(1+.2*c3+.2*signs[1])
            expected2 = REF_PA[1]*level_scale*(1+.2*c2+.2*signs[2])
        require(close(sample[5], expected3) and close(sample[6], expected2),
                f"boundary current: {run_id}@{t}")
        require(close(sample[3], 0), f"unexplained DNa03 synaptic current: {run_id}@{t}")
        while arrival_index < len(arrivals) and arrivals[arrival_index][0] <= t:
            at, amp = arrivals[arrival_index]
            syn_current *= math.exp(-(at-syn_time)/5000)
            syn_current += amp
            syn_time = at
            arrival_index += 1
        predicted = syn_current * math.exp(-(t-syn_time)/5000)
        max_syn_error = max(max_syn_error, abs(sample[4]-predicted))
        require(close(sample[4], predicted, 1e-8), f"DNa02 synaptic current: {run_id}@{t}")
        require(sample[11] <= raw["final_summary"]["peak_queued_events"],
                f"queue sample: {run_id}@{t}")
        require(sample[12] == 0 and sample[13] == 0 and sample[14] == 0,
                f"neutral DAN/APL sample: {run_id}@{t}")
        require(all(math.isfinite(v) for v in sample), f"nonfinite trace: {run_id}@{t}")
    return {"run_id": run_id, "spikes": len(spikes), "trace_samples": len(trace),
            "boundary_events": len(events)-1, "max_synaptic_reconstruction_error_pa": max_syn_error,
            "A_C_route_silent": True}


def main() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    result = json.loads((OUT / "result.json").read_text(encoding="utf-8"))
    meta = json.loads((OUT / "meta.json").read_text(encoding="utf-8"))
    require(result["protocol_sha256"] == meta["protocol_sha256"] == sha(PROTOCOL), "protocol identity")
    require(result["model_config_sha256"] == meta["model_config_sha256"] == sha(CONFIG), "model identity")
    expected_primary = expected_ids(protocol)
    expected_fine = [f"R_A_nominal_{seed}_tick250" for seed in protocol["numerical_refinement"]["seeds"]]
    require([r["run_id"] for r in result["runs"]] == expected_primary + expected_fine,
            "exact 24+3 schedule and ordering")
    ledgers = {seed: read_gz(OUT / f"boundary_{seed}.json.gz") for seed in protocol["seeds"]}
    audited = []
    for row in result["runs"]:
        spec = read_gz(OUT / row["file"])["spec"]
        audited.append(audit_run(row, protocol, sha(PROTOCOL), ledgers[spec["seed"]],
                                 meta["trace_columns"]))
    raw = {row["run_id"]: read_gz(OUT / row["file"]) for row in result["runs"]}
    for seed in protocol["seeds"]:
        for level in ("low", "nominal", "high"):
            a, c = raw[f"A_{level}_{seed}"], raw[f"C_{level}_{seed}"]
            require(a["all_spikes_time_us_source_id"] == c["all_spikes_time_us_source_id"],
                    f"neutral A/C spike identity: {seed}/{level}")
    numerical = {}
    r = protocol["numerical_refinement"]
    for seed in r["seeds"]:
        coarse = raw[f"A_nominal_{seed}"]["metrics"]
        fine = raw[f"R_A_nominal_{seed}_tick250"]["metrics"]
        max_diff = 0
        checks = []
        for sid in ("519624", "523769"):
            a, b = coarse["dn"][sid], fine["dn"][sid]
            absolute = abs(a["rate_hz"]-b["rate_hz"])
            relative = absolute/max(a["rate_hz"], b["rate_hz"], 1)
            second = max(abs(x-y) for x, y in zip(a["spike_counts_by_observation_second"],
                                                   b["spike_counts_by_observation_second"]))
            max_diff = max(max_diff, second)
            checks.append(absolute <= r["maximum_observation_rate_absolute_difference_hz"] and
                          relative <= r["maximum_observation_rate_relative_difference"] and
                          second <= r["maximum_per_second_dn_spike_count_difference"])
        checks.append(abs(coarse["max_outer_voltage_fraction_all_cells"]-
                          fine["max_outer_voltage_fraction_all_cells"]) <=
                      r["maximum_observation_outer_fraction_difference"])
        checks.append(coarse["boundary_checkpoint_sha256"] == fine["boundary_checkpoint_sha256"])
        numerical[str(seed)] = {"pass": all(checks), "max_second_spike_count_difference": max_diff}
        require(all(checks) == result["numerical_refinement"][str(seed)]["pass"],
                f"numerical refinement summary: {seed}")
    require(all(n["pass"] for n in numerical.values()), "numerical convergence")
    require(result["primary_conditions_complete"] == 24 and result["neutral_operating_state_gate_pass"],
            "final declared gate result")
    receipt = {"status": "passed", "primary_runs": 24, "numerical_refinements": 3,
               "trace_samples_checked": sum(a["trace_samples"] for a in audited),
               "raw_spikes_checked": sum(a["spikes"] for a in audited),
               "maximum_synaptic_reconstruction_error_pa": max(
                   a["max_synaptic_reconstruction_error_pa"] for a in audited),
               "A_C_spike_identity_pairs": 9, "numerical": numerical,
               "raw_files_sha256": {row["file"]: row["file_sha256"] for row in result["runs"]},
               "result_sha256": sha(OUT / "result.json"),
               "limit": "Recomputes saved traces/events; per-cell 500-us voltage counters are internal runtime counters, not independently re-integrated."}
    (OUT / "audit.json").write_text(json.dumps(receipt, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in receipt.items() if k != "raw_files_sha256"}, indent=2))


if __name__ == "__main__":
    main()
