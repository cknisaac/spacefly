# Circuit V1 critical-route evidence gate

**2026-09-30 — evidence/design only. Electrical readiness: NO.**

Read with [Circuit V1](../CIRCUIT_V1.md), [the historical sign audit](CIRCUIT_V1_SIGN_AUDIT.md), [biology](BIOLOGY.md), [assumptions](../ASSUMPTIONS.md) and [current state](../CURRENT.md). `docs/BIOLOGY.md` is the canonical biology document; there is no separate root `BIOLOGY.md`.

## Decision

Use a **115-body candidate for the next anatomical/evidence design**, retaining the complete right visual KC class and APL, with **MBON32_R as the candidate learning output and PPL103_R as its candidate compartmental DAN**. The route reaches left DNa02 directly and through left DNa03. This is a concrete alternative to the old MBON11→MBON01→relay route, whose essential MBON01 glutamate effects remain unresolved.

This choice reduces necessary pathway stages and DAN heterogeneity. It does **not** establish KC→MBON32 plasticity experimentally, resolve its exact downstream receptors, or supply the absent drive needed by an inhibitory output pathway. It is a conditional model proposal, not an electrically validated replacement. The implemented 140-body subset and its policy artifacts remain unchanged. No new circuit, electrical parameter, simulation or training was implemented here.

### Four stop-condition answers

1. **Sensory→action:** artificial visible-cue interface → MeVP41_R **13285**, LoVP97(PLP251)_R **13707**, LoVP42_R **13874** → all 107 `KCg-d_R` bodies → MBON32_R **519131** → DNa03_L **519624** → DNa02_L **523769** → fixed one-key interface. Preserve the parallel MBON32→DNa02 source connection. The keyboard interface is an engineering boundary, not an identified fly motor-neuron pathway.
2. **DAN/plasticity:** artificial teaching interface → PPL103(y2a'1)_R **14182** → the proposed γ2 KC→MBON32 plastic compartment. There are **105 candidate KC→MBON32 pairs / 1,129 contacts**. Their individual γ2 locations and plasticity remain unverified. No active plastic mask is approved by this document.
3. **Assumptions:** source-class transfer of physiology; target effects where only inferred; MBON32-specific plasticity; visual cue encoding; signed game-utility conversion into DAN drive; truncated boundary activity; APL spatial reduction; intrinsic model families; fixed key readout. Exact effects, delays, magnitudes, receptor localization and plastic timing retain UNKNOWN fields.
4. **Electrical readiness:** **NO.** Anatomy and a falsifiable route are specified. A complete effect/dynamics/boundary contract is not. This evidence gate is complete by explicitly bracketing the gaps; the activity and learning gates remain open.

## Evidence vocabulary

| Label | Meaning |
| --- | --- |
| `MEASURED` | Retained source reconstruction/annotation observation, or a named direct experiment. EM contacts are not measured conductances. |
| `LITERATURE-CONSTRAINED` | Experimental class/mechanism evidence transferred with its scope stated. |
| `INFERRED` | Homology, transmitter-based expectation or mechanistic extrapolation, without an exact-target demonstration. |
| `ENGINEERING ASSUMPTION` | Explicit interface, model reduction or experiment-design choice. |
| `UNKNOWN` | Unsupported or absent evidence; never an implicit positive, zero or fitted value. |

An anatomical observation and its proposed electrical effect have separate labels. A cited paper's diagram or model sign is not automatically a measured synaptic effect.

## Exact candidate roster and anatomy

| Population | Exact source bodies | Consensus transmitter | Basis / unresolved detail |
| --- | --- | --- | --- |
| Visual-associated inputs | 13285, 13707, 13874 | ACh | Source annotations `MEASURED`; exact functional tuning `UNKNOWN`. |
| Right visual KCs | Complete 107-body `KCg-d` / `soma_side == R` class | ACh | Class cholinergic identity `LITERATURE-CONSTRAINED`; see label reconciliation below. |
| APL_R | 10540 | GABA | Local inhibitory role `LITERATURE-CONSTRAINED`. |
| PPL103(y2a'1)_R | 14182 | Dopamine | γ2/α′1 class mapping `INFERRED`; compartment mechanism constrained below. |
| MBON32(y2)_R | 519131 | GABA | Exact downstream inhibitory effects `INFERRED`, target receptors `UNKNOWN`. |
| DNa03_L | 519624 | ACh | Relay effect onto DNa02 `INFERRED`. |
| DNa02_L | 523769 | ACh | Steering-related class function `LITERATURE-CONSTRAINED`; keyboard role `ENGINEERING ASSUMPTION`. |

The KC IDs are listed in [Circuit V1 §12](../CIRCUIT_V1.md) and in the [machine-readable evidence](figures/circuit_v1_critical_route_anatomy.json). The proposed 115 IDs are also enumerated in that JSON. Their ascending little-endian int64 ID hash is `7b19610ab5c6ec6d295bde7de59da3898b7f27503e553a40b3ceee9e8ec12969`.

All numbers below are `MEASURED` source anatomy in the pinned traced parent:

| Block | Directed pairs | Source contacts |
| --- | ---: | ---: |
| Complete induced 115-body proposal | 10,009 | 45,010 |
| Outside → proposed bodies | 21,129 | 216,255 |
| Proposed bodies → outside | 20,056 | 172,440 |
| Input trio → KCs | 76 | 1,427 |
| KCs → MBON32 | 105 | 1,129 |
| MBON32 → DNa03 | 1 | 38 |
| MBON32 → DNa02 | 1 | 55 |
| DNa03 → DNa02 | 1 | 255 |
| PPL103 → KCs | 107 | 743 |
| PPL103 → MBON32 | 1 | 219 |
| KCs → APL / APL → KCs | 106 / 106 | 5,521 / 5,455 |
| KCs → KCs | 9,370 | 29,043 |

The input trio directly contacts **59/107 KCs**. This does not establish adequate sensory coding. All induced pairs, including KC recurrence, APL's source self-pair and feedback, must remain in anatomy. Any future inactive UNKNOWN or lesion mask must be separate and reported. The 154-body comparison union in the JSON includes alternatives and is **not** this proposal; its boundary statistics must not be substituted for the 115-body statistics.

Example exact source path, with zero-based `source_row` in the imported source order:

| Pre → post | Contacts | Source row |
| --- | ---: | ---: |
| 13285 → 74269 (one KC) | 50 | 225735 |
| 74269 → 519131 | 6 | 5078118 |
| 519131 → 519624 | 38 | 371057 |
| 519624 → 523769 | 255 | 4834 |
| 519131 → 523769, parallel direct path | 55 | 185086 |
| 14182 → 74269 | 5 | 5900596 |
| 14182 → 519131 | 219 | 7577 |

These paths prove anatomical reachability, not response propagation or synaptic colocalization.

## Two corrections to the previous audit's interpretation

**KC predictions versus consensus.** The 107 KCs have 106 dopamine and one GABA individual predictions, dopamine cell-type predictions, and ACh consensus. MaleCNS methods explicitly allow experimental cell-type evidence to override the classifier in `consensusNt` and recommend that field. This reconciles the field semantics; the predictions are not equally supported biological alternatives. Preserve them all. The release does not provide a per-row experimental citation for these bodies, and a null ground-truth field does not invalidate the class consensus. [MaleCNS methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC12636603/)

KC cholinergic transmission has experimental support from transmitter machinery and receptor-sensitive KC-evoked MBON responses. Treat ACh class identity as `LITERATURE-CONSTRAINED`; effects at untested targets remain separately assessed. [Barnstedt et al., 2016](https://pmc.ncbi.nlm.nih.gov/articles/PMC4819445/)

**`receptorType` is not a synaptic receptor inventory.** A whole-source read found only 752 non-null entries: `putative_ppk23` (269), `putative_ppk25` (257), `putative_IR52b` (226), on sensory annotations. Its null values in Circuit V1 cannot establish absence of postsynaptic ACh/GABA/glutamate receptors. The imported `receptor_type_annotation` and policy's similarly named join preserve this source field; they must not be interpreted as target-receptor assays. A future schema clarification is warranted, not fabrication of receptor values.

The historical **78.09% UNKNOWN contact coverage remains the result of the unchanged policy**. Neither correction signs KC recurrence or downstream edges, and no revised coverage claim is made.

## Critical mechanism assessment

| Required mechanism | Evidence and class | Exact-source effect / remaining gap |
| --- | --- | --- |
| Visible cue → input trio | `ENGINEERING ASSUMPTION`: causal feature injection at the circuit boundary. | Natural feature tuning and retinal preprocessing `UNKNOWN`; no ideal action time, target key or judgement may be injected. |
| Input trio → visual KCs | Exact pairs `MEASURED`; visual γd class role `LITERATURE-CONSTRAINED`; cholinergic excitation at these exact targets `INFERRED`. | Receptor-specific effect, gain and temporal filtering `UNKNOWN`. Keep inference distinct from measured positive effects. |
| KC → MBON32 | Exact pairs `MEASURED`; KC cholinergic MBON drive `LITERATURE-CONSTRAINED`; transfer to visual KCγd→MBON32 `INFERRED`. | Exact receptors and plastic locations `UNKNOWN`. |
| MBON32 → DNa03 and DNa02 | Pairs `MEASURED`; inhibitory expectation `INFERRED` from GABA and the proposed steering architecture. | No target-specific paired physiology/receptor proof established here; exact effects `UNKNOWN`. |
| DNa03 → DNa02 | Pair `MEASURED`; excitatory expectation `INFERRED`. | Cholinergic annotation and published model sign do not constitute direct synaptic physiology. |
| DNa02 → motor action | Steering function `LITERATURE-CONSTRAINED`; one-key interface `ENGINEERING ASSUMPTION`. | No reconstructed DN→premotor→motor-neuron→muscle chain is selected. DNa02 is not a keyboard-action neuron. |
| PPL103 → γ2 learning | Contacts `MEASURED`; source compartment homology `INFERRED`; dopamine-dependent compartment learning `LITERATURE-CONSTRAINED`. | Exact KCγd→MBON32 plasticity and release/receptor overlap `UNKNOWN`; proposed depression mechanism `INFERRED`. |
| KCs ↔ APL | Contacts `MEASURED`; recurrent inhibition `LITERATURE-CONSTRAINED`. | Local graded dynamics required; class-specific transfer and spatial reduction remain assumptions. |
| KC recurrence / other induced feedback | Contacts `MEASURED`. | Functional effects, localization and strengths `UNKNOWN`. Must not become uniformly excitatory. |
| Game outcome → DAN signal | `ENGINEERING ASSUMPTION`. | An aversive compartment is not automatically a signed scalar RPE channel. Reward improvement cannot select its polarity after the fact. |

### Visual route

Visual γd KCs and pathways supporting visual associative memory have direct experimental support; the classic VPN-MB1/2 study does not identify these three MaleCNS bodies. [Vogt et al., 2016](https://elifesciences.org/articles/14009)

Raw cross-dataset annotations map MeVP41 to **MTe30**, LoVP42 to **LTe25**, and LoVP97 to **PLP251**. The visual connectome study places PLP251 among local visual interneurons receiving MC62 input. Thus `cb_intrinsic` is compatible with its visual-associated role; it is not evidence against that role. Exact game-cue selectivity remains unknown. [Ganguly et al., 2024](https://pmc.ncbi.nlm.nih.gov/articles/PMC11228034/)

### Learning output and descending route

MBON32 supplies a shorter anatomical route to descending circuitry than the old typical-MBON chain. Mushroom-body connectomics identifies atypical MBON outputs and substantial extra-MB inputs, warning against treating MBON32 as a pure KC sum. [Li et al., 2020](https://elifesciences.org/articles/62576)

Steering recordings establish DNa02's relationship to turning. The same study proposes MBON32-mediated inhibition and PPL103-dependent KC→MBON32 depression as a circuit hypothesis. It does not directly measure plasticity at the selected visual synapses. Its bilateral steering mechanism also cannot be reproduced by calling one retained DN a complete motor circuit. [Rayshubskiy et al., 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC12279373/)

The retained MBON32 output is expected to suppress downstream activity; reducing its KC drive could disinhibit that output. This is an `INFERRED` causal hypothesis whose viability depends on the missing excitatory drive. A quiescent DN cannot be made to act by removing inhibition alone. No tonic drive is assigned to make this hypothesis work.

### DAN localization and plasticity

Use PPL103_R **14182**, annotated `PPL103(y2a'1)_R` with PPL103 cross-matches, as the single anatomical teaching candidate. Its contacts to all 107 KCs and MBON32 support access, **not** proof that its release sites overlap each candidate KC→MBON32 contact. The imported pair tables and body statistics lack per-contact ROI/coordinates. A γ2 ROI and release-site overlap audit is still needed; a neuron-name match is not that audit.

Experimental learning/forgetting in γ2/α′1 supports dopamine-dependent changes at the **typical MBON-γ2α′1** pathway. It does not directly establish the atypical MBON32 rule. MaleCNS comparison IDs **519368 and 521086** (right MBON12) are useful reference cells, not substituted plasticity evidence for MBON32. [Berry et al., 2018](https://pmc.ncbi.nlm.nih.gov/articles/PMC6239218/)

The synthetic mandatory PRE→POST trace is not automatically adopted: compartment experiments report learning-related depression without requiring postsynaptic MBON depolarization. A universal positive `Δw = η e D` would also obscure depression and compartment dependence. The four synthetic gate tests remain software properties. [Hige et al., 2015](https://pmc.ncbi.nlm.nih.gov/articles/PMC4674068/)

### Minimum APL and intrinsic/delay treatment

APL requires local graded, non-spiking inhibition; a single global spike-triggered inhibitory cell is not an adequate default. [Amin et al., 2020](https://elifesciences.org/articles/56954) Its contribution to sparse KC representations is experimentally supported. [Lin et al., 2014](https://pmc.ncbi.nlm.nih.gov/articles/PMC4000970/)

Minimum proposed reduction: distinguish sensory/calyx-facing and lobe-facing APL activity and declare their coupling as an `ENGINEERING ASSUMPTION`. This is a design constraint, not an implemented two-state fit. Contact-to-region mapping remains `UNKNOWN`; preserve other APL inputs as boundary losses. If those local states cannot be justified, defer APL simulation rather than replacing it with uniform LIF.

| Cell family | Known/constrained property | Unknown model quantities |
| --- | --- | --- |
| Inputs | Visual class/anatomical association; encoding is engineered | Tuning, adaptation, membrane and synaptic time scales |
| KCs | Class-level sparse sensory representation | Exact visual-KC intrinsic parameters and recurrent dynamics |
| MBON32 | Anatomical integration of multiple inputs | Exact intrinsic dynamics, target effects and plastic rule |
| PPL103 | Dopaminergic compartment identity | Release dynamics, baseline/tonic state and reward-interface kinetics |
| APL | Local graded inhibition | Spatial coupling, leak, gain and relevant local compartment boundaries |
| DNa03/DNa02 | Descending class identity; DNa02 steering physiology | Exact-body constants, baseline state and effective readout dynamics |

Every biological axonal/conduction/synaptic delay in the selected route remains `UNKNOWN`. Literature constrains mechanism families, not a common numerical delay. Any later LIF or other reduced dynamics must be an explicit class-specific approximation with provenance. This gate assigns **no numerical weights, delays, membrane constants or drives**.

## Boundary inputs: a blocking part of the model

The proposed circuit retains these fractions of traced-parent incoming contacts:

| Population | Retained / parent contacts | Retained fraction |
| --- | ---: | ---: |
| Input trio | 5 / 7,341 | 0.07% |
| KCs | 36,696 / 60,502 | 60.65% |
| APL | 5,848 / 119,936 | 4.88% |
| PPL103 | 748 / 15,339 | 4.88% |
| MBON32 | 1,361 / 16,474 | 8.26% |
| DNa03 | 42 / 17,716 | 0.24% |
| DNa02 | 310 / 23,957 | 1.29% |

Contact fractions are not fractions of physiological drive; they also omit untraced source fragments. The smaller proposal has a **worse DNa03 boundary deficit** than original V1, which retained 1.11%. This is a cost of the reduction, not an improvement in completeness.

`BoundaryInputPolicy` must eventually name the excluded influences for sensory cells, APL, DAN, MBON and DNs. Options to evaluate later are measured/independently constrained boundary activity or an expanded source circuit. No zero-input default, tonic rescue, missing-contact rescaling or task-score-tuned input is selected here. The unilateral readout deliberately omits bilateral steering and body feedback and must be labelled accordingly.

## Alternatives considered

| Alternative | Exact source evidence | Decision |
| --- | --- | --- |
| Original MBON11→MBON01→MBON26/32 route | MBON01 **10013**→MBON26 **11176**: 28 contacts; →MBON32 **519131**: 58 | Keep as historical/plasticity reference. Exact glutamate effects remain UNKNOWN; it is not a signed fallback. |
| Typical γ2 plastic output → MBON32 | MBON12 **519368**, **521086** each →MBON32: 3 contacts | Stronger class plasticity evidence does not validate these small bridges as task-effective. Do not insert them merely to claim the plasticity gap is solved. |
| DNa03→DNa11→DNa02 | **519624→10971**: 207; **10971→523769**: 224 contacts | Adds a stage without establishing exact-target signs or fixing boundary drive. Retain direct DNa03→DNa02 for this proposal. |
| Additional LAL routes | LAL010_L **14986**, LAL051_L **14192**, LAL171_R **18956** have source paths in the JSON | Available for a separately justified boundary expansion, not chosen by contact count or hoped-for performance. |

## Reproducibility and next gate

Run `python scripts/audit_critical_route_evidence.py` with the repository's Arrow/NumPy environment. It streams the parent graph, checks both pinned parent hashes, enumerates all candidate IDs, reports source rows, compares raw transmitter/cross-match fields, and computes the complete induced/boundary counts separately for the 115-body proposal. It writes only analysis JSON. Parent hashes are recorded in that JSON and [Circuit V1](../CIRCUIT_V1.md).

Before a later electrical implementation: approve an explicit policy revision for inferred effects; localize candidate plastic contacts; specify class dynamics and APL reduction; resolve the boundary strategy; and define causal input/output checks. Values need provenance independent of task success. M2 synthetic reliability remains failed and [future diagnostics](FUTURE_DIAGNOSTICS.md) remain paused. No electrical test, optimization or training follows automatically from this report.
