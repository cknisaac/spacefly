# A8.2: first-action local update direction at outcome 373

**Stage result: INCONCLUSIVE for the predeclared small-step direction; no useful delay demonstrated.** Synthetic Branch A, one exact seed-2002 outcome-373 state. The [locked protocol](../configs/a8_2_first_action_local_direction.json), [raw state/edge/probe result](figures/a8_2_first_action_local_direction/result.json), [trusted branch checkpoints](figures/a8_2_first_action_local_direction/) and [independent audit](figures/a8_2_first_action_local_direction/audit.json) preserve the experiment. This was a diagnostic weight transplant, not an altered training run or production learning rule.

## Matched-state construction

The unchanged training trajectory was replayed through the first outcome-373 DOWN at **371.325 s**, an ignored null press **375 ms before** the note. All 372 preceding historical events matched. At that action, the existing 480 local eligibilities were snapshotted. The diagnostic first-action RPE was the predeclared **−0.8371985**, versus the later actual scored-judgement RPE **+1.0378015**. Raw candidate change on each selected edge was `0.2 × e(first DOWN) × (−0.8371985)`.

Replay continued through the historical scored outcome, and all 373 events matched. The exact first-action weights equalled the saved A5 pre-scored-update weights. The reconstructed pre-update coupled state matched A5 fieldwise. Four branches then shared the same A5 post-outcome **nonweight** state: no update, historical full scored update, **5%** of the candidate raw vector and **100%** of that vector, each clipped independently to existing 0–2-mV bounds. The same 32-note A5 panel was probed with plasticity and exploration off. Historical no/full probes reproduced A5 exactly.

| Branch | First motor threshold crossing / DOWN | GOOD+ / 32 | Mean utility | Mean absolute scored-attempt error |
| --- | ---: | ---: | ---: | ---: |
| No update | **372.456 s** | 17 | −0.1113 | 83.0 ms |
| Historical positive update | **372.383 s** | 0 | −1.0000 | 144.7 ms |
| First-action negative, 5% raw | **372.456 s** | 17 | −0.1113 | 83.0 ms |
| First-action negative, full raw | **372.455 s** | 17 | −0.0430 | 75.6 ms |

The **5%** candidate had applied L1 **2.3684 mV** with **no clipping**, yet no first-crossing tick moved. Its prespecified direction test is therefore **inconclusive**; we did not try a larger “small” fraction after seeing this. The full candidate proposed L1 **47.3682 mV**, applied L1 **20.7741 mV**, and clipped **96** selected weights at the lower bound. It advanced first crossing by **1 ms**, rather than delaying it. Its better mean utility and scored-attempt error are downstream effects, not evidence that it corrected the first motor-action timing mechanism. There was no silence.

The first-action eligibility was nonzero on **all 480** selected edges. By the predeclared source cue classes, **85.55%** of its total mass lay in the 500/400-ms bins, **4.50%** in the 300-ms bin, and only **3.38%** in the previously causally implicated 36-edge 300-ms→motor-97–105 cohort. This distribution is expected for a press 375 ms before the note. It explains why simply reversing the reward sign at that action does not algebraically reverse the prior scored-outcome update: the two update vectors are based on **different eligibility times and edge mixtures**. It does not by itself prove which first-action edges should change.

## Audit and interpretation

The independent auditor checked source/protocol/checkpoint hashes, the first null action and its 480 eligibility values, raw and clipped candidate vectors, exact nonweight state matching, historical no/full reproduction, **128** frozen note judgements, **256** DOWN actions, **998** motor on-threshold rises, all replayed key actions, and no probe learning or exploration. It passed.

The A8.1 sign reversal confirms a **feedback-objective mismatch** for first-action timing. A8.2 shows that correcting that scalar sign with the existing nonnegative eligibility is **not yet a demonstrated local fix**. Its small-step response is below the 1-ms threshold readout resolution; its full-step response is nonlinear and clipped. We cannot infer a useful learning-rate setting, a production edge mask, generalization, or M2 passage from this state.

## One next proposed stage: A8.3, not run

- **Question:** Does the structurally defined **500/400-ms first-action eligibility component** itself delay the next frozen first motor crossing when depressed, or does it share the full negative update's opposing/nonlinear effect?
- **Why next:** At the observed first null action, those cue classes carry **85.55%** of candidate eligibility, while the full candidate did not delay crossing. Testing their fixed component alone distinguishes a mixed-vector cancellation hypothesis from an ineffective or paradoxical far-cue direction.
- **Hypothesis and outcomes:** If the far-cue-only negative component delays crossing, other candidate components opposed it; if it advances crossing, the far-cue component itself has a paradoxical local dynamical effect; if it does not move crossing, this state remains threshold-insensitive at the fixed displacement.
- **Intervention:** Use the same A8.2 pre-update checkpoint and **only one** structural mask: selected edges whose presynaptic encoder preferred time is exactly 500 or 400 ms. Apply their **full** existing first-action negative raw candidate change with the same 0–2-mV bounds, leaving all other selected weights at no-update values. Compare with A8.2's saved no-update and full-candidate branches. Do not scale or redistribute omitted L1.
- **Controls:** Same 32-note A5 panel, neural/queue/RNG/reward/readout state, frozen plasticity/exploration, exact old references, and recorded clipping. Verify all nonselected weights are identical.
- **Primary endpoint:** First upward motor on-threshold crossing relative to no update and full candidate, with silence explicit.
- **Secondary endpoints:** First DOWN, motor-window counts, all actions, utility/GOOD+, applied L1 and bounds.
- **Predeclared interpretation:** A later crossing without silence supports a far-cue component with useful local direction at this one state. Earlier crossing opposes that hypothesis; no movement is inconclusive. Score improvement without crossing movement does not count as upstream timing repair.
- **Do not:** Try another mask, fraction, checkpoint, rate or threshold after seeing the result; do not call this a biological or production plasticity rule.
- **Output:** One locked protocol, raw branch and checkpoint, independent weight/state/readout audit, report and handoff update.
- **Stop:** Stop after A8.3; a candidate learning rule still requires separate design and development evidence.
