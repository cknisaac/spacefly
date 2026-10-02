# MaleCNS v1.0 staged scale profile

**Date:** 2026-09-29. **Scope:** non-learning electrical stress test of the validated **MaleCNS v1.0 official traced-only** graph. BANC and all other connectomes are absent. This is not osu play, a task circuit, or a biological validation of fly dynamics.

## Source and extraction

The parent graph is the previously validated 165,122-neuron, 25,563,197-directed-pair MaleCNS v1.0 normalized graph. `protocol.json` records the parent Parquet SHA-256 values, and the profiler now refuses files that differ from `validation_receipt.json`. The selector starts with the lowest-source-ID annotated MBON (body `10013`) and, at each stage, adds outside neurons ranked by total source synapse count crossing the current selected boundary; source ID breaks ties. The 20,000-neuron stage first adds every annotated Kenyon cell, MBON and DAN before expansion. All five induced graphs are nested. This is a strong-edge-biased stress sample, not a representative random sample or a validated mushroom-body functional circuit.

| Stage | Neurons | Internal directed pairs | Internal source synapse count | Incoming cut pairs | Outgoing cut pairs |
| --- | ---: | ---: | ---: | ---: | ---: |
| n100 | 100 | 2,123 | 32,683 | 53,553 | 40,370 |
| n1000 | 1,000 | 151,045 | 705,522 | 254,607 | 239,891 |
| n10000 | 10,000 | 1,981,622 | 11,252,567 | 1,388,780 | 1,235,998 |
| MB-enriched anatomical subset | 20,000 | 4,620,697 | 27,696,616 | 2,311,487 | 1,979,943 |
| Larger network | 50,000 | 11,140,426 | 64,835,589 | 3,246,990 | 1,971,326 |

All five stages required zero disconnected fill neurons. Their manifests also record cut synapse counts, selected-source-ID hashes, parent hashes, and sample-file hashes. `scripts/audit_malecns_scale.py` independently checked all sampled node IDs, exact edge source rows, both endpoints, synapse counts, induced-edge completeness and stage nesting against the parent Parquet tables; all passed. The parent import's full/traced product reconciliation remains in [the dataset report](MALECNS_V1_DATASET_REPORT.md).

## Fixed electrical scenario

The source gives anatomy and contact counts, but not enough physiology for a fly-brain simulation. For this one stress scenario, **every retained edge is assigned a positive effect** of `min(0.02 × sqrt(synapse_count), 0.2)` mV-equivalent units, a 2 ms delay, and the M1 default LIF parameters. All neurons receive 0.8 mV-equivalent constant drive; a seeded 1% receive 1.2 mV. Seed `20260929` selects drivers separately within each stage, so driver source IDs are not nested even though the graph samples are. The integration tick is 1 ms, and plasticity is absent. These numbers and the all-positive sign are **engineering overlays, not MaleCNS measurements**. They were fixed before the run and were not searched for a passing regime.

The declared safety limits were 2,000,000 queued arrivals and 20,000,000 scheduled arrivals per stage. On a limit, the simulator records a complete spike batch at the stopping tick and does not emit a partial batch of outgoing events. The censored stages did **not** complete their requested duration. A limit stop is a failed stability/scale check, not a stable activity measurement.

## Results

`events/s` means delivered synaptic arrivals per wall-clock second. `sim s/s` means simulated time advanced per wall-clock second. Active synapses are distinct extracted edge slots that scheduled at least one arrival, not active biological synaptic contacts. Peak RAM is the process peak working set since process start; it includes the loaded parent graph and extraction buffers, so stages share a cumulative process baseline. VRAM allocated by this CPU-only backend was **0 bytes**; GPU memory usage was not benchmarked.

| Stage | Requested / reached sim time | Outcome | Mean spike rate, Hz/neuron | Silent neurons | Active pairs | Delivered events/s | Sim s/s | Process peak RAM |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 100 | 0.50 / 0.50 s | Complete; driven-only activity | 0.50 | 99.0% | 33 / 2,123 | 12,181 | 7.383 | 1.47 GiB |
| 1,000 | 0.50 / 0.50 s | Complete; recurrent overactivity | 188.94 | 0.3% | 150,951 / 151,045 | 392,944 | 0.01237 | 1.48 GiB |
| 10,000 | 0.25 / 0.075 s | 20M event limit projected | 122.41 at stop | 0.01% | 1,981,617 / 1,981,622 | 240,388 | 0.000939 | 2.07 GiB |
| MB-enriched 20,000 | 0.10 / 0.039 s | 2M queue limit projected | 21.57 at stop | 29.9% | 2,987,622 / 4,620,697 | 222,481 | 0.003113 | 2.55 GiB |
| Larger 50,000 | 0.10 / 0.035 s | 2M queue limit projected | 6.68 at stop | 78.2% | 2,406,748 / 11,140,426 | 179,907 | 0.003687 | 3.35 GiB |

The 100-neuron sample had 25 spikes, all from its one driven neuron; none of the 99 undriven neurons fired. At 1,000, 987 of 990 undriven neurons fired, 110 of 500 ticks had more than 25% of neurons spike together, and 39 neurons averaged over 250 Hz. At 10,000, the first half of the 75 completed ticks contained 1,334 spikes and the second half 90,471; 16 ticks exceeded 25% simultaneous spiking. The 20,000 and 50,000 stages were stopped during the rising transient before the requested 100 ms and cannot establish steady-state spike rates or silence. Their event queues were projected to cross 2 million arrivals at the next spike batch. The final run profiles record actual scheduled/delivered counts, queue peaks, first/second-half counts, driver/undriven activity, and RSS before and after simulation.

**Decision:** This fixed overlay does **not** pass the requested non-silent/non-explosive activity check. The topology import and sparse runtime adapter work at 50,000 neurons, but the chosen electrical model is silent at the smallest sample, overactive at 1,000, and event-limited at larger scales. The result must not be presented as a failure or success of real MaleCNS physiology. The all-positive effects, uniform LIF cells and tonic drives are especially strong unvalidated assumptions; induced samples also remove substantial outside input and output. Stage durations and driver populations differ, so the rows are scale stress points rather than matched physiological comparisons. The Python CPU simulator's tickwise neuron scan and per-arrival heap also make it far slower as activity grows; sparse storage alone does not solve runtime throughput.

## Reproduction and next gate

With the validated MaleCNS files under `data/processed/malecns_v1_traced/`, from the project root:

```powershell
$env:PYTHONPATH = (Resolve-Path 'src').Path
python scripts/profile_malecns_scale.py --reproduce-failed-overlay
python scripts/audit_malecns_scale.py
python -m unittest discover -s tests -q
```

Raw generated manifests, sampled Parquet files, the resolved protocol, per-stage JSON profiles, `run_code_hashes.json`, and `audit.json` are under gitignored `runs/malecns_v1_scale/`. Code-file hashes were captured immediately after the final rerun, with no intervening numerical source edits; no committed code revision was available for these untracked workspace files. The audited run passed **87 automated tests** and all five exact-source sample checks. Runtime throughput is a measurement of this Python CPU reference implementation under this one electrical overlay, not a benchmark of a future compiled or GPU backend.

Before interpreting fly-circuit activity, identify an actual sensory-to-learning-to-motor route and boundary policy; obtain or declare defensible class-specific effects, delays and intrinsic dynamics; then run sensitivity checks with the same safety limits and input definitions. This report does not authorize training or parameter search.
