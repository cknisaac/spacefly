# Larval L2 engineering-family controllability — FAIL

**Run date:** 2026-10-02  
**Decision:** **FAIL — reject L2 under this simulator abstraction; stop before plasticity**  
**Scope:** Pre-training controllability only. No teaching, plasticity, task learning, or task-performance search.

## Frozen policy and inputs

The parameter family and acceptance rule were frozen in [the policy](../configs/larval_l2_electrical_family_v4_policy.json) before the family run (SHA-256 `f97bfc78cdaea4d916a6e3e151b80087d37c838b4889a903e7721147f7bb5769`). The family contains 72 configurations: contact effect `[0.01, 0.05, 0.125, 0.275]` mV-equivalent/contact; membrane time constant `[10, 20]` ms (C fixed at 1 nF); threshold `[1, 3, 7]` mV-equivalent; and shared KC/nociceptive pulse `[8, 12, 16]` mV-equivalent for 5 ms. Synaptic decay, delay, refractory interval, zero tonic drive, and Goro event readouts are fixed as recorded in the policy. Every numeric value is an **ENGINEERING ASSUMPTION** or **ENGINEERING OVERLAY**, not a measurement of larval L2 physiology.

Frozen L2 context manifest SHA-256: `97560028444a02c8bb0c68c6608fd68dcfc5c103276b67debd30b059d0f6003b`. Preserved v3 parent model SHA-256: `c5f9adcf02378ded60ad66f11f8e1e03738955b94a1ab0a1089cc99b3033f60e`. Both matched before simulation. The v1/v2/v3 artifacts were not modified.

The runner crossed each configuration with KC→MBON-d1 multipliers `[0.25, 0.5, 0.75, 1.0]`, eight predeclared sensory states and two exact replays: 4,608 driven simulation runs plus 72 silent zero-drive baselines (4,680 total). Only KC→MBON-d1 weights changed within each configuration. The frozen rule required a non-saturated action set under decreasing weights, nested action sets, deterministic finite replay, a silent baseline, and a sufficiently large face-connected feasible region, including the 2-spike readout robustness check.

## Results

| Measure | Result |
|---|---:|
| Configurations meeting the per-configuration primary gate | **0 / 72** |
| Largest face-connected feasible component | **0** |
| Configurations robust at the 2-spike readout | **0** |
| Zero-drive baselines silent and finite | **72 / 72** |
| Driven replays deterministic and finite | **2,304 / 2,304 paired cells** |
| Maximum role spikes in a driven cell: KC / MBON-d1 / Ipsigoro / Goro / noci PN | **30 / 8 / 0 / 0 / 4** |
| Goro action states at either 1- or 2-spike threshold | **0 across the entire family** |
| MBON-d1 responses differing across KC-weight factors | **151 / 576 config-state combinations** |

The simulator remained numerically finite, and the zero-drive baseline remained silent. Some parameter/state conditions activated KCs and nociceptive PNs; MBON-d1 activity was present in some conditions and sometimes varied with KC weight. No condition propagated activity to Ipsigoro or Goro, so the fixed action output never occurred. The action-set nesting checks pass trivially for empty sets and therefore do not establish controllability.

Raw per-configuration and per-cell records are in [the run result](../runs/larval_l2_electrical_family_v4.json), SHA-256 `da88de1043f008b29e2393d301efeae3e68cb297d327afb9dfc994bed48074e6`. Reproduction command: `\.venv\Scripts\python.exe scripts\run_larval_l2_engineering_family_v4.py` from the project root. The runner checks the frozen manifest/model hashes before simulation.

## Decision and scope

The predeclared robust-region criterion failed. **No Electrical Model v4 is admitted, and no internal plasticity implementation or learning run is authorized by this result.** L2 is rejected under this stated engineering abstraction; this does not disprove the biological pathway or establish that a living larva cannot route these signals. The failure is consistent with absent transfer in this simplified signed network, but this run does not isolate a unique biological or simulator cause.

There is no further L2 simulator stage under this policy. A future attempt would require a separately justified pathway/model redesign or new independent evidence and a new frozen contract; do not extend these ranges or tune values in response to this result. This L2 side investigation does not alter the separate MaleCNS Candidate 1 retirement or B6.1/B6.2 status.
