# Eligibility, timing and credit at synthetic outcome 373

**Status:** complete, 2026-09-30. This is a single, previously selected synthetic checkpoint, not a learning-success claim or a fly-circuit experiment. The [locked protocol](../configs/eligibility_timing_credit_diagnostic.json), [full machine-readable result](figures/eligibility_timing_credit/result.json), [source manifest](figures/eligibility_timing_credit/meta.json) and [independent audit](figures/eligibility_timing_credit/audit.json) retain every edge, branch, note, DOWN action and available timing error.

## Exact state and intervention

Seed **2002**, training outcome **373**, delivered dopamine time **371.725 s**. The real training judgement was `GREAT_300`, **25 ms late**, with utility **+0.875** against expected utility **−0.16280149**, giving RPE/dopamine amplitude **+1.03780149**. Exact deterministic replay intercepted the state immediately before that dopamine call. It recovered all 480 pre-update weights, eligibility values, raw proposals, bounds and the real after-weights from the A3 ledger. The checkpoint hash is `75efd8a69a68f5b060708d4fad360b75c45b807eba4a085ac5418ed4001ecef3`; the raw result also records neuron, queue, readout, reward, RNG and topology digests. Both full-update and no-update immediate frozen probes exactly reproduce the A3 counterfactual, including the full event/action records.

Every branch starts with that same checkpoint. It advances the dopamine/plasticity clock once, changes only the declared selected effective weights, then freezes plasticity and exploration for the same disjoint 32-note relative panel. Restoring each branch's pre-update weights yields the exact same post-clock checkpoint bytes as no update, checking that neuron state, queued arrivals, eligibility, predictor, RNG, topology and readout state did not change between branches. The complete panel and all DOWN times are in the raw result. No later training, learning-rate search or production-rule edit occurred.

The ten branch names, source-bin boundaries, clipping classification, eligibility-age cutoffs, opposite-RPE control and primary paired timing measure were [saved before new probe outcomes](../configs/eligibility_timing_credit_diagnostic.json). A component counted as reproducing *most* of the full timing advance only if its mean paired scored-attempt shift was in the same direction and at least half as large. An opposing component needed a paired delay of at least 10 ms. These definitions were not adjusted to the results.

## The proposal was broad; the applied update was localized

All **480** selected plastic edges are synthetic **relay→motor** connections: 40 relay sources, 32 motor cells, 12 targets per relay. They are not MaleCNS synapses. Each relay has an existing time-to-contact sensory parent, allowing a structural split by preferred cue time. Every edge had **positive** eligibility (minimum **0.142**, median **9.066**, maximum **14.490**); therefore positive RPE proposed potentiation on all 480. The raw proposal L1 was **790.485 mV**. The applied L1 was only **62.170 mV**: 309 weights were already at the **2 mV** upper bound, 354 proposed values exceeded it, and **171 edges actually changed**. The 45 clipped edges below the bound before the proposal contributed **18.444 mV** of applied change; the 126 unclipped edges contributed **43.726 mV**. There were no negative eligibility values or proposals.

| Existing cue-source group | Edges | Raw proposal L1 (mV) | Applied L1 (mV) | Changed edges | Real-proposal clipped edges |
| --- | ---: | ---: | ---: | ---: | ---: |
| Far, preferred 500/400/300/200 ms before note | 192 | 162.039 | **62.170** | **171** | 66 |
| Mid, preferred 150/100/75 ms | 144 | 363.169 | **0** | 0 | 144 |
| Near, preferred 50/25/0 ms | 144 | 265.277 | **0** | 0 | 144 |

Thus **79.5% of the raw L1** was proposed on mid/near sources, but all those weights were at the upper bound and had **no applied effect**. Within the far group, the applied L1 by preferred bin was **3.003, 14.691, 38.486 and 5.990 mV** at 500, 400, 300 and 200 ms respectively. These within-group magnitudes are descriptive; the individual bins were *not* separately intervened on and cannot be assigned a causal timing effect from L1 alone. All 32 motor targets receive selected edges; this diagnostic identifies the causal **source group**, not a special motor target.

The implementation stores aggregate eligibility, not addition timestamps. Exact replay snapshots at `t−450 ms` and `t−150 ms`, plus the known **150-ms exponential trace**, decompose eligibility at dopamine into contributions from additions aged **0–150 ms**, **150–450 ms** and **>450 ms**. Their L1 values were **3230.359**, **576.032** and **2.070**, respectively (total **3808.461**). The corresponding raw proposal L1 for 0–150 and >150 ms was **670.494** and **119.991 mV**. This recovers the age of eligibility **additions** under the implemented decay. It does not recover individual pre/post spike-pair lags, identify which prior note generated each addition, or imply biological eligibility timing.

## Matched frozen behavior

Negative paired timing means earlier scored attempts than the no-update branch. Each row used the same 32 notes. Each update branch's exact raw and applied vector, clipping list, all judgements and all DOWN/error records are in the [result](figures/eligibility_timing_credit/result.json).

| Branch | Applied L1 (mV) | GOOD+/32 | Mean utility | Mean signed attempt (ms) | Paired shift vs no update (ms) | DOWN count |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| No update | 0 | **17** | **−0.1113** | **−83.000** | 0 | 64 |
| Real full update | 62.170 | **0** | **−1.0000** | **−144.719** | **−61.719** | 64 |
| Far source only | 62.170 | 0 | −1.0000 | −144.719 | **−61.719** | 64 |
| Mid source only | 0 | 17 | −0.1113 | −83.000 | 0 | 64 |
| Near source only | 0 | 17 | −0.1113 | −83.000 | 0 | 64 |
| Full-proposal clipped edges only | 18.444 | 0 | −0.9609 | −140.625 | −57.625 | 64 |
| Full-proposal unclipped edges only | 43.726 | 0 | −1.0000 | −144.219 | −61.219 | 64 |
| Eligibility additions aged 0–150 ms only | 27.205 | 0 | −0.9609 | −141.625 | −58.625 | 64 |
| Eligibility additions older than 150 ms only | 44.655 | 0 | −0.9609 | −139.625 | −56.625 | 64 |
| Exact reversed RPE | 666.868 | 0 | −1.0000 | undefined: **no DOWN** | undefined | 0 |

The full update changed the 32 scored attempts **38–106 ms earlier each**; all became early MISS. Each branch normally generated 32 earlier null presses and 32 scored attempts; the full update shifted the scored attempts across the early MISS boundary. Hit-only MAE is undefined for full, far-only and unclipped-only because they have no hits. The table uses **all scored-attempt errors**, including early misses, and the raw ledger preserves null presses separately. The full branch had 4,644 motor spikes versus 6,307 with no update, so the effect cannot be described as a simple increase in total motor firing.

Far-source-only exactly reproduces the full applied vector and the full timing shift. Mid/near-only produce zero applied change and exact no-update behavior. The two disjoint clipping-status vectors sum to the full applied vector, yet **either one alone** reproduces most of the earlier shift. Both independently clipped age components also reproduce most of it; their applied vectors need not add to the full vector because each is clipped from the same original weights. These behavioral effects are **nonadditive** around the motor threshold/readout. There is no tested component that delays paired presses by the predeclared 10-ms opposing criterion. Raw size does not predict the timing effect: the largest raw source groups have no behavioral effect because of saturation.

The sign-reversal control uses **exactly `−1.03780149` dopamine** with the same eligibility. It depresses all 480 weights, applies **666.868 mV** L1 after lower-bound clipping and produces only **385 motor spikes** and **zero DOWN actions**. Because there are no attempts, there is no opposite-direction press-time estimate. It supports sensitivity to RPE sign but **does not show a reversed timing shift**. It is not a proposed learning rule.

## Mechanistic conclusion and limits

At this checkpoint, a positive global RPE following a rewarded, slightly late training press potentiated a **broad eligible set in the raw rule**. Saturation then confined effective plasticity to earlier preferred-cue relay→motor edges. That applied change **causally advanced** the frozen policy's later scored presses from already early (**−83 ms**) to too early (**−145 ms**). This is a concrete **reward-to-retained-timing credit mismatch**: reward for one successful explored action did not reinforce a useful retained timing policy at this state. It is not evidence that every far-cue edge was incorrectly credited, that the eligibility decay constant is wrong, or that this one update explains long-term failure. The 2002 trajectory recovered after subsequent updates in A3. The synthetic graph, fixed readout and bound saturation are engineering features; no fly biological conclusion follows.

**Single next diagnostic intervention, before any production-rule change:** from the same pre-dopamine checkpoint, apply the exact full outcome-373 update **except for the 300-ms preferred-cue source bin**, holding that bin's weights at their pre-update values. Compare with the already established full and no-update frozen controls on the identical panel. This one predeclared omission tests whether the bin containing **38.486/62.170 mV of applied change** is necessary for the early shift; its size alone is not causal proof. Record all actions and threshold crossings, and treat continued early shifts as evidence that other far-cue bins can suffice. This is a proposal only; it was not run here.

## Verification

The independent [audit](figures/eligibility_timing_credit/audit.json) passed all **10 branches, 320 frozen note outcomes, 576 DOWN actions and 480 edge reconstructions**. It recomputed source-group membership, raw/applied update and clipping arithmetic, age identities, event/action/timing summaries, A3 full/skip reference equality and result hashes. The source manifest explicitly records the two earlier permitted simulator-source hash drifts; exact training-event and A3 probe replay matched. The project's `unittest` regression suite passed **107 tests**. A first attempt with `pytest` could not run because that optional test runner is absent from the local environment; `unittest` is the suite used by this project. Two runner construction errors (an indentation error and an invalid simulator attribute reference) were fixed before the first diagnostic result; no branch/group or threshold was changed after viewing probe outcomes.
