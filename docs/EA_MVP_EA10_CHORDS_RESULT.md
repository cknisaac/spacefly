# EA-MVP EA-10 — simultaneous chord notes

**Decision: PASS within the declared two-chord scope.**

## Engineering assumption

**ENGINEERING ASSUMPTION:** the fixed readout fans the shared MBON05 timing response to every lane visible at that position on the current sample. This is needed because the admitted MBON path carries timing but has no tested independent lane outputs. Lane membership comes from the fixed current-lane selector; the synapses do not learn chord identity.

## Admission and game checks

The task-free admission probe passed for a single lane, two different lane pairs, and all four lanes. Each selected lane produced the same DOWN at 501 ms and UP at 511 ms. It used no game, feedback, or learning, left the retained weights unchanged, and replayed exactly.

The frozen headless map then presented two sequential equal-time two-note chords: lanes 0+1 at 500 ms and lanes 2+3 at 1,250 ms. With lane-0-trained retained weights, the policy emitted one DOWN per note lane at 501 ms and released at 511 ms; the second chord had the same 1-ms timing. All four notes were PERFECT. The matched initial-weight arm emitted no actions and missed all four. Each arm used one neural initialization, and the retained weights were unchanged during playback.

The frozen config restricts the claim to simultaneous notes with equal note times in sequential chords. The protocol and result are `configs/ea_mvp_chords_v1.json` and `runs/ea_mvp/chords_v1.json`; the separate admission protocol and result are `configs/ea_mvp_chord_admission_v1.json` and `runs/ea_mvp/chord_admission_v1.json`.

## Limits

This does not establish support for staggered overlapping notes, dense streams, simultaneous holds, or learned lane identity. The result is an engineered fanout around one learned timing signal. It leaves all strict biology results unchanged.
