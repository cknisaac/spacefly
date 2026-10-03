# EA-MVP EA-6 v2 confirmation — FAIL

**2026-10-03.** This is an **ENGINEERING ASSUMPTION** result for the separate MaleCNS-constrained learner branch. The strict biology results and saved playable osu! recreation were not changed. The prior EA-5 v2 repeated-note development PASS remains valid only within its narrow scope.

## Frozen question and protocol

Could the retained KC→MBON05 weights learned from one standardized 500-ms approach produce a Good-or-better **first** key press on 40 fresh isolated notes with unique, unseen visible leads from 380 to 614 ms? The [EA-6 v2 protocol](../configs/ea_mvp_confirmation_v2.json) was frozen before the run, pinning 46 code files, source/teacher checksums, eight independent ±1% seeded contact-efficacy initializations, 500 training trials, five matched arms, the 40-note sequence and the existing ≥32/40, ≥8/40 control-margin, ≥6/8-run gate. The ±1% efficacy perturbation is an **ENGINEERING ASSUMPTION** for bounded unmeasured electrical scale, not biological variability established by data. Every arm within a seed started from the same vector.

The five arms were learning on, DAN off, plasticity off, shuffled teaching, and untrained. The shuffled control rotated observable judgement labels by 250 trials and delivered each reassigned label only when the current trial's real outcome became available. It is an offline negative control, not a physiological route or a candidate policy. Every fresh evaluation used frozen weights with DAN teaching and plasticity off.

## Result

| Arm | Fresh Good-or-better first DOWN, each of 8 seeds | Changed selected weights |
| --- | ---: | ---: |
| Learning on | **13/40** | 7 KC→MBON05 slots |
| Shuffled teaching | **13/40** | 7 KC→MBON05 slots |
| DAN off | 0/40 | 0 |
| Plasticity off | 0/40 | 0 |
| Untrained | 0/40 | 0 |

**0/8 runs passed** the predeclared behavioral gate, versus the required 6/8. Learning-on fell below 32/40 in every run and had a zero-point margin over shuffled teaching, versus the required eight-note margin. Its repeated training note still acquired a first press (seed 101 at trial 371), so the failure is in speed transfer and outcome-pairing specificity, not an absence of any local weight change.

The readout accumulates a maximum MBON voltage within each 0.05-position bin and emits on the first bin whose maximum is below its fixed threshold. A different approach speed changes how long the fixed neural dynamics are driven within a bin. For one frozen trained policy, 450-ms lead left the last bin above threshold and yielded no press; 500 ms pressed +1 ms, while 600 ms crossed an earlier bin and pressed −74 ms. In seed 101, fresh leads 500–572 ms were the only 13 Good-or-better cases; 380–494 and 578–614 ms failed. These values are diagnosis, not a parameter-selection sweep.

## Integrity audit and decision

The run's own checks reported source/code pins, exact fresh-evaluation replay, local-update integrity and unchanged DAN-off/plasticity-off/untrained weights. A separate auditor recomputed every first DOWN from raw actions, checked all 40 per-arm receipts against the frozen sequence and receipt hashes, checked weight continuity and logged local updates, and found **zero violations**. [Summary receipt](../runs/ea_mvp/confirmation_v2/summary.json) SHA-256 `9419d9671464af8ea8374fce2f39b4490abd66fc0228cac084faece4b558e2c3`; [independent audit](../runs/ea_mvp/confirmation_v2/independent_audit.json) SHA-256 `2a0b473fe6cb0c514cf95c65290b5d8e98d1426c398e41db526946dcb4ae0cc2`.

**EA-6 v2 FAIL.** The strongest supported statement is that local changes in seven source-identified fly synapses acquired a press for a repeated 500-ms note under disclosed engineering assumptions. This candidate did not demonstrate robust unseen-speed first-press learning or an advantage over shuffled outcome pairing. No four-lane, hold, Freedom Dive, live-lazer, or biological learning claim follows.

## Exactly one next stage

EA-6.1: test **mixed-speed training under the unchanged current-position-only encoder and fixed readout**. Freeze a curriculum from a declared environment coverage range, not from optimization of this confirmation score; use a task-free neural controllability preflight across that range. Correct the absolute-game versus trial-relative neural clock conversion before any variable-speed teaching and verify it with offset-equivalent fixtures. Then run a bounded development experiment, retaining this EA-6 v2 FAIL and reserving a new untouched speed/seed split for any later confirmation. If mixed-speed training fails, a causal speed-normalized sensory encoder would be a separately named **ENGINEERING ASSUMPTION** and would change the input claim to position plus recent motion.
