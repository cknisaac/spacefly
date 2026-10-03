# FD-2 fixed-speed visual input follow-up

**Status: fixed-speed policy gate PASS with a monotone TTC input assumption.** The earlier FD-2 v1/v2 failures remain preserved. No learning, training, game score, or chart score was used.

## What was tested

The frozen EA13 weights for seeds 907, 1009, and 1103 were replayed twice at five constant pre-map speed factors (0.5×, 0.75×, 1.0×, 1.25×, 1.5×). Each speed run used a fresh 50-ms visual TTC estimator. These are fixed-speed-per-map runs; the estimate and policy received only present/past visual position and the resulting countdown.

## Versioned results

| Follow-up | Outcome | Finding |
| --- | --- | --- |
| Corrected TTC geometry controls, protocol v2 | **FAIL** | Constant-speed geometry passed; two abrupt within-note speed changes exceeded the 55-ms TTC bound. The user's map contract keeps speed fixed within a map, so this is a recorded unsupported case. |
| Fixed-speed policy, no cue latch/filter | **FAIL** | Policy timing varied across pre-map speeds; frozen weights still did not change. |
| Latched cue | **FAIL** | Keeping the cue active after first crossing did not by itself make all speeds pass. Preserved unchanged. |
| Latched cue + monotone countdown | **PASS** | All 30 learning-on seed/speed/repeat traces produced one lane-0 DOWN at **+1 ms** from contact and one UP exactly 10 ms later. Repeats matched exactly. The untrained control was silent. Weights stayed unchanged. |

The final assumption is **ENGINEERING ASSUMPTION FD2-A8**: for a constant-speed approach, latch cue activation until the note disappears; while active, clip upward quantization bumps in estimated countdown with `q[t] = min(q[t-1], q_raw[t])`, holding the previous estimate across invalid/no-motion samples. This encodes the task-independent expectation that remaining time should not increase while the note approaches the receptor. It does not estimate note identity, use future chart timing, or modify the fly circuit.

## Interpretation and limits

This admits the fixed-speed one-note timing input only over the tested 0.5×–1.5× range. It does not admit mid-map speed changes, multiple simultaneous heads, lane fanout, hold-tail release, song scoring, or full-map playback. The first FD-2 FAIL reports and all strict-biology outcomes are unchanged. No training occurred.

The exact pre-run configuration is `configs/ea_mvp_fd2_fixed_speed_monotonic_ttc_v1.json`; runner is `scripts/run_ea_mvp_fd2_monotonic_ttc.py`; raw receipt is `runs/ea_mvp/fd2_fixed_speed_monotonic_ttc_v1.json`. The raw receipt contains protocol/source hashes, all 30 action traces, repeat checks, and the untrained control.
