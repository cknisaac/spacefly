# FD-2 — sensory mapping probe result and next assumption proposal

**Status: FAIL — stop before FD-3.** No training, game episode, or score-based selection was run.

## Frozen probe

The tested mapping was selected from playfield boundaries only:

- Normalize current rendered y to `p_screen = clamp((receptor_y - y) / playfield_height, 0, 1)`.
- Reverse orientation for the existing EA13 encoder: `p_EA13 = 1 - p_screen`.
- This mapping uses current screen position only. It does not read note IDs, target times, map schedules, judgements, or scores.
- Probe durations were the FD-1 measured 1,281 ms, 1,499 ms, and 1,786 ms visible approaches. These bracket the chart-renderer geometry; they were not selected by score.

## Result

Across the three frozen learning-on weight receipts (907, 1009, 1103), all three durations, and two exact repeats per condition, the circuit emitted **0/18 expected DOWN actions**. Every pair of repeats matched exactly. The matched untrained control was silent. Weights were unchanged.

The fixed EA13 readout therefore did not transfer from its learned 500-ms countdown to a full rendered screen trajectory under this simple boundary transform. **FD-2 is not admitted; FD-3 and chart playback were not run.** This is a frozen-policy/input-transfer failure, not a finding that the connectome or strict biology failed. Strict biology reports and the saved Pygame recreation are unchanged.

## Assumptions tested / not admitted

| ID | Candidate **ENGINEERING ASSUMPTION** | Why considered | Decision |
| --- | --- | --- | --- |
| FD2-A1 | Reverse normalized screen y into EA13 countdown with `1 - p_screen`. | Coordinate directions differ: screen y increases toward the receptor; EA13 countdown decreases toward contact. Boundary mapping adds no fitted parameter. | **Rejected by this probe** for the full 1.28–1.79 s approach: 0/18 actions. Do not silently keep it as admitted. |
| FD2-A2 | Crop renderer overdraw outside playfield `[0,1]`. | The existing observation schema accepts only normalized values in this interval; renderer margins produced out-of-range tuples. | Still needed, not independently admitted as a working multi-note policy. |
| FD2-A3 | Select only the currently nearest-to-receptor head; fan out exact-position ties to their current lanes; reconsider the remaining visible heads on later frames. | The current connectome-constrained timing circuit accepts one scalar position stream, not 14 separately tagged notes. | Proposed only. Requires task-free admission and explicit disclosure that farther heads are temporarily ignored. |
| FD2-A4 | Use the rendered distinction between tap heads, hold heads, and hold tails; keep at most two active hold key states and release on the visual tail reaching the strike line. | Head/tail tuples alone do not distinguish a tap head from a hold head when its tail is offscreen. | Proposed only. Requires a refreshed frame stream with visible hold identity from note shape. |
| FD2-A5 | Insert one 1-ms blank sample after the selected head crosses the receptor before selecting the next head. | Existing readout rearms on a blank-to-visible transition. | Proposed only; check for task-free rearm determinism. |

## Proposed next **ENGINEERING ASSUMPTION** for approval

Use a fixed visual time-to-contact estimator based only on the selected head’s current and recent past rendered positions. With `p_screen` increasing from the top of the playfield toward the receptor and `v_hat` the recent positive screen-position velocity:

`remaining_ms = (1 - p_screen) / v_hat`

`p_EA13 = clamp(remaining_ms / 500 ms, 0, 1)`

A fixed short velocity window (candidate: 50 ms, which spans about 19 px at the chart’s median screen travel and avoids single-pixel derivative noise) would convert a 1.3–1.8 s rendered approach into the existing final 500-ms EA13 countdown without reading future note time. A no-motion/velocity-floor rule must also be frozen. This is a new sensory engineering assumption; it is **not approved or frozen yet**.

If approved, the next work is only task-independent validation of that fixed estimator (blank/stationary input, constant-speed ramps, and abrupt speed changes; deterministic output and countdown boundedness). No chart score or action success may be used to tune its window or floor. Then run FD-3 using the frozen estimator; stop on failure.

## Reproducibility

Runner: `scripts/run_ea_mvp_fd2_sensory_probe.py`  
Machine receipt: `runs/ea_mvp/fd2_sensory_probe_v1.json`  
Source config SHA-256: `528ac42f04bd7f3e254ee187b32f2279fa337ce47a370eb364411b59ae87f870`
