# Electrical Model V1 neutral operating-state gate

**2026-09-30. Decision: PASS for the predeclared engineering neutral gate.** This is a task-independent numerical operating-state result for the frozen 115-body [Electrical Model V1](ELECTRICAL_MODEL_V1.md). It does **not** establish a biologically valid fly state, sensory-to-motor transmission, a keypress policy, or learning.

## Frozen protocol and data

The [protocol](../configs/electrical_v1_neutral_gate.json) was saved before the 24-run panel. It uses the [DN boundary contract](DN_BOUNDARY_OPERATING_STATE_CONTRACT.md): seeds **31001, 31002, 31003**; A and C at low/nominal/high, B at omitted boundary, D at nominal independent background. Every run used **10 s settling + 60 s observation**, no visual transient, game, reward, exploration, plasticity or readout. The electrical [config](../configs/electrical_model_v1.json) remained at SHA-256 `fe7e0c488e5ce1beb3642cd003a19198e4f1d0758c6e6dd7ecb6c714bb935d0c`. No value or condition was changed after inspecting activity.

The saved [result](figures/electrical_v1_neutral_gate/result.json) indexes all **24** individual compressed run records, three **250-µs** numerical refinements, and the per-seed autonomous boundary ledgers. [Metadata](figures/electrical_v1_neutral_gate/meta.json) includes the complete resolved config, protocol, code/source hashes, Python/NumPy versions and trace schema. Every run has 10-ms selective DN voltage, separate leak/synaptic/boundary currents, refractory and queue samples, all spike times, exact per-second DN refractory bins and every declared gate check. The [independent saved-record audit](figures/electrical_v1_neutral_gate/audit.json) passed.

## Results

Rates below are the **range across all three declared seeds** for the 60-s observation, in Hz. A/C use the same boundary realization for each matched seed/level. The full per-seed records remain in the result and raw files; no seed was excluded.

| Condition | DNa03 rate | DNa02 rate | Interpretation |
| --- | ---: | ---: | --- |
| A low | 0 | 0 | Silence was allowed by the protocol. |
| A nominal | 10.133–10.567 | 12.383–12.633 | Both DNs exceed the ≥1-Hz active floor. |
| A high | 35.400–35.783 | 37.833–38.067 | Below the 100-Hz ceiling. |
| B omitted | 0 | 0 | Explicit deafferentation control; silence was allowed. |
| C low | 0 | 0 | Same as matched A low. |
| C nominal | 10.133–10.567 | 12.383–12.633 | Spike times **identical** to matched A nominal. |
| C high | 35.400–35.783 | 37.833–38.067 | Spike times **identical** to matched A high. |
| D nominal, independent | 9.617–10.000 | 12.050–13.300 | Active with zero shared *boundary* component under matched marginal construction. |

For A nominal by seed, DNa03/DNa02 rates were **31001: 10.250/12.633**, **31002: 10.133/12.383**, **31003: 10.567/12.500 Hz**. C nominal reproduced each exact spike train. The largest nominal A/C silent interval for either DN was **1.286 s**, below the declared 30-s limit. D remained active in all three seeds; this is evidence about the chosen proxy construction, not a measurement of biological DN correlation.

All **24/24** primary runs met the declared numerical and activity checks. Across runs, no cell had a recorded normalized voltage sample outside `[−2,2]` (or `[−4,4]`); the maximum DN refractory occupancy was **9.521%** over observation and **13.75%** in any full 1-s bin, below 25%/50%. Peak queued events were **1**, with no overflow or dropped event; scheduled-minus-delivered equalled final queue length. Every 10-s checkpoint replayed deterministically over the next second, and every run's autonomous boundary checkpoint matched its seed's independently generated boundary ledger. The low and B silence did not count as gate failures.

The separately predeclared numerical check reran **A nominal at each seed for the full 70 s** with a 250-µs threshold grid, against the frozen 500-µs model. Boundary event states matched exactly. The largest relative observation-rate difference across DN/seed comparisons was **0.402%**, the largest 1-s spike-count difference was **one**, and the voltage outer-fraction difference was zero. All three refinement comparisons passed their locked tolerances. This checks grid sensitivity for nominal A; it does not prove convergence for every possible task-driven trajectory.

The [saved-record auditor](../scripts/audit_electrical_v1_neutral_gate.py) independently checked **189,027** selective trace samples and **50,036** spike records across the 24 runs and three refinements. It reconstructed the injected boundary current at every saved sample from the exact sign-flip ledgers and reconstructed DNa02's only neutral synaptic current from DNa03 spike arrivals (maximum absolute residual **5.33×10⁻¹⁵ pA**). It independently recomputed spike counts, rates, silent gaps and refractory occupancy/bins. All nine A/C matched pairs had identical spike times. The per-cell 500-µs voltage excursion counters were checked as recorded model counters rather than independently re-integrated, which is the audit's explicit limit.

## What passed, and what remains open

**The gate passed because the declared DN boundary produces stable, finite, nonsaturated DN activity at nominal A/C**, with matched reproducibility and acceptable grid sensitivity. It did **not** show that the proposed MBON32→DN motor route transmits sensory or learned signals. The fixed neutral input drove **zero spikes** in the three selected visual cells, all 107 KCs, and MBON32. APL and PPL103 also remained inactive. Consequently A and C were exactly identical in all nine seed/level pairs: disconnecting MBON32 had no functional effect in this neutral experiment. The only observed network transmission was the named DNa03→DNa02 hypothesis; the boundary caused the initial DN activity. This is an expected interpretive limit of the [contract](DN_BOUNDARY_OPERATING_STATE_CONTRACT.md), not grounds to tune V1 or relabel the inactive route as validated.

The exact MBON32→DN and DNa03→DNa02 target effects, omitted DN conductances, APL branch geometry, visual tuning, and PPL103-gated KC→MBON32 plasticity remain `UNKNOWN` beyond the bounded hypotheses recorded in [Electrical Model V1](ELECTRICAL_MODEL_V1.md) and [ASSUMPTIONS.md](../ASSUMPTIONS.md). No game map, one-key readout, motor causality perturbation or training was run. Any future claim that this circuit can *play* or *learn* requires a separately predeclared sensory/MBON perturbation and fixed readout test, with the existing UNKNOWN and engineering labels intact. The current result licenses only the next causal route validation stage; it is not a learning gate.
