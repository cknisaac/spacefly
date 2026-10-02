# DN boundary operating-state contract V1

**2026-09-30 · Design only · Contract ID: `dn-boundary-v1`.**

**Decision:** the remaining DN boundary evidence/design blocker is closed by a **bounded ENGINEERING ASSUMPTION**, not by discovering the missing biological input. Circuit V1 is ready to proceed to **Electrical Model V1 specification**. No electrical implementation, dynamics gate or task baseline has passed or run. The existing 140-body policy remains non-runnable.

Read with [route closure](CIRCUIT_V1_ROUTE_CLOSURE.md), [sign audit](CIRCUIT_V1_SIGN_AUDIT.md), [Circuit V1](../CIRCUIT_V1.md), [biology](BIOLOGY.md), [assumptions](../ASSUMPTIONS.md) and [current state](../CURRENT.md). This contract applies to **DNa03 519624 and DNa02 523769 in the proposed 115-body circuit**, including both MBON32 output branches. It does not supply boundary models for other populations.

## 1. Meaning and causal separation

**ENGINEERING ASSUMPTION:** represent the **net tonic and fluctuating depolarizing influence of omitted upstream circuitry during one fixed, active-like operating state**. This is an artificial current-drive surrogate for a reduced DN subsystem. “Active-like” means a declared excitable state in which suppression/disinhibition can be tested; it does not assert that the model reconstructs walking, arousal, a turning command or an intact fly.

**LITERATURE-CONSTRAINED:** DNa02 voltage/activity depend on locomotor state. [Rayshubskiy et al., 2025](https://cdn.elifesciences.org/articles/102230/elife-102230-v1.pdf) reports walking-related depolarization and convergence of internal and sensory signals. [Fine-grained descending control of steering](https://www.sciencedirect.com/science/article/pii/S0092867424009620) reports greater DNa02 activity during walking than immobility. Neither source identifies the net omitted current for these two MaleCNS bodies, nor a shared DNa03/DNa02 input covariance.

**INFERRED:** treating an active state as a source of background drive is plausible for examining a disinhibitory route. Extending that interpretation to DNa03 and replacing heterogeneous inputs with one net current per DN are explicit reductions. **UNKNOWN:** the true magnitude, sign balance, shunting, covariance, state transitions and spectral content of missing drive in this specimen.

**ENGINEERING ASSUMPTION — causal contract:**

```text
fixed contract + independently fixed DN electrical scales + boundary seed
                              ↓
                 autonomous background event clock
                              ↓
                  current at DNa03 and DNa02

visible cue → sensory/KC/MBON route → DNs → fixed artificial readout
```

There is **no arrow into the background generator** from images, notes, map identity/BPM, desired key, ideal action time, reward, score, readout, neural activity or future state. The generator may read only its configuration, dedicated RNG state and elapsed simulation time. It must not restart at notes, trials, rewards or presses. A predetermined run start is not synchronized with task events. Later task runs carry its state continuously through note blocks.

**ENGINEERING ASSUMPTION:** the proxy adds no anatomical edges and does not turn any UNKNOWN edge positive. It represents an aggregate net depolarizing *hypothesis*, not “all missing synapses are excitatory.” Inhibitory fluctuations, conductance loading, receptor dynamics and multiplicative shunting are not reconstructed. Lower positive current represents less net drive, not an inhibitory synapse.

## 2. Omitted-input evidence

All counts in this section are **MEASURED source anatomy/annotations**, relative to the pinned traced-only MaleCNS parent, not measured physiology. Parent hashes and independent partner checks are in [route closure](CIRCUIT_V1_ROUTE_CLOSURE.md). Additional untraced or filtered contacts remain unquantified.

| Target | All incoming pairs / contacts | Retained pairs / contacts | Omitted pairs / contacts | Omitted contact share |
| --- | ---: | ---: | ---: | ---: |
| DNa03 519624 | 716 / 17,716 | 2 / 42 | **714 / 17,674** | **99.7629%** |
| DNa02 523769 | 1,138 / 23,957 | 2 / 310 | **1,136 / 23,647** | **98.7060%** |

**MEASURED:** retained input to DNa03 is MBON32's 38 contacts plus DNa02's four; retained input to DNa02 is DNa03's 255 plus MBON32's 55. The four feedback contacts remain anatomically present with UNKNOWN effect; this boundary contract does not sign or silently activate them.

| Major omitted source types, ranked by contacts | DNa03 | DNa02 |
| --- | --- | --- |
| First three | PFL2 830; LAL112 577; LAL051 495 | AN03A008 741; PS049 492; PS059 476 |
| Next three | LAL014 484; LAL122 432; LAL144 432 | AN04B003 425; PFL3 356; LAL126 318 |
| Additional examples | LAL121 406; LC33 381; PVLP138 357 | LAL083 312; GNG521 311; VES052 308 |

**MEASURED:** omitted sources span **485 / 731 distinct cell-type labels**, counting an unknown label as one category when present. DNa03's omitted contacts include 16,478 central-brain intrinsic, 545 visual projection, 403 descending and 229 ascending annotations; DNa02's include 19,197, 595, 1,598 and 1,660, respectively, plus other classes listed in the [new audit](figures/dn_boundary_input_audit.json). **INFERRED:** the missing input is heterogeneous; a single identified natural presynaptic population is not an adequate description.

**MEASURED:** the targets have **430 shared omitted presynaptic bodies**, **284 DNa03-only**, **706 DNa02-only**, and **1,420 unique omitted bodies** overall. Shared bodies supply **14,401 DNa03 contacts (81.48% of its omitted contacts)** and **17,331 DNa02 contacts (73.29%)**. **INFERRED:** common drive deserves representation. **UNKNOWN:** its functional sign, lag and correlation; shared anatomical parents do not imply an 81%, 73% or any other measured current correlation.

| Omitted contacts by presynaptic consensus transmitter | DNa03 | DNa02 |
| --- | ---: | ---: |
| Acetylcholine | 10,369 | 15,642 |
| GABA | 3,504 | 4,328 |
| Glutamate | 3,648 | 3,470 |
| Dopamine | 49 | 23 |
| Octopamine | 36 | 76 |
| Histamine | 1 | 4 |
| Serotonin | 1 | 0 |
| Unclear | 66 | 104 |

| Annotation confidence/accounting | DNa03 omitted parents | DNa02 omitted parents |
| --- | ---: | ---: |
| Individual prediction confidence: min / median / max | 0.3826 / 0.9283 / 0.9747 | 0.2400 / 0.9310 / 0.9747 |
| Missing prediction-confidence entries | 0 | 0 |
| Prediction versus consensus disagreements: pairs / contacts | 12 / 142 | 14 / 99 |
| Non-null ground-truth annotation: pairs / contacts | 53 / 650 | 214 / 2,695 |

**MEASURED:** confidence statistics are unweighted across omitted presynaptic bodies, using imported `transmitter_confidence`, which preserves source `predicted_nt_confidence`. **UNKNOWN:** confidence of the consensus or postsynaptic effect is not supplied by that number. Ground-truth is an annotation provenance field, not an assay in this specimen. The [official source documentation](https://male-cns.janelia.org/download/) distinguishes neuron-level predictions from synapse products. No transmitter category is automatically converted to a current sign, and neither contact count nor confidence scales proxy strength.

## 3. Minimal temporal model

**ENGINEERING ASSUMPTION — all constants and process choices below:** use a stationary tonic component plus bounded common and private fluctuations. Hold the behavioral-state mean fixed within a run. Add no slow state switching, oscillation, locomotor-phase or task-aligned component in V1.

For target `i` in `{519624, 523769}`:

```text
I_boundary,i(t) / I_ref,i = s × [1 + 0.20 X_common(t) + 0.20 X_i(t)]
```

- `X_common`, `X_519624` and `X_523769` are mutually independent symmetric random telegraph processes taking values −1 or +1. Initial signs are independent fair draws from their stationary distribution.
- Each process flips sign at independent exponentially distributed intervals with mean **100 ms** (flip rate 10/s). Its autocorrelation is `exp(−|lag| / 50 ms)`. This is a specified engineering timescale, not a measured DN constant or a note rhythm.
- The same common process reaches both targets at the same time. Private processes are independent. The *boundary fluctuations alone* have zero-lag correlation **0.5**, before any neuronal dynamics. Output spike correlation is not prescribed.
- The normalized instantaneous drive is always in **[0.60s, 1.40s]**, mean `s`, variance `0.08s²`. Boundedness is algebraic; no hidden clipping is needed.
- Model the proxy as a separately logged injected current, not as fabricated presynaptic spikes or an anatomical conductance. Do not infer inhibitory/excitatory conductances from its two fluctuation components.

**ENGINEERING ASSUMPTION:** equal fluctuation coefficients give a simple intermediate common/private split; they do not estimate correlation from the 430 shared bodies. The fixed-state approximation deliberately omits slow changes in arousal/walking and task-correlated external sensory input. Common delays, unequal target filtering and anticorrelated external pathways are omitted. These restrictions bound the interpretation of any later result.

**ENGINEERING ASSUMPTION — correlation control:** include a nominal-strength `independent-background` diagnostic. Replace the common process with two mutually independent copies, independent of both private streams. This preserves each target's marginal distribution, variance, support and 50-ms autocorrelation while changing boundary cross-correlation from 0.5 to 0. Do not simply delete the common term, which would confound correlation with variance. No slow-state or timescale sweep is authorized by this contract.

### Reproducibility requirements for later implementation

**ENGINEERING ASSUMPTION:** predeclare master seeds **31001, 31002, 31003**; these identify boundary realizations, not fly specimens or learning seeds. Use dedicated named common/private/replacement streams. Specify the RNG algorithm and seed derivation in Electrical Model V1 before generating any traces. An ablation must not consume a different number of boundary draws. Save generator states and next flip times in checkpoints.

Use the project's integer-microsecond timeline. Specify event rounding, simultaneous flips/arrivals/threshold ordering and the mapping of continuous intervals to that timeline before execution. The formulas above describe the continuous-time target process; any discretization error is an implementation issue to check, not permission to change the timescale. The initial state, event times and normalized trajectories must match across paired conditions regardless of their neural output. No traces are generated in this task.

## 4. Admissible strength envelope, fixed before osu

**ENGINEERING ASSUMPTION:** define a separate positive reference current for each DN from its *independently specified electrical model*, not from an observed task or a fitted firing rate:

```text
DeltaV_i = V_onset,i − V_rest,i > 0
I_ref,i = DeltaV_i / R_in,i          with R_in,i > 0 and finite
```

`V_rest` is the model's declared no-input equilibrium, `V_onset` its declared spike-onset reference, and `R_in` its declared small-signal input resistance at that equilibrium. In a passive-leak subthreshold model this is `g_leak × DeltaV`. It is a passive voltage-margin scale, **not a claim about measured rheobase**; adaptation/nonlinear conductances can make actual firing onset differ.

**UNKNOWN:** exact physical values for these MaleCNS bodies. **ENGINEERING ASSUMPTION:** Electrical Model V1 must choose class-specific values with literature/inference/assumption provenance and freeze them before boundary or task results. It must not alter these values to rescue a failed boundary condition. Models lacking a finite positive reference require an explicit contract revision before use; no hidden alternate normalization. The same normalized setting need not mean equal pA across cells, and no pA values are invented here.

| Predeclared level | `s` | Mean `I/I_ref` | Strict instantaneous support | Status |
| --- | ---: | ---: | ---: | --- |
| Low | **0.50** | 0.50 | **0.30–0.70** | ENGINEERING ASSUMPTION |
| Nominal | **1.00** | 1.00 | **0.60–1.40** | ENGINEERING ASSUMPTION |
| High | **1.50** | 1.50 | **0.90–2.10** | ENGINEERING ASSUMPTION |

**ENGINEERING ASSUMPTION — rationale:** center the envelope on a transparent voltage-margin scale; bracket it by half and one-and-a-half of that scale. The low condition is deliberately allowed to be subthreshold; it is not removed for failing to fire. This is a bounded engineering sensitivity range, not a literature-derived biological credible interval. Test these three joint levels, not a Cartesian search over separate DN gains or interpolated levels. Nominal is fixed at 1.00 regardless of which level later performs best.

**ENGINEERING ASSUMPTION — admission versus success:** these are the only candidate strengths permitted by V1. The later neutral dynamics gate can reject this contract/model combination. It cannot pick whichever level passes as a new nominal, widen the envelope, change fluctuation size, retarget rates or quietly discard a failing seed. Report all results. Revisions require a new version and a mechanistic, task-independent justification before another evaluation.

Parent connectivity motivates having a boundary and a common component; it contributes **no multiplier** to this envelope. The 99% cut does not justify 100-fold compensation. Published DN spike rates are contextual evidence, not injected-current estimates.

## 5. Mandatory controls and locked comparison

**ENGINEERING ASSUMPTION:** the letters below follow this request, not the earlier A=expansion/B=omission/C=proxy policy table.

| Condition | Boundary | MBON32→DN coupling | Purpose |
| --- | --- | --- | --- |
| **A: proxy enabled** | Fixed contract; low/nominal/high | Both source branches retained under the separately named effect hypothesis | Operating state of the proposed reduced model |
| **B: omitted boundary** | Exactly no injected boundary current | Same branches as A | Explicit deafferentation control, not intact-fly physiology |
| **C: MBON output disconnected** | Same low/nominal/high traces as A | Explicitly disable **519131→519624 and 519131→523769** functional coupling | Determine whether background/readout can explain apparent route output |
| **D: independent-background diagnostic** | Nominal; matched marginals, zero boundary cross-correlation | Same branches as A | Dependence on the assumed common drive |

No anatomical row is deleted. C retains DNa03→DNa02 and all other model choices; deleting only MBON32→DNa03 would leave its direct DNa02 path and is insufficient. Disable learning in every condition, including eligibility-dependent updates, exploration and reward-derived DAN drive. Do not change the synthetic learning rule or the existing source policy.

Use all three seeds for every condition: A and C at three levels (18 runs), B once per seed (3), and D at nominal (3): **24 future neutral runs**, not launched here. B needs no duplicate strength labels. Reuse the complete initial neural state and boundary trajectories within each pair; preserve these traces even when B does not inject them. No score-based seed or setting selection.

## 6. Task-independent operating-state gate

**ENGINEERING ASSUMPTION:** these are prospective engineering acceptance criteria, not measurements or universal DN firing limits. Evaluate each condition for **10 s settling + 60 s recorded neutral time**, with the readout detached and no osu engine, map, note clock, reward or ideal-action data present. Use one fixed neutral sensory condition, no sensory transients, no exploration and no plasticity. All other Electrical Model V1 settings and its explicit UNKNOWN handling must be locked first. Log retained synaptic drive separately from boundary drive so intrinsic/retained activity cannot be mistaken for injected current.

| Criterion | Required outcome / interpretation |
| --- | --- |
| Causal integrity | Background event trace depends only on contract, seed and elapsed time. Paired normalized traces are identical. No resets or adaptation to neural output. Any breach fails the gate. |
| Numerical safety, every level/seed/control | No NaN/Inf, invalid state, queue overflow, dropped events, undisclosed clipping or corrective state clamp. Normal declared spike/reset/refractory operations are not clipping. |
| Membrane boundedness | With `z=(V−V_rest)/DeltaV`, require non-spike state within **[−2, 2] for ≥99.9%** of recorded time and no non-spike excursion outside **[−4, 4]**. A model with explicit action-potential waveforms must predeclare its spike-state exclusion; it cannot mask arbitrary bad samples after observing them. |
| Saturation avoidance, every level/seed/control | Each DN mean rate **≤100 Hz** and refractory occupancy **≤25%** over the recorded interval. Also no full **1-s bin** with refractory occupancy >50%. These are deliberately broad engineering ceilings, not a literature fit. Log maxima and every violating bin. |
| Nominal active-state criterion | In **A and C at nominal**, each DN in every seed emits **≥60 spikes in 60 s** (≥1 Hz) and has no continuous silent interval longer than **30 s**, while satisfying all safety limits. This requires an active test state without a narrow target rate. |
| Low and omission controls | Silence is allowed at low strength and in B. It is not a reason to raise current or reject those results. D may be silent; report this as dependence on the shared-input assumption rather than selecting a different correlation. |
| Reproducibility | Same seed/config/state reproduces boundary events and deterministic CPU outputs; checkpoint continuation preserves the autonomous background clock. Electrical Model V1 must additionally pass its numerical convergence checks. |

**ENGINEERING ASSUMPTION:** declare a *neutral operating-state pass* only if every safety/reproducibility criterion passes and both nominal A/C satisfy the active-state criterion for all three seeds. Low/high assess sensitivity and safety; they cannot replace nominal. Dependence on common input in D limits robustness and must be reported even if the nominal gate passes. A failed seed is retained as failure; do not pool it away.

**INFERRED:** under strictly neutral input MBON32 may be silent, so A and C can legitimately be identical. This gate tests a bounded operating regime, not motor-route causality. A later independently designed MBON perturbation or sensory-route test is needed to establish transmission. No required press count, hit rate, score, motor success, learned advantage or A-over-C action advantage appears in this gate.

## 7. Evidence ledger, readiness and stop

| Element | Classification |
| --- | --- |
| Source counts, labels, parent overlap and raw prediction-confidence statistics | MEASURED, reconstruction/annotation observations |
| DNa02 locomotor-state dependence | LITERATURE-CONSTRAINED; other flies and preparations |
| Relevance of shared external drive; active-state reduction for the selected DN pair | INFERRED |
| Tonic net depolarization, telegraph approximation, 50-ms correlation time, equal common/private terms, strength levels, normalization, seeds, controls and pass thresholds | ENGINEERING ASSUMPTION |
| Actual omitted current, conductance/shunting, receptor effects, correlation, input spectrum and individual DN electrical parameters | UNKNOWN |

**Evidence/design blocker closed: YES, under the restricted engineering interpretation above.** There is now a specified represented state, causal interface, bounded process, fixed normalized strength envelope, no-performance selection rule and falsifiable neutral gate. Biological uncertainty is not erased. The contract's existence does not imply it will pass its own gate.

**Ready for Electrical Model V1: YES for the next specification/design stage. NO for claiming a runnable or validated circuit.** That stage must instantiate separately justified cell dynamics (including APL's local graded state), effective connection hypotheses/UNKNOWN policy, delays, numerical units/integration, this contract's physical DN scales, and neutral-input/readout interfaces. It must preserve exact anatomy and provenance. Those implementation specifications are work to do in Electrical Model V1, not additional evidence silently supplied by this boundary contract. The original 140-body subset/policy remains unchanged; this proposal is 115 bodies. No positive-sign fallback, shared-LIF default or reuse of the failed all-positive overlay is authorized.

**Data verification performed:** reran the data-only route summary, rechecking both parent hashes and all DN parent/partner pair counts. Added [audit_dn_boundary_inputs.py](../scripts/audit_dn_boundary_inputs.py) and [its audit JSON](figures/dn_boundary_input_audit.json), joining all omitted parent IDs to the pinned neuron annotations and enumerating all 430 shared IDs. The new audit records its parent/ledger hashes. No neural simulation or proxy trajectory was generated. No pA calibration, task evaluation or training occurred.

**Stop here.** This contract resolves the requested design task; it does not launch Electrical Model V1. Synthetic diagnosis remains a separate workflow whose handoff is [FUTURE_DIAGNOSTICS.md](FUTURE_DIAGNOSTICS.md).
