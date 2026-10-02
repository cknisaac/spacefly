# Complementary 300-ms target cohort at outcome 373

**Status:** complete, 2026-09-30. Synthetic Branch A, seed 2002 outcome 373. This is one predeclared diagnostic omission from the exact saved A5 pre-dopamine checkpoint, with no new training or production change. The [locked protocol](../configs/cue_300ms_complement_threshold_diagnostic.json), [complete raw result](figures/cue_300ms_complement_threshold/result.json), [branch checkpoint hashes](figures/cue_300ms_complement_threshold/meta.json) and [independent audit](figures/cue_300ms_complement_threshold/audit.json) are saved.

## Question and locked comparison

The prior [12-edge target-cohort test](CUE_300MS_THRESHOLD_COHORT_DIAGNOSTIC.md) omitted 300-ms relay sources 48–51 to motor targets 94–96. That omission moved the first motor threshold crossing **8 ms earlier**, so those 12 changes did not account for the harmful crossing advance. Before any new probe, the one complementary cohort was fixed: **36 edges from the same relay sources to motor targets 97–105**, sparse slots listed in the protocol. This is the structural complement within the 48-edge 300-ms bin, not a score-ranked mask.

Three identical pre-state branches were compared: no update, the production full real update, and the same full update with only those 36 weights restored to pre-update values. The omitted cohort carried **35.708 mV raw proposed L1** and **31.655 mV applied L1**. The intervention retained **30.515 mV** of the original **62.170-mV** applied L1 and left the other 444 plastic weights, clipping on retained components and all nonweight state identical to full. Plasticity and exploration were frozen on the same 32-note A5 probe. The primary endpoint was the first upward motor on-threshold crossing, not score.

| Branch | First threshold rise / null DOWN (s) | Window count, prior tick → crossing | First scored DOWN (s) | Frozen GOOD+ | Mean utility | Mean scored-attempt error |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| No update | 372.456 | 7 → 11 | 372.656 | 17/32 | −0.111328 | −83.0 ms |
| Real full update | 372.383 | 9 → 12 | 372.583 | 0/32 | −1 | −144.719 ms |
| Full except targets 97–105 | **372.456** | 8 → 10 | **372.656** | 17/32 | −0.189453 | −85.5 ms |

The complementary omission **fully removed the 73-ms first-crossing advance** in this exact combined update. Its first null and scored DOWN times matched no update. All branches had 64 DOWN actions (32 null). The omission's first note was GOOD at −69 ms, matching no update; full was an early MISS at −142 ms. Over the panel, omission produced 17 GOOD and 15 MEH, versus no update's 4 GREAT, 13 GOOD and 15 MEH; the restored GOOD+ count therefore does not imply identical utility. Full produced 32 MISS. Every action, signed error and spike/readout trace is retained in the raw result.

## Interpretation

In this selected state, the 300-ms projections to motor **97–105 are necessary as a cohort for the full update's early first threshold crossing**. The earlier 94–96 omission had the opposite effect, and the full 48-edge omission restored no-update timing. This triangulates the local source of the upstream crossing shift to the complementary cohort or its interaction with retained edges. It does **not** prove any one of those 36 edges is necessary, that the cohort alone is sufficient, or that the same mechanism holds at another checkpoint. The 20-ms readout window makes spike phase and coincidence consequential; score alone would not establish the upstream effect. No mask is proposed as a production learning rule.

## Reproducibility and audit

The runner verified all 480 pre-weights and eligibilities, RPE, raw proposals, neural/queue/RNG/reward/readout/topology states, and exact production full/no branch reproduction. The independent auditor independently reconstructed the 36 slots from source and destination IDs, verified the complement to the prior 12 slots, all branch weights and other state, reran frozen probes, and recomputed every threshold crossing and decision from motor spike batches. Its receipt passed **3 branches, 96 note outcomes, 192 DOWN actions and 768 upward on-threshold crossings**. No extra cohort, parameter variation or training run was performed.
