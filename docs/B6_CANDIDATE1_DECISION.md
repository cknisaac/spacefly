# B6 — Candidate 1 decision

**2026-10-01 · decision version MVP-C1-D1 · B6 PASS (auditable retirement decision).**

**NO-GO: retire frozen MVP-C1 before training. No revision is admitted.** B3 and B3.1 remain FAIL. This decision concerns the specified engineering model; it does not reject the biological γ4 pathway. Available budget does not supply the missing evidence for a revision. No B3 rerun, numerical adjustment, B4/B5 run or Candidate 2 start was performed.

## Evidence and decision

| Evidence | Established result | Decision consequence |
| --- | --- | --- |
| [B1](B1_MVP_PATHWAY_RULE_SELECTION.md) | MaleCNS topology and relevant γ4 KC/PAM temporal plasticity support pathway/rule selection. | Anatomical contacts and rule support do not identify an electrical transfer function. |
| [B2](B2_CANDIDATE1_DESIGN.md), [B2.1](B2_1_CANDIDATE1_EXECUTABLE_DYNAMICS.md) | Explicit frozen mask, dynamics, encoder, teaching and motor contracts; exact gains, thresholds and autonomous boundary drives are engineering assumptions. | Design completeness passed; functional controllability was still required. |
| [B3](B3_CANDIDATE1_CONTROLLABILITY.md) | All 39 arms have silent MBON05. Selected-weight interventions reach its input, but nominal low/base/high weights give identical DNp42 cue spike counts and first DOWN in each of three seeds. All background-only arms press. | No demonstrated causal control from selected weights through MBON05 to first action. Training is not admitted. |
| [B3.1](B3_1_MBON05_INPUT_TRANSFER.md) | Seed 31001 baseline reproduced exactly. Removing only APL→MBON05 current raises peak voltage 0.616388→0.665515 against threshold 1, with zero MBON05 spikes and identical neural/action ledgers and first DOWN at 524000 µs. | APL-only suppression is rejected as a sufficient explanation in this matched test. It is not a justified repair. |
| [A1](A1_PLASTICITY_PLUMBING.md), [A2 schema](A2_1_MVP_CHECKPOINT_SCHEMA.md), [A2 coupled result](A2_2_A2_3_COUPLED_RESULT.md), [A3](A3_FIRST_ACTION_EVALUATION.md), [A4](A4_MATCHED_CONTROL_FRAMEWORK.md) | Plumbing, full-state replay, first-action scoring and matched-control infrastructure passed their declared scopes. | These validate the measurement machinery; they do not establish candidate controllability. |
| [A5](A5_CROSS_STATE_DIAGNOSTICS.md) | Six fixture states were captured, exactly replayed and assessed with a common panel. Policies are identical initial policies. A6 remains open. | Infrastructure progress does not rescue the failed candidate. |

The six B3 pairing probes establish local polarity and confinement for one selected KC/PAM pair repeated over three seeds. They are not independent physiological validations of all 13,957 selected contacts. Likewise, B3.1 is a single matched seed/state diagnosis, not a universal assertion about APL.

## Independently supported revision audit

The audited evidence supports **no specific, independently calibrated revision**:

| Possible change | Independent evidence available | Admission |
| --- | --- | --- |
| Increase KC→MBON05 gain or lower threshold | [Barnstedt et al.](https://pubmed.ncbi.nlm.nih.gov/26948892/) supports cholinergic KC excitation and receptor dependence, not these model's normalized contact amplitudes or MBON05 threshold. | Rejected: selecting a value from the observed voltage deficit would be outcome-driven tuning. |
| Remove APL input | Graded inhibitory APL is a declared model component; the omission was already the frozen B3.1 diagnostic. | Rejected as a sufficient repair by the saved result; no independent replacement law is supplied. |
| Expand the plastic mask or change temporal rule | [Handler et al.](https://pmc.ncbi.nlm.nih.gov/articles/PMC9012144/) supports temporally bidirectional KC/DAN plasticity in relevant compartments. Anatomical coverage alone does not identify missing electrical efficacy. | No supported transfer repair. Local update polarity already passes. |
| Change downstream signs, route or autonomous drive | [Li et al.](https://elifesciences.org/articles/62576.pdf) supports anatomical downstream connectivity, including MBON20 links to descending neurons. | Exact pair effects and boundary calibration remain unresolved; a new route requires a new explicit design. |

Primary literature was checked against the existing selection rationale. Barnstedt's abstract was accessible; direct Handler and Li HTML access was challenged, with indexed primary text/PDF material available. No new quantitative physiological constraint was extracted. This is a bounded audit of the cited evidence, not a claim that no useful evidence exists anywhere. No new electrical setting, seed cohort or revision manifest has been selected.

## Budget reconciliation

The [machine-readable ledger](figures/b6_candidate1_decision/budget_reconciliation.json) reconstructs active turns from the local A and B session records, pinned by snapshot byte lengths and SHA-256 hashes. Each charged row includes turn ID, timestamps, duration and event hashes. The original B1/B2/B2.1 ledgers remain unchanged.

| Charge | Active time |
| --- | ---: |
| Earlier partial B1/B2/B2.1 ledger | 37m 15s, superseded subtotal; **not added twice** |
| All recorded Branch A support turns overlapping/after B1 | 2h 02m 48.289s |
| Branch B turns including B6 through 12:45:34.446784 UTC | 1h 12m 33.936s |
| Recorded total assigned to Candidate 1 | **3h 15m 22.225s** |
| Reserved B6 closeout | **10m**, reserved rather than claimed as already spent |
| Conservative committed total | **3h 25m 22.225s** |
| Candidate 1 headroom under 8h after reserve | **4h 34m 37.775s** |
| Overall headroom under 24h after reserve | **20h 34m 37.775s** |

Accounting deliberately charges all recorded A support, status questions, interrupted attempts and concurrent A/B turns fully to C1. It includes the whole A turn crossing B1's start. Idle gaps are excluded; nested approval activity is already inside root-turn durations. The clock measures recorded agent active development, not CPU time or human/off-platform effort. No unrecorded work is asserted. There is one started candidate of at most three. C1's unused allowance is not permission to exceed 8h on another candidate. The closeout reserve bounds this still-active turn; any later work must reconcile its final task-complete event and charge additional work before admission.

These records close the previously missing local active-time entries. The caps are preserved and no further run is being authorized, so the decision is PASS rather than INCONCLUSIVE on local provenance or budget.

## Unknowns and outstanding gates

- **Effect signs:** exact receptor-dependent MBON05→MBON20 and MBON20→DNp42 effects remain UNKNOWN; the double-inhibitory output route is an engineering hypothesis. General KC cholinergic excitation does not quantify each selected contact.
- **Electrical transfer:** per-contact efficacy, intrinsic excitability, decay/delay constants, APL transfer strength and compartment-to-soma transfer lack identifying calibration for this model.
- **Omitted inputs:** only 191 of 8,422 natural DNp42 input contacts are retained; omitted network inputs are replaced by an autonomous telegraph boundary. Other cut-edge contributions and their correlations are unresolved. The position encoder is a fixed artificial KC input, not a validated visual reconstruction.
- **Teaching:** too-early null first actions receive no teaching pulse under B2. All nominal B3 first actions are in this category. This remains a separate learning-chain blind spot even if electrical transfer were repaired.
- **Infrastructure:** A6 integration/readiness is open. A5 reports 153/154 regression tests passing; a legacy Circuit V1 Parquet hash discrepancy under pyarrow 21 versus 25 remains disclosed. Fixture replay success does not remove that gate or validate learning.

## Integrity and verification

The read-only [audit script](../scripts/audit_b6_candidate1.py) verified **89 saved hashes**: 39 B3 neural ledgers and 39 first-action records, eight B3.1 raw artifacts, and three frozen protocol/configuration files. It pinned 197 existing JSON/report artifacts in [evidence_audit.json](figures/b6_candidate1_decision/evidence_audit.json). No simulator was imported or run. Full upstream multi-gigabyte source products were not rehashed; source provenance is chained through the existing receipts and B3.1 source-identity object. B3's field named `source_identity` contains a frozen-policy hash, not the complete connectome manifest; it is not used as a substitute for source provenance here.

## Exactly one next stage, proposed only

**B6.1 — next-candidate admission specification (research/design only).**

- **Question:** Can one independently evidenced candidate specification satisfy an explicit transfer, teaching and provenance admission contract within the remaining caps?
- **Why next:** C1 has been retired, and neither a supported replacement nor a training-ready candidate exists.
- **Hypothesis/outcomes:** A supported specification permits a later separately authorized candidate design; insufficient evidence yields NO-GO; missing provenance or budget yields INCONCLUSIVE.
- **Intervention:** Audit a bounded, predeclared evidence set and write at most one candidate specification. Declare candidate identity, changed assumptions, quantitative constraints with provenance and falsifiable pre-training gates before any simulation.
- **Controls:** Preserve C1, its protocols and raw failures; preserve 8h per candidate, 24h overall and maximum three candidates. Charge this research to its declared candidate and overall ledger from its start.
- **Primary endpoint:** A complete evidence-linked admission specification, including causal selected-weight→output→first-action control and a teaching path for the relevant first-action failures.
- **Secondary:** Unknown effect signs, omitted-input coverage and A6 readiness.
- **Interpretation:** PASS only for an auditable specification with independent support and budget; FAIL for outcome-tuned or cap-breaking proposals; INCONCLUSIVE for essential missing evidence/time.
- **Do not:** Pick numerical values from C1 failures, run simulations/training, launch Candidate 2 automatically, or infer a biological pathway failure from C1.
- **Output/stop:** One admission report and ledger/status update; stop. This proposal does not start the stage or a second candidate.
