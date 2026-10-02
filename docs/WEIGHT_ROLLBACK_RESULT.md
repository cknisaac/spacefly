# Synthetic late-state weight-rollback diagnostic

**2026-09-30. Complete, descriptive five-seed experiment.** The [predeclared protocol](../configs/weight_rollback_diagnostic.json) fixed seeds **2000–2004**, the same networks and configuration, the 384-outcome state, donor weights after 384/96/24 outcomes, and two 32-note frozen panels. No learning-rate, reward, topology, motor, map, or model parameter was selected from these probes. This is a synthetic fixture, not a fly-circuit result or an M2 reliability pass.

## Intervention and verification

For each seed, deterministic replay reconstructed the complete same-network state after 384 outcomes and checked every training event against the [longitudinal ledger](figures/long_continuation/runs.jsonl). Three clones then received (1) their actual 384-outcome weights, (2) their own 96-outcome weights, or (3) their own 24-outcome weights. Only the **480 selected plastic effective weights** could differ. The runner restored those slots after each transplant and required the entire serialized late checkpoint to match byte-for-byte; this checks that neuron state, queued arrivals, eligibility, predictor, RNG, topology, motor/readout and all other state were untouched by transplant. Queued arrivals retain their already captured late weights, as required by this fixed-late-state design.

Every clone was probed with plasticity and exploration disabled on both the original common panel and fixed continuation notes **385–416**. All **30 branches / 960 note outcomes** had zero exploration pulses and zero weight changes. The unchanged 384-weight common probe matched the saved longitudinal probe **event, timing, DOWN action and metric records exactly in all five seeds**. Its continuation probe also matched the prior exploration/map diagnostic's frozen 384-off branch exactly in all five seeds. The independent [audit receipt](figures/weight_rollback_diagnostic/audit.json) checked row uniqueness, protocol/source hashes, all per-event utilities, timing-error and DOWN-action counts, donor sums/bounds, both reference matches, and the aggregate result. Every note's utility and signed timing error and every DOWN time/disposition are in the [raw ledger](figures/weight_rollback_diagnostic/runs.jsonl).

## Per-seed results

Each triplet is **384 / 96 / 24 donor-weight checkpoint**. GOOD+ is the percentage of 32 frozen notes judged GOOD or better; utility is the mean raw game utility. These are paired **within seed and map**, not independent network replicates.

| Seed | Common GOOD+ % | Common mean utility | Continuation GOOD+ % | Continuation mean utility | What the transplant shows |
| ---: | --- | --- | --- | --- | --- |
| 2000 | 0 / 0 / **100** | −0.961 / −0.648 / **+0.926** | 0 / 0 / **100** | −0.941 / −0.629 / **+0.926** | 24 weights fully rescue; 96 weights improve utility but not GOOD+. |
| 2001 | 0 / **100** / **100** | −0.834 / +0.445 / +0.328 | 0 / **100** / **100** | −0.805 / +0.465 / +0.328 | Both earlier vectors fully rescue. |
| 2002 | **78.125** / 12.5 / **100** | +0.113 / −0.707 / **+0.625** | **84.375** / 15.625 / **100** | +0.152 / −0.629 / **+0.664** | 96 weights sharply **harm** a strong late state; 24 weights improve it. |
| 2003 | 0 / 75 / **100** | −0.727 / +0.094 / **+0.984** | 0 / 87.5 / **100** | −0.668 / +0.250 / **+0.977** | Both earlier vectors rescue, 24 more strongly. |
| 2004 | 0 / 25 / 0 | −1.000 / −0.500 / −0.902 | 0 / 15.625 / 0 | −1.000 / −0.688 / −0.844 | 96 weights partially rescue; 24 weights do not restore GOOD+. |
| **Five-seed mean** | **15.625 / 42.5 / 80.0** | −0.682 / −0.263 / +0.392 | **16.875 / 43.75 / 80.0** | −0.652 / −0.246 / +0.410 | Descriptive, selected subset only. |

The action/timing records are not reduced to GOOD+ alone. The next table gives **early attempted MISS counts** and **all DOWN counts** in the same 384/96/24 order. A missed note without an attempted early press has no hit-error timestamp; the raw ledger preserves the null versus early-attempt distinction and every recorded signed error. Mean absolute error among hits is also saved per branch, but can be misleading when most notes are MISS (for example, seed 2004 with 96 weights has a 3 ms mean among its few hits while most notes still miss).

| Seed | Common early attempted MISS | Common DOWN | Continuation early attempted MISS | Continuation DOWN |
| ---: | --- | --- | --- | --- |
| 2000 | 28 / 0 / 0 | 64 / 32 / 64 | 26 / 0 / 0 | 64 / 32 / 64 |
| 2001 | 15 / 0 / 0 | 32 / 96 / 64 | 12 / 0 / 0 | 32 / 96 / 64 |
| 2002 | 0 / 22 / 0 | 64 / 64 / 64 | 0 / 19 / 0 | 64 / 64 / 64 |
| 2003 | 8 / 0 / 0 | 64 / 64 / 64 | 4 / 0 / 0 | 64 / 64 / 64 |
| 2004 | 32 / 24 / 22 | 32 / 40 / 32 | 32 / 27 / 16 | 32 / 37 / 32 |

Only donor vectors were changed; no clipping update occurred during frozen probes. The table below records the transplant displacement from the actual 384 weights and upper-bound occupancy, to expose saturation and intervention size. L1 is the sum of absolute mV-equivalent changes over selected edges, **not** a voltage delivered to one neuron.

| Seed | 96-weight L1 displacement (mV) | 24-weight L1 displacement (mV) | Upper-bound edges at 384 / 96 / 24 |
| ---: | ---: | ---: | --- |
| 2000 | 391.99 | 160.81 | 339 / 0 / 0 |
| 2001 | 470.26 | 351.53 | 0 / 411 / 286 |
| 2002 | 37.50 | 65.80 | 289 / 326 / 265 |
| 2003 | 27.38 | 167.89 | 309 / 315 / 0 |
| 2004 | 113.38 | 103.42 | 0 / 0 / 0 |

## Mechanistic conclusion and limits

Earlier selected-weight vectors can substantially change the frozen behavior **at an otherwise identical late state**. Four weak late seeds have at least one GOOD+ rescue on both maps; seed 2002 shows the converse, where 96-outcome weights damage a strong late state. The 24-outcome vector improves four seeds' GOOD+ and leaves seed 2004 at zero. Thus the late weight vector is a causal contributor to behavior in these fixed-state comparisons, but its age or distance from the late vector is not a monotonic predictor of quality. Seed 2002's 96-vector harms despite a smaller L1 displacement than its beneficial 24-vector. Bound occupancy alone also fails to explain the pattern.

This transplant **does not reconstruct the trajectory** the network would have taken had it kept the earlier weights, identify which update was harmful, prove local update direction, or establish a corrected learning rule. The frozen 384 neuron/queue/readout/eligibility/predictor state may interact with each donor vector; already queued arrivals retain late weights. The five seeds were the user-stopped diagnostic subset, so these means are **descriptive, not a confirmatory reliability estimate**. The synthetic M2 gate remains failed. No parameter search or follow-up experiment was run.

## Execution record and reproduction

The first launch stopped **before any seed** on the saved model-source hash guard: later MaleCNS scale work had changed only `simulation/__init__.py` and `simulation/spiking.py` among the pinned synthetic source files. The runner was amended to allow only those two exact current hashes, record both original and replay hashes, and require exact training-event and reference-probe replay. A later process exited during seed 2000 with code 1 and no captured traceback or durable row; the same protocol was resumed with stdout/stderr capture and completed all five seeds. The cause of that empty-output exit is unknown and no result was accepted from it. No production model source, parameters, protocol or source ledger was modified.

The [protocol](../configs/weight_rollback_diagnostic.json) SHA-256 is `698236aad27cd4d299ee981f03084bc0b438f687041a87f710a20decae191b36`; final [run ledger](figures/weight_rollback_diagnostic/runs.jsonl) SHA-256 is `cab2b2fc807edc8f63219969c9707cb960c8ee7fd25484ebfd1681c4e6d2b28d`. The output directory also contains `meta.json`, `status.json`, `result.json`, `audit.json` and captured stdout/stderr. Reproduce only from trusted local source data:

```powershell
$env:PYTHONPATH = 'src'
.\.venv\Scripts\python.exe -m scripts.weight_rollback_diagnostic
.\.venv\Scripts\python.exe -m scripts.audit_weight_rollback_diagnostic
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
```

The final full regression suite passed **96 tests in 13.628 seconds** after the independent audit was strengthened to recompute every reported aggregate. Stop after this diagnostic as requested.
