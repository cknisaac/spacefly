# MaleCNS Level 4 — moving-note result

**Result:** **FAIL** under the frozen Level 4 contract  
**Run:** one run, 120 blocks / 1,200 moving-note presentations per arm  
**Capacity gate:** reported 3/3 in both cores, but not informative because the untrained moving baseline already produced action at all 21 positions  
**Level 3B:** remains frozen as **mechanistic success / strict behavioral gate incomplete**; its original strict result remains **FAIL**

## Frozen protocol

One note moved linearly from `x=1.0` to `x=0.0` over 100 ms. The unchanged
Gaussian encoder received the current `x(t)` on the existing 1-ms integration
grid. The existing 120-block / 1,200-presentation schedule was retained for
each arm; teacher timing used the schedule class but that class was never
passed to the encoder. Target teaching stimulated all three frozen PAM08 DANs
at `x=0.70` on 600 target-class notes; wrong-region teaching stimulated them
at `x=0.20` on 600 wrong-class notes. The matched control used target-timed
DAN stimulation with plasticity disabled.

The learning rule, per-note eligibility reset, connected-DAN anatomy gate,
η=`0.00005`, immutable 20% original-weight floor, fixed threshold
`0.005572335995331903`, KC cohort, MBON05, DAN ensemble, encoder, and readout
were inherited unchanged. Updates were committed at each note boundary using
eligibility at the scheduled DAN spike. No external trained decoder was used.

The protocol was frozen before this run in
[the Level 4 protocol](MALECNS_LEVEL4_MOVING_NOTE_PROTOCOL.md) and
[its config](../configs/malecns_level4_moving_note.json). Its moving-note
capacity gate was coded to require 3/3 in each teaching core before training.

## Results

The pre-run capacity computation returned 3/3 for both cores. Inspection shows
why that number was not evidence of learned capacity: the untrained moving
baseline already had zero MBON voltage and action at **all 21 positions**.
Clamping eligible edges to the floor could not improve on that all-action
baseline. The capacity step did not include a baseline no-action gate; this is
a limitation of the frozen Level 4 protocol and is reported without changing
the run or its criteria.

During the single training run:

- All arms completed 120 blocks / 1,200 presentations.
- All 600 scheduled DAN events in each arm activated all three DANs.
- The moving-note input caused **zero KC spikes** across all 3,600 notes.
- No presentation had positive eligibility at its teaching gate, so **no KC→MBON weight changed** in the target, wrong-region, or matched control arm. No weight reached the LTD floor.
- With weights unchanged, the inherited static 21-position map stayed at its baseline and remained no-action everywhere.
- The moving-note map was 0.000000 mV at every position in every arm. Since the fixed rule defines action as MBON voltage ≤ threshold, this was action at all 21 positions, including the untrained baseline and plasticity-off control.

### Final moving-note position → MBON/action map

The same map was measured for target teaching, wrong-region teaching,
plasticity-off control, and the untrained baseline:

| Position bins | MBON05 max voltage | Action |
|---|---:|---|
| 0.00, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.00 | 0.000000 mV at every bin | ACTION at every bin |

Thus both moving-note cores are nominally 3/3, but the result is not learning:
the control and baseline have the same actions and there are no weight updates.
The target and wrong-region outside-halo locality checks fail because every
position is an action. The matched plasticity-off no-action gate also fails.

### Inherited static position map

Because no weights changed, all three arms retain this same fixed static
position map. Every position is no-action under the inherited threshold.

| Position | MBON05 max voltage (mV) | Action |
|---:|---:|---|
| 0.00 | 0.008010579 | no-action |
| 0.05 | 0.014215610 | no-action |
| 0.10 | 0.015860566 | no-action |
| 0.15 | 0.015056665 | no-action |
| 0.20 | 0.009310005 | no-action |
| 0.25 | 0.011181216 | no-action |
| 0.30 | 0.009622703 | no-action |
| 0.35 | 0.009945537 | no-action |
| 0.40 | 0.016840031 | no-action |
| 0.45 | 0.011751978 | no-action |
| 0.50 | 0.014575051 | no-action |
| 0.55 | 0.015085034 | no-action |
| 0.60 | 0.016351110 | no-action |
| 0.65 | 0.011371990 | no-action |
| 0.70 | 0.013596590 | no-action |
| 0.75 | 0.012864267 | no-action |
| 0.80 | 0.013536520 | no-action |
| 0.85 | 0.015670464 | no-action |
| 0.90 | 0.013665335 | no-action |
| 0.95 | 0.016772147 | no-action |
| 1.00 | 0.008940782 | no-action |

## Frozen gate

| Criterion | Result |
|---|---|
| 120 blocks / 1,200 presentations per arm | PASS |
| 600 scheduled teaching events per arm activate all three DANs | PASS |
| Moving-note target and wrong cores 3/3 | PASS nominally; baseline/control also action at all 21 bins |
| Target and wrong responses local to their own halos | FAIL |
| Matched DAN-on/plasticity-off weights and moving map unchanged | PASS |
| Matched control remains no-action | FAIL |
| Trained maps persist with teacher/plasticity OFF | PASS trivially; weights never changed |
| Updates require positive presentation-local eligibility and connected active DAN | PASS; no update was attempted because eligibility was zero |
| Updates stay within anatomy mask and immutable floor | PASS; no weights changed |
| Fixed encoder, threshold, and readout | PASS |

Overall Level 4 status is **FAIL**. The specific blocker is temporal drive:
with the frozen Gaussian peak drive and a 1.0-to-0.0 sweep over 100 ms, the
selected KCs did not spike. The MBON then remained at zero, which the inherited
low-voltage action rule interpreted as action everywhere. This run does not
justify a change to Level 3B and Level 3B has not been reopened.

## Receipts and verification

- [Frozen config](../configs/malecns_level4_moving_note.json), SHA-256
  `8487538edf132f68f1df5570ed465c28c3079ea28b08d4be09918a53bad52f7c`
- [Full run receipt](../runs/malecns_level4_moving_note/result.json), SHA-256
  `a54e2473c8bd2c92596478d0a90aa15b210ba13090a3c6b4d9f92c5b30225754`
- [Runner](../src/project_b/malecns_continuous_position_learning/experiment_level4_moving_note.py)
- Focused Level 4 tests: **3 passed**; module/test compilation passed.
- No rerun, tuning, or Level 3B changes followed.
