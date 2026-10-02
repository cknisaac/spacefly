# MaleCNS continuous-position learning — Level 2 v2.3

**2026-10-02 · MALECNS-CONTINUOUS-POSITION-LEARNING-v2.3 · FAIL under the unchanged v2.2 gate.** This continuation changed training duration from 96 to 120 blocks only. Each arm completed 1,200 presentations with no early stopping. All v2.2 model, learning and readout settings, fixed threshold, eligibility scope and gate definitions were retained.

## Completion, learning and floor

| Arm | Blocks / presentations | Teacher pulses | Changed weights | Final floor weights |
|---|---:|---:|---:|---|
| Target teacher | 120 / 1200 | 600 | 6/32 | 49544, 49545, 49867 |
| Plasticity off | 120 / 1200 | 0 | 0/32 | none |
| Wrong-region teacher | 120 / 1200 | 600 | 6/32 | 45467, 45950 |

Target teaching formed actions at all three target-core positions (0.65, 0.70, 0.75). Wrong-region teaching formed actions at all three wrong-core positions (0.15, 0.20, 0.25) and shifted away from the target core. Both final maps matched their frozen evaluations. Plasticity-off remained unchanged.

Target-arm floor first occurred at block 63; by block 120, source IDs 49544, 49545 and 49867 were at the 20% floor. Wrong-region floor first occurred at block 49; IDs 45467 and 45950 were at the floor by block 120. Plasticity-off had no weight changes or floor values.

## Learning curves

The raw receipt has all 120 block values for each arm. The table samples blocks 1, 24, 48, 72, 96 and 120. Action counts are out of 3 points in each corresponding core.

| Block | Target mean mV | Target actions / 3 | Wrong mean mV | Wrong actions / 3 | Full-grid actions: target / off / wrong | Target / wrong floor weights |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.012516468 | 0/3 | 0.011759337 | 0/3 | 0 / 0 / 0 | 0 / 0 |
| 24 | 0.010357331 | 0/3 | 0.009812122 | 0/3 | 0 / 0 / 0 | 0 / 0 |
| 48 | 0.008128370 | 0/3 | 0.008007201 | 0/3 | 0 / 0 / 0 | 0 / 0 |
| 72 | 0.005960136 | 1/3 | 0.006301234 | 1/3 | 1 / 0 / 1 | 1 / 1 |
| 96 | 0.004357212 | 1/3 | 0.004707316 | 2/3 | 1 / 0 / 2 | 2 / 2 |
| 120 | 0.003084202 | 3/3 | 0.003449315 | 3/3 | 3 / 0 / 4 | 3 / 2 |

## Final position → MBON05 / action maps

Teacher and plasticity were off during evaluation. “Yes” means MBON05 maximum voltage was ≤ 0.005572335995331903 mV-equivalent.

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

**FAIL under the frozen v2.2 criteria.** All criteria passed except `distant_positions_mostly_remain_no_action`. This inherited metric defines distant positions relative to the primary target region [0.65, 0.75] for both teacher arms. It therefore counts the intended wrong-region action core (0.15–0.25) plus the adjacent 0.30 action as distant actions. The wrong-region arm made four contiguous actions from 0.15 through 0.30; this correctly creates the wrong-shifted region but fails the unchanged primary-target-anchored distant-position check. The target-teacher arm had no actions at its 12 target-distant positions.

No model or gate parameters were changed after results. This is a deterministic engineering fixture and does not establish biological fly learning.

## Reproduction

- Frozen config: [`../configs/malecns_continuous_position_learning_v2_3.json`](../configs/malecns_continuous_position_learning_v2_3.json)
- Full result and all block curves: [`../runs/malecns_continuous_position_learning_v2_3/result.json`](../runs/malecns_continuous_position_learning_v2_3/result.json)
- Runner: [`../src/project_b/malecns_continuous_position_learning/experiment_v2_3.py`](../src/project_b/malecns_continuous_position_learning/experiment_v2_3.py)
- Config SHA-256: `e9c2b0ed9970c32d2b5c1b237cdfb49363296c1603fd3206fb887ea9bfb44089`
