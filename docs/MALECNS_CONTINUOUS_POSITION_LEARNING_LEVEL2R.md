# MaleCNS continuous-position learning — Level 2R

**2026-10-02 · MALECNS-CONTINUOUS-POSITION-LEARNING-LEVEL2R · FAIL.** This one 120-block confirmation used a new outcome-blind cohort and the same v2.5 arm-specific locality contract. The threshold was rederived and frozen by the original task-independent pretraining probe before any training. No learning parameter was retuned.

## New outcome-blind KC cohort

The selection scans the pinned B2 runtime mask in source order after the previously used first 48 rows. It takes the next 32 positive-contact pairs at zero-based rows 48–51 and 53–80, skipping row 52 because it contains zero plastic contact rows. No activity or learning outcomes were consulted. The selected source IDs are:

`51459, 51535, 51552, 51553, 51742, 51751, 51865, 51937, 52318, 52564, 52856, 52938, 53756, 53987, 54202, 54255, 55542, 55853, 56251, 56650, 56866, 57152, 57770, 57806, 58058, 58471, 60011, 60388, 60471, 60545, 60834, 61312`.

The new cohort has **687 audited plastic contact rows** across 32 KC→MBON05 pairs; the preferred positions are reassigned linearly by within-cohort rank. Starting weights use the same contact-count normalization. The pretraining probe receipt is tied to the frozen cohort config hash.

## Task-independent threshold probe

The same fixed local-weakening procedure was run before training: at centers 0.20, 0.50 and 0.80, multiply the weights of KCs within ±0.10 preferred position by 0.20; evaluate local positions within ±0.05 and distant positions ≥0.20 from the center. The full naive grid had no actions, all local/distant/replay criteria passed.

| Probe quantity | Value (mV-equivalent) |
|---|---:|
| Largest local response after weakening, L | 0.002606732 |
| Smallest distant baseline response, D | 0.007903275 |
| Frozen threshold, (L + D) / 2 | **0.005255003** |

The Level 2R threshold **0.005255003491522959** differs from the earlier cohort’s value and was frozen before training. Probe status: **PASS**.

## Training and criteria

All three arms completed 120 blocks / 1,200 presentations with no early stopping. Training settings were unchanged: Gaussian encoder σ=0.08 and peak drive 1.2 mV-equivalent; same LIF/contact-normalized overlay; presentation-local eligibility; η=0.00005; 20% weight floor; same target [0.65, 0.75] and wrong region [0.15, 0.25]; same controls; new probe-derived fixed action threshold.

| Arm | Teacher pulses | Changed weights | Final floor weights | Core actions |
|---|---:|---:|---|---:|
| Target teacher | 600 | 6/32 | 57152, 57770 | 2/3 |
| Plasticity off | 0 | 0/32 | none | 0/3 |
| Wrong-region teacher | 600 | 6/32 | 51865, 51937 | 3/3 |

Target-arm weights 57152 and 57770 first reached the floor at block 52. Wrong-region weights 51865 and 51937 first reached it at block 57. The target arm learned actions at 0.65 and 0.70, but not 0.75. The wrong-region arm learned all three core positions. The control remained unchanged and no-action.

## Corrected locality and frozen retention

| Arm | Own allowed halo | Action positions after training | Outside-halo actions | Outside-halo no-action | Frozen persistence |
|---|---|---|---|---:|---|
| Target teacher | [0.60, 0.80] | 0.65, 0.70 | none | 100% | FAIL: target core incomplete |
| Wrong-region teacher | [0.10, 0.30] | 0.15, 0.20, 0.25 | none | 100% | PASS |

Evaluation used teacher and plasticity OFF. The 0.30 grid point remained no-action for this new cohort.

## Learning curve samples

The raw receipt stores all 120 block curves for each arm. This table samples blocks 1, 24, 48, 72, 96 and 120. Action counts are out of three points in the corresponding core.

| Block | Target mean (mV) | Target actions / 3 | Wrong mean (mV) | Wrong actions / 3 | Full-grid actions: target / off / wrong |
|---:|---:|---:|---:|---:|---:|
| 1 | 0.012154748 | 0/3 | 0.011504846 | 0/3 | 0 / 0 / 0 |
| 24 | 0.009997812 | 0/3 | 0.009441841 | 0/3 | 0 / 0 / 0 |
| 48 | 0.007951539 | 0/3 | 0.007500890 | 0/3 | 0 / 0 / 0 |
| 72 | 0.006241848 | 1/3 | 0.005593209 | 1/3 | 1 / 0 / 1 |
| 96 | 0.005123157 | 2/3 | 0.004299421 | 2/3 | 2 / 0 / 2 |
| 120 | 0.004208119 | 2/3 | 0.003156498 | 3/3 | 2 / 0 / 3 |

## Full final position → MBON05 / action maps

Each cell is maximum MBON05 voltage (mV-equivalent) / action. “Yes” means voltage ≤ the new frozen threshold 0.005255003491522959.

| Position | Target teacher | Plasticity off | Wrong-region teacher |
|---:|---:|---:|---:|
| 0.00 | 0.007903275 / No | 0.007903275 / No | 0.007903275 / No |
| 0.05 | 0.013424977 / No | 0.013424977 / No | 0.013424977 / No |
| 0.10 | 0.012578728 / No | 0.012578728 / No | 0.009172328 / No |
| 0.15 | 0.014292427 / No | 0.014292427 / No | 0.003221678 / Yes |
| 0.20 | 0.009800835 / No | 0.009800835 / No | 0.001669770 / Yes |
| 0.25 | 0.010691141 / No | 0.010691141 / No | 0.004578045 / Yes |
| 0.30 | 0.015260550 / No | 0.015260550 / No | 0.011349947 / No |
| 0.35 | 0.013587719 / No | 0.013587719 / No | 0.013587719 / No |
| 0.40 | 0.017452464 / No | 0.017452464 / No | 0.017452464 / No |
| 0.45 | 0.012581768 / No | 0.012581768 / No | 0.012581768 / No |
| 0.50 | 0.010764904 / No | 0.010764904 / No | 0.010764904 / No |
| 0.55 | 0.012999976 / No | 0.012999976 / No | 0.012999976 / No |
| 0.60 | 0.010173496 / No | 0.013775345 / No | 0.013775345 / No |
| 0.65 | 0.003340021 / Yes | 0.008977281 / No | 0.008977281 / No |
| 0.70 | 0.003485873 / Yes | 0.013335724 / No | 0.013335724 / No |
| 0.75 | 0.005798464 / No | 0.014434405 / No | 0.014434405 / No |
| 0.80 | 0.008282306 / No | 0.009985219 / No | 0.009985219 / No |
| 0.85 | 0.013033659 / No | 0.013033659 / No | 0.013033659 / No |
| 0.90 | 0.015087836 / No | 0.015087836 / No | 0.015087836 / No |
| 0.95 | 0.020249732 / No | 0.020249732 / No | 0.020249732 / No |
| 1.00 | 0.012702867 / No | 0.012702867 / No | 0.012702867 / No |

## Decision

**FAIL.** The task-independent probe passed and froze the threshold before training. All 120 blocks ran in every arm; wrong-region core actions, plasticity-off no-action/control, locality, threshold, encoder, circuit identity and learning-rule checks passed. The target-teacher core reached only 2/3 positions, so its required learned action region and complete frozen target retention did not pass. No parameters were changed after seeing the result, and no second run was performed.

This is a result for one deterministic engineering fixture and a second source-order KC cohort; it does not establish or refute biological fly learning.

## Reproduction artifacts

- Frozen cohort/training config: [`../configs/malecns_continuous_position_learning_level2r.json`](../configs/malecns_continuous_position_learning_level2r.json)
- Pretraining probe and newly frozen threshold: [`../runs/malecns_continuous_position_learning_level2r/controllability.json`](../runs/malecns_continuous_position_learning_level2r/controllability.json)
- Full training result, curves, logs and maps: [`../runs/malecns_continuous_position_learning_level2r/result.json`](../runs/malecns_continuous_position_learning_level2r/result.json)
- Runner: [`../src/project_b/malecns_continuous_position_learning/experiment_level2r.py`](../src/project_b/malecns_continuous_position_learning/experiment_level2r.py)
- Probe runner reused unchanged: [`../src/project_b/malecns_continuous_position_learning/probe.py`](../src/project_b/malecns_continuous_position_learning/probe.py)
- Protocol tests: [`../tests/test_malecns_continuous_position_learning_level2r.py`](../tests/test_malecns_continuous_position_learning_level2r.py)
- Training config SHA-256: `2e6ad163bdf79235535be496ccb469ccd629cf0d58da1edbd818503919775cbc`
- Probe receipt SHA-256: `15722a649c332176976aacd4e877bda9fbbfeaa0d0c7cf9329a321272bb838e4`
