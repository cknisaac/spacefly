# EA-MVP EA-13 — broad-pattern evaluation

**Decision: PASS for the frozen, narrow headless transfer checks.** No training or parameter selection was run during EA-13.

## Frozen test

The protocol reused three already completed fixed-speed weight sets (seeds 907, 1009, and 1103) without additional training. It evaluated three fresh pattern families at the same fixed 500-ms visual approach, using learning-on, shuffled-teaching, and untrained weights. Each case was repeated twice. Cues stayed separated; the tested intervals were 550 ms. The encoder, neural model, lane selector, chord fanout, hold release rule, thresholds, and game settings were unchanged.

| Fresh pattern | Learning-on result across 3 seeds | Shuffled-teaching result | Untrained control |
| --- | --- | --- | --- |
| Eight taps with fast lane switches | 3/3 cases passed; 24/24 notes PERFECT | Exactly same actions and results | Silent; 24/24 notes MISS |
| New lane pairs (0+2, 1+3) and one four-lane chord | 3/3 cases passed; 24/24 notes PERFECT | Exactly same actions and results | Silent; 24/24 notes MISS |
| Sequential holds of 0.6 s, 1.7 s, and 2.8 s | 3/3 cases passed; 18/18 heads and tails PERFECT | Exactly same actions and results | Silent; 18/18 heads and tails MISS |

All repeated traces matched exactly. The trained actions had one DOWN per note at the target plus 1 ms. Taps and chords released 10 ms later; holds released exactly at their tail times. Initial-weight controls emitted no actions.

The frozen protocol is `configs/ea_mvp_broad_eval_v1.json`; its runner is `scripts/run_ea_mvp_broad_eval.py`; the complete per-seed/per-arm receipt is `runs/ea_mvp/broad_eval_v1.json`.

## Interpretation

The retained final synaptic weights transferred to these fresh lane orders, chord sets, and hold durations under the fixed speed and fixed readout assumptions. The untrained controls were silent, so the tested output depended on the retained changed-weight state. However, shuffled-teaching weights produced exactly the same actions and scores as the learning-on weights. EA-13 therefore does **not** show that the correct judgement-to-trial pairing was needed to acquire the behavior. It also does not repair the earlier result where shuffled teaching matched the fixed-speed score.

This is not a fresh eight-seed formal confirmation, a variable-speed test, an overlapping or mixed tap/chord/hold test, or a live osu!lazer desktop-client test. Fixed 500-ms approach speed was retained as instructed. The result leaves strict biology statuses unchanged and supports no claim about fly behavior.
