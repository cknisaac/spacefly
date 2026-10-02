# Fixed null-press action-cost development test

**Status:** complete; **the predeclared progression rule failed**. Synthetic Branch A only, 2026-09-30. This was one diagnostic learning-method test on **eight previously used development seeds, 1000–1007**, with the unchanged overnight map generator, 24 training notes, 16 frozen notes and readout threshold 10. It cannot pass M2 or support a held-out claim. The [locked protocol](../configs/null_press_action_cost_development.json), [32-run raw ledger](figures/null_press_action_cost_development/runs.jsonl), [cohort result](figures/null_press_action_cost_development/result.json), [source manifest](figures/null_press_action_cost_development/meta.json) and [independent audit](figures/null_press_action_cost_development/audit.json) retain every seed, action and outcome.

## One declared method

The preceding [three-checkpoint mechanism test](CUE_300MS_SATURATION_CONTRAST_DIAGNOSTIC.md) showed that an earlier first motor action can be an unscored **null press**, followed 200 ms later by the scored press. Positive reward on the second press can strengthen eligibility associated with the first. To test whether the missing penalty for the first action was the actionable defect, a diagnostic-only overlay delivered a **−1.0 dopamine-like signal immediately after each training-phase null DOWN**, through the unchanged production plasticity method. The one magnitude equals the existing centered MISS utility and was fixed before sampling. It was never applied during frozen evaluation. No score, judgement, predictor, encoder, readout, eligibility rule, weight bound or production source was changed.

For every seed the four paired conditions shared the same generated map and cue gains: unchanged `legacy_on`, `null_cost_on`, `null_cost_off` (all plasticity disabled) and `null_cost_shuffled` (the null cost retained, judgement utilities deterministically permuted from that seed's cost-on training). The original zero-action-cost on run exactly reproduced its saved overnight-development summary in **all eight seeds**. Exploration remained the original global-tick seeded process. The raw ledger includes every training/frozen judgement, DOWN/UP and null disposition, cost event, final weight vector and bound occupancy.

| Frozen cohort measure | Legacy on | Null cost on | Cost off | Cost with shuffled judgement rewards |
| --- | ---: | ---: | ---: | ---: |
| Mean GOOD+ | **57.03%** | **44.53%** | 0% | 7.81% |
| Pooled hit timing MAE | **59.43 ms** | **72.16 ms** | undefined: no hits | 61.0 ms over 16 hits |
| Null DOWN actions across 128 frozen notes | 66 | 53 | 0 | 16 |
| Early-MISS DOWN actions | 26 | 31 | 0 | 0 |
| Frozen notes with no DOWN | 0 | 0 | **128** | **112** |
| Mean first-DOWN offset where defined | −175.02 ms | −170.88 ms | undefined | −261.0 ms |

Cost on strictly beat legacy on in **1/8 seeds**, cost off in **5/8**, and cost shuffled in **5/8**; the declared progression rule required at least six wins against each, fewer premature/null first actions without silence, and lower timing MAE. It failed. Seed 1001 improved GOOD+ **12.5→100%**, but its frozen null presses rose **2→16** and the mean first DOWN moved from **−149 to −254.5 ms**. That improvement therefore strengthened the same two-press behavior the method was meant to correct. Seed 1004 fell **100→0% GOOD+**, with 16 null presses becoming zero and first DOWN moving from **−254.8 to −112.8 ms**; its missed correction crossed into a single early hit/MEH regime. Seeds 1003 and 1005 also lost GOOD+, while 1000 and 1007 stayed at zero. Every seed is in the raw ledger; no unfavorable seed was dropped.

The overlay delivered **131** null-cost events in cost-on and **114** in cost-shuffled training. They applied aggregate L1 displacement of **1,841.38 mV** and **919.70 mV** respectively (sums over events, not a net vector); bounds remained enforced. The signal broadly affects any eligible selected edge at a null action. These data show that immediate null punishment can reduce null actions in aggregate yet move some policies into early scored misses or silence, while other policies still obtain scores through null-plus-cooldown. Thus this fixed cost is **not a validated repair** of temporal credit assignment. Its single magnitude was not tuned after the failure.

## Audit and limit

The independent auditor checked the locked config and source hashes, all 32 unique runs/maps/configs, all **2,688** saved action records by replaying the headless game, **512** frozen note outcomes, the 245 training null-cost event timestamps and amplitudes, shuffled reward multiset, frozen absence of weight changes, weight bounds, all cohort metrics and all eight exact historical legacy summaries. It passed. The test does not establish that any action cost is intrinsically wrong; it rejects this one fixed immediate global-negative-modulation implementation on this development cohort. A new mechanism must be declared from the failure mode, not chosen by searching penalty strengths on these seeds.
