# One-lane lazer MVP L0.4 capacity result

**Stage:** L0.4 — causal capacity  
**Status:** **PASS for engineering controllability only**  
**Run:** one predeclared four-condition panel, each condition replayed twice  
**Training/teaching:** none

## Frozen inputs

- Capacity contract: [`configs/lazer_mvp_capacity.json`](../configs/lazer_mvp_capacity.json), SHA-256 `21343a6546ce921a2592c0d2d49553ba3ff8d028c9b7c0a21ca1c521bd910a7f`.
- Position/neural configuration: `configs/malecns_continuous_position_learning_v2_5.json`, SHA-256 `528ac42f04bd7f3e254ee187b32f2279fa337ce47a370eb364411b59ae87f870`.
- Game profile: `configs/lazer_mvp.yaml`, SHA-256 `eb49541eb9306adb9c19076d4eafc4f5df8dc351d90e1219ff21442ed966b0c8`.
- One lane-0 tap note at 500,000 µs; visible position moves linearly from 1.0 to 0.0; neural tick is 1,000 µs; no mods; lazer OD8 profile.
- Initial weights are contact-row fractions. The target intervention sets only five predeclared KCs in the Good-window position region to 20% of original. The matched control sets five position-distant KCs to the same floor. Each vector remains fixed for the note.

## Results

| Condition | First DOWN | Judgement | Outcome |
|---|---:|---|---|
| Initial-weight baseline | None | Automatic MISS | 0 DOWN / 0 UP |
| Plasticity-off control | None | Automatic MISS | 0 DOWN / 0 UP; exactly matches baseline |
| Good-window KC floor | 488,000 µs (−12,000 µs) | PERFECT (305 base accuracy) | 1 DOWN / 1 UP |
| Matched out-of-window KC floor | 163,000 µs (−337,000 µs) | Automatic MISS after a null press | 1 DOWN / 1 UP |

All four conditions replayed exactly. The target intervention first acted in
position bin 0.05, within the pinned ±73.5-ms Good window. The out-of-window
press occurred before the early Miss window, so it was a `NULL_PRESS`; the
note later expired automatically. The baseline MBON-valid gate opened at
44,000 µs in every condition.

All frozen criteria passed. Full result receipt:
`runs/lazer_mvp_capacity/result.json`, SHA-256
`7ec737260c1bd98492e8e05e1a1b0cfe14996d9b1ab1c41b6cd2e926de78cc96`.

## Interpretation and limit

The selected model and fixed readout can place a key-down in the actual lazer
Good window when the target-local weights are directly set to the existing
20% LTD floor. This is a task-free maximum-change controllability result. It
does **not** show that a fly can learn this weight pattern, that a biological
teacher would produce it, or that the MBON-to-key overlay is a measured motor
pathway. Level 4D remains frozen at its prior FAIL; this result does not
change or re-score its training outcome.

## Stop and next proposal

No further experiment was run. The next proposed gate is to specify and test
an outcome-event contract for early judged presses, late judged presses,
too-early null presses, and no-press expiries. It must preserve the time when
each outcome becomes observable and must not change weights or train. A
biological interpretation of those labels remains a separate evidence gap.
