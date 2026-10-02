# L1R-E2/E3 frozen electrical family and controllability result

**Date:** 2026-10-02  
**Variant:** L1R-E  
**L1R-E2 decision:** **PASS**  
**L1R-E3 decision:** **FAIL**

## Scope

This experiment tests only whether measured KC→MBON-m1 contact counts, under a frozen family of **ENGINEERING ASSUMPTION** electrical values, allow weight changes to control MBON-m1 output and a fixed inverse action overlay. The artificial teaching port, plasticity, training, reward, and exploration were disabled.

This is not a test of a biological dopamine pathway or a claim that the electrical quantities reproduce larval physiology.

## L1R-E2 frozen inputs

The complete policy was serialized before the first response was simulated:

- policy: `configs/larval_l1re_electrical_family_v1_policy.json`
- policy SHA-256: `4CD26CA601C2340408ADE63F8FD37A795922CB73DFB0FABB64D1E33EE02DBD60`
- anatomy manifest SHA-256: `58AAE08A16C9CAABB1A987B6FB10B4C81908722ABEEC60182ABF2483B7036A9C`
- 72 configurations: contact effect `[0.01, 0.05, 0.125, 0.275]`, membrane time constant `[10, 20]` ms, threshold `[1, 3, 7]`, and KC pulse `[8, 12, 16]` for 5 ms;
- fixed 5-ms synaptic decay, 2-ms delay and refractory interval, 1-ms tick, zero tonic drive, and 100-ms response window;
- eight non-overlapping current-position KC groups, generated from ascending source IDs;
- weight factors `[1.0, 0.8, 0.6, 0.4, 0.2]`;
- fixed inverse action thresholds of `≤0`, `≤1`, and `≤2` bilateral MBON-m1 spikes;
- two exact deterministic replays for every driven state/factor/configuration cell.

The encoder contract forbids future note time, time-to-contact, desired action time, evaluation target identity, reward, held-out answers, and the teaching event. The action mapping is deterministic and non-trainable. L1R-E2 therefore **PASSes** as a complete pre-outcome freeze.

## L1R-E3 execution

- runner: `scripts/run_larval_l1re_controllability_family.py`
- raw result: `runs/larval_l1re_controllability_family_v1.json`
- result SHA-256: `509ADF1C06E30B22C4E823C0649F5552A3347A4889DFDC704F571727AB700FCA`
- raw result size: 6,571,743 bytes

All 72 zero-drive baselines were silent, disarmed, finite, and within queue bounds. The 72 × 5 × 8 design produced **2,880 driven condition cells**, each run twice for **5,760 driven simulations**; all 2,880 replay pairs matched. Together with the baselines, the gate executed 5,832 simulations. All driven runs remained finite and bounded. The raw artifact preserves every configuration, state, factor, neural response, action overlay, diagnostic, and digest. No outcome was omitted.

## Frozen-gate results

| Requirement | Result |
|---|---:|
| Qualifying configurations | **2 / 72**; required ≥12 |
| Values spanned on every axis | **FAIL**; qualifiers span only one contact scale, one τm, one threshold, and two pulse values |
| Largest face-connected component | **2**; required ≥8 |
| Component members robust at an adjacent threshold | **0**; required ≥6 |
| Zero-drive check | 72 / 72 PASS |
| Exact replay check | 72 / 72 configurations PASS |
| Finite/bounded driven runs | 72 / 72 configurations PASS |
| All intended KCs activate for all cues/factors | 40 / 72 configurations |
| Full-weight MBON activity in ≥6 states | 9 / 72 configurations |
| ≥30% low-weight reduction in ≥6 states | 9 / 72 configurations |
| Monotonic response in ≥7 states | 72 / 72 configurations |
| No reversal over one spike | 72 / 72 configurations |
| Qualifying action transition | 2 / 72 configurations |

The two qualifiers were adjacent:

| ID | mV-equivalent/contact | τm | threshold | KC pulse | qualifying action threshold |
|---|---:|---:|---:|---:|---:|
| L1RE-55 | 0.275 | 10 ms | 1 | 12 | 0 spikes |
| L1RE-56 | 0.275 | 10 ms | 1 | 16 | 0 spikes |

For both, all eight states produced MBON-m1 spikes at full weight and all eight met the 30% reduction rule. At the zero-spike action threshold, factors 1.0 through 0.4 produced no action state and factor 0.2 produced actions for states 2, 4, 5, 6, and 7. The adjacent thresholds saturated all eight states at factor 0.2, so neither configuration met the adjacent-threshold robustness rule.

## Decision and stop

L1R-E3 **FAILS** the predeclared family gate. The isolated two-configuration island is too narrow to support the required robust controllability claim. No nominal `configs/larval_l1re_electrical_v1.json` was created.

Per the frozen outcome policy, this version of the L1R-E electrical abstraction stops here. Artificial-teacher plasticity, acquisition, retention, controls, and confirmation were not implemented or run. The result rejects this declared numerical abstraction for the MVP; it does not disprove the measured KC→MBON-m1 anatomy or biological learning in larvae.

## Verification

The builder and runner compile under Python. Nineteen existing LIF, sparse-graph, and spiking-network unit tests passed with `unittest`. The environment did not contain `pytest`; the same standard-library test cases were executed directly.
