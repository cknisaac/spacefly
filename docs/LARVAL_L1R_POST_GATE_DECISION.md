# L1R post-gate implementation decision

**Date:** 2026-10-02  
**Status:** **L1R-E SELECTED; Option 3 rate controllability PASS**  
**Trigger:** [L1R-0](LARVAL_L1R_0_ADMISSION_RESULT.md) failed the literal DAN-c1-gated KC→MBON-m1 learning-locus gate.

The user selected **L1R-E** on 2026-10-02. The reduced-output implementation therefore preserves measured KC→MBON-m1 anatomy and uses a separately labelled artificial local teaching port. L1R-C1 remains an unselected alternative.

L1R-E subsequently passed its immutable-manifest and protocol-freeze stages, then failed the frozen 72-member pre-training controllability gate. Only 2/72 configurations qualified, the largest face-connected component had size 2, and no member was robust at an adjacent action threshold. The frozen requirements were ≥12 qualifiers, component size ≥8, and ≥6 adjacent-threshold-robust members. No nominal model, plasticity, or learning run exists. See [L1R-E2/E3 result](LARVAL_L1RE_E2_E3_CONTROLLABILITY.md).

At the user's direction, an explicitly outcome-informed L1R-E v2 engineering family then expanded the contact scale, separated KC and MBON parameters, lowered MBON thresholds, and tested 100/150-ms response windows. It produced 48/128 qualifiers spanning every axis, but they formed 12 disconnected four-member components. The frozen component-size and adjacent-threshold requirements therefore failed. No v2 nominal model, plasticity, or learning run exists. See [L1R-E v2 result](LARVAL_L1RE_V2_CONTROLLABILITY.md).

Continuing through the listed refinements, Option 2's continuous LIF membrane readout **FAILed** because the subthreshold mean reversed at intermediate weight factors in every configuration. Option 3's explicit rate-model reduction **PASSed** its engineering controllability gate across 12/12 configurations. The action cutoffs are derived from measured anatomical input totals and the low-weight endpoint, so this pass demonstrates the declared rate equation's controllability only. MBONs are not represented as spiking cells; no learning or biological pathway claim is established. See [Option 3 result](LARVAL_L1RE_OPTION3_RATE_CONTROLLABILITY.md). This is the stopping point for the user's instruction to continue until an option passes.

## Option A — L1R-E: preserve MBON-m1 with an artificial teacher

### Model

```text
current-position cue
  → fixed KC encoder
  → measured KC→MBON-m1 anatomy
  → local KC→MBON-m1 plastic weights
  → fixed inverse MBON-m1 action interface

artificial teaching event
  → eligibility-gated depression of selected KC→MBON-m1 weights
```

### Evidence and assumptions

- KC→MBON-m1 anatomy: **MEASURED** in the pinned L1EM source.
- Conditioning-related MBON-m1 response decrease: **LITERATURE-CONSTRAINED**, with multiple possible circuit mechanisms.
- KC→MBON-m1 as the storage locus: **INFERRED**.
- Teaching event at that locus: **ENGINEERING ASSUMPTION**. It must not be called DAN-c1 or represented as a measured DAN-c1→MBON-m1 relation.
- Electrical dynamics, encoder, and output interface: **ENGINEERING ASSUMPTIONS**.

### Permitted final claim

> A connectome-constrained larval MBON-m1 model stored a sensory–action association in internal KC→MBON-m1 weights under an artificial local teaching signal and drove a fixed non-trainable action interface.

This option cannot claim a reconstructed larval dopamine teaching pathway or DAN-c1-gated KC→MBON-m1 plasticity.

### Next stage if selected

**L1R-E1 — immutable KC→MBON-m1 manifest and artificial-teacher contract.** Reuse the L1R-1 manifest requirements, omit DAN-c1 from the biological learning locus, and add a separately labelled artificial modulatory port. Then continue through the frozen electrical family and controllability gate before plasticity.

## Option B — L1R-C1: anatomy-aligned DAN-c1 / MBON-c1 candidate

### Model

```text
current-position cue
  → fixed KC encoder
  → measured KC→MBON-c1 anatomy
  → candidate local KC→MBON-c1 plastic weights
  → fixed inverse MBON-c1 action interface

DAN-c1 teaching event
  → inferred eligibility-gated KC→MBON-c1 rule
```

### Evidence and assumptions

- KC→MBON-c1 and DAN-c1→MBON-c1 anatomy: **MEASURED** in the pinned L1EM source.
- DAN-c1 lower-peduncle innervation and aversive teaching role: **LITERATURE-CONSTRAINED**.
- Exact KC→MBON-c1 storage locus and update polarity: **UNKNOWN / INFERRED**; no reviewed primary experiment measures the exact local equation.
- MBON-c1→keypress mapping: **ENGINEERING ASSUMPTION**.
- Electrical dynamics and encoder: **ENGINEERING ASSUMPTIONS**.

### Relationship to existing work

This is not literal L1R. It overlaps the existing Candidate L3 anatomy and electrical work, which already established:

- 116 KC→MBON-c1 rows / 2,504 pinned contacts;
- four DAN-c1→MBON-c1 rows / 209 contacts;
- engineering controllability of the prior MBON-c1→DN overlay;
- an **INCONCLUSIVE** exact local-rule polarity gate.

The reduced-output boundary would remove the unsupported DN/action interpretation, but it would not resolve the unknown biological plasticity polarity. A new candidate version must explicitly decide whether an inferred local rule is allowed.

### Permitted final claim if the inferred-rule gate is admitted

> A connectome-constrained larval lower-peduncle model, using measured KC/DAN/MBON anatomy and an explicitly inferred DAN-c1-gated local plasticity rule, stored a sensory–action association in KC→MBON-c1 weights and drove a fixed non-trainable action interface.

### Next stage if selected

**L1R-C1-0 — reduced-output rule-admission contract.** Reconcile the existing L3 rule-direction result with the new inverse MBON output boundary and freeze whether an inferred LTD rule is scientifically admissible before any new simulation.

## What cannot be selected implicitly

- Keep the name L1R while replacing MBON-m1 with MBON-c1.
- Keep the biological DAN-c1 label while implementing an artificial teacher at MBON-m1.
- Choose the route based on which one is more likely to pass simulation.
- Reuse L3's DN action result as evidence for the reduced MBON output rule.
- Begin learning before the selected candidate passes its new controllability and local-rule gates.

## Decision needed

Choose exactly one:

1. **L1R-E** — preserve MBON-m1 and accept an explicitly artificial local teacher and narrower claim.
2. **L1R-C1** — switch to the anatomy-aligned DAN-c1/MBON-c1 pair as a newly named candidate, retaining an inferred-rule evidence gate.

Until one scope is selected, there is no scientifically faithful implementation target. Existing L1R-0, L1/L2/L3, and adult MaleCNS artifacts remain unchanged.
