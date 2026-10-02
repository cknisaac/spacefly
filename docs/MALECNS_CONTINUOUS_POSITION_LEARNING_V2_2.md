# MaleCNS continuous-position learning — Level 2 v2.2

**2026-10-02 · MALECNS-CONTINUOUS-POSITION-LEARNING-v2.2 · FAIL.** This was one predeclared continuation of v2.1. The only model/protocol parameter changed was training duration, from 32 to 96 blocks. All three arms ran all 96 blocks (960 presentations each), with no early stopping. The inherited action threshold, encoder, circuit, readout, learning rule, η, floor, regions and presentation-local eligibility stayed fixed. No post-result tuning or repeat run was done.

## Frozen settings and run completion

The run kept the same 32 selected KCs and MBON05 source ID 10495, 685 audited plastic contact rows, Gaussian current-position encoder, contact-normalized initialization, LIF model, presentation-local eligibility, η = 0.00005, 20% initial-weight floor, target region [0.65, 0.75], wrong region [0.15, 0.25], and inherited fixed threshold **0.005572335995331903 mV-equivalent**. The v2.1 block schedule was repeated exactly three times to form the 96-block schedule. Configuration validation confirmed all non-duration v2.1 settings were identical before training.

| Arm | Blocks / presentations | Teacher pulses | Changed weights | Weights reaching floor |
|---|---:|---:|---:|---|
| Target teacher | 96 / 960 | 480 | 6/32 | 49544, 49545 |
| Plasticity off | 96 / 960 | 0 | 0/32 | none |
| Wrong-region teacher | 96 / 960 | 480 | 6/32 | 45467, 45950 |

The target-teacher arm first reached the floor at block 63; two KC weights (source IDs 49544 and 49545) were at the floor by block 96. The wrong-region teacher arm first reached the floor at block 49; source IDs 45467 and 45950 were at the floor by block 96. No plasticity-off weights changed or reached the floor.

## Learning curves

The full 96-point/block curves for each arm, including target and wrong-region means, action counts, full-grid action counts, and floor IDs at every block, are saved in the result JSON. This table samples every 12 blocks for readability. Action counts are measured on each 3-position core.

| Block | Target arm target mean (mV) | Target actions / 3 | Wrong arm wrong mean (mV) | Wrong actions / 3 | Full-grid actions: target / off / wrong | Target floor count | Wrong floor count |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.012516468 | 0/3 | 0.011759337 | 0/3 | 0 / 0 / 0 | 0 | 0 |
| 12 | 0.011478914 | 0/3 | 0.010798258 | 0/3 | 0 / 0 / 0 | 0 | 0 |
| 24 | 0.010357331 | 0/3 | 0.009812122 | 0/3 | 0 / 0 / 0 | 0 | 0 |
| 36 | 0.009241549 | 0/3 | 0.008909661 | 0/3 | 0 / 0 / 0 | 0 | 0 |
| 48 | 0.008128370 | 0/3 | 0.008007201 | 0/3 | 0 / 0 / 0 | 0 | 0 |
| 60 | 0.007025164 | 1/3 | 0.007104740 | 1/3 | 1 / 0 / 1 | 0 | 1 |
| 72 | 0.005960136 | 1/3 | 0.006301234 | 1/3 | 1 / 0 / 1 | 1 | 1 |
| 84 | 0.005099562 | 1/3 | 0.005502774 | 1/3 | 1 / 0 / 1 | 1 | 2 |
| 96 | 0.004357212 | 1/3 | 0.004707316 | 2/3 | 1 / 0 / 2 | 2 | 2 |

The target arm’s target-core mean fell from 0.012516468 mV after block 1 to 0.004357212 mV after block 96. At block 96 it produced one action, at position 0.70. Wrong-region teaching produced two actions at 0.15 and 0.20, but did not reach the required full three-position core.

## Final full position → MBON05 / action maps

Each cell is `MBON05 max voltage in mV / action`. “Yes” means voltage ≤ the frozen threshold; “No” means above it. Evaluation used teacher and plasticity OFF.

| Position | Target teacher | Plasticity off | Wrong-region teacher |
|---:|---:|---:|---:|
| 0.00 | 0.008010579 / No | 0.008010579 / No | 0.008010579 / No |
| 0.05 | 0.014215610 / No | 0.014215610 / No | 0.014215610 / No |
| 0.10 | 0.015860566 / No | 0.015860566 / No | 0.013053061 / No |
| 0.15 | 0.015056665 / No | 0.015056665 / No | 0.005549213 / Yes |
| 0.20 | 0.009310005 / No | 0.009310005 / No | 0.002988830 / Yes |
| 0.25 | 0.011181216 / No | 0.011181216 / No | 0.005583903 / No |
| 0.30 | 0.009622703 / No | 0.009622703 / No | 0.005719845 / No |
| 0.35 | 0.009945537 / No | 0.009945537 / No | 0.009945537 / No |
| 0.40 | 0.016840031 / No | 0.016840031 / No | 0.016840031 / No |
| 0.45 | 0.011751978 / No | 0.011751978 / No | 0.011751978 / No |
| 0.50 | 0.014575051 / No | 0.014575051 / No | 0.014575051 / No |
| 0.55 | 0.015085034 / No | 0.015085034 / No | 0.015085034 / No |
| 0.60 | 0.013441528 / No | 0.016351110 / No | 0.016351110 / No |
| 0.65 | 0.005666785 / No | 0.011371990 / No | 0.011371990 / No |
| 0.70 | 0.001780807 / Yes | 0.013596590 / No | 0.013596590 / No |
| 0.75 | 0.005624045 / No | 0.012864267 / No | 0.012864267 / No |
| 0.80 | 0.012043322 / No | 0.013536520 / No | 0.013536520 / No |
| 0.85 | 0.015670464 / No | 0.015670464 / No | 0.015670464 / No |
| 0.90 | 0.013665335 / No | 0.013665335 / No | 0.013665335 / No |
| 0.95 | 0.016772147 / No | 0.016772147 / No | 0.016772147 / No |
| 1.00 | 0.008940782 / No | 0.008940782 / No | 0.008940782 / No |

## Decision

**FAIL.** The frozen pass criteria were not met:

- PASS — all 96 blocks and 960 presentations run in every arm.
- FAIL — target teaching creates action core at 0 65 to 0 75.
- FAIL — wrong region teaching creates action core at 0 15 to 0 25.
- PASS — wrong region teaching shifts away from target core.
- PASS — plasticity off weights and map are unchanged.
- FAIL — distant positions mostly remain no action.
- FAIL — target learned region persists frozen.
- FAIL — wrong region learned region persists frozen.
- PASS — inherited threshold is fixed on all evaluations.
- PASS — encoder and fixed readout preserved.

Target teaching reached the threshold only at 0.70, so the full [0.65, 0.75] core did not become an action region. Wrong-region teaching made actions at 0.15 and 0.20, while 0.25 remained no-action. The two resulting wrong-region actions are within the 12 positions the distant-position rule classifies as distant from the target; consequently only 10/12 distant positions remained no-action, below the predeclared 90% requirement. Frozen evaluation preserved these maps, but persistence could not pass because neither learned core was complete. Plasticity-off remained exactly at baseline.

Fixed threshold, encoder and readout checks passed. This is a failed gate for this frozen engineering fixture, not evidence against fly biology. No parameter was changed after seeing the result, and the run stops here as requested.

## Reproduction artifacts

- Frozen v2.2 config and 96-block schedule: [`../configs/malecns_continuous_position_learning_v2_2.json`](../configs/malecns_continuous_position_learning_v2_2.json)
- Full result, all 2,880 presentations, all block curves, floor records and final maps: [`../runs/malecns_continuous_position_learning_v2_2/result.json`](../runs/malecns_continuous_position_learning_v2_2/result.json)
- Runner: [`../src/project_b/malecns_continuous_position_learning/experiment_v2_2.py`](../src/project_b/malecns_continuous_position_learning/experiment_v2_2.py)
- Frozen-protocol tests: [`../tests/test_malecns_continuous_position_learning_v2_2.py`](../tests/test_malecns_continuous_position_learning_v2_2.py)
- Config SHA-256: `35961763f3fce3967df4d24c957abd029e2a947262a81da7c07457d771138882`
