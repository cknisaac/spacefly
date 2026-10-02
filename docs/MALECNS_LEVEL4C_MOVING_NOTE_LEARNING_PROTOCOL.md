# MaleCNS Level 4C — moving-note learning protocol

**Protocol:** `MALECNS-LEVEL4C-MOVING-NOTE-LEARNING-v1`  
**Status:** frozen before the Level 4C training run

## Inherited system

Level 4C uses the frozen Level 4B output-validity rule and admitted 500-ms
trajectory. It holds fixed the x=1.0→0.0 current-position-only traversal, same
32 KCs, MBON05, Gaussian encoder, LIF/contact model, three PAM08 DANs
(87177, 107285, 55210), 0.005572335995331903-mV action threshold,
presentation-local eligibility, η=0.00005, 1,000,000-µs eligibility decay,
and 20% immutable original-weight floor.

At each note, output is disabled until that note's first KC spike. Starting at
that spike, the instantaneous MBON05 voltage is compared with the inherited
threshold. The first action is the earliest enabled 1-ms sample at or below
threshold. Position-map bins record whether any enabled sample in the bin
crossed threshold; pre-spike bins with no enabled samples are marked disabled.

## Frozen training schedule

The fixed duration is **120 blocks / 1,200 presentations per arm**, exactly the
inherited Level 3B schedule, with 600 target-class and 600 wrong-region-class
notes. No early stopping is allowed. Each presentation is a fresh 500-ms note;
updated weights first affect the next note.

| Arm | Scheduled event | Plasticity |
|---|---|---|
| Target teaching | Stimulate all three DANs when a target-class note reaches x=0.70 | On |
| Wrong-region teaching | Stimulate all three DANs when a wrong-region-class note reaches x=0.20 | On |
| Matched DAN-on control | Stimulate all three DANs when a target-class note reaches x=0.70 | Off |

Each external DAN pulse starts at the trajectory tick reaching the arm's
trigger position and uses the inherited 2.0-mV-equivalent, 20-ms pulse and
fresh-resting LIF DAN model. Updates require positive eligibility accumulated
from current-note KC spikes by the first spike of an anatomically connected
stimulated DAN. Eligibility resets at every note. The inherited LocalLTD rule
commits at note end and enforces the 20% floor against immutable run-start
weights.

## Evaluation and pass criteria

After training, each arm gets a fresh 500-ms note with DAN stimulation and
plasticity off, retaining its learned weights. The naive baseline is evaluated
the same way with initial weights. The primary measure is the first action's
position and time.

- Naive baseline has no first action.
- Target-trained first action lies in the target core `[0.65, 0.75]`.
- Wrong-region-trained first action lies in the wrong core `[0.15, 0.25]`.
- Matched DAN-on/plasticity-off retains initial weights and has no first action.
- Target and wrong first actions appear on frozen-weight evaluation with DAN/plasticity off.
- No training or evaluation note emits an action before its first KC spike.
- Every update has positive current-note eligibility and an active anatomically
  connected DAN; weights never fall below 20% of immutable original weights.
- All 120 blocks and 1,200 presentations complete in all arms.

The receipt records training KC spikes, all DAN spike times, per-presentation
first-action data, weight changes and full evolving weights. It also records
the complete MBON timecourse, KC spikes, first action, and position-action map
for each fresh post-training evaluation note.

## Stop rule

Run the three arms once at the frozen duration. Do not tune or rerun. Stop after
Level 4C; do not add osu timing scoring or biological downstream motor neurons.
