# MaleCNS continuous-position learning — Level 2 v2.4

**2026-10-02 · MALECNS-CONTINUOUS-POSITION-LEARNING-v2.4 · FAIL under the unchanged v2.2 gate.** This continuation changed training duration from 120 to 144 blocks only. Each arm completed 1,440 presentations with no early stopping. All v2.2 model, learning and readout settings, fixed threshold, eligibility scope and gate definitions were retained.

## Completion, learning and floor

| Arm | Blocks / presentations | Teacher pulses | Changed weights | Final floor weights |
|---|---:|---:|---:|---|
| Target teacher | 144 / 1440 | 720 | 6/32 | 49544, 49545, 49867 |
| Plasticity off | 144 / 1440 | 0 | 0/32 | none |
| Wrong-region teacher | 144 / 1440 | 720 | 6/32 | 45467, 45620, 45950 |

Target teaching formed actions at all three target-core positions (0.65, 0.70, 0.75). Wrong-region teaching formed actions at all three wrong-core positions (0.15, 0.20, 0.25), plus the adjacent 0.30 position, and shifted away from the target core. Both final maps matched frozen evaluation. Plasticity-off remained unchanged.

Target-arm floor first occurred at block 63; by block 144, source IDs 49544, 49545 and 49867 were at the 20% floor. Wrong-region floor first occurred at block 49; IDs 45467, 45620 and 45950 were at floor by block 144. Plasticity-off had no weight changes or floor values.

## Learning curves

The raw receipt has all 144 block values for each arm. This table samples blocks 1, 24, 48, 72, 96, 120 and 144. Action counts are out of 3 positions in the corresponding cores.

| Block | Target mean mV | Target actions / 3 | Wrong mean mV | Wrong actions / 3 | Full-grid actions: target / off / wrong | Target / wrong floor weights |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.012516468 | 0/3 | 0.011759337 | 0/3 | 0 / 0 / 0 | 0 / 0 |
| 24 | 0.010357331 | 0/3 | 0.009812122 | 0/3 | 0 / 0 / 0 | 0 / 0 |
| 48 | 0.008128370 | 0/3 | 0.008007201 | 0/3 | 0 / 0 / 0 | 0 / 0 |
| 72 | 0.005960136 | 1/3 | 0.006301234 | 1/3 | 1 / 0 / 1 | 1 / 1 |
| 96 | 0.004357212 | 1/3 | 0.004707316 | 2/3 | 1 / 0 / 2 | 2 / 2 |
| 120 | 0.003084202 | 3/3 | 0.003449315 | 3/3 | 3 / 0 / 4 | 3 / 2 |
| 144 | 0.002734923 | 3/3 | 0.002350747 | 3/3 | 3 / 0 / 4 | 3 / 3 |

## Final position → MBON05 / action maps

Teacher and plasticity were off during evaluation. “Yes” means MBON05 maximum voltage was ≤ 0.005572335995331903 mV-equivalent.

| Position | Target teacher | Plasticity off | Wrong-region teacher |
|---:|---:|---:|---:|
| 0.00 | 0.008010579 / No | 0.008010579 / No | 0.008010579 / No |
| 0.05 | 0.014215610 / No | 0.014215610 / No | 0.014215610 / No |
| 0.10 | 0.015860566 / No | 0.015860566 / No | 0.011676070 / No |
| 0.15 | 0.015056665 / No | 0.015056665 / No | 0.002520291 / Yes |
| 0.20 | 0.009310005 / No | 0.009310005 / No | 0.001102658 / Yes |
| 0.25 | 0.011181216 / No | 0.011181216 / No | 0.003429291 / Yes |
| 0.30 | 0.009622703 / No | 0.009622703 / No | 0.003768416 / Yes |
| 0.35 | 0.009945537 / No | 0.009945537 / No | 0.009945537 / No |
| 0.40 | 0.016840031 / No | 0.016840031 / No | 0.016840031 / No |
| 0.45 | 0.011751978 / No | 0.011751978 / No | 0.011751978 / No |
| 0.50 | 0.014575051 / No | 0.014575051 / No | 0.014575051 / No |
| 0.55 | 0.015085034 / No | 0.015085034 / No | 0.015085034 / No |
| 0.60 | 0.012000788 / No | 0.016351110 / No | 0.016351110 / No |
| 0.65 | 0.004640023 / Yes | 0.011371990 / No | 0.011371990 / No |
| 0.70 | 0.000000000 / Yes | 0.013596590 / No | 0.013596590 / No |
| 0.75 | 0.003564747 / Yes | 0.012864267 / No | 0.012864267 / No |
| 0.80 | 0.011367316 / No | 0.013536520 / No | 0.013536520 / No |
| 0.85 | 0.015670464 / No | 0.015670464 / No | 0.015670464 / No |
| 0.90 | 0.013665335 / No | 0.013665335 / No | 0.013665335 / No |
| 0.95 | 0.016772147 / No | 0.016772147 / No | 0.016772147 / No |
| 1.00 | 0.008940782 / No | 0.008940782 / No | 0.008940782 / No |

## Decision

**FAIL under the unchanged v2.2 criteria.** All criteria passed except `distant_positions_mostly_remain_no_action`. The inherited metric defines distant positions relative to the primary target region [0.65, 0.75] for both teacher arms. It therefore counts the intended wrong-region action core (0.15–0.25) and adjacent 0.30 action as distant actions. The wrong-region arm had four contiguous actions from 0.15 through 0.30; this is the expected wrong-shifted response but fails the unchanged primary-target-anchored distant-position check. The target-teacher arm had no actions among its 12 target-distant positions.

No model or gate parameters were changed after seeing results. This is a deterministic engineering fixture and does not establish biological fly learning. The requested 120- then 144-block sequence is complete; no further run was started.

## Reproduction

- Frozen config: [`../configs/malecns_continuous_position_learning_v2_4.json`](../configs/malecns_continuous_position_learning_v2_4.json)
- Full result and all block curves: [`../runs/malecns_continuous_position_learning_v2_4/result.json`](../runs/malecns_continuous_position_learning_v2_4/result.json)
- Runner: [`../src/project_b/malecns_continuous_position_learning/experiment_v2_4.py`](../src/project_b/malecns_continuous_position_learning/experiment_v2_4.py)
- Config SHA-256: `67e6f526cc6a56d63a11a5945117bfb84908c434488934ff5bc7a9c5def62754`
