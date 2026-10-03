# EA-MVP EA-7: continuous fixed-speed one-lane taps

**2026-10-03.** Engineering-assumption track only. Strict biology results and the saved osu! recreation remain unchanged.

## Fixed-speed confirmation scope

The user clarified that scroll speed is chosen before a map and stays fixed while notes fall. The frozen variable-speed EA-6 v2 result remains **FAIL** for the separate unseen-speed test. At the user's request, the fixed-speed confirmation was stopped after three complete seeds. An independent audit verified all receipts for those three seeds: learning-on scored 40/40 Good-or-better at the trained 500-ms approach, with DAN-off, plasticity-off and untrained controls at 0/40. The shuffled-teaching control also scored 40/40, so the result does not establish that the correct outcome-to-trial pairing matters. This is a **user-capped 3-of-8 check**, not a formal PASS under the original six-of-eight confirmation rule. The initial-weight perturbation across those repeats used the predeclared ±1% range.

## Continuous map v1 failure

The first continuous three-note prototype preserved one neural simulator across three separated lane-0 taps at the trained fixed speed. Its readout rearmed at each blank-to-visible transition, but its “first valid signal” rule accepted any MBON voltage above zero. Tiny residual voltage from the previous cue (about `4e-8 mV`) made an empty top-position bin qualify as an action. The learned arm pressed the first note correctly, then at `763000 µs` and `1513000 µs`, roughly 487 ms before the next targets. The matched initial-weight arm made the same two early presses. Weights stayed fixed; this was a readout gating defect. The failed receipt remains at `runs/ea_mvp/continuous_one_lane_v1.json`.

## Task-free rearm gate and continuous map v2

The declared **ENGINEERING ASSUMPTION** is now: after a blank-to-visible transition, wait for a KC spike from that new cue before starting that cue's fixed readout. The fly membrane state and synaptic weights remain continuous. In the frozen task-free probe, the learned policy emitted one DOWN at `501000 µs` in each of three identical position sweeps separated by blank intervals; the initial-weight control emitted none. All six checks and exact replays passed. Receipt: `runs/ea_mvp/readout_rearm_probe_v1.json`.

The corrected continuous game run then used three lane-0 taps at 500,000, 1,250,000 and 2,000,000 µs, each with a fixed 500-ms visible approach. The trained, retained weights emitted DOWN at 501,000, 1,251,000 and 2,001,000 µs, all PERFECT. The matched initial weights emitted no DOWN and received three MISSes. There was one neural initialization, three readout rearms, no extra actions, unchanged weights, post-result-only feedback and exact replay. **EA-7 continuous three-note fixed-speed admission: PASS.** Receipt: `runs/ea_mvp/continuous_one_lane_v2.json`.

## Scope and next stage

This demonstrates a three-note, one-lane, fixed-speed headless sequence with weights learned in isolated trials and neural state retained continuously during playback. It does not demonstrate online learning within a map, denser/overlapping notes, four lanes, chords, holds, or play in the actual osu!lazer client. A four-lane system needs a frozen lane-sensitive sensory and fixed motor mapping while retaining real source anatomy; the current 32-KC→MBON05 one-lane readout cannot distinguish four lanes. The next stage is a separately specified lane-mapping admission design, before four-lane training. A hold-note design follows that only if lane mapping passes.
