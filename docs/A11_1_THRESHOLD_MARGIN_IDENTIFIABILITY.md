# A11.1 threshold-margin identifiability gate

**Stage result: INCONCLUSIVE under the predeclared timing-separation criterion.** At one exact seed-2002 outcome-373 checkpoint, the already locked A11 motor sign pattern and its inverse produced different motor spikes and both signed local first-action tags, but **all four branches crossed the fixed readout threshold on the same tick**. No weight update, training sweep, amplitude search or readout change occurred. M2 remains **NO**.

The [protocol](../configs/a11_1_threshold_margin_identifiability.json) was locked before branch outcomes. The [raw result](figures/a11_1_threshold_margin_identifiability/result.json) contains the pre-intervention checkpoint, four one-tick intervention checkpoints, all 480 tags, per-cell spike batches, readout ticks, actions and judgements. The [independent audit](figures/a11_1_threshold_margin_identifiability/audit.json) reconstructed the parent state, four branches, spike windows and note judgements.

## Why this exact state

[A11](A11_SIGNED_PERTURBATION_INFORMATION_GATE.md) showed that a 22-positive/10-negative motor pulse and its sign-inverted mirror yielded different motor spike populations yet both caused a first DOWN at **371.325 s**. A11.1 used the same seed, note, 32 motor IDs, sign vector and ±20-mV-equivalent drive. The checkpoint was fixed at **371.390 s**: exactly one 1-ms neural tick before A11's saved **no-pulse** trajectory first crossed at 371.391 s. A pre-intervention inspection found the readout key **up**, **5** spikes in its 20-ms window, and unchanged on threshold **10**. No other time or sign stream was tested.

Four clones had identical weights, neuron/queue/eligibility state, RNG, predictor, game, readout and cue input. On one tick only, the diagnostic set motor drive to **zero**, **shared +20**, **A11's locked ±20**, or its **inverse**. This was an exogenous diagnostic pulse; the continuation's exploration probability remained zero, synaptic plasticity remained disabled, and the production rule was untouched. The no-pulse branch reproduced A11's saved no-pulse action/judgement sequence exactly. The predictor's normal outcome update occurred only after the first crossing and did not affect the primary endpoint.

## Locked gate and observations

PASS required both signs in each signed branch's first-action tag, a positive 20-ms signed per-cell response contrast, and **at least one 1-ms tick difference** between signed and inverse first on-threshold rises, with first actions in both. A missing sign or nonpositive response contrast was FAIL; signs and motor response with identical crossing were INCONCLUSIVE.

| Branch | New motor spikes at first tick | Readout count at first tick | First crossing / first DOWN | First-action tags +/− | Judgement |
| --- | ---: | ---: | --- | ---: | --- |
| No pulse reference | 5 | **10** | **371.391 s**, null | 0 / 0 | MEH_50 |
| Shared +20 control | 27 | **32** | **371.391 s**, null | 480 / 0 | MEH_50 |
| Locked signed | 19 | **24** | **371.391 s**, null | 316 / 164 | MEH_50 |
| Sign inverse | 8 | **13** | **371.391 s**, null | 164 / 316 | MEH_50 |

The signed 20-ms motor-response contrast was **+26**. Thus the sign perturbation changed neural activity while both signed branches exceeded the fixed 10-spike threshold on the same tick. Crucially, the **unperturbed** branch already reached exactly 10 on that tick. With an intervention made one tick beforehand, an earlier crossing could not be observed on this 1-ms grid; only a delay was possible. The inverse's count of 13 did not cause one. This makes the selected state a **one-sided timing test**, a limitation of the stage design. The result does not establish that signed neural effects are never visible as action timing, or that a useful signed weight update exists.

The independent audit passed: exact A11 parent checkpoint and pre-count, **four branch replays**, **12 action replays**, **629 recounted motor spikes**, recomputed 20-ms threshold windows, first-action tags, note judgements and zero weight changes. The full regression suite passed **115 tests**.

## Contract interpretation and one next stage

A-C3 still has exogenous signed tags in this state but no validated mapping from those signs to beneficial weight changes. A-C4 remains open: the fixed readout collapses different motor spike counts into an identical first action at both A11 tested states. The no-pulse comparison shows that these particular interventions were applied at or before a threshold event, not whether selected plastic weights can place the *first* press correctly. A-C5–A-C7 remain unrun; the original M2 gate remains failed.

**Exactly one next proposed stage, not run: A11.2 perturbation dynamic-range audit.** Use the saved A11/A11.1 pre-states, neuron voltages, refractory state, synaptic drive and unchanged LIF/readout equations to calculate and independently verify which motor cells a single tick's ±20 drive can recruit and why the fixed threshold is reached in both mirror branches. Report the smallest model-derived drive interval in which sign patterns could yield different readout outcomes **without running a parameter or score search**. This is an information-capacity audit, not authorization to change the production amplitude or run a new learning rule. Stop after that analysis and reassess the fault tree.
