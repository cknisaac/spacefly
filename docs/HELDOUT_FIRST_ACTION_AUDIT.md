# First actions in the original M2 held-out study

**Status:** complete, 2026-09-30. This is an observational replay of the **unchanged** original synthetic plasticity-on policy for all held-out seeds **2000–2031**. It adds action records to the prior [overnight result](OVERNIGHT_RESULT.md); it does not train a new method, change the game or advance M2. The [predeclared protocol](../configs/heldout_first_action_audit.json), [all 32 raw runs](figures/heldout_first_action_audit/runs.jsonl), [aggregate result](figures/heldout_first_action_audit/result.json), [source manifest](figures/heldout_first_action_audit/meta.json) and [independent audit](figures/heldout_first_action_audit/audit.json) are saved.

## Exact reproduction and action pairing

Every seed used the original 24 training plus 16 frozen notes, map, cue gains, threshold 10, plasticity and exploration configuration. Each replay's full judgement/learning summary and resolved config **exactly matched its original held-out row** before actions were interpreted. The spaced maps have at least 800 ms between notes. A DOWN was paired to note `i` only in its nonoverlapping interval from 500 ms before the note through its expiry; the ledger keeps the action's actual game disposition and note ID. A GOOD+ was classified as null-first only if a **same-note null DOWN occurred earlier than its judged hit DOWN**. No UP or another note's action was counted.

| Measure across 32 × 16 frozen notes | Observed |
| --- | ---: |
| Frozen notes | **512** |
| GOOD+ judgements | **236** (46.1%) |
| GOOD+ after earlier same-note null DOWN | **233/236 (98.73%)** |
| GOOD+ on the first DOWN | **3/236 (1.27%)** |
| Total null DOWN actions | **304** |
| Total early-MISS DOWN actions | **143** |
| First DOWN was null / early MISS / judged hit | **288 / 95 / 129** notes |
| Frozen notes with no DOWN | **0** |

The three GOOD+ notes scored on the first DOWN all belong to **seed 2015**. The full per-seed table is in the aggregate result and every action is in the raw ledger. Seed 2012 generated **32 null DOWN actions across 16 notes**, illustrating that some notes received more than one ignored press before the judged one.

## Interpretation

The original 46.1% GOOD+ result was real according to the implemented game rules, but **almost all of those judgements followed an earlier unscored motor command**. It therefore does not demonstrate that the first motor action was timed precisely. The fixed 200-ms readout cooldown allows a persistent motor policy to press again after a null action. At selected exact checkpoints, positive RPE was already shown to advance the first threshold crossing and move the later scored press across judgement boundaries; this broad action audit shows the null-first pattern is common across the original held-out seeds, not unique to seed 2002.

This audit does not prove all 32 seeds share the same synaptic cause, that every null action is harmful, or that eliminating null presses will improve score. Two fixed development interventions aimed at null credit actually worsened mean performance; see [the root-cause synthesis](SYNTHETIC_M2_ROOT_CAUSE.md). The 32 original held-out seeds are now used for mechanism diagnosis and cannot be reused as untouched confirmation of a new rule.

## Independent verification

The auditor checked the locked protocol and source hashes, all 32 exact historical summaries and configs, independently replayed **3,998** saved action records through the game, reconstructed each action-to-note association, recomputed all 512 frozen note sequences and the 233/236 classification, and checked zero frozen weight updates. Its [receipt](figures/heldout_first_action_audit/audit.json) passed. No action was inferred from judgement alone.
