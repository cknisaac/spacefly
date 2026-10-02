# MaleCNS Level 4D — final moving-note repair result

**Date:** 2026-10-02  
**Protocol:** `MALECNS-LEVEL4D-FINAL-MOVING-NOTE-REPAIR-v1`  
**Result:** **FAIL** under the frozen strict target/wrong first-action contract

Level 4D was the final infrastructure repair cycle. It completed once and
Level 4 is stopped.

## Repairs and fixed settings

The output gate opened at the first positive MBON05 response, 44 ms into the
note, rather than on the raw first KC spike at 41 ms. The inherited Level 4B
position readout was used unchanged after validity opened: the maximum MBON05
voltage among valid samples in each 0.05-position bin, compared with the same
0.005572335995331903-mV threshold. The naive baseline and matched control then
had no action; x=0.95 and 1.00 remained disabled before the MBON response.

KC spikes received eligibility only if they occurred during the final **50 ms**
before the first active connected DAN spike. Earlier spikes received zero
credit. At 500 ms per traversal, that window spans 0.10 normalized position.
The inherited 1,000-ms exponential decay within the window, LTD rule, η,
original-weight floor, encoder, circuit, speed, threshold, and DAN ensemble
were unchanged.

## Frozen-duration run

All three arms completed **120 blocks / 1,200 presentations**. Each arm
delivered 600 scheduled pulses, and all three DANs spiked at every pulse.
Pulses began at the position crossing: 150 ms at x=0.70 and 400 ms at x=0.20;
the first DAN spike followed at 164 ms and 414 ms, respectively.

After training, the evaluation note used retained weights with DAN stimulation
and plasticity off:

| Evaluation | First action | Position map actions | Result |
|---|---|---|---|
| Naive baseline | None | None | PASS: no first action |
| Target teaching | None | None | **FAIL:** target first action was not acquired |
| Wrong-region teaching | 413 ms, x=0.20 | x=0.20 | PASS: first action in wrong core |
| DAN-on / plasticity-off | None | None | PASS: unchanged weights and no action |

The wrong-region action was read out at completion of its 0.05 bin `[0.175,
0.225]`, with maximum MBON05 voltage 0.004040828 mV. All non-action bins in
the four maps are no-action; x=0.95 and 1.00 are disabled because they have no
valid MBON samples. The full per-bin voltages/sample counts and timecourses
are in the JSON receipt.

## Learning and gate checks

| Arm | Weight changes | KC slots at immutable floor | DAN events | Behavior |
|---|---:|---:|---:|---|
| Target teaching | 1,506 | 2 | 600/600, all 3 DANs | No first action acquired |
| Wrong-region teaching | 1,432 | 2 | 600/600, all 3 DANs | First action at x=0.20 persists frozen |
| DAN-on / plasticity-off | 0 | 0 | 600/600, all 3 DANs | Weights unchanged; no action |

The receipt confirms that every update had positive current-note eligibility
inside the frozen 50-ms window and an active anatomically connected DAN; the
immutable 20% original-weight floor held throughout. No action occurred before
MBON05 output validity. All planned blocks and presentations completed.

## Strict criteria

| Criterion | Result |
|---|---|
| Naive baseline has no first action | PASS |
| Target first action in `[0.65, 0.75]`, retained frozen | FAIL; no action |
| Wrong-region first action in `[0.15, 0.25]`, retained frozen | PASS; x=0.20 |
| DAN-on / plasticity-off unchanged and action-free | PASS |
| Output waits for nonzero MBON05 sensory response | PASS |
| All updates stay inside local eligibility and anatomical gate | PASS |
| Immutable original-weight floor respected | PASS |
| Fixed 120-block duration and all DAN events complete | PASS |

The overall Level 4D result is **FAIL** because target teaching did not
produce the required first action. The wrong-region first action did localize
to its taught position, and the baseline/control gates now pass. No further
tuning, rerun, or parameter search was performed.

## Frozen artifacts

- [Level 4D protocol](MALECNS_LEVEL4D_FINAL_REPAIR_PROTOCOL.md)
- [Frozen config](../configs/malecns_level4d_final_moving_note_repair.json)
- [Complete result receipt](../runs/malecns_level4d_final_moving_note_repair/result.json)
- [Runner](../src/project_b/malecns_continuous_position_learning/experiment_level4d_final_moving_note_repair.py)

No osu timing scoring or biological downstream motor neurons were added. Level
4 is complete and stopped after this final run.
