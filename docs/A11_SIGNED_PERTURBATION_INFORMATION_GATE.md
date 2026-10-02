# A11: signed perturbation information gate

**Stage result: INCONCLUSIVE under the locked joint information-and-timing criterion.** A fixed independent ±20-mV-equivalent motor perturbation supplied signed local first-action tags and differentiated motor spikes, but it did not differentiate the **time** of the first motor threshold crossing from its sign-inverted mirror. This one-state diagnostic did not change weights or train a corrected learner. M2 remains **NO**.

The [protocol](../configs/a11_signed_perturbation_information_gate.json) was locked before branch outcomes. The [raw result](figures/a11_signed_perturbation_information_gate/result.json) contains the exact pre-pulse checkpoint, all branch interventions, 480-slot tags, per-cell spike batches, every readout tick/action and judgement. The [independent audit](figures/a11_signed_perturbation_information_gate/audit.json) replays all four branches, reconstructs the motor spike window and actions, rejudges the note and checks zero learning. This is synthetic Branch A only.

## Question and one locked intervention

A10 failed at A-C3 because a shared positive exploration pulse made all 32 motors fire once: population-centered participation was zero on every edge. A11 asked whether **one independently signed motor pulse** could supply usable first-action signs and whether reversing those signs changed first threshold timing. It tests the H3 sign-information hypothesis and one part of H4 motor controllability. It cannot test whether any weight update improves timing, retention or across-seed learning.

The exact seed-2002 outcome-373 historical trajectory was reconstructed to **371.324 s**, immediately before the already documented global exploration pulse. All four branches cloned that checkpoint. The known pulse draw and RNG were identical. Only the motor drive on that one tick differed:

1. **No pulse:** zero motor drive on that tick.
2. **Historical shared:** unchanged +20 drive on every motor cell.
3. **Locked signed:** +20 or −20 per motor cell from one deterministic SHA256 keyed sign stream.
4. **Inverse:** negate that one stream, an antithetic control rather than a searched second stream.

Each cell's sign was an independent symmetric pseudorandom choice, so its distribution had zero mean. The **single realized 32-cell pattern was 22 positive / 10 negative**, not exactly balanced. The pattern was not redrawn or selected after seeing behavior. After the intervention tick, exploration and synaptic plasticity were disabled identically. The encoder, graph, weights, queued events, game, readout, note and other state remained fixed. The shared branch reproduced the previously saved historical first-action state exactly. No ideal press time entered neural code. The production reward predictor still updated when the note eventually resolved; that update occurred **after** the measured first action/crossing and could not affect these endpoints. “Frozen learning” here means no synaptic weight change, not a frozen predictor baseline.

At the pulse, the diagnostic tag on selected edge `i→j` was its **causal presynaptic trace × motor perturbation sign**. If a first DOWN occurred, that tag decayed with the already existing 150-ms eligibility constant until the action and was attached to that action. No dopamine or weight update was delivered. This tag has a real exogenous sign; it is still not a measured synaptic timing gradient.

## Predeclared criterion and observed result

The locked PASS criterion required both signs in each signed branch's first-action tags, a positive signed per-cell motor-response contrast over the first 20 ms, and at least **one 1-ms tick difference** in first on-threshold rise between signed and inverse branches, with both first actions present. Missing signs or nonpositive motor-response contrast was FAIL; signs and response without a timing difference was INCONCLUSIVE.

| Branch | Motor spikes in first 20 ms | First motor on-threshold rise | First DOWN | First-action tags +/− | Resolved judgement |
| --- | ---: | ---: | --- | ---: | --- |
| No pulse | 0 | **371.391 s** | 371.391 s, null | 0 / 0 | MEH_50 |
| Historical shared +20 | 32 | **371.325 s** | 371.325 s, null | 480 / 0 | GREAT_300 |
| Locked signed | 22 | **371.325 s** | 371.325 s, null | 316 / 164 | GREAT_300 |
| Sign inverse | 10 | **371.325 s** | 371.325 s, null | 164 / 316 | GREAT_300 |

The signed response contrast `Σ_j sign_j × (spikes_j(signed) − spikes_j(inverse))` was **+32**. The mirror changed which cells spiked, and both action-tag vectors contained both signs. Yet **both reached the readout's fixed on threshold of 10 spikes at 371.325 s**. Their first DOWNs and complete subsequent action sequences matched. The no-pulse branch crossed **66 ms later**, showing that this pulse can causally shift motor timing in this state. The signed redistribution did not move the binary crossing because both realizations were at or above threshold. The downstream judgement differences are descriptive only; no branch learned.

The independent auditor checked the exact 372 historical outcomes preceding the state, the saved historical shared-pulse reference, all four interventions, **18 replayed actions**, **1,221 recounted motor spikes**, per-tick readout counts, independent game judgement and unchanged weights. It passed. The full regression suite passed **115 tests**.

## Contract interpretation and one next stage

At this single state, exogenous independent perturbation **solved the narrow sign-availability problem** that defeated A10's centered count: H3 cannot be stated as “no signed local tag can be available.” It has **not** shown that tag sign reliably says which way a synapse moves the first action. The identical signed/inverse crossing leaves A-C4 unresolved. The no-pulse comparison demonstrates aggregate motor timing control, while the 10-spike readout threshold can collapse distinct signed motor patterns into the same action. H5 retention and H6 reliability remain untested. A-C5–A-C7 are still blocked.

**Exactly one next proposed stage, not run: A11.1 threshold-margin identifiability gate.** Clone the already saved no-pulse A11 trajectory at the tick immediately before its first natural threshold crossing (371.391 s). Use the same fixed sign pattern and its inverse once, with the unchanged 20-mV amplitude, learning frozen and the fixed readout/game. Predeclare a timing separation criterion and audit the pre-intervention readout count before running. This asks whether signed effects on motor spikes are visible in first-action time near a threshold margin, rather than searching sign seeds, amplitudes, masks or readout thresholds. If both signs still cross together or create silence, report it without another pattern search. Authorization for A11.1 is separate; no further stage was run here.
