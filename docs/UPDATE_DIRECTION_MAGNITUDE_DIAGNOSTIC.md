# A2 — local update direction versus magnitude

**Status:** complete, 2026-09-30. This is a four-checkpoint synthetic mechanism diagnostic, not a learning-rule change or an M2 reliability result. The complete machine-readable [raw ledger](figures/update_direction_magnitude_diagnostic/runs.jsonl), [protocol](../configs/update_direction_magnitude_diagnostic.json), [manifest](figures/update_direction_magnitude_diagnostic/meta.json), and [independent audit](figures/update_direction_magnitude_diagnostic/audit.json) preserve every proposed/applied edge update, frozen judgement and DOWN action.

## Fixed design

Before any A2 probe outcome, the existing deterministic `on` training ledgers for seeds **2004** and **2002** were inspected for update geometry. The saved protocol selects, for each seed, the **first** one-based outcome from 193–288 with raw update L1 ≥ 20 mV and zero proposed bound hits, plus outcome 384. This yields **2004:213, 2004:384, 2002:200, 2002:384**. Seed 2004 was chosen as the previously identified weak/low-upper-bound late case; seed 2002 is the contrasting strong late case. The selection uses saved update geometry, not A2 probe utility. These are selected diagnostic seeds, not untouched confirmation seeds.

At each exact event, the runner intercepts the real `apply_dopamine` call **after judgement and reward-predictor update but before the weight change**. It saves the trusted whole-session state, including neurons, pending arrivals, eligibility, predictor, RNG, topology, motor/readout and game state. Four clones invoke the unchanged production plasticity method with `0`, `+0.05D`, `D`, and `-0.05D`. Thus the positive and negative **raw proposed** step magnitudes match at 5% of the actual raw vector. Bounds may make their *applied* magnitudes unequal; those differences are reported, not corrected by another chosen step. The negative branch is diagnostic only.

Every clone then plays the same previously fixed, disjoint 32-note probe panel at the same relative offsets and cue gains. Plasticity and exploration are disabled in the probes. Initial RNG and all nonweight state match; the runner restores each branch's weights and asserts the complete checkpoint equals the zero-branch checkpoint. The full branch's effective weights and canonical loaded checkpoint reproduce the actual post-update state. Both 384 full branches reproduce the saved longitudinal common probe exactly. Probe outcomes never feed training or selection.

The longitudinal study's saved simulator hashes differ from the current scale-study simulator files at only the two previously documented, exactly pinned paths. A2 required **exact replay of all 384 training events for each seed**, all saved milestone state summaries and the selected update diagnostics before accepting any row. The observed differences in these probe branches are therefore local effects of changing selected plastic weights in the reconstructed synthetic state, subject to the stated clipping and finite-panel limits.

## Results

Mean utility is per 32 frozen notes; GOOD+ is secondary. The common panel has a discrete judgement scale, so equal utility can coexist with changed press times.

| Seed:outcome | No update | 5% positive | Full actual | 5% negative | Full GOOD+ | Full clipped edges | Full applied/raw L1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2004:213 | −0.9609 | −0.9609 | **−0.2383** | −1.0000 | 11/32 | 0 | 100.0% |
| 2004:384 | −1.0000 | −1.0000 | −1.0000 | −1.0000 | 0/32 | 79 lower | 65.1% |
| 2002:200 | 0.3281 | 0.3281 | **0.5977** | 0.3281 | 32/32 | 0 | 100.0% |
| 2002:384 | −0.8340 | **−0.9609** | **0.1133** | −0.8340 | 25/32 | 289 upper | 43.1% |

For the two no-clipping real updates, full application helped on this frozen panel. At 2004:213 it converted 28 MISS/4 MEH to 11 GOOD/13 OK/8 MEH; hit timing MAE fell from 127 to 83.5 ms. At 2002:200 every branch had 32 GOOD+; the full update improved judgement quality and hit MAE from 52.22 to 35.59 ms. The 5% positive step changed some exact DOWN times in both cases, but did not change mean utility or judgement counts. The negative step clipped **334** and **307** edges respectively, so its applied vector was much smaller than its equal-raw-magnitude positive counterpart.

At 2004:384, all four branches remained at 32 MISS and utility −1. The real update had raw L1 16.04 mV and applied L1 10.44 mV; 79 lower-bound edges clipped. Some press times changed, but the panel stayed score silent. This checkpoint is **inconclusive** for direction versus magnitude.

At 2002:384, the 5% positive branch worsened utility by **0.1270** versus no update (17 MEH/15 MISS became 4 MEH/28 MISS). The full real update improved utility by **0.9473** versus no update, produced 25 GOOD and 7 OK, and reduced hit MAE from 120.35 to 68.25 ms. It also changed DOWN count from 32 to 64, with 32 null presses; all actions are in the ledger. The 5% negative branch had the same mean utility as no update and clipped 118 edges. The full raw L1 663.56 mV became applied L1 286.31 mV after 289 upper-bound hits; the raw/applied vector cosine was about 0.769. This is a nonlinear, clipped response. It is **not** the stipulated direction-error signature, because the negative branch did not improve behavior, and it is **not** the stipulated overshoot signature, because the full update helped.

The source events' rewards, previous predicted utilities, RPEs and eligibility summaries were, respectively: 2004:213 `−0.6875/−0.3705/−0.3170`, mean eligibility `1.837`; 2004:384 `−1/−0.2894/−0.7106`, `0.235`; 2002:200 `−0.375/−0.0411/−0.3339`, `3.009`; and 2002:384 `1/−0.0465/+1.0465`, `6.605`. All 480 per-edge eligibilities, raw updates, applied updates and bound-hit slots are in each raw row. Each probe row contains its own per-note reward, expected reward, RPE, signed hit error, judgement and every DOWN disposition/time. Timing MAE is undefined where a branch has no scored hits; it is never replaced with zero.

## Interpretation and limits

1. **Locally harmful direction?** There is a narrow local warning: 5% of the raw positive direction harmed utility at **2002:384**. The corresponding full update helped, and the negative step did not help. This does not establish a wrong credit-assignment direction or a generally harmful training update. The other two informative full updates helped; the fourth checkpoint was score silent.
2. **Useful direction with full-step overshoot?** **No observed case.** None had a beneficial small positive step followed by a harmful full update. A useful direction may still exist in other states, but A2 gives no overshoot evidence under its predeclared criterion.
3. **Material clipping?** **Yes, in both late cases.** Full applied/raw L1 was 65.1% at 2004:384 and 43.1% at 2002:384, with 79 lower and 289 upper bound hits. At the two middle checkpoints the real full vector was unclipped. Several negative branches also clipped heavily; their applied magnitudes are not matched to the positive branches. Clipping attenuated components without reversing their sign.
4. **Consistent cases?** **No.** Two unclipped full updates helped, one late update was score silent, and the other late case had a harmful 5% step followed by a beneficial clipped full update. The finite 32-note panel and nonlinear keyboard/readout thresholds limit how far local changes generalize.
5. **Single next learning-mechanism question:** Do **successive outcome-specific dopamine/eligibility updates undo earlier useful timing changes** as the same network continues, even when some isolated updates help? A separately authorized short, fixed continuation from matched states could compare retained frozen behavior with those subsequent updates enabled versus disabled, using matched exploration and a disjoint panel. No such continuation was run here.

The direction/magnitude diagnosis is confined to these four predeclared checkpoints. There was no step-size search, extra seed, altered production rule, long training sweep, fly simulation or claim that synthetic reinforcement learning now passes controls.

## Execution and verification

The first execution reproduced all 384 seed-2004 training events but stopped before writing a result row when a raw pickle-byte comparison between an in-memory post-update object and a loaded clone failed. The integrity check was strengthened to compare effective weights and canonical loaded checkpoint bytes; experimental branches and settings stayed fixed. The completed rerun accepted all four rows. The independent audit initially used a looser clipping-comparison tolerance than the runner; matching the runner's `1e−12` definition fixed only the auditor. The final audit passed **4 cases, 16 branches, 512 frozen outcomes and 800 DOWN actions**, recomputing vector arithmetic, clipping, utilities, judgements, panel identity, source hashes and both saved 384-probe references. The regression suite passed **96 tests** before A2 execution and was rerun after the final documentation/code changes.
