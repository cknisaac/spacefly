# Candidate L1R — proposed reduced-output larval learning roadmap

**Status:** **L1R-0 FAIL — literal L1R retired before implementation.** L1R-1 through L1R-9 were not run.  
**Date:** 2026-10-02  
**Purpose:** Test whether a connectome-constrained larval mushroom-body model can store a sensory–action association in local KC→MBON plastic weights when the biological model ends at the MBON and the motor conversion is a fixed engineering interface.

## Scientific claim and boundary

If every required gate passes, the permitted claim is:

> A connectome-constrained larval mushroom-body model acquired a sensory–action association through dopamine-gated local KC→MBON plasticity. The learned KC→MBON weights changed MBON activity, drove a fixed non-trainable action interface, and retained the effect after teaching and plasticity were disabled.

The project must not claim that the fixed output interface is biological, that the complete larval motor pathway has been reconstructed, that engineering electrical values reproduce a living larva quantitatively, or that an exact KC→MBON-m1 plasticity mechanism is measured unless new evidence establishes it.

The only adaptive task state may be in the admitted KC→MBON weights. The encoder, output mapping, thresholds, teaching policy during a frozen run, and all evaluation machinery are non-trainable. No BPTT, PPO, Adam, learned decoder, future timestamp, time-to-contact value, desired action time, or held-out answer may enter the primary model.

## Important correction before implementation

The archived handoff proposes `γ KCs → MBON-m1 ← DAN-c1`, but the existing [Phase 0 audit](LARVAL_MVP_PHASE0_AUDIT.md) rejects that literal identity/compartment combination. It reports distinct MBON-m1/CN-62 and DAN-c1/lower-peduncle identities, no direct DAN-c1→MBON-m1 edge in the inspected S1 matrix, and no demonstrated compartment-matched KC→MBON-m1 plastic locus. Removing the downstream motor path does not resolve that learning-locus mismatch.

Therefore **L1R-0 is the sole next proposed L1R stage**. Manifest construction, electrical modeling, controllability, plasticity, and learning are conditional on L1R-0 passing. A hidden substitution of MBON-c1, MBON-d1, DAN-d1, or an adult homolog is prohibited; such a change would be a separately named candidate.

## Roadmap summary

| Stage | Question | Required decision |
|---|---|---|
| **L1R-0** | Is literal KC→MBON-m1 plasticity under DAN-c1 a defensible larval learning locus? | **FAIL — same learning territory unsupported** |
| **L1R-1** | Can the admitted anatomy and plastic mask be reproduced exactly? | PASS before dynamics |
| **L1R-2** | Can a small electrical family and fixed MBON→action rule be frozen independently of outcomes? | PASS for design completeness |
| **L1R-3** | Do KC→MBON weight changes robustly control MBON output and the fixed action variable? | PASS before plasticity |
| **L1R-4** | Is an evidence-labelled local DAN-gated rule admissible and correctly implemented? | PASS before task learning |
| **L1R-5** | Is the one-way acquisition protocol causal, leak-free, and fully frozen? | PASS before development runs |
| **L1R-6** | Does learning work reliably enough in development to justify confirmation? | PASS before final freeze |
| **L1R-7** | Is the candidate completely frozen and independently ready? | PASS before confirmation |
| **L1R-8** | Does internal learning replicate on untouched seeds and beat matched controls? | PASS for the reduced MVP |
| **L1R-9** | Can biological downstream circuitry be restored one verified block at a time? | Optional post-MVP extension |

Every completed stage must be reported as **PASS**, **FAIL**, or **INCONCLUSIVE** under criteria frozen before that stage. Stop after each stage and obtain separate authorization for the next one.

---

## L1R-0 — identity and learning-locus admission

### Question

Does the evidence support the literal larval combination of selected KCs, MBON-m1 L/R, and DAN-c1 L/R as one compartment-compatible learning locus strongly enough to test it as an explicitly inferred hypothesis?

### Explicit steps

1. Pin the larval connectome release, annotation tables, source checksums, organismal stage, and exact source IDs.
2. Reproduce the MBON-m1 and DAN-c1 identity crosswalks independently of the archived handoff's labels.
3. Extract every selected KC→MBON-m1 source row and contact count, retaining hemisphere and source-row provenance.
4. Test spatial overlap at the finest available compartment/coordinate resolution among selected KC presynaptic sites, MBON-m1 inputs, and DAN-c1 arbor or release territory. Absence of a direct DAN chemical edge is not automatically fatal for modulation, but a claimed shared learning compartment requires positive spatial or functional evidence.
5. Audit primary evidence for DAN-c1 teaching, MBON-m1 conditioning-related response change, direction of change, developmental stage, stimulus, and whether those results belong to the same compartment and cells.
6. Write an evidence ledger separating **MEASURED**, **LITERATURE-CONSTRAINED**, **INFERRED**, **ENGINEERING ASSUMPTION**, and **UNKNOWN** claims.
7. State one immutable candidate identity. Do not repair a mismatch by renaming or swapping cells inside L1R.

### PASS criterion

All of the following must hold:

- exact bilateral MBON-m1 and DAN-c1 identities are source-linked without an unresolved name/homology conflict;
- selected KC→MBON-m1 contacts are reproducible from the pinned source with positive contact counts and valid endpoints;
- independent spatial or functional evidence places DAN-c1 modulation at the same KC/MBON-m1 learning territory, rather than merely elsewhere in the lower peduncle;
- larval evidence supports both DAN-c1 as a teaching source and conditioning-related depression of the selected MBON-m1 output, with developmental-stage limits stated;
- the proposed local KC→MBON-m1 LTD direction is at least a coherent **INFERRED** hypothesis from those independent premises;
- no required premise depends only on adult homology or on the desired action outcome.

**FAIL** if the identity/compartment contradiction remains, the candidate requires a cell substitution, or same-locus teaching/plasticity cannot be supported. **INCONCLUSIVE** if essential source coordinates or annotations are unavailable or internally inconsistent. Either outcome stops L1R before manifest construction.

### Outputs and stop

Produce a source ledger, exact-ID table, spatial/contact audit, evidence report, hashes, and a PASS/FAIL/INCONCLUSIVE decision. Stop. Do not construct or simulate L1R in this stage.

---

## L1R-1 — immutable anatomy and candidate plastic mask

### Question

Can the admitted learning core be represented as a small, reproducible source-derived manifest without adding speculative downstream neurons?

### Explicit steps

1. Build a manifest containing only admitted KCs, MBON-m1 L/R, DAN-c1 L/R, source annotations, hemisphere, transmitter knowledge, evidence category, and provenance.
2. Store every measured KC→MBON-m1 row with source IDs and contact counts.
3. Store DAN anatomy separately from its modulatory role. Do not convert dopamine into an ordinary fast synapse unless L1R-0 provides that evidence.
4. Define the candidate plastic mask from a predeclared compartment/contact rule. Preserve excluded KC→MBON contacts in an audit table.
5. Add a deterministic builder and integrity audit covering node uniqueness, endpoints, positive counts, duplicate handling, bilateral totals, and source hashes.
6. Exclude Basin-4, Goro, premotor neurons, and any inferred motor path.

### PASS criterion

- two clean rebuilds produce byte-identical manifests and hashes;
- all source IDs are unique, every edge endpoint exists, all retained contact counts are positive, and aggregate counts match the source extraction exactly;
- 100% of included and excluded candidate contacts have a recorded reason and evidence category;
- the mask rule was fixed before any electrical response was observed;
- no speculative edge or motor neuron appears in the manifest.

Any source mismatch is **FAIL**. Missing compartment localization needed by the admitted mask is **INCONCLUSIVE** and returns to L1R-0 rather than being filled by assumption.

### Outputs and stop

Save the immutable manifest, builder, integrity result, plastic-mask audit, and report. Stop before electrical values are assigned.

---

## L1R-2 — frozen electrical family, causal encoder, and fixed output

### Question

Can all unknown dynamics and the engineering MBON→action boundary be specified before observing controllability or learning outcomes?

### Explicit steps

1. Freeze a current-based spiking model with explicit units, update order, reset, refractory behavior, delays, and numerical safety limits.
2. Label every numeric quantity as measured, constrained, inferred, or engineering.
3. Freeze a small family rather than one selected point. The starting proposal is:
   - contact effect: `[0.01, 0.05, 0.125, 0.275]` mV-equivalent/contact;
   - membrane time constant: `[10, 20]` ms;
   - threshold above rest: `[1, 3, 7]` mV-equivalent;
   - fixed KC pulse: `[8, 12, 16]` mV-equivalent for 5 ms;
   - synaptic decay 5 ms, delay 2 ms, refractory period 2 ms, integration step 1 ms, and zero tonic drive.
   This is a 72-member engineering family. Values may be revised only before the policy is frozen and only from task-independent rationale.
4. Freeze eight non-overlapping current-position KC states generated from current observation only. Log the observation and emitted KC drive.
5. Define the MBON response as the bilateral MBON-m1 spike count in a fixed 100 ms response window. Record voltage and synaptic-drive summaries as secondary endpoints.
6. Define the engineering action rule: the interface is armed only by a valid current-position cue; while armed, lower MBON spike count means greater action drive. Evaluate fixed thresholds of `≤0`, `≤1`, and `≤2` bilateral spikes as predeclared offline overlays. The interface has no learned parameter and sees no target label, reward, future time, or teaching event.
7. Freeze hashes for the family, encoder, readout, manifest, software revision, and simulation protocol before L1R-3.

### PASS criterion

- every required parameter, unit, evidence label, state code, output equation, threshold overlay, and safety bound is present and machine-readable;
- the encoder passes an information-flow audit proving it cannot access future note time, desired action time, target identity during evaluation, reward, or held-out answers;
- the action mapping is deterministic, monotonic in MBON activity, fixed, and non-trainable;
- the complete family and L1R-3 interpretation rules are hash-frozen before a circuit response is inspected.

Design incompleteness is **INCONCLUSIVE**. Any outcome-selected value or trainable output mapping is **FAIL**.

### Outputs and stop

Save the policy, encoder/readout contract, resolved family manifest, information-flow audit, hashes, and report. Stop before the family run.

---

## L1R-3 — robust pre-training controllability

### Question

Across a nontrivial region of the frozen family, can changing only KC→MBON-m1 weights monotonically change MBON-m1 output and the fixed action variable?

### Explicit steps

1. Run every frozen electrical configuration with plasticity, dopamine, teaching, reward, and exploration disabled.
2. Run a zero-drive baseline for each configuration.
3. For each of eight sensory states, apply KC→MBON weight factors `[1.0, 0.8, 0.6, 0.4, 0.2]`; change no other network quantity.
4. Run two exact deterministic replays of every configuration/state/factor cell.
5. Record KC spikes, MBON spikes, MBON voltage summaries, fixed action output at all three frozen thresholds, event-queue diagnostics, finiteness, and replay digests.
6. Evaluate the frozen gate without selecting the best state, threshold, or configuration after the run.

### Per-configuration PASS criterion

A configuration qualifies only if:

- zero drive causes no spikes and no armed action, with finite state and bounded event queues;
- every replay is exact and every driven state remains finite;
- all eight cues activate their intended KC group;
- at full weight, MBON-m1 emits at least one spike in at least six of eight states, avoiding a trivially silent starting model;
- reducing weights from `1.0` to `0.2` reduces MBON spike count by at least 30% in at least six of eight states;
- MBON responses are monotonic non-increasing as weights decrease in at least seven of eight states, with no state showing a reversal larger than one spike;
- for at least one frozen action threshold, action-state sets are nested as weights decrease, at least three states change from no-action at `1.0` to action at a lower factor, and the lower-weight action set contains 2–6 of eight states rather than zero or all eight.

### Family PASS criterion

The L1R-3 gate passes only if:

- at least **12 of 72** configurations qualify;
- qualifying configurations span at least two values on every varied electrical axis;
- the largest face-connected component contains at least **8** qualifying configurations; and
- at least **6** configurations in that component retain a qualifying, non-saturated transition at an adjacent frozen action threshold.

If the family passes, select the nominal model by the predeclared coordinate-wise median of the largest qualifying component, with lower contact scale and then lower pulse amplitude as tie-breakers. Task accuracy may not select the nominal point.

Zero qualifying configurations or failure of the robust-region rule is **FAIL** and retires L1R under this abstraction before plasticity. Numerical pathology or incomplete execution is **INCONCLUSIVE** and permits only repair of the runner, not parameter changes.

### Outputs and stop

Save every raw cell, family summary, connected-region analysis, replay audit, report, and—only on PASS—the frozen nominal electrical model. Stop before implementing plasticity.

---

## L1R-4 — local plasticity admission and invariant implementation

### Question

Is DAN-c1-gated depression at the admitted KC→MBON-m1 mask a defensible labelled hypothesis, directionally compatible with L1R-3, and implemented without hidden updates?

### Explicit steps

1. Freeze the rule's evidence chain and label the exact locus/equation as **INFERRED** unless directly measured.
2. Confirm that depression moves the nominal model toward the action transition found in L1R-3. Do not change LTD to LTP to obtain an action.
3. Specify the eligibility kernel, DAN timing, update equation, learning rate, bounds, update ordering, mask, and checkpoint state before task trials.
4. Route teaching through an explicit DAN-c1 event interface. Reward, task score, and target labels may not directly write weights.
5. Add exact local tests and coupled checkpoint/replay tests.

### PASS criterion

All tests must pass:

- active KC plus eligible timing plus DAN decreases only eligible selected weights;
- KC without DAN changes no weight;
- DAN without eligible KC changes no weight;
- inactive selected KC synapses remain byte-identical;
- non-plastic edges remain byte-identical;
- plasticity OFF produces zero weight change;
- bounds are respected and no NaN/Inf occurs;
- identical seeds and inputs yield byte-identical updates;
- checkpoint/resume with pending eligibility and DAN events reproduces the uninterrupted future exactly;
- a one-update causal probe changes MBON response in the L1R-3 direction.

Evidence incompatible with LTD, a required external gradient, nonlocal updates, or inability to reproduce the state is **FAIL**. Missing evidence that prevents even an explicitly inferred admission is **INCONCLUSIVE**.

### Outputs and stop

Save the rule policy, evidence ledger, implementation, test records, checkpoint schema update, and report. Stop before task learning.

---

## L1R-5 — one-way acquisition protocol freeze

### Question

Is the first learning experiment fully specified, causal, leak-free, and capable of failing before any development outcome is seen?

### Explicit steps

1. Use the same eight current-position states and fixed KC encoder from L1R-2.
2. Select one target state by a declared deterministic rule before learning results; do not choose the easiest state from L1R-3.
3. Define a balanced 64-trial training epoch: eight presentations per state in seeded shuffled order.
4. Deliver the frozen DAN event only for target-state teaching trials at the L1R-4 timing. The simulator receives no future note time or desired action timestamp.
5. Define frozen evaluation as 100 presentations per state with plasticity OFF, DAN OFF, teaching OFF, exploration OFF, retained weights, zeroed fast neural state, and unchanged encoder/output.
6. Define matched arms from identical initial states and trial orders: normal plastic training, plasticity OFF, DAN disabled, shuffled/wrong-state teaching, and naive untrained evaluation.
7. Define the primary behavioral measures as target-state action rate and non-target false-action rate. Define neural/weight measures separately.
8. Predeclare seed generation, missing-action handling, saturation limits, stopping limits, artifact schema, and development-only tuning rules.

### PASS criterion

- a static information-flow audit finds no path from future time, desired action, reward, target answer, or evaluation labels to the encoder/readout or directly to weights;
- all five arms start from identical model state and differ only by the named intervention;
- evaluation disables every update/teaching/exploration path while preserving learned weights;
- target/non-target outcomes, first action, MBON response, weight changes, saturation, and failures are all recorded;
- a dry run with learning disabled replays exactly and changes no weights;
- the full protocol and all success criteria for L1R-6 are frozen before development outcomes.

Leakage, mismatched controls, or an unfrozen success rule is **FAIL**. Missing implementation fields are **INCONCLUSIVE**.

### Outputs and stop

Save the preregistered protocol, resolved fixtures, information-flow audit, dry-run result, hashes, and report. Stop before learning development.

---

## L1R-6 — bounded development and retained acquisition

### Entry dependency

L1R-0 through L1R-5 must pass. Branch A's integrated infrastructure dry run, or an explicitly equivalent integration test using the L1R runner, must also pass before this stage so checkpoint, first-action, control, and frozen-evaluation machinery are exercised together.

### Question

Can local KC→MBON-m1 plasticity produce reliable, state-specific acquisition that persists under frozen evaluation and exceeds matched controls?

### Explicit steps

1. Run eight predeclared development seeds across all five matched arms.
2. Capture initial, early, middle, and final checkpoints automatically.
3. Evaluate every checkpoint with the frozen evaluation protocol.
4. Record every run, including failure, no-action, all-action, saturation, and numerical-stop cases.
5. Permit at most two documented development revisions. Each revision becomes a new version with a stated rationale and reruns all eight seeds; no seed may be discarded. Confirmation data remain unseen.

### PASS criterion

At least **6 of 8** normal-training seeds must simultaneously satisfy:

- frozen target-state action rate is at least **75%**;
- target-state action rate improves by at least **50 percentage points** over that seed's naive evaluation;
- aggregate non-target false-action rate is at most **25%**;
- normal training beats each matched plasticity-OFF, DAN-disabled, shuffled-teaching, and naive arm by at least **40 percentage points** on target-state action rate;
- target-state MBON spike count falls by at least **30%** from naive under the frozen evaluation;
- only selected KC→MBON weights change;
- no more than **20%** of plastic weights end at either bound; and
- the final frozen replay is deterministic and finite.

The stage **FAILS** if no allowed development version meets the gate, if success requires all-state action, if controls improve equivalently, or if the effect disappears when teaching/plasticity are disabled for evaluation. Infrastructure failure is **INCONCLUSIVE** only when it prevents valid measurement without revealing a candidate outcome.

### Outputs and stop

Save all seeds/arms/checkpoints, development-version ledger, failures, plots, raw neural/weight/action data, and a decision report. Stop before final freeze.

---

## L1R-7 — final freeze and independent readiness audit

### Question

Is one complete L1R candidate frozen, reproducible, and ready for untouched confirmation?

### Explicit steps

1. Freeze hashes for data source, IDs, manifest, plastic mask, electrical model, encoder, output, local rule, teaching policy, timing, training length, seeds, controls, evaluation, metrics, and pass criteria.
2. Freeze a seed generator that excludes all development seeds.
3. Run regression, exact replay, checkpoint, information-boundary, and no-update evaluation tests.
4. Independently audit configuration completeness and verify that no confirmation outcome exists yet.

### PASS criterion

- every required artifact exists, is immutable/hash-pinned, and refers to the same candidate version;
- all regression and deterministic replay tests pass;
- training and evaluation have disjoint seed sets;
- the evaluator cannot update weights or receive teaching/exploration;
- no unresolved field could change an action, update, control comparison, or pass decision;
- the independent audit returns PASS with no material exception.

Any post-development choice left open is **INCONCLUSIVE**. Any use of confirmation data to finish the design is **FAIL** for that confirmation attempt.

### Outputs and stop

Save the final manifest bundle, receipt, readiness audit, and confirmation execution command. Stop before confirmation.

---

## L1R-8 — untouched confirmation and internal-storage test

### Question

Does the frozen L1R candidate replicate state-specific retained acquisition on new seeds because its internal KC→MBON weights changed?

### Explicit steps

1. Run **32 untouched seeds** across the five frozen matched arms.
2. Train exactly as frozen; then evaluate 100 presentations per state with plasticity, DAN, teaching, and exploration disabled.
3. Add one mechanistic rollback evaluation per trained seed: restore only selected KC→MBON weights to their initial values while preserving all other final checkpoint state and run the same frozen panel.
4. Report all seeds and all exclusions as failures unless the preregistration explicitly defines a non-candidate infrastructure exception.

### Per-seed success criterion

A normal-training seed succeeds only if:

- target action rate is at least **80%**;
- aggregate non-target false-action rate is at most **20%**;
- target action improves at least **50 percentage points** over its paired naive arm;
- normal training beats each paired plasticity-OFF, DAN-disabled, shuffled-teaching, and naive arm by at least **30 percentage points** on target action rate;
- target MBON response decreases at least **30%** from naive;
- replacing only the learned KC→MBON weights with their initial values removes at least **80%** of the acquired target-action improvement;
- weight-mask integrity, frozen-evaluation integrity, finiteness, and saturation limits pass.

### Overall PASS criterion

At least **24 of 32** untouched normal-training seeds must meet every per-seed criterion. In addition, normal training must beat every matched control in at least **24 of 32** paired seeds, and no safety/information-boundary audit may fail.

Fewer than 24 successful seeds, equivalent control improvement, failure of weight rollback, generalized all-state action, leakage, or evaluation-time updating is **FAIL**. A platform interruption is **INCONCLUSIVE** only under the frozen exception rule and must be rerun without changing the candidate.

No parameter, seed, threshold, training length, or analysis rule may change after confirmation begins. A failed confirmation ends this candidate version.

### Outputs and stop

Save all raw runs, paired-control and rollback comparisons, exact hashes, confirmation report, assumption ledger, and final PASS/FAIL/INCONCLUSIVE decision. Stop. A PASS supports only the reduced-output model claim stated above.

---

## L1R-9 — optional downstream biological restoration

This stage is outside the reduced MVP and begins only after L1R-8 PASS. Add one independently verified downstream block at a time:

1. source-verify its exact anatomy and contacts;
2. classify its effect/sign evidence;
3. freeze its electrical assumptions before response data;
4. repeat a pre-training selected-weight controllability gate;
5. repeat frozen learning retention and the weight-rollback control.

An extension that fails is removed without invalidating a previously confirmed reduced-output L1R result. The artificial MBON→action boundary remains explicitly labelled until a complete downstream replacement passes its own confirmation.

## Dependency and stop map

```text
L1R-0 evidence/identity
   PASS
     ↓
L1R-1 immutable manifest
   PASS
     ↓
L1R-2 model + encoder + fixed output freeze
   PASS
     ↓
L1R-3 robust controllability
   PASS ────────────────┐
     ↓                  │
L1R-4 local plasticity  │
   PASS                 │
     ↓                  │
L1R-5 task prereg       │
   PASS                 │
     ↓                  ↓
L1R-6 development ← A6 integration readiness
   PASS
     ↓
L1R-7 final freeze/readiness
   PASS
     ↓
L1R-8 untouched confirmation
   PASS
     ↓
L1R-9 optional motor-path restoration
```

Any biological **FAIL** retires literal L1R. Any engineering **FAIL** retires that frozen abstraction/version and requires a separately justified proposal; it does not authorize widening a sweep after seeing results. **INCONCLUSIVE** permits repair only of the missing evidence or invalid measurement identified by that stage.

## Current next action

L1R-0 has now **FAILED** under its predeclared criteria; see the [admission result](LARVAL_L1R_0_ADMISSION_RESULT.md). The exact identities, KC→MBON-m1 contacts, DAN-c1 teaching role, and MBON-m1 conditioning response are independently supported, but evidence does not place DAN-c1 at the selected KC→MBON-m1 learning territory. The matched source anatomy instead pairs DAN-c1 with MBON-c1. Do not build or simulate literal L1R. Any engineering-only teaching assignment or anatomy-aligned replacement is a separately scoped candidate, not L1R-1.
