# MaleCNS Level 4D — final moving-note repair protocol

**Protocol:** `MALECNS-LEVEL4D-FINAL-MOVING-NOTE-REPAIR-v1`  
**Status:** frozen before the final Level 4 training run

Level 4D is the final infrastructure repair cycle. It preserves the recorded
Level 4C FAIL and changes only output-validity timing and the moving-note
eligibility locality window.

## Repair 1: MBON sensory validity

The prior receipt shows the first KC spike at 41 ms while MBON05 remains at
0 mV. The first nonzero MBON05 response is at 44 ms. Level 4D therefore keeps
output disabled until the first positive MBON05 sample, rather than enabling it
on the raw KC-spike tick. Once valid, it uses the unchanged Level 4B
maximum-voltage readout: for each inherited 0.05 position bin, action is true
only if the maximum voltage among valid samples in that bin is at or below the
inherited 0.005572335995331903-mV threshold. Bins with no valid samples remain
disabled. The first-action timestamp is the sample time when that bin's
maximum-voltage decision is complete.

This retains the prior frozen position-bin readout. Level 4C's per-sample
first-action measurement exposed the same-tick 0-mV artifact; Level 4D records
first action using the inherited bin maximum.

## Repair 2: eligibility locality

The frozen traversal moves 0.002 normalized position per millisecond. A
50,000-µs eligibility window therefore spans 0.10 position. The read-only
Level 4C spike receipt shows that, at the target and wrong DAN gates, the last
50 ms contain three unique KC spikes in each teaching note. A 25-ms window
contains only two and one, respectively; 75 ms includes spikes as far back as
x=0.808 for target teaching and x=0.324 for wrong teaching, outside the
corresponding inherited teaching halos. The single frozen choice is therefore
the last 50 ms before the first connected DAN spike.

Only current-note KC spikes with times in the inclusive interval
`[DAN spike time − 50 ms, DAN spike time]` contribute to eligibility. Earlier
spikes receive zero eligibility. Inside the window, the inherited 1,000-ms
exponential eligibility decay, LocalLTD formula, η, and immutable 20% floor
are unchanged. Eligibility still resets at every note.

## Fixed system and run

All other settings remain fixed: 500-ms x=1.0→0.0 traversal, same 32 KCs,
MBON05, Gaussian encoder, LIF/contact model, PAM08 DANs 87177/107285/55210,
0.005572335995331903-mV threshold, η=0.00005, and immutable original-weight
floor of 20%. The training duration is 120 blocks / 1,200 presentations per
arm, with no early stopping.

The three arms are target teaching at x=0.70, wrong-region teaching at x=0.20,
and a target-timed DAN-on/plasticity-off control. Each scheduled pulse starts
at the trigger crossing and retains the inherited 2.0-mV-equivalent, 20-ms DAN
stimulation. After training, each arm receives one fresh note with DAN and
plasticity off and its final weights retained.

## Frozen pass criteria

- Naive baseline has no first action.
- Target first action lies in `[0.65, 0.75]` and persists with DAN/plasticity off.
- Wrong-region first action lies in `[0.15, 0.25]` and persists with DAN/plasticity off.
- Matched DAN-on/plasticity-off weights remain unchanged and produce no first action.
- Output validity opens only after nonzero MBON05 sensory response; no action
  occurs before validity.
- Every weight update has positive current-note eligibility inside the 50-ms
  window and an active anatomically connected DAN.
- Every weight remains at least 20% of its immutable original value.
- All 120 blocks / 1,200 presentations complete in every arm.

Run the three arms once. Do not tune or rerun. Stop Level 4 after reporting
PASS or FAIL.
