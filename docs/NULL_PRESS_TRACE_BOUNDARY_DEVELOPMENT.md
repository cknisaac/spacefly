# Null-action trace-boundary development test

**Status:** complete; **the predeclared progression rule failed**. Synthetic Branch A only, 2026-09-30. This tested one diagnostic reset of local eligibility and presynaptic traces immediately after each training-phase null DOWN. It used eight already explored development seeds **1000–1007**, 24 training and 16 frozen notes on the exact overnight map generator, and readout threshold 10. The [locked protocol](../configs/null_press_trace_boundary_development.json), [32-run raw ledger](figures/null_press_trace_boundary_development/runs.jsonl), [cohort result](figures/null_press_trace_boundary_development/result.json), [source manifest](figures/null_press_trace_boundary_development/meta.json) and [independent audit](figures/null_press_trace_boundary_development/audit.json) preserve all cases.

## One declared intervention

The hypothesis was that the scored second press's RPE wrongly credits activity from before an earlier unscored null press. The diagnostic wrapper set all **480** selected eligibility traces and **40** selected presynaptic traces to zero at each training null action. It changed no weight at that moment and gave no extra reward or penalty. It left the production eligibility equation, dopamine, utility, predictor, game and readout untouched. Frozen traces were never reset by the wrapper. Conditions were unchanged `legacy_on`, `boundary_reset_on`, plasticity-off, and reset with shuffled judgement utilities. All conditions shared seed-specific maps and cue gains; the eight legacy summaries exactly matched the earlier overnight-development records.

| Frozen cohort measure | Legacy on | Trace reset on | Reset off | Reset with shuffled rewards |
| --- | ---: | ---: | ---: | ---: |
| Mean GOOD+ | **57.03%** | **47.66%** | 0% | 12.50% |
| Pooled hit timing MAE | **59.43 ms** | **67.11 ms** | undefined: no hits | 43.13 ms over 16 hits |
| Null DOWN actions across 128 frozen notes | 66 | 61 | 0 | 16 |
| Early-MISS DOWN actions | 26 | 33 | 0 | 0 |
| Frozen notes with no DOWN | 0 | 0 | **128** | **112** |
| Mean first-DOWN offset where defined | −175.02 ms | −177.98 ms | undefined | −243.13 ms |

Reset on strictly beat legacy in **1/8 seeds**, reset off in **4/8**, and reset shuffled in **4/8**. The rule required at least six wins against each, lower MAE, fewer null actions without more early misses or silence. It failed every substantive improvement condition except a small aggregate null reduction. Seed 1001 again improved 12.5→100% GOOD+ but still had **16/16 null-first** frozen notes; this is score gain through the same two-press path. Seed 1004 fell 100→0%, and seed 1005 fell 43.75→0%. All eight seeds and controls remain in the raw ledger. No reset window, strength or other parameter was searched.

There were **134** training resets in the on branch and **115** in shuffled, removing aggregate pre-reset eligibility L1 of **28,270.32** and **26,907.69** respectively (sums of dimensionless trace values across events). Removing all pre-null traces can also remove useful credit. The remaining post-null activity and reward dynamics still support null-first policies in some seeds. The failed result therefore narrows the repair requirement: a useful rule must assign credit to specific action-causing activity with a signed temporal consequence, while retaining useful learning and avoiding silence. This result alone does not establish that all action-boundary trace methods fail.

## Audit and limit

The independent auditor validated the protocol/source hashes, all 32 runs and maps, replayed **2,712** saved actions through the game, verified **512** frozen outcomes, checked the **249** reset times against training null actions and the zero-weight-change reset contract, recomputed bounds and cohort metrics, and matched all eight legacy summaries to historical rows. It passed. This was development evidence only; no new held-out M2 evaluation was run and no production learning rule was changed.
