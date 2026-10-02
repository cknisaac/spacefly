# A11.2 signed motor pulse with temporal headroom

**Stage result: INCONCLUSIVE for bidirectional first-crossing control.** A single locked, exact-state intervention supplied 11 ms of potential advance before the unperturbed first motor crossing. The existing signed ±20-mV-equivalent pulse and its sign inverse each advanced that crossing by 10 ms. The two patterns recruited different motor cells, but the fixed readout threshold was exceeded by both on the first available tick. This does not establish a useful signed weight update or an M2 pass.

The [protocol](../configs/a11_2_bidirectional_headroom_gate.json) was saved before either signed branch at this checkpoint was run. The [raw result](figures/a11_2_bidirectional_headroom_gate/result.json) includes the exact pre-state, per-cell analytic next-tick voltage and drive thresholds, three complete branch spike/readout/action traces, and checkpoint hashes. The [independent audit](figures/a11_2_bidirectional_headroom_gate/audit.json) replayed those branches and recomputed the one-tick LIF and readout arithmetic.

## Locked question and method

[A11.1](A11_1_THRESHOLD_MARGIN_IDENTIFIABILITY.md) intervened one tick before the saved natural crossing, so it could only detect delay. A11.2 reused the A11 no-pulse trajectory at **371.380 s**, exactly 11 neural ticks before its already known natural first crossing at **371.391 s**. At intervention the key was up, the 20-ms readout window held **5** motor spikes against an unchanged threshold of **10**, and outcome 373 was unresolved. The prior DOWN at 370.605 s left the 200-ms cooldown nonbinding. No other checkpoint was tested.

The three branches were no pulse, A11's exact 22-positive/10-negative motor sign vector at ±20, and its exact inverse at ±20. Only those 32 motor external drives changed for one 1-ms integration interval. The cloned weights, eligibility, neuron and queued-arrival state, RNG, predictor, game, readout, sensory input and note were identical. Plasticity and exploration were disabled. There was no training, learning-rule change, readout adjustment, amplitude trial or score-based selection.

Before interpreting the branch continuations, the saved membrane voltages, synaptic drives, refractory times and pending arrivals were integrated with the unchanged LIF equation. The audit derived the external-drive coefficient and critical next-tick drive for every one of the 32 motors. It predicted the immediate spike sets and readout counts for the three locked drives exactly; the independent audit recomputed all 32 cells and verified each prediction against replay.

## Predeclared gate and observation

The bidirectional local gate required both pulse branches to retain first DOWNs, with one first on-threshold rise at least one 1-ms tick **before** no pulse and the other at least one tick **after** no pulse. A one-sided movement did not pass. Simultaneous early crossings or a qualitative action switch were inconclusive for bidirectional control. This was an existence test at one checkpoint, not a learning gate.

| Branch | New motor spikes on intervention tick | Readout count after tick | First threshold rise / first DOWN | Later scored DOWN | Outcome 373 |
| --- | ---: | ---: | --- | --- | --- |
| No pulse | 0 | 5/10 | 371.391 s, null | 371.591 s | MEH_50, −109 ms |
| Locked signed | 19 | 24/10 | 371.381 s, null | 371.581 s | MEH_50, −119 ms |
| Sign inverse | 8 | 13/10 | 371.381 s, null | 371.581 s | MEH_50, −119 ms |

Each branch had three key actions: first null DOWN, UP and later scored DOWN. Both signed branches shifted the first and scored DOWN 10 ms earlier than no pulse. Neither delayed the natural crossing. Different motor spike sets therefore remained hidden by the thresholded readout at this fixed amplitude. The result is **INCONCLUSIVE** about whether signed motor effects can cause bidirectional crossing changes in some properly resolved regime; it is a negative result for this exact ±20 intervention.

## Dynamic-range finding

At this pre-state, five old spikes remain in the next readout window, so five newly recruited motors suffice for an immediate crossing. The fifth recruitable cell in the positive-sign group needs **3.233323 mV equivalent** one-tick drive; the fifth in the negative-sign group needs **11.825782 mV equivalent**. Thus the saved LIF geometry predicts an *immediate threshold separation* for scalar amplitudes from **3.233323 mV inclusive to 11.825782 mV exclusive**: the signed orientation would cross on the next tick while its inverse would not. The locked ±20 pulse is above both group thresholds, which explains the observed 24/10 and 13/10 counts. These are exact-state model calculations, not empirically tested alternative amplitudes or biological voltage estimates. An immediate separation would still not establish that the inverse delays the later natural crossing; that requires a separate causal continuation.

## Audit, interpretation and stop

The independent audit passed: exact parent reconstruction and saved pre-state, **32** per-cell voltage/drive calculations, **three** complete branch replays, **nine** action replays, **441** motor spike recounts, readout-window recomputation, game judgement replay, unaltered weights and no exploration. The full regression suite passed **115 tests**. The production learning rule and fixed readout remain unchanged.

A-C3 useful signed timing credit and A-C4 local **weight-update** first-crossing control remain open; A-C5–A-C7 are blocked, and M2 remains **NO**. The one next proposed stage, **A11.3**, is a separately locked same-state test of **one** amplitude defined algebraically as the midpoint of the two critical drives above. It would reuse the same sign vector, inverse and no-pulse control, and require the same bidirectional criterion. This would test whether the readout's analytically identified unsaturated range reveals a delayed inverse crossing. It is proposed only; no new amplitude was applied in A11.2.
