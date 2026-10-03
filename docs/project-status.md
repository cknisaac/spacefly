# Current project status

**Iteration 1 closed 2026-10-04.** The playable native 4K osu!mania recreation,
the separate EA-MVP engineering-assumption learner, the frozen *Freedom Dive*
headless playback, and the replay companion are complete within their recorded
gates. Start with the [iteration-one summary](EA_MVP_ITERATION_1_SUMMARY.md),
[fly-training explainer](EA_MVP_FLY_TRAINING_EXPLAINER.md), and
[saved HTML playback](../visualization/ea-mvp-training-playback.html).
The engineering learner's repeated-note result does not change the strict
MaleCNS Level 4D **FAIL** below. Unfamiliar-speed transfer failed, shuffled
teaching matched learning-on, dense same-lane repeats remain weak, and
uninterrupted full-map osu!lazer score parity remains unverified. The original
recreation is preserved; see its [map-specific result](OSU_MANIA_FREEDOM_DIVE_NORMAL_RESULT.md).

## Preserved MaleCNS branch result

**As of 2026-10-03:** the MaleCNS moving-learning branch ends at Level 4D. Its branch classification is **Mechanistic success / behavioral robustness incomplete**. Its declared strict behavioral gate is **FAIL**.

| Frozen Level 4D condition | Observed first action |
| --- | --- |
| Naive moving-note baseline | None |
| Teaching near target x≈0.70 | None; required target action absent |
| Teaching near wrong region x=0.20 | x=0.20 at 413 ms; retained with DAN/plasticity off |
| Matched DAN-on/plasticity-off control | None; weights unchanged |

All scheduled DAN pulses activated the three selected neurons. The implemented rule changed only eligible, anatomically reachable KC→MBON05 weights and respected the original-weight floor. These checks show that the modeled mechanism ran as specified. They do not establish biological learning in an animal or robust action at the intended target.

Read the [branch freeze summary](MALECNS_MOVING_LEARNING_BRANCH_FREEZE.md), [Level 4D protocol](MALECNS_LEVEL4D_FINAL_REPAIR_PROTOCOL.md), [result report](MALECNS_LEVEL4D_FINAL_REPAIR_RESULT.md), and [compact published result](../results/malecns-level4d/summary.md). Earlier Levels 1–4C, larval studies, and synthetic tests retain their original PASS/FAIL records in the [result registry](../results/index.md). No later learning run is implied by this documentation.
