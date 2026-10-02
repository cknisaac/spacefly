# MaleCNS Level 4 — moving-note protocol

**Stage:** Level 4, moving note  
**Protocol status:** frozen before training  
**Level 3B status:** frozen at *mechanistic success / strict behavioral gate incomplete*; its strict result remains **FAIL**  
**Level 4 run status:** complete; see [the result report](MALECNS_LEVEL4_MOVING_NOTE_RESULT.md)

## Question

Can the frozen Level 3B learning mechanism acquire a localized action response
when a single note moves through the position axis and the encoder receives
only its current position?

## Why this is next

Level 3B showed DAN-gated, anatomy-limited KC→MBON learning under static
position presentations, with a strict target-core result of 2/3. Level 4
changes the stimulus to one moving note while preserving that learning
mechanism and fixed readout.

## Frozen intervention

- In every presentation, one note moves linearly from normalized position
  `x=1.0` to `x=0.0` over the inherited 100,000-µs observation window.
- At each inherited 1,000-µs integration tick, the unchanged Gaussian encoder
  receives only `x(t) = 1 - t / duration`. The schedule class is used only to
  schedule external teaching; it is never an encoder input.
- The position map records maximum MBON05 voltage within each inherited
  0.05-wide position bin along the trajectory. Action uses the inherited fixed
  threshold.
- The frozen schedule remains 120 blocks / 1,200 notes per arm, with the same
  200,000-µs trial spacing. The moving note is replayed from fresh resting
  neural state for each note, as in the inherited one-presentation model.
- Target-region teaching stimulates the frozen DAN ensemble on the 600 notes
  already labeled `target_region`, timed so the first DAN spike coincides with
  current position `0.70`. Wrong-region teaching uses the 600 existing
  `wrong_region_distractor` schedule entries and triggers at current position
  `0.20`. The matched control uses target-timed DAN stimulation with
  plasticity disabled. Other notes receive no teaching event.
- The inherited 2.0-mV-equivalent, 20,000-µs isolated DAN pulse is used. Its
  frozen latency is 14,000 µs, taken from the Level 3B pretraining receipt.
  The pulse begins 14,000 µs before the note crosses the teaching position.
- Eligibility resets for each moving note. Only KC spikes up to the first
  connected DAN spike can contribute to that note's update. The LTD update is
  committed at the end of the current note and affects subsequent notes.

## Fixed settings and controls

The Level 3B cohort (32 KCs), MBON05, PAM08 DAN ensemble (87177, 107285,
55210), strict γ4 anatomy mask, LIF/contact model, Gaussian encoder, eligibility
rule, η=`0.00005`, 20% immutable original-weight floor, 120-block schedule,
teacher pulse, action threshold, and readout are inherited unchanged. No
external trained decoder is used.

Arms:

1. Target teaching.
2. Wrong-region teaching.
3. Matched DAN-on/plasticity-off control.

Before training, the runner computes a moving-note capacity ceiling separately
for target and wrong regions by clamping every positive-eligibility,
anatomically reachable KC→MBON05 edge from that frozen moving-note trajectory
to its original 20% floor. Training proceeds only if each moving-note core
reaches 3/3 under that ceiling.

## Endpoints and pass criteria

Primary endpoint: after training and with teacher/plasticity OFF, the moving
note's binned position map reaches all three action bins in each arm's own
core: target `[0.65, 0.70, 0.75]`; wrong `[0.15, 0.20, 0.25]`.

The stage passes only if all of the following hold:

- The run completes 120 blocks / 1,200 notes in every arm; all 600 scheduled
  teaching events per arm activate all three DANs.
- Target and wrong actions meet their own 3/3 moving-note cores and remain
  within their inherited halos `[0.60, 0.80]` and `[0.10, 0.30]` (or at least
  90% of outside-halo bins are no-action).
- The matched DAN-on/plasticity-off control retains exactly baseline weights
  and the baseline moving map and remains no-action.
- Trained moving-note maps persist under frozen teacher/plasticity-off
  evaluation.
- Every update has positive eligibility for that note and a connected active
  DAN, falls within the ensemble's anatomical union mask, and respects the
  immutable 20% original-weight floor.
- The encoder, threshold, fixed readout, and inherited learning settings remain
  unchanged.

The full inherited static 21-position maps are reported as secondary endpoints.
The Level 3B strict FAIL remains preserved regardless of the Level 4 result.

## Stop rule

Run once. Do not early-stop, tune, rerun, change Level 3B parameters, or reopen
Level 3B unless the moving-note result reveals a genuine blocker. Report the
full position maps, learning curves, changed weights, floor hits, controls,
and predeclared gate result, then stop.

## Recorded outcome

The single run completed and **FAILed**. The moving-note capacity core count
was nominally 3/3, but the untrained baseline already acted at every position.
Across all arms the moving note elicited zero KC spikes, zero positive gate
eligibilities, and zero weight changes. The MBON voltage was 0 mV at all 21
moving bins, so baseline and plasticity-off also acted everywhere; locality
and no-action-control criteria failed. See the [result report](MALECNS_LEVEL4_MOVING_NOTE_RESULT.md)
and full JSON receipt. No tuning or rerun followed.

The task-free [Level 4A admission test](MALECNS_LEVEL4A_TEMPORAL_INPUT_ADMISSION_RESULT.md)
later found that 500 ms is the shortest predeclared duration that admits KC
spiking, meaningful MBON activity, a baseline that is not action everywhere,
and deterministic replay. The earlier 100-ms Level 4 failure remains intact.
The selected 500-ms speed is frozen in
[`malecns_level4_moving_note_admitted_500ms.json`](../configs/malecns_level4_moving_note_admitted_500ms.json).
No learning was run under Level 4A.

## Frozen artifacts

- [Level 4 config](../configs/malecns_level4_moving_note.json)
- [Level 4 runner](../src/project_b/malecns_continuous_position_learning/experiment_level4_moving_note.py)
- [Level 3B milestone classification](MALECNS_LEVEL3B_MILESTONE_AND_LEVEL4_AUTHORIZATION.md)

## Level 4B output-admission correction

The task-free Level 4B rerun added a fixed validity gate because the raw
inherited threshold labeled the zero-voltage startup bins as action before
sensory activity. Output is disabled until the first KC spike of each note;
from that spike onward the inherited MBON threshold is applied unchanged.
Level 4B passed on the frozen 500-ms note with 30 KC spikes, nonzero MBON
activity, no target/wrong-region baseline actions, and exact deterministic
replay. The rule is frozen in
[`malecns_level4_moving_note_500ms_readout_validity_v1.json`](../configs/malecns_level4_moving_note_500ms_readout_validity_v1.json).
No learning or DAN stimulation occurred. See the [Level 4B result](MALECNS_LEVEL4B_MOVING_OUTPUT_ADMISSION_RESULT.md).
