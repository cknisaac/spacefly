# EA-MVP EA-5 v2: repeated-note learning and retention

**2026-10-03.** Separate **ENGINEERING ASSUMPTION** branch only. Strict biology results and the saved playable recreation remain untouched. The v1 failure remains recorded in [EA-4/EA-5 v1 result](EA_MVP_EA4_EA5_RESULT.md).

## Frozen revision

The no-game `EA-MVP-EA5.1-TEMPORAL-CREDIT-v1` protocol predeclared eligibility windows of 150, 250 and 500 ms and chose the shortest window that admitted at least three audited KCs and let their bounded local weight intervention cause a first DOWN during a position-only traversal. The 150-ms arm admitted one KC and no DOWN; 250 ms admitted seven KCs and a DOWN; 500 ms admitted 23 KCs and a DOWN. Exact replays passed. **250 ms** was selected under that rule, then frozen as EA-06 v2 before development. This is an **ENGINEERING ASSUMPTION** for temporal credit assignment, selected without a game, note judgement or task score.

The game-label→DAN adapter, source graph, fixed encoder/readout, LTD rate, weight floor and one-lane game stayed at their earlier values. The v2 development protocol froze 500 repeated isolated notes and checkpoints 0/100/250/500 before the run.

## Development outcome

| Arm | First DOWN acquired | Good-or-better first DOWN across 500 trials | Final first-DOWN error | Changed fly synapses |
| --- | ---: | ---: | ---: | ---: |
| Learning on | Trial 364 | 137/500 | +1 ms, PERFECT | 7 audited KC→MBON05 slots |
| DAN off | Never | 0/500 | None | 0 |
| Plasticity off | Never | 0/500 | None | 0 |

After acquisition, all remaining 137 repeated-note trials had a Good-or-better first DOWN. A separate frozen-weight check with teaching/plasticity off retained a +1-ms PERFECT press when the same 500-ms visual approach was shifted to note times 500, 750 and 1000 ms. The retained weight vector was unchanged by those checks. Development receipt: `runs/ea_mvp/development_v2.json`, SHA-256 `2f559f0f351fdbef31662b704833f9176124fc88546f0dd0468bbd3f157d40ab`.

**EA-5 v2 PASS for repeated-note acquisition and retention, within its development scope.** This does not yet satisfy the predeclared EA-6 confirmation criterion or establish generalization to different note speeds, four lanes, holds or live osu!lazer.

## Exposed generalization risk

In a separate exploratory frozen-weight check, varying only the visible lead time produced: 400 ms → an early first DOWN at −349 ms and MISS; 450 ms → no DOWN and MISS; 500/550/600 ms → +1 ms and PERFECT. These exploratory cases are **not** confirmation and were not used to select a parameter. They show a concrete dependence on the training approach speed. The next confirmation protocol must include unseen lead times and report failures; it must not describe time-shifted copies of the 500-ms approach as evidence of speed generalization.

## Next stage

Predeclare a meaningful confirmation split with unseen lead times, independent initial conditions, 40 fresh notes per run, all specified controls, and frozen policy evaluation. Because the exploratory speed check failed at 400/450 ms, the current candidate may fail the existing 6-of-8, ≥80% first-DOWN gate. Preserve that result if so. A revised speed-robust learner would need a separately frozen engineering assumption and development run; do not tune the v2 assumptions on confirmation outcomes.
