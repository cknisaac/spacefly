# Independent reward and modulation contract

The headless osu environment produces a `JudgementRecord`. It does not compute learning utility, reward prediction error (RPE), or a dopamine-like signal. `project_b.neuromodulation` consumes a resolved judgement after the game has judged it, independently of neurons, synapses, and plasticity.

```text
JudgementRecord → JudgementUtility → RewardPrediction → ModulatorySignal
                 hit value + u       V̂ before/after + δ  synthetic D
```

The default utility is the master specification's centered hit-value rule, `u = 2 × (hit_value / 320) − 1`. Hit value is a categorical judgement value, **not** game score or accuracy. Timing shaping and null-press costs are absent from this isolated path; a null press is an action disposition, not a MISS judgement.

| Judgement | Hit value | Utility |
| --- | ---: | ---: |
| MAX | 320 | +1.0000 |
| 300 | 300 | +0.8750 |
| 200 | 200 | +0.2500 |
| 100 | 100 | −0.3750 |
| 50 | 50 | −0.6875 |
| MISS | 0 | −1.0000 |

`RewardPredictor` holds one expected utility `V̂`, initially 0 by default. For each actual utility `u`, it first reports `δ = u − V̂`, then updates `V̂ ← V̂ + αδ`, with default `α = 0.1`. This is a global exponential moving average, not a context-specific or biologically measured prediction. With `V̂=0.2` and `u=0.8`, RPE is `+0.6` and the new expectation is `0.26`; another `0.8` outcome gives RPE `+0.54`. Repeated identical outcomes approach zero surprise. A MISS after repeated MAX judgements yields negative RPE.

`RPEModulator` emits a distinct, timestamped `ModulatorySignal` with `amplitude = gain × δ` and default `gain = 1`. A zero gain suppresses modulation while leaving utility and RPE intact. The signal is labelled `synthetic_dopamine_like`; it is **not** a modeled DAN spike, compartmental dopamine concentration, or a measured fly biological quantity. It is generated at the judgement timestamp. The independent module does not mutate neurons or synapses. The later [synthetic closed loop](CLOSED_LOOP.md) explicitly delivers this scalar to selected-edge plasticity at the current neural tick; biological feedback latency, DAN targeting and dynamics remain open.

`ReinforcementPipeline.process_judgement` accepts only `JudgementRecord`, processes records in nondecreasing event-time order, and returns a `ReinforcementEvent` retaining the original judgement, mapped utility, delivered learning utility, prediction/RPE, and modulation separately. It does not read or change game score, accuracy, neural state, or synaptic weight. The predictor can also be exercised directly with a numeric utility, as in the `0.2 → 0.8` example. Tests in `tests/test_neuromodulation.py` exercise all six judgement tiers through the complete chain, the numeric example, declining repeated surprise, unexpected failure, separation from game state, and invalid input rejection.

For the explicitly labelled **shuffled-reward experiment only**, `process_judgement(..., learning_utility=...)` substitutes a validated, prerecorded utility at the predictor input. `ReinforcementEvent.utility` still contains the game's actual mapped judgement, while `learning_utility` records what reached the predictor and synthetic modulation. The experimental runner permutes the plasticity-on training utility multiset within each seed and applies that order to a separate run. Its frozen evaluation uses actual judgement utility, with plasticity already disabled. This is an offline yoked control, not a causal reward policy for deployment.
