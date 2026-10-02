> **Status:** User-provided research handoff, archived 2026-10-02. It proposes Candidate L1R and a reduced MBON-m1 output boundary. This is preserved as a research proposal; it does not by itself revise the active MaleCNS Branch B roadmap, admit a new candidate, or authorize a simulation. See `CURRENT.md` and `BRANCH_B_FLY_LEARNING_ROADMAP.md` for active stage status.
>
> **Detailed proposal and result:** See [Candidate L1R roadmap](LARVAL_L1R_PROPOSED_ROADMAP.md) and [L1R-0 admission result](LARVAL_L1R_0_ADMISSION_RESULT.md). L1R-0 subsequently failed: DAN-c1 teaching and MBON-m1 conditioning effects are independently supported, but they do not form a supported local KC→MBON-m1 learning locus. Later L1R stages were not run.

---
# Larval Learning Project — Research Handoff

## 1. Project goal

The objective is to test whether a **connectome-constrained Drosophila larval mushroom-body circuit can genuinely learn through internal synaptic plasticity**.

The defining requirement is:

```text
fixed causal sensory input
→ fly neural circuit
→ LOCAL INTERNAL SYNAPTIC PLASTICITY
→ changed fly neural activity
→ fixed non-trainable output
→ improved behavior
```

The adaptive component must remain inside the simulated fly circuit.

The project is **not** intended to become:

```text
frozen fly brain
→ trainable ML decoder
→ action
```

No BPTT, PPO, Adam, trainable readout, or other external task learner is permitted for the primary result.

---

# 2. Why the larval project was pursued

The adult MaleCNS project repeatedly encountered the same fundamental problem:

> connectomics gives anatomy, but not enough quantitative physiology to uniquely determine how activity propagates through the entire reconstructed circuit.

The larval nervous system appeared attractive because it is substantially smaller and several mushroom-body components involved in learning have unusually good anatomical and functional characterization.

The hope was that larval circuitry would allow both:

```text
biologically grounded learning
+
biologically reconstructed motor execution
```

within one compact model.

The research ultimately showed that those are **two separate problems**.

---

# 3. Original Candidate L1

The first larval candidate was based on the `γ1pedc` mushroom-body compartment:

```text
γ KCs
   ↓
KC → MBON-m1
   ↑
 DAN-c1
```

The initial proposed full pathway was approximately:

```text
γ KCs
   ↓
MBON-m1
   ↓
convergence / downstream neurons
   ↓
Basin-4
   ↓
premotor/action circuitry
   ↓
action
```

The appeal was that the learning compartment seemed particularly well suited to a simple LTD/disinhibition learning mechanism.

---

# 4. L1 research resolution

A later primary-source/connectome audit separated what was actually supported from what had been inferred.

## Supported / partially supported learning-side claims

The research supports the following overall picture:

- DAN-c1 innervates the relevant lower-peduncle / `γ1pedc` region.
- DAN-c1 participates causally in larval aversive learning.
- MBON-m1 responses decrease following aversive conditioning.
- MBON-m1 is inhibitory/GABAergic.
- A depression-like learning mechanism affecting MBON-m1 output is therefore biologically plausible.

However, the exact statement:

> DAN-c1 directly induces plasticity at specifically isolated KC→MBON-m1 synapses

remains **partially supported rather than directly demonstrated at individual synapses**.

The evidence is assembled from DAN-c1 behavioral manipulation plus MBON-m1 functional changes after conditioning.

That distinction should remain explicit.

---

# 5. Why original L1 was rejected

The major failure was the proposed downstream motor route.

The research audit found no verified machine-readable chain supporting:

```text
MBON-m1
→ Basin-4
→ action
```

as originally proposed.

In particular:

- no exact MBON-m1→Basin-4 edge chain with verified neuron IDs and synapse counts was established;
- Basin-4 appeared in the literature mainly as part of nociceptive / aversive teaching circuitry rather than as the demonstrated downstream motor target of MBON-m1;
- no experiment was found showing that manipulating MBON-m1 causally changes Basin-4 activity.

Therefore:

```text
Candidate L1 as originally specified
= REJECTED
```

This rejection concerned the **claimed downstream sensorimotor pathway**, not necessarily the mushroom-body learning compartment itself.

---

# 6. Candidate L2

A second candidate, L2, was constructed with a better-defined anatomical downstream route.

Its subgraph and context manifests were validated, and the model was subjected to a strict pre-training controllability gate before any plasticity was allowed.

The principle was:

> if changing the proposed plastic synapses cannot causally change the final output before learning, implementing a learning rule is pointless.

This was intentionally tested before dopamine/plasticity/task learning.

---

# 7. L2 electrical evidence problem

The physiology audit found useful qualitative evidence but **no exact quantitative electrical calibration** for the relevant cells.

For example, the reviewed evidence supported qualitative effects such as:

```text
MBON-d1 → Ipsigoro      negative/inhibitory net effect
Ipsigoro → Goro         positive net effect
```

and Goro has behavioral relevance.

But the literature did not provide the exact quantities required to instantiate the pathway:

```text
unitary PSP/current
conductance per anatomical contact
exact membrane properties
exact spike threshold
exact edge delay
Goro spike-count → behavior mapping
```

for the relevant cells.

Adjacent electrophysiological measurements existed in other larval or adult cell classes, but they could not justifiably be transferred as measurements of MBON-d1, Ipsigoro, Goro, or their specific synapses.

---

# 8. Option B: explicit engineering assumptions

Because exact quantitative physiology was unavailable, the project explicitly changed policy.

Rather than claiming:

> these electrical values reproduce the biological larva,

the model would instead say:

> these are disclosed engineering assumptions used to instantiate measured or supported connectivity.

A bounded engineering family was therefore defined before testing.

Parameters included things such as:

```text
contact → synaptic effect scale
membrane time constant
threshold
sensory/context pulse scale
synaptic decay
delay
action criterion
```

These were not treated as biological measurements.

Importantly, the family was frozen **before** evaluating controllability so that values could not simply be adjusted until the circuit worked.

---

# 9. L2 controllability result

The family test failed.

Across:

```text
72 electrical configurations
× 4 KC→MBON weight factors
× 8 sensory states
× deterministic replays
```

the circuit remained numerically stable, and KC/MBON activity could occur.

Changing KC→MBON weights sometimes changed MBON-d1 activity.

However:

```text
Ipsigoro spikes = 0
Goro spikes     = 0
actions         = 0
```

throughout the tested family.

Therefore no usable control authority propagated from the proposed plastic locus to the action node.

The result was:

```text
L2 under this simulator abstraction
= REJECTED
```

No plasticity or learning was run.

This was the correct stopping point.

The physiology audit also explicitly concluded that extending the gain or threshold sweep after seeing the failure would become outcome-based tuning rather than independent calibration.

---

# 10. What the two failures taught us

L1 and L2 failed for different reasons.

### L1

```text
learning compartment:
plausible / partially supported

claimed downstream path:
unsupported
```

### L2

```text
anatomical downstream candidate:
better specified

electrical control authority:
failed under frozen engineering family
```

Together they exposed a more important design issue:

> We were requiring both mushroom-body learning and full sensorimotor reconstruction to succeed simultaneously.

Those are different scientific questions.

---

# 11. Revised MVP boundary

The project will now separate them.

The MVP will test:

> **Can the larval mushroom-body learning circuit alter its own output through internal local synaptic plasticity?**

It will **not yet require reconstruction of the full biological motor pathway**.

The revised candidate is therefore a reduced-output version of L1:

## Candidate L1R

```text
current note position
        ↓
fixed causal KC encoder
        ↓
       KCs
        │
        │ plastic
        ▼
     MBON-m1
        ▲
        │
      DAN-c1

     MBON-m1
        ↓
fixed non-trainable engineering mapping
        ↓
      action
```

The biological model terminates at MBON-m1.

The action interface is an explicit engineering boundary.

---

# 12. Why this is scientifically acceptable for the MVP

The critical distinction is **where learning occurs**.

This would still be:

```text
fly synapses learn
→ fly neural output changes
→ fixed switch converts that output into action
```

It is not:

```text
frozen fly activity
→ trained decoder learns what activity means
→ action
```

The output rule contains no trainable parameters.

For example, conceptually:

```text
lower MBON-m1 activity
→ greater action drive

if fixed action drive crosses fixed threshold:
    KEY_DOWN
```

The rule is deliberately simple and frozen.

Thus any learned state must be stored in the internal KC→MBON pathway.

---

# 13. Revised claim

The MVP claim should now be approximately:

> **A connectome-constrained larval Drosophila mushroom-body model acquires a sensory–action association through dopamine-gated internal KC→MBON plasticity. The resulting change in MBON output drives a fixed, non-trainable action interface and persists after plasticity and teaching are disabled.**

It should **not** claim:

```text
the complete larval motor pathway was reconstructed

the chosen electrical parameters are exact biology

MBON-m1 directly controls Basin-4

the simulated larva literally performs the biological motor action

the artificial keyboard boundary is itself biological
```

---

# 14. Evidence / assumption ledger going forward

The project should continue using:

```text
MEASURED
LITERATURE-CONSTRAINED
INFERRED
ENGINEERING ASSUMPTION
UNKNOWN
```

Likely categorization:

| Component | Status |
|---|---|
| Larval KC / MBON anatomy | MEASURED |
| DAN-c1 anatomical compartment | MEASURED / literature-supported |
| DAN-c1 role in aversive learning | LITERATURE-CONSTRAINED |
| Depression of MBON-m1 response after conditioning | LITERATURE-CONSTRAINED |
| Exact isolated KC→MBON-m1 synaptic plasticity mechanism | INFERRED / partially supported |
| Exact electrical parameters | ENGINEERING ASSUMPTION |
| Current-position→KC encoder | ENGINEERING ASSUMPTION |
| Exact eligibility-trace equation | ENGINEERING ASSUMPTION constrained by biology |
| MBON-m1→keypress mapping | ENGINEERING ASSUMPTION |
| Full larval motor pathway | OUT OF MVP SCOPE |

---

# 15. Immediate next step: L1R anatomy / learning manifest

Before simulation, create a minimal immutable manifest containing only:

```text
selected γ KCs
KC→MBON-m1 contacts
MBON-m1 L/R
DAN-c1 L/R
compartment identity
known transmitter information
evidence provenance
```

Do not include Basin-4, Goro, or speculative motor nodes in the MVP manifest.

The reduced architecture should be intentionally small.

---

# 16. Pre-training controllability gate

Before plasticity, manually perturb only the candidate KC→MBON weights.

Example:

```text
100%
80%
60%
40%
20%
```

Across multiple predeclared KC input states measure:

```text
KC activity
↓
MBON-m1 activity
↓
fixed action variable
```

Required result:

> changing only KC→MBON strength must produce a meaningful monotonic change in MBON output and therefore in the fixed action variable.

No dopamine.

No learning.

No reward.

No task optimization.

This is the new controllability gate.

Because the biological circuit terminates at MBON-m1, the previous problem:

```text
MBON
→ unknown downstream transmission
→ unknown downstream transmission
→ action
```

is removed from the MVP.

---

# 17. Fixed output rule

The action rule must be decided before learning.

One reasonable form is:

```text
MBON activity measured in fixed window

lower MBON activity
→ larger action drive

fixed threshold
→ action
```

The exact rule may differ, but it must be:

- deterministic;
- monotonic;
- simple;
- fixed before training;
- non-trainable;
- documented as an engineering assumption.

Do not optimize the threshold on final task performance.

---

# 18. Local plasticity stage

Only after controllability passes should the project implement plasticity.

Minimal proposed form:

```text
KC activation
→ local eligibility trace

DAN-c1 activation shortly afterwards
→ depression of eligible KC→MBON weights
```

Unit tests should demonstrate:

```text
KC + appropriate DAN → LTD

KC alone → no LTD

DAN alone → no unrelated LTD

inactive KC synapses → unchanged

plasticity OFF → no weight changes

non-plastic synapses → unchanged
```

No external gradient is permitted.

---

# 19. First learning task

Do not start with full osu timing correction.

The first task should be **one-way state/action acquisition**.

Example:

```text
moving note
↓
current visible position only
↓
fixed KC population code

target state + teaching
↓
DAN-c1 event
↓
KC→MBON depression

future encounter with same state
↓
reduced MBON output
↓
fixed action interface activates
```

No:

```text
future timestamp
time-to-contact
desired press time
future note position
trained encoder
```

---

# 20. Frozen post-training evaluation

After training:

```text
plasticity OFF
DAN teaching OFF
exploration OFF
weights retained
encoder unchanged
output unchanged
```

Then evaluate fresh stimuli.

This is essential.

If improved behavior survives, the useful state is stored in the modified internal synapses.

If behavior disappears when plasticity/teaching is disabled, the learning claim fails.

---

# 21. Required controls

At minimum:

```text
A. normal plastic training

B. plasticity OFF

C. DAN disabled

D. shuffled / wrong-state teaching

E. naive untrained network
```

All other conditions remain matched.

Later, when the task becomes temporal, use **first action** as the primary behavioral measure so a later action cannot rescue an incorrect early one.

---

# 22. Development reliability

Once a single run works:

```text
run multiple independent development seeds
```

For example:

```text
8 development runs
```

Save early/mid/late checkpoints automatically.

Look for:

```text
weight saturation
action everywhere
no action anywhere
state-specific overfitting
unstable learning
failure to retain learning
```

Tuning is allowed only during this development phase and must be recorded.

---

# 23. Confirmation stage

After development, freeze:

```text
connectome version
neuron IDs
electrical model
encoder
plasticity equation
eligibility timing
learning rate
weight bounds
DAN policy
fixed output rule
training duration
seed generation
evaluation protocol
success criterion
controls
```

Then run untouched confirmation seeds.

No changes after seeing confirmation results.

---

# 24. Definition of MVP success

The minimum result is:

```text
NAIVE
→ target state does not reliably produce action

TRAINING
→ only internal KC→MBON weights adapt

AFTER TRAINING
→ MBON response changes

PLASTICITY + TEACHING FROZEN
→ improved target-state action remains

MATCHED CONTROLS
→ do not show equivalent improvement
```

If that happens, the project has demonstrated the key concept:

> **adaptive state is stored inside a connectome-constrained fly learning circuit rather than in an external decoder.**

---

# 25. Future Phase 2 — restore biological motor circuitry incrementally

The fixed MBON→action boundary is not intended to be the final project forever.

Once L1R learning works, replace the artificial boundary incrementally.

### Phase 2A

```text
KC → MBON
       ↓
verified downstream CN
       ↓
fixed action
```

Test controllability again.

### Phase 2B

```text
KC → MBON
       ↓
CN
       ↓
verified premotor neuron
       ↓
fixed action
```

Test controllability again.

### Phase 2C

Continue extending toward a biological action pathway only where anatomy and model behavior support it.

Each additional downstream block must independently pass:

```text
anatomical verification
↓
effect/sign evidence
↓
frozen electrical model
↓
pre-training controllability
```

A downstream extension failing should not invalidate the already-demonstrated mushroom-body learning result.

---

# 26. Long-term adult MaleCNS return

The adult project remains the larger long-term target.

The larval work should provide reusable methodology:

```text
verify anatomy
→ define evidence ledger
→ choose engineering assumptions explicitly
→ test controllability BEFORE learning
→ implement local plasticity
→ freeze
→ matched controls
→ fresh confirmation
```

The biggest lesson from both larval L1/L2 and adult MaleCNS is:

> **Never spend substantial effort implementing a learning rule until the proposed plastic locus has demonstrated task-independent control authority over the chosen output.**

---

# Current project status

```text
Original Larval L1
learning-side evidence       PARTIALLY SUPPORTED
claimed Basin-4 path         UNSUPPORTED
original candidate           REJECTED

Larval L2
anatomy                      VALIDATED
electrical family            FROZEN + TESTED
KC→MBON influence            PARTIAL
downstream propagation       FAIL
controllability              FAIL
plasticity                   NOT RUN
candidate                    REJECTED

Larval L1R
γ1pedc learning core         REOPENED
biological endpoint          MBON-m1
motor reconstruction         DEFERRED
output                       FIXED ENGINEERING INTERFACE
next gate                    KC→MBON→MBON-output CONTROLLABILITY
```

## Next single action

**Implement Candidate L1R only through MBON-m1 and run the reduced pre-training controllability test.**

Do not implement dopamine learning until that passes.
