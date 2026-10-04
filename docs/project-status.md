# Current project status

**As of 2026-10-05:** iteration 1 is complete on the [EA-MVP engineering branch](https://github.com/cknisaac/spacefly/tree/ea-mvp-engineering-assumption-fly-learner). It trained a repeated fixed-speed timing response in selected KC→MBON05 weights, then used frozen weights for a headless Freedom Dive replay. Shuffled teaching produced the same later behavior, dense same-lane repeats remain weak, and full-map osu!lazer score parity is partial. See the [iteration-one summary](https://github.com/cknisaac/spacefly/blob/ea-mvp-engineering-assumption-fly-learner/docs/EA_MVP_ITERATION_1_SUMMARY.md) for the declared gates and limits.

## Earlier strict MaleCNS branch

The strict moving-learning branch ended at Level 4D on 2026-10-03. Its branch classification remains **Mechanistic success / behavioral robustness incomplete**. Its declared strict behavioral gate is **FAIL**.

| Frozen Level 4D condition | Observed first action |
| --- | --- |
| Naive moving-note baseline | None |
| Teaching near target x≈0.70 | None; required target action absent |
| Teaching near wrong region x=0.20 | x=0.20 at 413 ms; retained with DAN/plasticity off |
| Matched DAN-on/plasticity-off control | None; weights unchanged |

All scheduled DAN pulses activated the three selected neurons. The implemented rule changed only eligible, anatomically reachable KC→MBON05 weights and respected the original-weight floor. These checks show that the modeled mechanism ran as specified. They do not establish biological learning in an animal or robust action at the intended target.

Read the [branch freeze summary](MALECNS_MOVING_LEARNING_BRANCH_FREEZE.md), [Level 4D protocol](MALECNS_LEVEL4D_FINAL_REPAIR_PROTOCOL.md), [result report](MALECNS_LEVEL4D_FINAL_REPAIR_RESULT.md), and [compact published result](../results/malecns-level4d/summary.md). Earlier Levels 1–4C, larval studies, and synthetic tests retain their original PASS/FAIL records in the [result registry](../results/index.md). No later learning run is implied by this documentation.
