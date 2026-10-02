# Successive-update interference diagnostic

**Status:** complete, 2026-09-30. This is a short, selected-cohort diagnostic of the synthetic 128-neuron fixture. It does not validate reinforcement learning above controls or a fly circuit. The locked [protocol](../configs/successive_update_interference_diagnostic.json), per-update [raw trajectories](figures/successive_update_interference/runs.jsonl), [causal skip record](figures/successive_update_interference/counterfactual.json), [source manifest](figures/successive_update_interference/meta.json) and [independent audit](figures/successive_update_interference/audit.json) preserve the evidence.

## Predeclared design

The existing longitudinal ledger selected **seed 2001 after outcomes 96–112** because its saved frozen GOOD+ was 32/32 at 96 and 0/32 at 384. **Seed 2002 after 368–384** was the contrast: it was the only on-condition trajectory retaining GOOD+ at 384 (25/32). No intermediate frozen probes were available when these 16-update windows were locked. This is a diagnostic cohort selected from already inspected synthetic seeds, not held-out confirmation.

For each seed, the runner exactly replayed the real on-condition training path from the original configuration. It froze a clone at update 0 and after **every one of the 16 real plastic updates**, ran the same disjoint 32-note relative-time/cue-gain panel with plasticity and exploration off, and continued the untouched training session. The first seed's start probe exactly matched its previously saved outcome-96 probe; the second seed's final probe exactly matched its saved outcome-384 probe. Every intervening training event and selected update diagnostic matched the source ledger. No probe affected training, checkpoint choice or settings.

Before probing, a meaningful *single-update deterioration* was defined as: predecessor GOOD+ ≥16/32, a loss of ≥8 GOOD+ notes **and** mean utility ≥0.25 lower, with at least four real outcomes remaining in the window. The first qualifying transition in seed 2001 had priority; otherwise the first in seed 2002. One such transition, if present, would receive one real-versus-skip intervention. A meaningful improvement required ≥8 additional GOOD+ notes and utility ≥0.25 higher. The protocol separately defined a directional timing-drift criterion and a pre-collapse timing-shift criterion. No alternative window, seed, threshold or skip target was selected after viewing the new probes.

## Observed frozen trajectories

Each entry gives **GOOD+/32; mean utility** on the identical relative probe panel. The paired rows are different outcome ranges, not paired biological specimens.

| Step in window | Seed 2001: after outcome | Frozen result | Seed 2002: after outcome | Frozen result |
| ---: | ---: | ---: | ---: | ---: |
| 0 | 96 | 32; 0.4453 | 368 | 0; −1.0000 |
| 1 | 97 | 32; 0.4453 | 369 | 0; −1.0000 |
| 2 | 98 | 32; 0.4453 | 370 | 0; −1.0000 |
| 3 | 99 | 32; 0.4453 | 371 | 0; −0.9609 |
| 4 | 100 | 32; 0.4453 | 372 | 17; −0.1113 |
| 5 | 101 | 32; 0.4453 | **373** | **0; −1.0000** |
| 6 | 102 | 32; 0.4453 | 374 | 32; 0.9336 |
| 7 | 103 | 32; 0.4453 | 375 | 32; 0.3281 |
| 8 | 104 | 32; 0.4453 | 376 | 10; −0.2480 |
| 9 | 105 | 32; 0.4453 | 377 | 0; −0.9609 |
| 10 | 106 | 32; 0.4453 | 378 | 28; 0.6992 |
| 11 | 107 | 28; 0.2109 | 379 | 32; 0.3281 |
| 12 | 108 | 32; 0.4453 | 380 | 17; −0.1211 |
| 13 | 109 | 32; 0.4453 | 381 | 0; −0.6680 |
| 14 | 110 | 32; 0.4453 | 382 | 28; 0.6680 |
| 15 | 111 | 32; 0.4453 | 383 | 0; −0.8340 |
| 16 | 112 | 28; 0.2109 | 384 | 25; 0.1133 |

Seed 2001 stayed useful throughout the selected window. Its 4-note dips after 107 and 112 were below the locked 8-note/0.25-utility threshold; the first recovered on the next real update. This window **does not capture or explain** its later saved collapse to 0/32 by outcome 384.

Seed 2002 repeatedly crossed the performance boundary. The locked rule found meaningful gains after 372, 374, 378, 382 and 384, and eligible one-step deteriorations after 373, 376 and 380. Its first eligible transition was **outcome 373**: frozen GOOD+ fell **17→0**, and mean utility **−0.1113→−1.0000**. The training outcome that triggered the update was itself **GREAT**, with game utility `0.875`, expected utility before reward `−0.1628`, RPE `+1.0378`, and mean eligibility `7.934`. The raw update L1 was **790.49 mV** across 480 selected edges; applied L1 was **62.17 mV** because **354 upper-bound edges clipped** (171 edges actually changed). This temporal pairing shows that an apparently successful training judgement can precede a harmful retained-policy change, but the observational transition alone cannot assign causality.

The continuous timing record shows the loss mechanism more clearly than GOOD+ alone. At 372 the mean signed scored-attempt error was **−83.0 ms** and hit MAE was **83.0 ms**. After 373, scored-attempt error shifted to **−144.7 ms** and all 32 notes became MISS, so hit-only MAE is undefined. The next real outcome, a MISS with negative RPE, was followed by recovery to 32/32 GOOD+ at 374. Later reversals recur; neither trajectory meets the protocol's progressive one-direction median-DOWN drift rule (only 8 of 16 increments shared each net-shift sign, below the required 12). This is oscillation, not demonstrated monotonic accumulation.

Timing can move before a judgement-category fall: seed 2002 remained 32/32 GOOD+ after 374 and 375, while hit MAE moved **16.41→52.62 ms** and mean signed scored-attempt error moved **+16.41→−52.62 ms**. Its median all-DOWN nearest-note offset shifted **69 ms earlier**; the next update, 376, reduced GOOD+ to 10/32. Median all-DOWN offsets include null presses and are not equivalent to scored hit errors. The ledger retains every DOWN and every signed event error so both can be inspected.

## One matched causal skip: outcome 373

The predeclared selection rule chose **seed 2002, outcome 373**, once only. Two branches started from the same complete checkpoint after outcome 372. They matched the exact state immediately before dopamine, including the 480 weights, eligibility, time, raw proposed vector and RNG state. Branch A applied the real positive update through the production method; branch B called the same method with zero dopamine for that event only. Both then used the unchanged rule for outcomes 374–384, the same scheduled notes, reward definition and tick-by-tick RNG stream. The real branch exactly reproduced every saved source training event and both previously observed probes. Both branches ended at the same simulation time, with identical final RNG-state hashes and **the same 14 realized exploration pulses** after the intervention.

| Frozen probe | Real update | Skip only update 373 |
| --- | ---: | ---: |
| Immediately after 373: GOOD+ | **0/32** | **17/32** |
| Immediately after 373: mean utility | **−1.0000** | **−0.1113** |
| Immediately after 373: mean signed attempt error | −144.72 ms | −83.00 ms |
| End after 384: GOOD+ | 25/32 | 25/32 |
| End after 384: mean utility | 0.1133 | 0.1133 |
| End after 384: hit timing MAE | 68.25 ms | 66.91 ms |

Skipping the update **causally preserved the earlier useful frozen behavior immediately**. It did **not** preserve a higher GOOD+ or utility at the end of the short sequence. The branch's subsequent closed-loop training judgements, reward predictions/RPEs and later update vectors changed endogenously; this is the expected consequence of changing an earlier weight update, not a replay mismatch. The scheduled notes, underlying RNG draw stream and realized exploration pulses remained matched. The final equality of score categories does not imply identical weights or exact press times: final probe action/event records differ slightly.

## Interpretation and limits

1. **Does useful behavior emerge before later training destroys it?** **Yes within seed 2002's short window:** 17 GOOD+ after 372 became zero after 373, and later useful states were repeatedly lost and recovered. Seed 2001's useful state persisted through this particular 16-update window; its known outcome-384 collapse remains outside the diagnostic window.
2. **Are specific updates causally responsible?** **Outcome 373 caused a temporary immediate loss** in the selected seed: skipping only that update preserved 17 GOOD+ with matched pre-update state and exploration. The loss did not persist through outcome 384, so A3 does not identify one update responsible for the long-term synthetic learning failure.
3. **One update or cumulative interference?** The observed short-window failure is **repeated state-dependent reversals**, including an acute harmful update and later recovery. It is not dominated by one lasting harmful update and does not meet the declared monotonic timing-drift criterion. Cumulative damage in seed 2001's later unprobed interval remains unresolved.
4. **Timing before category collapse?** **Yes descriptively** at 374→375→376: substantial earlier scored and DOWN timing while GOOD+ stayed 32, then a GOOD+ drop. For the selected 372→373 loss, the large early shift and category collapse occurred together.
5. **Does clipping participate?** **It materially reshaped the harmful 373 update** (354/480 edges; only 7.9% of raw L1 applied). Beneficial 372 and 374 updates also clipped, so these data do not isolate clipping as the cause of harm.
6. **Single next Branch A mechanism question:** Does a **positive global RPE after a well-timed training press reinforce a broad eligibility pattern whose net motor effect advances subsequent presses past the scoring window**? The 373 event makes this a concrete credit-assignment/timing-sign question; no rule alteration or new test was run here.

All claims refer to one fixed 32-note artificial panel translated to each checkpoint time. It is disjoint from training but has been reused in prior diagnostics, and the two selected trajectories are not a representative seed sample. The reference model remains the synthetic fixture; no connectome or fly-learning result follows from this test.

## Verification and execution record

The diagnostic exactly checked **112** saved training events for seed 2001 and **384** for seed 2002, plus every update vector in the two windows. The prior model-source manifest differs only at the two exactly pinned simulator paths already documented in A1/A2; saved events and the saved 96/384 reference probes matched. The first counterfactual attempt stopped before writing a result because a pickle hash from an in-memory session differed from one produced by a loaded clone despite identical raw update geometry. The runner was repaired to assert exact pre-update weights, eligibility, time and raw vector, exact A/B pre-state hash equality, and real-branch event/probe replay. The intervention, target, windows and thresholds were unchanged. No unaccepted counterfactual result was used.

The [independent audit](figures/successive_update_interference/audit.json) passed **2 trajectories, 34 frozen checkpoints, 32 real updates, 1,216 frozen note outcomes including the four causal probes, and 2,800 DOWN actions**. It recomputed update arithmetic/clipping, event and timing metrics, panel equality, source hashes, candidate selection, both saved reference probes and real-branch replay. The final regression suite passed **96 tests**. No learning-rate tuning, extra seed/window, production rule change or broader training run was performed.
