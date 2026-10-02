# MaleCNS continuous-position learning — Level 2 v2.5

**2026-10-02 · MALECNS-CONTINUOUS-POSITION-LEARNING-v2.5 · PASS.** This is a protocol-correction confirmation, not a reinterpretation of prior runs. The model and 120-block training protocol are unchanged from v2.3. Only the locality evaluation was corrected to compare each teaching arm with its own taught region and halo. v2.3 and v2.4 remain FAIL under their original frozen target-anchored criterion.

## Frozen model and run

The fresh run used the same 32 KCs, MBON05 source ID 10495, Gaussian encoder, contact normalization, LIF model, presentation-local eligibility, η = 0.00005, 20% initial-weight floor, fixed action threshold **0.005572335995331903 mV-equivalent**, target [0.65, 0.75], wrong region [0.15, 0.25], and 120-block schedule. It ran all 120 blocks / 1,200 presentations in each of the three arms without early stopping. Automated config comparison against v2.3 verified circuit and training settings were unchanged. No 144+ block run was performed.

| Arm | Blocks / presentations | Teacher pulses | Changed weights | Final floor weights |
|---|---:|---:|---:|---|
| Target teacher | 120 / 1200 | 600 | 6/32 | 49544, 49545, 49867 |
| Plasticity off | 120 / 1200 | 0 | 0/32 | none |
| Wrong-region teacher | 120 / 1200 | 600 | 6/32 | 45467, 45950 |

Target-arm weights 49544, 49545 and 49867 first reached the floor at block 63 and remained there at block 120. Wrong-region weights 45467 and 45950 first reached the floor at block 49. Plasticity-off weights did not change or reach the floor.

## Corrected locality contract

| Teaching arm | Core | Allowed halo | Final actions | Outside-halo grid actions | Outside-halo no-action | Result |
|---|---|---|---|---:|---:|---|
| Target teacher | 0.65–0.75 | 0.60–0.80 | 0.65, 0.70, 0.75 | none | 100% | PASS |
| Wrong-region teacher | 0.15–0.25 | 0.10–0.30 | 0.15, 0.20, 0.25, 0.30 | none | 100% | PASS |

The target arm’s three actions were at 0.65, 0.70 and 0.75. The wrong-region arm’s four actions were at 0.15, 0.20, 0.25 and 0.30; 0.30 is inside its allowed halo. Both arms had no actions outside their own halos (16/16 outside points no-action per arm). The plasticity-off arm had no actions anywhere and exactly retained its baseline map. Both learned maps matched the frozen evaluations with teacher and plasticity off.

## Learning curve samples

The result JSON contains every block curve for all arms. This table samples blocks 1, 24, 48, 72, 96 and 120. Core action counts are out of three positions.

| Block | Target mean (mV) | Target actions / 3 | Wrong mean (mV) | Wrong actions / 3 | Full-grid actions: target / off / wrong |
|---:|---:|---:|---:|---:|---:|
| 1 | 0.012516468 | 0/3 | 0.011759337 | 0/3 | 0 / 0 / 0 |
| 24 | 0.010357331 | 0/3 | 0.009812122 | 0/3 | 0 / 0 / 0 |
| 48 | 0.008128370 | 0/3 | 0.008007201 | 0/3 | 0 / 0 / 0 |
| 72 | 0.005960136 | 1/3 | 0.006301234 | 1/3 | 1 / 0 / 1 |
| 96 | 0.004357212 | 1/3 | 0.004707316 | 2/3 | 1 / 0 / 2 |
| 120 | 0.003084202 | 3/3 | 0.003449315 | 3/3 | 3 / 0 / 4 |

## Full final position → MBON05 / action maps

Evaluation used teacher and plasticity OFF. Each cell is maximum MBON05 voltage (mV-equivalent) / action; “Yes” means voltage ≤ the inherited threshold.

| Position | Target teacher | Plasticity off | Wrong-region teacher |
|---:|---:|---:|---:|
| 0.00 | 0.008010579 / No | 0.008010579 / No | 0.008010579 / No |
| 0.05 | 0.014215610 / No | 0.014215610 / No | 0.014215610 / No |
| 0.10 | 0.015860566 / No | 0.015860566 / No | 0.012364565 / No |
| 0.15 | 0.015056665 / No | 0.015056665 / No | 0.003872849 / Yes |
| 0.20 | 0.009310005 / No | 0.009310005 / No | 0.001970409 / Yes |
| 0.25 | 0.011181216 / No | 0.011181216 / No | 0.004504686 / Yes |
| 0.30 | 0.009622703 / No | 0.009622703 / No | 0.004744131 / Yes |
| 0.35 | 0.009945537 / No | 0.009945537 / No | 0.009945537 / No |
| 0.40 | 0.016840031 / No | 0.016840031 / No | 0.016840031 / No |
| 0.45 | 0.011751978 / No | 0.011751978 / No | 0.011751978 / No |
| 0.50 | 0.014575051 / No | 0.014575051 / No | 0.014575051 / No |
| 0.55 | 0.015085034 / No | 0.015085034 / No | 0.015085034 / No |
| 0.60 | 0.012721158 / No | 0.016351110 / No | 0.016351110 / No |
| 0.65 | 0.005152624 / Yes | 0.011371990 / No | 0.011371990 / No |
| 0.70 | 0.000061633 / Yes | 0.013596590 / No | 0.013596590 / No |
| 0.75 | 0.004038349 / Yes | 0.012864267 / No | 0.012864267 / No |
| 0.80 | 0.011691965 / No | 0.013536520 / No | 0.013536520 / No |
| 0.85 | 0.015670464 / No | 0.015670464 / No | 0.015670464 / No |
| 0.90 | 0.013665335 / No | 0.013665335 / No | 0.013665335 / No |
| 0.95 | 0.016772147 / No | 0.016772147 / No | 0.016772147 / No |
| 1.00 | 0.008940782 / No | 0.008940782 / No | 0.008940782 / No |

## Decision

**PASS under the corrected v2.5 contract.** All three target-core positions became actions under target teaching; all three wrong-core positions became actions under wrong-region teaching; plasticity-off stayed no-action and unchanged; both action maps persisted with teacher/plasticity off; all actions stayed inside the arm-specific halos; and threshold, encoder, circuit and learning settings matched the frozen predecessor.

This result corrects the locality evaluation only. It does not change the recorded FAIL decisions for v2.3 and v2.4 under their original target-anchored criteria. It is a single deterministic engineering-fixture confirmation, not evidence of biological fly learning. The requested run is complete and stopped at 120 blocks.

## Reproduction

- Frozen config: [`../configs/malecns_continuous_position_learning_v2_5.json`](../configs/malecns_continuous_position_learning_v2_5.json)
- Full result, 120-block curves, exact maps and criteria: [`../runs/malecns_continuous_position_learning_v2_5/result.json`](../runs/malecns_continuous_position_learning_v2_5/result.json)
- Runner: [`../src/project_b/malecns_continuous_position_learning/experiment_v2_5.py`](../src/project_b/malecns_continuous_position_learning/experiment_v2_5.py)
- Config SHA-256: `e81a9da42f28be4ad288f8f416a8186b2443230c012d1563bc827c3f0c8b5485`
