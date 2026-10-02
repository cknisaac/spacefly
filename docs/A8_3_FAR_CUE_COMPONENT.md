# A8.3: far-cue component of the first-action negative proposal

**Stage result: INCONCLUSIVE for moving the first motor crossing.** Synthetic Branch A, one exact seed-2002 outcome-373 state. The [locked protocol](../configs/a8_3_far_cue_component.json), [raw branch result](figures/a8_3_far_cue_component/result.json), [trusted checkpoint](figures/a8_3_far_cue_component/far_cue_only_checkpoint.pkl) and [independent audit](figures/a8_3_far_cue_component/audit.json) preserve this one structural test. No training or production rule was changed.

The fixed mask contained all **96** selected relay→motor edges in the encoder's 500-ms and 400-ms preferred-cue classes. These carried **85.55%** of the eligibility at outcome 373's first null DOWN. The branch applied their exact full first-action negative raw candidate changes from A8.2, left the other **384** weights at no-update values, did not redistribute L1, and used the same A5 frozen panel and nonweight state. Raw L1 was **40.5224 mV**; applied L1 was **13.9283 mV** after all **96** selected far-cue weights hit the lower bound.

| Frozen branch | First motor threshold crossing / DOWN | GOOD+ / 32 | Mean utility |
| --- | ---: | ---: | ---: |
| A8.2 no update | **372.456 s** | 17 | −0.1113 |
| A8.2 full negative candidate | **372.455 s** | 17 | −0.0430 |
| **Far-cue negative component only** | **372.456 s** | 17 | −0.1113 |

The structurally dominant eligibility component did **not** move the first threshold crossing, first DOWN, GOOD+ or utility from no update. Under the predeclared rule this is **inconclusive**, rather than evidence of useful or opposing far-cue direction. It demonstrates that eligibility mass is a poor proxy for first-crossing causal sensitivity **in this fixed state**. The full candidate's 1-ms advance must involve the remaining components or their interaction with the far-cue change; this stage did not test a complementary mask. It does not establish that far-cue edges are inert in other states or that their weights should be permanently removed.

The independent auditor verified the 96-edge source-class mask, exact unselected weights/nonweight state, raw and clipped applied vector, **32** rejudged probe notes, **64** replayed DOWN actions, **232** reconstructed motor on-threshold rises, no exploration or probe learning, and the saved comparator crossing times. It passed. No second mask, fraction or checkpoint was tested.

## One next proposed stage: A9, not run

- **Name and question:** **A9 — one structural timing-controllability witness.** Can the existing synthetic topology and fixed readout produce a useful *first* press on the same frozen panel under one cue-class-defined weight configuration, without a second cooldown-timed press?
- **Why next:** A8.1 identified a first-action reward mismatch, while A8.2/A8.3 found no locally useful direction from reversing the current eligibility update. Before designing a new learner, a single construct can test whether the current selected-edge space contains an obvious late-cue first-action policy. This is more discriminating than another reward-strength or eligibility-decay search.
- **Hypothesis and outcomes:** A configuration retaining later cues while silencing the four earliest cue classes may delay initial motor recruitment into the hit window; it may instead remain early or go silent. Success is a feasibility witness only; failure does not prove no other weight vector works.
- **Intervention:** From the exact A8.2 no-update checkpoint, set selected edges whose source preferred time is **500, 400, 300 or 200 ms** to the existing lower bound **0 mV**. Leave all selected 150/100/75/50/25/0-ms edges and all nonselected edges unchanged. Run one frozen 32-note A5 probe. No iterative adjustment.
- **Controls:** A8.2 saved no-update probe and state; identical topology, neurons, queue, RNG, reward baseline, readout, notes and cue gains; plasticity/exploration off.
- **Primary endpoint:** Count of notes scoring GOOD+ on their **first** DOWN, with first-DOWN signed timing and silent-note counts. A single first-DOWN GOOD+ is a narrow existence witness, not a reliability pass.
- **Secondary endpoints:** First motor crossing, all DOWNs, judgement distribution, utility, motor spikes and selected-edge weight displacement/bounds.
- **Predeclared interpretation:** If at least one note has a first-DOWN GOOD+ without a preceding null, the current architecture can express that behavior in at least one frozen context; if none, this one witness fails or is silent, leaving general controllability unresolved. Do not treat a second-press GOOD+ as first-action success.
- **Do not:** Search cue-bin cutoffs, weight levels, masks, readout settings, seeds or probe maps; do not use this constructed configuration as a learned or biological result.
- **Output:** Locked protocol, one branch checkpoint, full raw action/judgement trace, independent audit, report and handoff update.
- **Stop:** Stop after A9 and decide whether learning-rule design or architecture diagnosis is the next most discriminating question.
