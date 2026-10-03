# FD-2 — visual time-to-contact probe result

**Status: FAIL — stop before FD-3.** The visual estimator is task-free and deterministic, but its fixed EA13 policy gate did not pass across pre-map speed settings. No training, game episode, or score-based tuning was run.

## Frozen setup

The approved **ENGINEERING ASSUMPTION** used recent visual motion to estimate contact time:

- `v_hat = (p[t] - p[t - 50 ms]) / 50 ms`
- `estimated_time_to_contact = (1 - p[t]) / v_hat`
- map that estimate to EA13's existing 500-ms input range.
- Return blank when the previous 50 ms contain no positive motion.

The encoder used only current and past visible positions. Speed factors (0.5×, 0.75×, 1.0×, 1.25×, 1.5×) were pre-map geometry controls around the recreation's current median 1.499-s approach. They were not selected by game performance. The unchanged learning-on weights for seeds 907, 1009, and 1103 were tested twice per factor; no learning occurred.

## Results

- Stationary visual input stayed blank; countdown values stayed bounded in `[0,1]`; all five constant-speed ramps ended at zero countdown.
- Pixel quantization made the estimate non-monotonic at individual 1-ms frames (maximum positive countdown step 0.10 at 0.5×). Maximum constant-speed time-to-contact deviation in the final 500 ms ranged from 13 to 32 ms.
- Frozen-policy gate (one DOWN within the inherited ±73.5-ms first-action window; one UP 10 ms later; exact repeats):

| Pre-map speed factor | Trained-weight result | DOWN timing relative to contact |
| --- | --- | --- |
| 0.5× | 0/6 trials passed | All six pressed 517 ms early |
| 0.75× | 6/6 passed | 1 ms late |
| 1.0× | 6/6 passed | 59 ms early |
| 1.25× | 0/6 passed | All six pressed 474 ms early |
| 1.5× | 2/6 passed | Four silent; two pressed 1 ms late |

The untrained control stayed silent. Repeats were exact and weights did not change. The circuit passes at two tested speeds but fails overall; the frozen readout responds to the long saturated `countdown=1` portion before the final 500-ms cue.

**Abrupt-speed-change control is INCONCLUSIVE:** its test trajectory had a position discontinuity at the speed switch for three of four combinations. Preserve its raw values, but do not interpret those cells or use them to set parameters. No corrected repeat was run.

## Decision and proposed next assumption

FD-2 **fails the predeclared fixed-policy admission gate**. This is an engineering input/readout transfer failure, not a strict biology result. FD-3, full-chart playback, lazer replay, and replay-view construction remain stopped.

Proposed additional **ENGINEERING ASSUMPTION**: when estimated time-to-contact is greater than 500 ms, provide **blank input** to the fly; start the cue at countdown 1 only when the estimate enters the existing 500-ms training horizon. This would remove the long saturated plateau associated with early key presses and matches the existing EA13 cue-onset contract. It has not been tested or admitted. The abrupt-speed test generator also needs a correction before that control can be used.

Per your stop rule, I need your approval before changing the encoder to add that 500-ms blank-to-visible gate and running the corrected task-independent checks. I will not continue into FD-3 until the encoder passes.

## Reproducibility

- Frozen protocol: `configs/ea_mvp_fd2_ttc_validation_v1.json`
- Runner: `scripts/run_ea_mvp_fd2_ttc_validation.py`
- Raw receipt: `runs/ea_mvp/fd2_ttc_validation_v1.json`
- Source config SHA-256: `528ac42f04bd7f3e254ee187b32f2279fa337ce47a370eb364411b59ae87f870`
