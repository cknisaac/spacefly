# A8.1: first-action reward-sign attribution

**Stage result: PASS for the predeclared feedback-attribution signature; no correction tested.** Synthetic Branch A, seed 2002 only. The [locked protocol](../configs/a8_1_first_action_reward_attribution.json), [raw 377-outcome/action ledger](figures/a8_1_first_action_reward_attribution/result.json) and [independent audit](figures/a8_1_first_action_reward_attribution/audit.json) preserve the exact comparison. The unchanged session was deterministically replayed through outcome 377; every saved training event matched the existing long-continuation ledger. No alternative dopamine event, weight update, frozen probe, or new training setting was applied.

## Predeclared diagnostic signal

For each note, the first DOWN was associated using the existing nonoverlapping note-window rule. Its diagnostic utility was **−1** if it was a null press or early MISS, the existing game utility if it was the scored valid hit, and −1 if the note expired without a DOWN. The diagnostic first-action RPE used the **same saved pre-outcome expected utility** as the actual training RPE. The baseline was not refitted or advanced with the diagnostic utility. This is a distinct proposed *first-action objective*, not a correction to the game's valid scored-judgement utility.

| Existing checkpoint | First DOWN relative to note | Later scored DOWN | Actual scored RPE | Diagnostic first-action RPE |
| --- | ---: | ---: | ---: | ---: |
| Seed 2002 outcome **372** | −195 ms, null | +5 ms, MAX | **+1.2920** | **−0.7080** |
| Seed 2002 outcome **373** | −375 ms, null; another null at −175 ms | +25 ms, GREAT | **+1.0378** | **−0.8372** |
| Seed 2002 outcome **377** | −229 ms, null | −29 ms, GREAT | **+0.8840** | **−0.9910** |

The sign reversed at **all three preselected checkpoints**. Across the unchanged first 377 outcomes, **303** first DOWNs were null, **43** were early MISS, **30** were valid hits and **one** note had no DOWN before resolution. All 303 null-first notes later had a scored DOWN. Actual and diagnostic RPE signs disagreed on **165/377** outcomes. This whole-trajectory count is context, not a selected success rate.

At outcomes 372/373/377, the actual positive update advanced the next frozen first motor crossing by 129/73/42 ms respectively in earlier matched-state tests. Outcome 372's advance *improved the old game GOOD+* by turning an early scored MISS into an ignored null followed by a hit; outcomes 373 and 377 harmed GOOD+. Under a first-action objective, all three training notes begin with an invalid early action. This explains why the positive scored-judgement RPE is misleading **for first-action timing**, without calling the original game judgement or utility a software bug.

## Audit and claim limit

The independent auditor verified the protocol/source hashes, replayed **1,545** saved key actions through the unchanged game, matched all **377** historical judgements and recomputed every note/action association, first-action utility, baseline subtraction and RPE sign. It passed. The first audit attempt failed before a receipt because the auditor expected the source config key `explicit_note_times_us`; the long-continuation ledger stores it as `training_note_times_us`. Only the auditor lookup was corrected; the raw replay and result were unchanged.

The result **confirms a feedback-attribution mismatch** at three selected checkpoints under the explicitly declared first-action objective. It does not prove that delivering negative RPE at first DOWN would improve behavior: the old null-cost development method failed, and local eligibility, action timing and clipping also matter. It does not establish the prevalence of this exact causal effect in unseen seeds. The former held-out seeds are diagnostic data.

## One next proposed stage: A8.2, not run

- **Question:** At the exact seed-2002 outcome-373 state, does a first-action-tagged negative local update produce a useful *direction of first motor-crossing movement* without assuming that the full step size is safe?
- **Why next:** A8.1 proved actual positive versus first-action negative RPE sign disagreement; the earlier full positive update advanced crossing 73 ms. A matched-state probe can test whether the alternative action-time local eligibility direction delays that crossing, while separating direction from silence or clipping.
- **Hypothesis and possible outcomes:** A fixed small displacement along the first-action negative raw proposal delays the first crossing toward the no-update state, or it advances/no-ops instead. A full candidate displacement may overshoot or silence; that is reported separately.
- **Intervention:** Reconstruct outcome 373's exact pre-first-DOWN and pre-scored-update states. At the first null DOWN, snapshot the existing local eligibility and compute `η × e(first DOWN) × D_first` with the saved baseline and fixed existing `η`. Transplant only the candidate's proposed selected-edge weight changes into the identical pre-scored-update nonweight state. Compare no update, historical full scored update, a **predeclared 5%** candidate raw displacement, and full candidate displacement. Apply original bounds independently in each branch. This is a diagnostic transplant, not a production rule or continuous training trajectory.
- **Controls:** Preserve topology, all 480 pre-update weights, neuron/queue/RNG/readout/reward state, the same 32-note disjoint A4/A5 panel, no exploration and no probe plasticity. Require exact historical no/full reproduction and exact first-action event replay.
- **Primary endpoint:** First upward motor threshold-crossing time and first DOWN time relative to no update, with silence treated as failure to demonstrate useful delay.
- **Secondary endpoints:** All DOWNs, scored timing, GOOD+/utility, candidate raw/applied vectors, clipping/bounds and eligibility timing.
- **Predeclared interpretation:** A small candidate step delaying first crossing without silence supports locally useful **direction** at this selected state; full-step harm with small-step benefit implicates magnitude. No movement is inconclusive; earlier crossing or silence fails the useful-direction signature. Do not generalize one checkpoint or infer M2 passage.
- **Do not:** Search fractions, masks, baselines, rates or other checkpoints; change the production rule; use score to choose the candidate.
- **Output:** Locked protocol, exact checkpoints/raw branches, independent state and action audit, report and handoff update.
- **Stop:** Stop after A8.2; any development cohort requires a new evidence-based stage.
