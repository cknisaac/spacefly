# MaleCNS Level 3B milestone and Level 4 authorization

**Recorded:** 2026-10-02  
**Level 3B classification:** **mechanistic success / strict behavioral gate incomplete**  
**Level 3B strict status:** **FAIL**, preserved under its original contract  
**Level 4 status:** **AUTHORIZED** within the scope below

This summary supplements the frozen Level 3B report. It does not revise the
underlying run receipt, its action maps, or its predeclared strict gate.

## Mechanistic success

The single frozen Level 3B run established the following mechanism-level
results:

- All three anatomy-selected PAM08 DANs (87177, 107285, 55210) were activated
  by the scheduled external teaching stimulation.
- KC→MBON05 updates were gated by current-presentation KC eligibility and
  activity from at least one anatomically connected member of the ensemble;
  all recorded updates were inside the union anatomy mask.
- Teaching reduced MBON05 responses in the taught regions. Target-region
  learning produced actions at 0.70 and 0.75; wrong-region teaching produced
  actions at 0.15, 0.20, 0.25, and 0.30, shifting the response toward the
  wrong taught region.
- The matched DAN-on/plasticity-off control changed no weights and remained
  no-action across the position grid.
- Learned actions were present in frozen evaluation with teacher stimulation
  and plasticity disabled: wrong-region retention passed; target learned
  positions 0.70 and 0.75 persisted.
- No external trained decoder was used. The inherited fixed threshold and
  readout were used.

These results support the stated mechanistic classification for this reduced
model. They do not establish complete biological sufficiency of the ensemble
or a complete fly-brain learning mechanism.

## Strict gate result

The target core was **2/3**: positions 0.70 and 0.75 acted; 0.65 did not.
Therefore `target_core_3_of_3` and the associated strict target-retention gate
remain **FAIL**. Overall Level 3B remains a recorded strict **FAIL**. The
mechanistic classification does not convert that gate to PASS.

The Level 3B threshold, η, training duration, encoder, DAN set, circuit,
eligibility, floor, and readout are frozen. Do not tune Level 3B to force 3/3.
Reopen Level 3B only if a later result identifies a genuine blocker to the
next authorized stage.

## Level 4 authorization

Level 4 is authorized to replace static position presentations with **one
moving note**, represented using **current position only**. Keep the Level 3B
learning mechanism and fixed action threshold/readout. In particular, the
moving-note input must not expose future position, time-to-contact, target
key, desired action time, or held-out outcome information.

Before executing the Level 4 experiment, freeze and record the trajectory,
movement timing, presentation and teaching schedule, evaluation grid or
trajectory probes, controls, and pass criteria. These details are not
specified by the authorization and must not be selected after viewing
outcomes. Carry forward the anatomy-gated eligibility/LTD mechanism and the
frozen Level 3B parameters; any change needed to make one moving note
representable must be separately identified and justified before a run.

At the time this milestone summary was first recorded, Level 4 had not yet
been run. The authorized protocol was subsequently frozen and run once; its
**FAIL** and the zero-KC-spike temporal-drive blocker are recorded in the
[Level 4 result report](MALECNS_LEVEL4_MOVING_NOTE_RESULT.md). Level 3B remains
frozen and its strict FAIL is unchanged.

## Source records

- [Frozen Level 3B report](MALECNS_DAN_BRIDGE_LEVEL3B_ENSEMBLE.md)
- [Level 3B configuration](../configs/malecns_dan_bridge_level3b_ensemble.json)
- [Level 3B training receipt](../runs/malecns_dan_bridge_level3b/result.json)
- [Level 3B capacity receipt](../runs/malecns_dan_bridge_level3b/capacity.json)
