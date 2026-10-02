# Fixed-checkpoint update-direction probe

Date: 2026-09-29. Status: completed diagnostic experiment C from [the mechanistic diagnosis](MECHANISTIC_DIAGNOSIS.md). This analyzes an existing synthetic model and saved study. It does not select a learning rate, change production code, retrain the model, or establish a new held-out reliability result.

## Question and fixed protocol

Does the last actual update fail because its direction is locally unfavorable, or because the full step is too large? The [protocol](../configs/update_direction_probe.json) was saved before probing. It fixes three previously selected diagnostic seeds (2000, 2009, 2013), the checkpoint immediately after training note 24, the original 16-note continuation for each seed, and three weight branches:

\[
d=w_{24}-w_{23},\qquad
w_{\mathrm{none}}=w_{23},\quad
w_{\mathrm{small}}=w_{23}+\epsilon d,\quad
w_{\mathrm{full}}=w_{23}+d.
\]

Here `d` is the **applied, clipped** last update, including zero for unchanged edges. The small scale is `epsilon = min(1, 0.004 mV / max(abs(d)))`, so no edge moves more than 10% of its initial 0.04 mV weight. This rule was chosen from the starting weight scale, not probe outcomes. No changes occur on unselected edges. The three observed epsilons were 0.002 (seed 2000), 0.027073 (2009), and 0.004972 (2013).

Every branch starts from a clone of the **same complete checkpoint**: membrane/current state, in-flight events, readout/cooldown state, game state, reward predictor, and RNG state. Only effective plastic weights differ. The primary probe disables exploration and learning, as in the original frozen phase. A secondary probe enables the original exploration process while keeping learning disabled; it uses three predefined future RNG streams, identically time-indexed across weight branches. Map note times and cue gains are unchanged. The secondary streams measure sensitivity to exploration, not statistical uncertainty across independent maps.

The full-update/no-exploration branch reproduced each original saved 40-note summary exactly. The replayed first 24 training outcomes also matched the ledger. The script independently checked raw last-update eligibility and clipping against the checkpoint's effective weights. Original source hashes recorded for the overnight study matched the present model sources.

## Main results: exploration off

There are 16 probe notes per seed. Utility is the original centered hit-value utility, from −1 for MISS to +1 for MAX. Mean signed/absolute timing errors below include only scored non-MISS hits; early MISS attempts are counted separately. Every DOWN action, including null presses, is recorded in the [raw result](figures/update_direction_probe.json).

| Seed and last D | Branch | GOOD+ /16 | Non-MISS /16 | Mean utility | Hit error, mean signed / absolute | Null DOWNs | Early attempted MISS |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2000; D = −0.849 | No update | 6 | 6 | −0.297 | −34.0 / 34.0 ms | 22 | 10 |
|  | Small | 6 | 6 | −0.297 | −34.0 / 34.0 ms | 22 | 10 |
|  | Full | **16** | **16** | **+0.922** | −2.4 / 20.4 ms | 16 | 0 |
| 2009; D = +0.152 | No update | 0 | 16 | −0.492 | −97.4 / 97.4 ms | 0 | 0 |
|  | Small | 0 | 16 | −0.492 | −97.4 / 97.4 ms | 0 | 0 |
|  | Full | 0 | 16 | −0.492 | −99.8 / 99.8 ms | 0 | 0 |
| 2013; D = +0.855 | No update | 6 | 6 | −0.453 | −44.7 / 44.7 ms | 16 | 10 |
|  | Small | 6 | 6 | −0.453 | −44.7 / 44.7 ms | 16 | 10 |
|  | Full | **0** | **0** | **−1.000** | No hits | 16 | 16 |

The seed 2000 final negative update changes ten early MISS outcomes into GOOD-or-better outcomes. The seed 2013 final positive update changes six GOOD-or-better outcomes into early MISS outcomes. Both effects persist through the full 16-note continuation from otherwise identical states. Seed 2009 stays in its early OK/MEH regime, with a 2.4 ms shift earlier under the full update but no change in utility.

The small displacement changes **no judgement tier or mean utility in any seed**. In seeds 2009 and 2013 it also changes no recorded DOWN time. In seed 2000 it shifts four early MISS attempts 2 ms earlier and some corresponding null presses by 2 ms, without changing their judgement tier. Thus the small step is not completely inert, but the reward measurement cannot determine whether that local direction helps or harms. The full 2000 update has the opposite practical outcome—large benefit—because the readout and cooldown produce discontinuous action changes.

## Secondary results: exploration allowed, no learning

Values below summarize **three fixed future RNG streams per seed**. A range is the observed range across those three streams, not a confidence interval. Each stream is paired across weight branches; the count of actual exploration pulses may still differ after an earlier action changes which cue is visible.

| Seed | No update: mean utility range; GOOD+ range | Small: mean utility range; GOOD+ range | Full: mean utility range; GOOD+ range |
| --- | --- | --- | --- |
| 2000 | −0.258 to −0.102; 6–8 | −0.258 to −0.102; 6–8 | **+0.527 to +0.777; 13–15** |
| 2009 | −0.648 to −0.473; 0–1 | −0.648 to −0.473; 0–1 | −0.570 to −0.512; 0–2 |
| 2013 | −0.453 to −0.316; 6–7 | −0.453 to −0.316; 6–7 | **−0.727 to −0.688; 2–3** |

The strong full-step benefit in seed 2000 and harm in seed 2013 survive these particular exploration streams. Seed 2009's full-step effect changes sign or disappears across streams. All small-step utility results exactly match no update in every secondary stream. This does not estimate a population effect; the three seeds were chosen from known outcomes, and all streams reuse each seed's map and trained state.

## Size and clipping at the intervened update

| Seed | Max absolute raw edge proposal | Max actual edge change | Raw / applied total absolute change | Edges proposed beyond bound | Upper-bound occupancy, no → full |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2000 | 2.092 mV | 2.000 mV | 202.07 / 201.60 mV | 6 below zero | 384 → 0 |
| 2009 | 0.148 mV | 0.148 mV | 6.71 / 6.71 mV | 0 | 0 → 0 |
| 2013 | 2.288 mV | 0.805 mV | 518.28 / 44.43 mV | 350 above 2 mV | 323 → 350 |

These sums are across selected edges, not voltages seen by one neuron. Seed 2013's 350 clipped proposals demonstrate that the full update is very large relative to the allowed weight range. Seed 2000's beneficial update removes 384 edges from the upper bound. Seed 2009 remains a precision failure without bound clipping. These are distinct dynamical regimes.

## Mechanistic conclusion

The experiment **rules out a universal claim that the update direction is always wrong**: one real negative update is strongly beneficial on its matched continuation. It also **rules out a universal claim that the full step is always beneficial**: one real positive update is strongly harmful. The effects are causal within each selected checkpoint.

It **does not resolve wrong local direction versus oversized step for seed 2013**. The predefined small displacement causes no observable action or reward change there; the full step moves many weights to the cap and destroys six otherwise GOOD-or-better outcomes. Either an unfavorable direction, a threshold/cooldown phase transition driven by a large update, or both could produce this contrast. A flat discrete reward at the small displacement cannot certify a useful or harmful reward gradient. The seed 2000 small perturbation producing a 2 ms early shift while the full step greatly improves outcomes further shows why local timing and full-step utility cannot be read as a smooth curve.

The result strengthens the diagnosis that the learning system has **heterogeneous update effects and discontinuous motor dynamics**. Clipping is measured, but simply lowering the learning rate has not been shown to fix the policy. The next question is whether reward/eligibility covariance and the global baseline point toward better actions under fixed probe contexts. That is a separate, conditional experiment; it was not run here. Further confirmation of any changed rule would require untouched seeds and the original reliability gate.

## Reproducibility

- [Predeclared protocol](../configs/update_direction_probe.json)
- [Executable experiment](../scripts/update_direction_probe.py)
- [Complete JSON: every per-note outcome and DOWN action, three seeds × four probe streams × three weight branches](figures/update_direction_probe.json)
- [Original overnight ledger](figures/overnight_synthetic/runs.jsonl)

Run from the project root:

```powershell
$env:PYTHONPATH = 'src'
python -m scripts.update_direction_probe
```

The first execution of the diagnostic script failed on an internal assertion: the exploration-enabled branch intentionally sets `training_notes` to 40, while the result collector incorrectly used that mutable field as the original probe start. The collector now uses the fixed, predeclared start at note index 24. The failed execution did not save an incomplete result; the rerun completed all comparisons and wrote the JSON. No model source was changed.
