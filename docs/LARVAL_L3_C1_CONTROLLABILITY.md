# Larval L3 C1 pre-training controllability

**Experiment:** `larval_l3_c1_controllability_v1`  
**Verdict:** **PASS — bounded engineering controllability only**

## Frozen setup

The run used the frozen manifest and electrical v1, the same eight ascending-KC position-bin inputs, 5 ms current pulse, 100 ms response window, fixed one-spike DN-VNC action boundary, and fixed LIF, sign, delay, and downstream edge settings. The only varied quantity was the KC→MBON-c1 edge-weight multiplier: `0, 0.25, 0.5, 1, 2, 4`. Plasticity, teaching, and exploration were off. Each of the 48 multiplier/state cells was run twice.

Input SHA-256 values were checked before the run:

| Frozen input | SHA-256 |
|---|---|
| `configs/larval_l3_c1_subgraph_manifest_v1.json` | `b54a8a7ec9e3b18f21f8df91584c33f875c3302c8e534b6020dec7290f004895` |
| `configs/larval_l3_c1_electrical_v1.json` | `5e32171707409a5dffc66f0c93d48bec307d442a01ace8b8554fa82e23c91f6e` |
| `runs/larval_l3_c1_neutral_dynamics_v1.json` | `8fa83febee7812f5ba3435592a9a4dc390f156ccd9ba929e25486bbf9b4ce7bc` |

## Results

| KC→MBON-c1 multiplier | States producing a DN-VNC action | DN-VNC spikes across all 8 states |
|---:|---|---:|
| 0× | none | 0 |
| 0.25× | none | 0 |
| 0.5× | none | 0 |
| 1× | none | 0 |
| 2× | 6 | 1 |
| 4× | 1, 3, 5, 6, 7 | 5 |

An action is one or more spikes from either frozen DN-VNC readout ID (`10411574`, `17379420`) within 100 ms. At 1×, all eight states reproduce the frozen neutral result for the KC, MBON-c1, and DN-VNC spike totals, action status, and individual readout counts. Each sweep row also records spikes per role and neuron source ID, spike times, event counters, end-of-window queue size, finite-state checks, and its deterministic replay digest in the result JSON.

## Gate interpretation

**PASS** by the predeclared engineering gate: actions occur for more than one representative state at a non-saturating factor (4× yields 5/8 states); active-state sets are nested as the factor increases; all 48 paired replays match; the 1× cell matches neutral; and every run is finite without a safety stop. The action states emerge only at 2×–4× under this assumed contact-to-current scale. That is evidence of controllability in this simulator, not evidence that larval C1 physiology uses this gain or that the circuit learns. No training or behavioral optimization was run.

## Artifacts

- Runner: `scripts/run_larval_l3_c1_controllability.py`
- Full measurements and hashes: `runs/larval_l3_c1_controllability_v1.json`
- Result SHA-256: `f3d224242f6dd0b7c526acdbf905fa43eda3d16182736473be359551e4c6f340`
