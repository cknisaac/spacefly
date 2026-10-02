# Fixed-weight reward-baseline and eligibility audit

Date: 2026-09-29. This is diagnostic experiment D from [the mechanistic diagnosis](MECHANISTIC_DIAGNOSIS.md). The circuit, saved weights and learning rule were not changed. It uses one previously selected failed case, so the measurements explain that checkpoint and do not estimate prevalence across seeds or establish a reliable learning system.

## Fixed checkpoint and sampling

The [protocol](../configs/context_baseline_probe.json) was saved before sampling. The experiment exactly replayed held-out plasticity-on seed **2013** through its 24th training outcome, then froze all 480 plastic weights. The selected checkpoint is immediately after the positive, harmful final update examined in [experiment C](UPDATE_DIRECTION_RESULT.md). At this point **350/480 edges are at the upper bound**, and the saved global reward predictor expects utility **+0.2301** after the previous MAX judgement.

Each trial clones the same complete checkpoint. Only the upcoming note's artificial cue gain changes, taking one of the original study's five values: 0.75, 0.9, 1.0, 1.1, or 1.25. The note time, earlier neural/game/readout state and all weights are fixed. The original exploration probability of 0.002 is enabled, but weight updates are disabled. Each gain has **32 independent, predeclared estimation streams and 32 disjoint evaluation streams**, for 320 one-note clones in total. All 320 future RNG seeds are distinct. The protocol fixes their SHA-256 construction; none were chosen based on outcomes.

At the first judgement/expiry of that note, the run records its true game utility `u`, every eligible edge value `e`, action times and dispositions, and the delivered judgement time. The raw [JSON ledger](figures/context_baseline_probe.json) contains all 320 trial records and all 480 eligibility values per trial. Reward estimates are calculated from the estimation split and applied only to the evaluation split. Every gain context receives equal weight in aggregate results, matching the original map generator's uniform gain choices.

## Reward estimates

| Cue gain | Utility mean from 32 estimation trials | Utility mean from 32 evaluation trials | Evaluation MISS /32 |
| ---: | ---: | ---: | ---: |
| 0.75 | −0.586 | −0.738 | 26 |
| 0.90 | −0.477 | −0.496 | 23 |
| 1.00 | −0.699 | −0.660 | 25 |
| 1.10 | −0.508 | −0.480 | 23 |
| 1.25 | −0.695 | −0.629 | 23 |

The balanced estimation mean over all contexts is **−0.593** (160 samples; descriptive standard error 0.059); the disjoint evaluation mean is **−0.601** (160 samples; standard error 0.058). Each individual context's estimate is noisier (standard error 0.118–0.145). All five current-policy context means are far below the saved **+0.230** baseline. Their differences from one another are modest relative to their estimation uncertainty. This is a strong sign of baseline **lag after the preceding MAX and policy/history change**. These data do not establish that five separate critics are needed.

## Proposed-update decomposition

For gain `g`, with the saved pre-trial baseline `b`, and using only the evaluation split:

\[
M_g(b)=\eta\,\mathbb E[e(u-b)\mid g]
=\eta\,\operatorname{Cov}(e,u\mid g)
+\eta\,\mathbb E[e\mid g](\mathbb E[u\mid g]-b),\qquad \eta=0.2.
\]

The second term is the **mean-drift term**. Eligibility is nonnegative, so a baseline above the actual context reward mean adds a negative component to many excitatory edges. The equation was checked at every edge for each context and for the context-weighted aggregate, with numerical error below 1e-12. These are mean *proposed* edge-weight changes in mV; sums across edges are diagnostics, not a voltage received by one neuron.

| Baseline used with evaluation samples | Baseline source | Mean over contexts of the drift vector's L1 norm | Aggregate raw update, signed sum over edges |
| --- | --- | ---: | ---: |
| Saved global EMA | +0.230 at checkpoint | **244.70 mV** | **−142.19 mV** |
| Fresh pooled mean | −0.593 from the disjoint estimation split | 26.02 mV | +103.87 mV |
| Gain-specific means | Five separate disjoint estimation means | **16.33 mV** | **+104.16 mV** |

The fresh pooled comparator was computed **after inspecting the predeclared global-versus-context result**. It is explicitly post hoc arithmetic on the same saved samples, with no added simulation or direction probe; its [separate calculation and data](figures/context_baseline_posthoc.json) make that distinction visible. It is necessary to avoid incorrectly attributing the entire correction to context specificity.

For the five-gain aggregate, the raw covariance term's signed edge sum is **+102.51 mV**. The saved-EMA drift term's signed sum is **−244.70 mV**, yielding the negative **−142.19 mV** total. With the gain-specific baselines, residual aggregate drift is **+1.65 mV** and the total is **+104.16 mV**. The saved-global and gain-specific raw vectors have cosine similarity **0.059**, with opposite signs on **145/480 edges**. The fresh pooled and gain-specific proposed vectors have cosine similarity **0.99976**. At this checkpoint, **the stale global estimate is the major measured source of the proposed-update change; gain-specific calibration adds comparatively little**.

This is an empirical decomposition under the fixed checkpoint and exploration process. A positive covariance term still is **not** proof that the eligibility rule estimates a useful policy gradient.

## Weight bounds and matched direction probes

The checkpoint already has 350 upper-bound edges. Applying each *full mean proposed vector* at this fixed state would clip **220 edges above the cap and 12 below zero** for the saved-global baseline, or **322 above the cap** for the gain-specific baseline. These are hypothetical proposals, not performed learning updates. The gain-specific raw vector has L1 magnitude **121.82 mV** across edges, but its clipped applied vector has only **12.15 mV**. Its positive covariance-driven components are mostly unable to grow at the current saturated weights.

To test orientation without selecting a step size from outcomes, each clipped proposed vector was scaled by the **same rule as experiment C**: at most 0.004 mV displacement on any edge. From identical copies of the checkpoint, the no-change, small saved-global, and small gain-specific directions were run through the original 16 frozen notes, first without exploration and then with the three matched future exploration streams from C. No probe weights were updated further.

| Probe | No change | Small saved-global direction | Small gain-specific direction |
| --- | ---: | ---: | ---: |
| Exploration off, GOOD+ /16 | 0 | 0 | 0 |
| Exploration off, mean utility | −1.000 | −1.000 | −1.000 |
| Exploration on, GOOD+ range across three streams | 2–3 | 2–3 | 2–3 |
| Exploration on, mean utility range | −0.727 to −0.688 | Same | Same |

Every judgement tier matches the no-change branch. One small saved-global probe changes one attempted-press time by 1 ms in one exploration stream; it does not change utility. The gain-specific direction changes no press time in these four probes. The small-probe reward is therefore **silent at this motor/readout resolution**. It neither validates a gain-specific critic as a learning fix nor shows that the saved global direction is behaviorally harmless under larger updates.

## Interpretation and limits

The originally suspected baseline mismatch is real at this checkpoint: reward expectation is +0.230 while the current policy's mean utility is about −0.6. That mismatch adds a large negative eligibility-weighted drift and can reverse the net proposed raw update relative to the covariance term. A fresh single pooled baseline removes most of that drift. The smaller additional improvement from separate gain means does not establish a scientifically necessary context-specific critic here.

Two blockers remain for a learning conclusion. First, the rule's positive eligibility-reward covariance is only a correlation; its relationship to better future actions was not demonstrated by the reward-silent 0.004 mV probes. Second, the 350 saturated edges cause extensive clipping, especially of the positive gain-specific proposal. Updating the critic at this already saturated checkpoint cannot retrospectively undo earlier weight dynamics.

The 320 one-note trials are independent only through their future RNG streams; they share the same neural checkpoint, note time and selected map. No trained policy was evaluated on untouched seeds. Gain values are an artificial time-to-contact input, not measured fly sensory contexts. The saved global baseline is a short EMA of prior game outcomes, not a biological DAN population. There was no model change, parameter search, longer training run, or advancement of the failed M2 gate.

## Reproduce

- [Predeclared protocol](../configs/context_baseline_probe.json)
- [Sampling, decomposition and small-direction script](../scripts/context_baseline_probe.py)
- [All sampled `e`, `u`, actions, moments and matched direction probes](figures/context_baseline_probe.json)
- [Explicit post hoc fresh-pooled arithmetic](../scripts/analyze_context_baseline.py) and [its output](figures/context_baseline_posthoc.json)

From the project root:

```powershell
$env:PYTHONPATH = 'src'
python -m scripts.context_baseline_probe
python -m scripts.analyze_context_baseline
```
