# A8: action-credit information readiness

**Stage result: FAIL for the current signal path.** This is a source and historical-data audit, not a new training experiment or a tested correction. The [locked protocol](../configs/a8_action_credit_readiness.json), [machine-readable result](figures/a8_action_credit_readiness/result.json) and [independent AST/provenance audit](figures/a8_action_credit_readiness/audit.json) record the scope. The narrow question was whether the *existing* synthetic learning path already exposes both a first-action reward boundary and signed local causal credit suitable for a timing-specific rule.

## What the current path actually provides

1. [TinyLaneSession.step](../src/project_b/experiments/tiny_brain.py) draws one Bernoulli exploration event per global tick. If it fires, the same **+20-mV-equivalent** drive is assigned to every motor cell. There is no independent positive/negative perturbation label for a motor cell or selected edge. A pulse can help trigger a press, but it cannot directly tell a selected synapse whether advancing or delaying that first press would help.
2. The readout's DOWN is sent to the game. The session discards the returned action disposition; it calls the reward pipeline only over **newly resolved judgements**. A null DOWN leaves the note unresolved, so it has no immediate reward/RPE event in the production path. A later scored judgement can therefore train after an earlier unscored action. The session *has* the action time and could expose the disposition to a separate feedback interface; this audit does not claim the information is impossible to obtain.
3. [ThreeFactorPlasticity](../src/project_b/plasticity/eligibility.py) increments presynaptic trace by +1 and eligibility by the nonnegative decayed trace. At dopamine delivery every raw selected-edge proposal is `η × e_ij × D` with one scalar `D`; there is no stored action identity. With nonnegative initialization, all nonzero raw proposals in an event have the sign of `D`. Clipping can zero components but does not supply a missing opposite sign.
4. The independently audited original frozen panel had **233/236 GOOD+** judgements preceded by a same-note null DOWN. This is behavioral evidence that the omitted action boundary matters to interpreting the old M2 score; it is not an estimate of how a new learning rule would perform.

The independent A8 auditor parsed the current source, checked that the one reward call is inside the new-judgements loop, verified the single shared positive motor-drive assignment and scalar dopamine expression, checked source/protocol hashes, and verified the historical first-action audit receipt. It passed.

## Interpretation and boundary

Under A8's predeclared criterion, the existing path fails design readiness for a **signed, first-action-specific** credit rule because both required ingredients are absent from the learning interface. This does **not** prove that every reinforcement algorithm needs independent signed exploration, nor that adding these two ingredients will pass M2. It establishes where the proposed correction must differ from the current rule and why adjusting `η`, a threshold or a reward magnitude cannot create action identity or opposite-signed local proposals.

The three previously tested broad interventions—null-action negative modulation, trace reset and quiet rearm—do not isolate whether **first-action feedback attribution** or **signed local causal credit** is the more decisive missing piece. One small observational replay should separate the first question before specifying a replacement update.

## One next proposed stage: A8.1, not run

- **Question:** At the already selected seed-2002 outcomes **372, 373 and 377**, does treating the *first* DOWN as the action to be evaluated reverse the sign of the available reward error relative to the actual scored-judgement RPE?
- **Why next:** These exact positive-RPE updates advanced first motor crossing, while the old reward path cannot report a null first action. Sign disagreement would show an actionable feedback-attribution error at the harmful checkpoints without changing weights.
- **Hypothesis and outcomes:** If the first DOWN is null and a later positive judgement resolves the note, a fixed first-action utility of −1 with the **same saved pre-outcome baseline** may produce negative rather than positive RPE. If the first DOWN is already the scored hit, the two signals should agree. Either result is informative; disagreement alone is not proof that applying the alternative update helps.
- **Intervention:** Deterministically replay the unchanged seed-2002 training trajectory through outcome 377 solely to log each first DOWN's time/disposition and the resolved judgement. Derive diagnostic `D_first = U_first − expected_utility_before`, with `U_first = −1` for a null or early-MISS first DOWN, the existing judgement utility for a first valid hit, and −1 if no DOWN occurs before expiry. Keep the historical baseline fixed for this comparison. Do not deliver `D_first` to synapses.
- **Controls:** Require exact replay of every saved training event, unchanged map, RNG, exploration, weights, game, readout and original RPE. Use the same predeclared three outcome IDs and report every outcome 1–377 as context; do not select cases by the new sign result.
- **Primary endpoint:** Actual versus diagnostic first-action RPE sign at each of 372, 373 and 377, with the complete action sequence for those notes.
- **Secondary endpoints:** Counts of null-first/scored-second patterns, sign disagreements across 1–377, action offsets and baseline values.
- **Predeclared interpretation:** A sign reversal at a selected harmful update supports reward-attribution mismatch at that checkpoint; agreement weakens that explanation there. Missing or ambiguous first-action association is inconclusive. No outcome proves a corrected learning rule or M2 pass.
- **Do not:** Apply an update, choose a new utility strength, tune the baseline, probe frozen performance, or search different checkpoints.
- **Output:** Locked protocol, raw per-note/action ledger, independent action/game replay audit, report and handoff update.
- **Stop:** Stop after A8.1; propose one next causal test from its result rather than launching it automatically.
