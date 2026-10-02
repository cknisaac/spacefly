# A9: one structural timing-controllability witness

**Stage result: FAIL for the predeclared first-action existence witness.** Synthetic Branch A, one seed-2002 outcome-373 checkpoint and one fixed 32-note frozen panel. The [locked protocol](../configs/a9_timing_controllability_witness.json), [raw result and actions](figures/a9_timing_controllability_witness/result.json), [checkpoint](figures/a9_timing_controllability_witness/witness_checkpoint.pkl) and [independent audit](figures/a9_timing_controllability_witness/audit.json) preserve the test. No training, parameter search, production edit or second constructed pattern occurred.

The one hand-specified configuration set all **192** selected relay→motor edges from the 500/400/300/200-ms preferred-cue classes to the existing **0-mV** lower bound. The 150-ms and later cue classes, all unselected edges, and all nonweight state remained exactly as in A8.2's no-update checkpoint. The same A5 probe froze plasticity and exploration.

| Measure | No-update reference | A9 constructed pattern |
| --- | ---: | ---: |
| First motor crossing on first probe note | 372.456 s, **269 ms early** | 372.523 s, **202 ms early** |
| Frozen scored GOOD+ | 17/32 | **32/32 MAX** |
| Mean hit timing MAE | 83.0 ms | **6.375 ms** |
| GOOD+ on **first** DOWN | 0/32 | **0/32** |
| First DOWN disposition | Null on the first note | **Null on all 32 notes** |
| DOWN count | 64 | **64: two per note** |
| Silent notes | 0 | 0 |

The first DOWNs in A9 were **188–211 ms early**, all ignored null presses. The next DOWN, 200 ms later under the fixed readout cooldown, scored MAX on every note; the first example was **−202 ms null → −2 ms MAX**. Thus a seemingly excellent 32/32 score and 6.375-ms judged-hit MAE still represented a two-press policy. Under A9's predeclared endpoint, the constructed pattern **failed** to witness even one first-DOWN GOOD+. This does not prove that no selected weight vector can produce a timely first press.

The independent auditor verified the exact 192-edge class mask, unchanged remaining weights and coupled state, reconstructed **140** motor on-threshold rises, replayed **64** DOWNs through the game, rejudged all **32** notes, and recomputed first-action associations. It passed. No probe learning or exploration occurred.

This result confirms an evaluation trap: scored GOOD+/MAE alone can strongly favor a cooldown-timed second action even after a large, structurally defined weight change. Future M2 confirmation must declare a first-action criterion in addition to the historical scored-judgement gate. A9 supplies no learned-policy result, no proof of unreachable first-action timing, and no validated correction.

## One next proposed stage: A10, not run

- **Name and question:** **A10 — signed, first-action credit design and causality gate.** Can one fully specified synthetic learning mechanism produce signed selected-edge credit tied to the first action while keeping target time out of sensory/motor code?
- **Why next:** A8.1 showed scored reward has the opposite sign from a first-action objective at all three selected harmful checkpoints. A8.2/A8.3 showed scalar sign reversal with the existing nonnegative eligibility did not yield a useful first-crossing correction. A9 showed 100% scored MAX can still have zero useful first actions. More weight-mask or threshold searches would not test the missing credit representation.
- **Hypothesis and outcomes:** A zero-mean motor perturbation tag combined with first-action utility can make selected-edge eligibility signed and action-indexed. It may pass deterministic causality/sanity tests or fail them; neither outcome yet predicts M2 performance.
- **Intervention:** Specify exactly one diagnostic-only candidate before training: on the existing Bernoulli exploration ticks (same 0.002 probability), draw an independent `±1` sign for each motor cell and apply the existing 20-mV-equivalent amplitude with that sign. Maintain a selected-edge trace formed from local presynaptic activity and the postsynaptic motor-cell perturbation sign, decaying with the existing eligibility time constant. At the first DOWN, use −1 utility for null/early MISS, existing utility for a valid first hit; at expiry without a DOWN use −1. Compute one first-action RPE and apply `η × signed_trace × RPE` only to the same 480 selected edges with existing bounds. Later same-note scored DOWNs remain game events but cannot train this candidate. Declare exact event order and baseline update once per note. This is an **engineering candidate**, not measured fly plasticity.
- **Controls:** Retain the original game, encoder, graph, motor readout, note maps, existing η/amplitude/probability/trace time constant and weight bounds. Keep an unchanged legacy branch available. Track the signed perturbation RNG independently so matched replay is possible.
- **Primary endpoint:** Design and deterministic unit/trace evidence that null first action generates one causal learning event, signed eligibility can be positive or negative, zero perturbation gives zero candidate update, and no later scored action changes the same note's candidate weights.
- **Secondary endpoints:** Sparse state cost, raw versus applied clipping, distribution of actual first actions under fixed exploration, reward-baseline behavior and exact checkpoint replay.
- **Predeclared interpretation:** A10 passes **design readiness only** if every causal/sign/selection invariant is implemented and audited; otherwise fail and revise the mechanism before behavior testing. No score improvement or M2 claim is made in A10.
- **Do not:** Tune the amplitude, rate, η, thresholds, cue bins or reward values; expose ideal press time to neural input; test multiple candidate rules; use old held-out seeds for final confirmation.
- **Output:** Versioned diagnostic design/config, unit and matched-state raw traces, independent audit, report and handoff update.
- **Stop:** Stop after A10. A separately specified development cohort is required before production adoption or fresh held-out M2 evaluation.
