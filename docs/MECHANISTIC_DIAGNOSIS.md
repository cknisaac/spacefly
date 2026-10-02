# Mechanistic diagnosis of the synthetic learning failure

Date: 2026-09-29. Scope: the current 128-neuron synthetic lane-one circuit, its saved overnight study, and targeted causal replays. No model parameters were optimized, no production model code was changed, and no new long training study was launched. M2 remains incomplete.

## 1. What actually failed

The system does not show zero improvement. Across the 32 held-out plasticity-on trials, the fraction of notes scoring GOOD or better was:

| Notes in each independent trial | GOOD+ |
| --- | ---: |
| Training 1–8 | 27.73% |
| Training 9–16 | 35.16% |
| Training 17–24 | 42.58% |
| Frozen 25–40 | 46.09% |

These are pooled outcomes at different points in a run, with changing notes and exploration removed during evaluation. They are not evaluations of successive checkpoints on one identical probe set. They establish an improving observed outcome trend, not a clean convergence curve.

The actual failure is **reliable, precise autonomous timing across seeds**. Frozen GOOD+ means were 46.1% on, 0% off, and 11.5% shuffled. On beat off in only 16/32 seeds and shuffled in 15/32; the declared requirement was 24/32 against each. Hit-only mean absolute timing error was 60.6 ms, exceeding 40 ms. Sixteen seeds had no GOOD+ frozen outcomes. All 143 on-condition frozen MISS records were early attempted presses, not automatic expirations. This argues against a universal inability to generate motor output.

The overnight job was **192 separate trials**, each starting from the same initial graph and weights and receiving only **24 training outcomes**, followed by 16 frozen outcomes. It was not one network trained continuously for six hours. It completed in 30.87 minutes. Seed variation changes map/exploration, not initial topology or initial weights. See [the overnight report](OVERNIGHT_RESULT.md).

## 2. New causal evidence

### Method and limits

The diagnostic script replays the saved configurations for three deliberately selected cases: seed 2000, the first seed with all frozen outcomes GOOD+; 2009, the first with all frozen notes hit but none GOOD+; and 2013, the first with all frozen outcomes MISS. Selection is based on known outcomes. These cases distinguish possible mechanisms; they do not estimate their prevalence across all seeds. The original full-cohort statistics above retain all 32 seeds. These seeds are now diagnostic data, not fresh confirmation data.

All three instrumented replays reproduced the saved summaries exactly. For each of 72 training outcomes, all 480 proposed weight changes were independently recomputed and clipped: **34,560 weight comparisons agreed**. For three selected synapses per outcome, eligibility was independently recomputed as an explicit sum over all earlier pre/post spike pairs: **216 comparisons**, maximum absolute discrepancy about 3.6e-15. This checks the intended formula, not whether that formula is an effective learning rule.

### A. A MAX can be produced by exploration and the cooldown

For the last training note of seed 2013, two clones start from the identical complete state after note 23. Weight updates are disabled in both; the only changed setting is whether the existing exploration pulses are allowed. Both consume the same RNG stream.

| Same note, same weights | DOWN times relative to the note | Result |
| --- | --- | --- |
| Exploration enabled | −411 ms: null; −208 ms: null; −8 ms: hit | MAX |
| Exploration disabled | −332 ms: null; −132 ms: early miss | MISS |

The −411 ms action coincides with an exploration pulse and 32 motor spikes. Subsequent presses are approximately one 200 ms cooldown apart. Removing exploration changes the phase of this press sequence and changes the same note from MAX to MISS. This is direct evidence that this particular successful training outcome depends on exploration/readout dynamics; it is not proof of a learned autonomous near-zero-time response. The same ablation leaves the final training outcome unchanged in seeds 2000 and 2009, so the effect is not universal.

In frozen evaluation, seed 2000 makes 16 null presses followed by 16 hits, and seed 2013 makes 16 null presses followed by 16 early misses. Even the successful case uses repeated presses. Null presses correctly generate no osu judgement; they nevertheless alter the readout's cooldown. The current objective has no separate cost for them. This is a task-design issue, not an incorrect MISS label.

### B. Positive updates can advance an already early response

After the last training outcome, two more clones retain identical membrane, synaptic-current, queue, readout, game and RNG state. One retains the actual last weight update; the other restores only the pre-update weights. Both then evaluate the next note with exploration and updates off.

| Seed | Last training signal | Next error with update | Next error with update undone | Effect |
| --- | --- | ---: | ---: | --- |
| 2000 | MISS, D = −0.849 | −25 ms | −35 ms | Negative update delays the response 10 ms |
| 2009 | OK, D = +0.152 | −111 ms | −110 ms | Positive update advances it 1 ms |
| 2013 | MAX, D = +0.855 | −155 ms | −137 ms | Positive update advances it 18 ms |

The paired branches have the same incoming queued events, whose weights were captured at emission by the existing simulator contract. Only future propagation uses the different effective weights.

Both branches have the same judgement tier in each comparison. The experiment proves a timing effect, **not a measured reduction in the discrete utility for that next note**. Seed 2013 misses even without the final update; that update worsens an existing early-timing problem rather than causing its entire failure. It would be incorrect to attribute the training-MAX/frozen-MISS contrast to this update alone: exploration and cue context also differ between those two notes.

### C. Updates are often large enough for clipping to dominate

Initial plastic weights are 0.04 mV; bounds are [0, 2] mV. Eligibility is an unnormalized sum of spike-pair contributions. The configured eta is 0.2.

| Seed | Largest raw single-edge update | Outcomes with upper clipping / 24 | Edges at upper bound after note 24 |
| --- | ---: | ---: | ---: |
| 2000 | 4.176 mV | 7 | 0/480 |
| 2009 | 0.671 mV | 0 | 0/480 |
| 2013 | 3.252 mV | 10 | 350/480 |

The largest raw update in seed 2000 exceeds the entire permitted weight range. On its note 23, 384/480 edges reach the cap; the following negative update moves them off it. Looking only at final saturation would miss this instability. In seed 2013's final update, raw absolute change totals 518.28 mV across edges but clipping permits only 44.43 mV. These sums describe aggregate edge changes, not a membrane voltage.

Clipping is confirmed and likely affects dynamics. It is not a complete explanation: seed 2009 has no upper saturation yet fails the GOOD+ criterion on every frozen note.

## 3. Separate the four problem classes

### Software bugs and verification gaps

**No causal implementation error has been demonstrated in the audited learning path.** Selected traces decay and accumulate according to their specification; dopamine is applied with the intended sign; weight overlays affect future transmissions; the replays are deterministic. The full existing suite passes **80 tests**. Frozen outcomes contain no weight changes. All training MISS events have negative RPE. There is no evidence here of a reversed reward sign, a disconnected plasticity update, or accidentally training during evaluation.

The checks have limits: the independent trace oracle covers three synapses per replay, the model-level causal branches cover three selected seeds, and the existing tests do not prove reward-gradient correctness or reliable learning.

A small confirmed configuration bug is unrelated to the recorded failure: `TinyBrainConfig(readout_on_threshold=2)` is accepted, but constructing its session fails because the readout's default off-threshold is also 2 and must be strictly smaller. The overnight study used threshold 10. This should be fixed as validation consistency, not advertised as a learning fix.

The study runner also does not compare current model hashes when resuming an existing ledger, and its deadline is checked between trials. Those are reproducibility/operational weaknesses. The audited run completed without resuming changed code; neither explains its early presses. The repository has no committed revision, although saved relevant source hashes match and this diagnostic records hashes of every model Python file.

### Mathematical problems

The implemented rule is:

\[
x_i(t)=\sum_{t_i<t}\exp[-(t-t_i)/80\text{ ms}],\quad
e_{ij}(t)=\sum_{t_j\le t}\exp[-(t-t_j)/150\text{ ms}]x_i(t_j^-),
\]
\[
u=2\,\mathrm{hitvalue}/320-1,\quad
D=u-b,\quad b\leftarrow b+0.1D,\quad
w\leftarrow\operatorname{clip}_{[0,2]}(w+0.2eD).
\]

1. **The eligibility rule is a correlation detector, with no demonstrated reward-gradient identity.** Every eligibility is nonnegative. Positive D potentiates every eligible excitatory edge; negative D depresses them. A pre/post correlation can be created when an external pulse, rather than the synapse, causes the motor spike. That association can sometimes be useful, but passing the four dopamine/eligibility gates does not prove that its expected update improves the policy. A stochastic spiking policy-gradient derivation includes sensitivity to the spike probability and its compensating non-spike contribution; the current deterministic LIF plus common motor-pulse process has no such derivation. This is a limitation of this implementation, not a claim that three-factor learning cannot work. See [Florian's original derivation, equations 2.3 and 2.9–2.19](https://florian.io/papers/2007_Florian_Modulated_STDP.pdf).

2. **A global reward mean need not remove drift from positive eligibility.** Conditional on a fixed pre-trial baseline b and stimulus context c, before clipping:

   \[
   \mathbb E[\Delta w\mid c,b]/\eta
   =\operatorname{Cov}(e,u\mid c,b)
   +\mathbb E[e\mid c,b](\mathbb E[u\mid c,b]-b).
   \]

   The second term can be nonzero when cue gain changes both firing/eligibility and expected reward. Even removal of this term would not automatically make the covariance term the correct timing gradient. Stimulus-dependent baselines for reward-modulated Hebbian rules are discussed in [Frémaux, Sprekeler and Gerstner (2010)](https://pubmed.ncbi.nlm.nih.gov/20926659/). Its applicability here is a mechanistic hypothesis; a biased expected update has not yet been measured in this circuit.

3. **Small RPE at a mediocre policy is not a sign bug.** For a constant repeated utility u, the implemented baseline gives `D_n = (u - b_0) * 0.9^(n-1)`. Learning drive diminishes even if the outcome is a poor early OK. Some worse-than-perfect outcomes correctly get positive surprise: 34 of 230 training MEH/OK outcomes have positive RPE. That means better than the running expectation, not good in absolute terms. Artificially forcing all hits to have positive dopamine would not resolve the missing credit-assignment argument.

4. **Judgement utility is piecewise constant in timing.** Moving an early press by 1 or 18 ms can leave utility unchanged. Timing variation must cross reward boundaries to provide a preference between actions. Timing error should be measured diagnostically; silently adding ideal-time shaping would change the experiment.

### Dynamical problems

**Exploration is a strong shared actuator.** Each accepted exploration event injects 20 mV drive into all 32 motor neurons for one 1 ms tick. An otherwise resting, nonrefractory motor neuron receives `20*(1-exp(-1/10)) ≈ 1.90 mV` from that pulse, above its 1 mV threshold. Actual pulse responses in the replays often contain all 32 spikes, exceeding readout threshold 10. Refractory state and inhibition explain partial or absent responses. This is not a small independent fluctuation at a plastic synapse.

**Readout dynamics can determine the judged timing.** The fixed decoder integrates spikes over 20 ms and imposes a 200 ms cooldown after every DOWN, including null presses. Sustained cue-driven firing can therefore generate a sequence whose first accepted press is determined by its phase modulo the cooldown. The pulse ablation demonstrates this mechanism in one case; the 32 frozen DOWNs in both seeds 2000 and 2013 show it persists without exploration.

**Potentiation can make a rising response earlier rather than more precise.** Increasing excitatory weights on the rising side of a cue generally advances first threshold crossing locally. Broad 55 ms sensory tuning, an 80 ms presynaptic trace and 150 ms eligibility retain activity preceding the judged press. Reinforcement can strengthen that earlier drive. The actual next-note branches demonstrate advancement, but recurrence, inhibition and cooldown make a globally monotone first-passage argument invalid. Oversized updates and clipping further invalidate a small-step approximation.

**An early resolved press removes the later learning opportunity for that note.** Once the game resolves a note, the encoder advances to the next unresolved note. The circuit cannot observe what would have happened later in that same trial. Exploration only adds excitatory motor drive; there is no explicit exploratory suppression or deliberate delay of the first action. Inhibition, refractory effects and cooldown can still delay later actions, so later timings are not mathematically impossible. Their exploration is indirect and confounded by the decoder.

These effects explain a plausible combination: reward-dependent acquisition of motor drive, sometimes successful cooldown-phase alignment, poor autonomous timing, and sensitivity to the last few large updates. Their population-level contributions remain to be quantified.

### Conceptual and experimental problems

- **The gate checks necessity, not optimization.** Recent activity plus dopamine causing a weight change is necessary for this proposed mechanism, but says nothing about whether that change improves future reward. The next gate must test update direction and repeatable frozen behavior.
- **A hit need not be a single well-timed action.** The current reward ignores extra null presses. A controller that repeatedly taps can earn MAX. It is legitimate to preserve osu judgement semantics; if economical actions are intended, that is a separately declared objective and metric, not a software relabeling of null presses.
- **Twenty-four learning events cannot establish asymptotic failure or convergence.** More independent seeds estimate reliability; they do not give each network more practice. Conversely, simply running longer is not justified while update direction and clipping remain unresolved.
- **The shuffled control has a narrower interpretation.** It preserves the multiset of raw learning utilities, then recomputes an EMA baseline in the shuffled order and delivers outcomes at its own action times. It does not preserve the on-run dopamine sequence, signal magnitude distribution, or reward timestamps. It tests dependence on outcome order/association, not a perfectly matched intervention on reward timing alone.
- **Capacity and transfer remain different questions.** Seed 2000 demonstrates that the allowed circuit can achieve 16/16 GOOD+ on its frozen map, albeit with extra presses. It does not establish a robust one-press policy across maps. Artificial exact time-to-contact input, sparse slow notes, and a synthetic excitatory relay route are engineering assumptions. Adding a fly connectome does not repair the learning-rule/readout contract or establish biological reward mechanisms.

## 4. Minimum discriminating experiments

The work above already supplies two small experiments: (A) independent arithmetic/replay checks, and (B) matched-state exploration removal and final-update removal. Do not repeat a threshold sweep. The immediate next experiment should be C. D and E are conditional follow-ups, not a mandate to run everything.

| Experiment | Fixed intervention and measurements | Competing explanations and decision |
| --- | --- | --- |
| **A — implemented rule vs wiring defect: completed** | Three exact saved-config replays; independent spike-pair sum and clipped update calculations; confirm frozen updates are zero. | Agreement makes a basic arithmetic/wiring explanation less likely in these cases. Any disagreement would require a code fix before interpreting dynamics. |
| **B — learned timing vs exploration/cooldown assistance: completed for three cases** | From the same pre-note state and weights, disable updates and compare exploration on/off. Record every DOWN, not only judgements. Separately undo only the last update in a frozen next-note clone. | Seed 2013's same-note MAX→MISS establishes exploration dependence. The paired final-update branches establish weight-dependent advancement. Other cases remaining unchanged prevents a universal explanation. Before a prevalence claim, extend these exact audits to all original 32 seeds with no tuning. |
| **C — wrong direction vs oversized step: completed** | Compared the unchanged pre-update weights, a predefined maximum 0.004 mV edge displacement along the actual applied update, and the full update from identical checkpoints in three selected seeds. Used the original 16 frozen notes without exploration plus three paired future exploration streams, logging utility, timing, every DOWN, and bounds. See [results](UPDATE_DIRECTION_RESULT.md). | The full final update helps seed 2000 (6→16 GOOD+) and harms seed 2013 (6→0 GOOD+) with exploration off; seed 2009 remains at zero. The small branch changes no judgement tier in any probe. Seed 2013's full update clips 350 proposed edges, but a flat small-step reward leaves wrong local direction versus oversized step unresolved. These selected cases do not estimate prevalence. |
| **D — baseline drift and eligibility covariance: completed** | At the frozen, saturated seed-2013 checkpoint, sampled 32 disjoint estimation and 32 evaluation streams for each of five original cue gains; recorded all 480 eligibilities and true utility per trial. Decomposed proposed updates under the saved global versus separately estimated gain baselines and applied C's fixed small-displacement probe rule. A fresh pooled baseline was added as explicitly post hoc arithmetic on the same samples. See [results](CONTEXT_BASELINE_RESULT.md). | The saved baseline (+0.230) substantially exceeds current-policy mean utility (about −0.6). Per-context drift L1 falls from 244.70 mV with that stale estimate to 26.02 mV with a fresh pooled baseline and 16.33 mV with gain-specific estimates. Positive covariance is not a policy-gradient proof; extensive upper clipping and reward-silent small probes mean no learning fix is established. |
| **E — too few outcomes vs plateau/instability: only after the local mechanism checks** | Continue the same networks and unchanged configuration for a predeclared finite horizon, retaining weights across note blocks. Clone and freeze at 24, 96 and 384 outcomes onto the same disjoint probe panel; do not let probe results feed training or choose settings. Log update norms, clipping, action counts and baseline error. Keep paired off/shuffled controls and report all chosen seeds. | Consistent frozen improvement with more outcomes supports insufficient experience. Cycling weights/press phases and non-improving probes support instability; declining RPE with unchanged poor behavior supports a plateau. Failure by 384 outcomes rejects that finite-budget criterion, not every possible training horizon. |

Predeclare the diagnostic probe maps, exploration streams, summaries, and stopping rules before C. Existing held-out seeds may be reused for explanation but cannot certify a subsequently modified model. A final reliability claim needs untouched seeds and the existing primary gate (or an explicitly revised gate declared before that study).

If clean autonomous timing appears unattainable under C despite usable reward variation, the next conditional test is a **constructive reachability check**: use recorded sensory/relay inputs and the exact LIF equations to construct one legal, fixed late-cue weight pattern within the existing topology and bounds. Label it a diagnostic oracle, not learned behavior. Its success would isolate a learning-rule failure; a failed construction alone would not prove impossibility. This avoids replacing mechanistic diagnosis with random weight search.

## 5. Recommended action and reproducibility

The most strongly supported current explanation is a mismatch between **what produces the successful training action** (sometimes an exploration-triggered, cooldown-timed press sequence) and **what receives credit** (broad, nonnegative pre/post eligibility on excitatory edges), compounded in some seeds by large clipped updates. Other seeds stall early without upper saturation. Global-baseline bias and insufficient experience remain competing, unproven contributors.

Experiments C and D are complete. Their opposing full-update effects, baseline lag, saturated weights, and silent small-step reward do not justify changing the learning rate or rule by intuition. A fresh pooled baseline removes most measured drift at the selected checkpoint; separate gain estimates add relatively little there. If a later diagnostic supports a step-size problem, derive an update bound from measured eligibility/weight scales and test that specific hypothesis. If the direction is wrong, formulate a local credit rule for the actual stochastic action mechanism and explicitly test the ability to learn later actions. Do not use connectome ingestion as a remedy for either problem.

Artifacts:

- [Diagnostic replay script](../scripts/diagnose_mechanisms.py)
- [Machine-readable diagnostics, all captured updates/actions and source hashes](figures/mechanism_diagnostics.json)
- [Original per-trial ledger](figures/overnight_synthetic/runs.jsonl)
- [Original protocol](../configs/overnight_synthetic.json)

Reproduce from the project root in PowerShell:

```powershell
$env:PYTHONPATH = 'src'
python -m scripts.diagnose_mechanisms
python -m unittest discover -s tests -q
```

The diagnostic uses trusted same-version in-memory checkpoints and deliberate inspection of private state. It modifies cloned weights/configuration for causal probes, leaves production source and original result files intact, and overwrites only its own diagnostic JSON. No gradient method, trainable decoder, arbitrary parameter search, fly data, or biological DAN model was added.

## Subsequent diagnostic status — 2026-09-30

The table above is the historical order of proposed tests: **E was later completed** in the [same-network continuation](LONG_CONTINUATION_RESULT.md), and its follow-up frozen exploration/map probe was partially completed for five seeds. The subsequently prepared [weight-rollback diagnostic](WEIGHT_ROLLBACK_RESULT.md) is now complete for those five seeds. Transplanting only 24- or 96-outcome selected plastic weights into otherwise identical 384-outcome states rescued several weak frozen policies on two maps; the 96-outcome vector sharply harmed the strong seed 2002, and the 24-outcome vector did not rescue seed 2004. All five unchanged late references exactly reproduce saved probes. This establishes weight-vector causality **at the fixed late state**, not the harmful update's location, a corrected learning rule, or population reliability. The current handoff and conditional next questions are in [FUTURE_DIAGNOSTICS.md](FUTURE_DIAGNOSTICS.md); no further experiment was run in this update.
