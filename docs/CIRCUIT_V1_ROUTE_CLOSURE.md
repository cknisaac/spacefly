# Circuit V1: closure of the three critical route questions

**2026-09-30. Evidence and design only. Electrical evidence gate: NOT YET PASSED.**

This updates the [critical-route evidence report](CIRCUIT_V1_CRITICAL_ROUTE_EVIDENCE.md), [Circuit V1](../CIRCUIT_V1.md), [biology](BIOLOGY.md), [assumptions](../ASSUMPTIONS.md) and [current handoff](../CURRENT.md). The 115-body proposal remains an anatomical design. The implemented 140-body subset and effect policy are unchanged.

## Five answers

1. **Motor route: conditionally usable (`INFERRED`).** Preserve both MBON32 **519131** → DNa03 **519624** → DNa02 **523769** and MBON32 → DNa02. An inhibitory MBON32 output and excitatory DNa03 relay are defensible *explicit hypotheses*, not established exact-target signs. No reviewed experiment directly establishes the effect of these exact MaleCNS connections.
2. **Plastic targets: a restricted subset is defensible (`INFERRED`).** Of the original **1,129 contacts / 105 KC pairs**, **796 contacts / 100 KC pairs** satisfy the conservative anatomical screen below. This supports candidacy under PPL103 **14182**, not experimentally verified MBON32 plasticity. No neuron substitution is required. The other 333 contacts remain source anatomy and are excluded from the primary plasticity candidate set.
3. **Boundary: recommend C, with B as its control (`ENGINEERING ASSUMPTION`).** Use an explicitly artificial, externally specified DN background/state proxy, paired with an omitted-input condition. Do not expand the circuit just to obtain activity. The proxy must be constrained independently of task performance before it is usable.
4. **Electrical modelling gate: NO (`ENGINEERING ASSUMPTION`, readiness decision).** Motor effects are bracketed and plastic-contact candidacy is localized; the DN boundary contract still lacks a defensible operating-state envelope. Choosing the word “background” does not close this gap.
5. **Single remaining blocker among these three questions: the DN boundary operating-state contract (`UNKNOWN`).** Establish what missing-input state the proxy represents and its independently justified admissible envelope, including temporal structure and shared versus private drive. This is one boundary-design blocker. Exact MBON32 plasticity remains a later learning blocker, not a requirement for a frozen baseline. General electrical implementation specifications remain outside this narrowly scoped audit.

No currents, weights, delays, electrical dynamics, firing-rate tuning or training were assigned or run. No non-critical UNKNOWN connection was signed.

## Evidence labels and scope

| Label | Meaning here |
| --- | --- |
| `MEASURED` | Observations in the named source reconstruction or a named experiment. EM contacts/ROI labels are source observations, not physiological measurements. |
| `LITERATURE-CONSTRAINED` | Experimental class/mechanism evidence with its actual cell, compartment and context stated. |
| `INFERRED` | A proposed transfer, functional interpretation or hypothesis beyond direct evidence. |
| `ENGINEERING ASSUMPTION` | A selection, reduction, interface or comparison chosen for this model. |
| `UNKNOWN` | Not established. Never silently replaced by excitation, inhibition or zero. |

`MEASURED` counts below refer only to the pinned **MaleCNS v1.0 traced-only, confidence ≥0.5 partner product**. Reconstruction errors, omitted fragments and confidence filtering remain limitations. A contact count is neither efficacy nor the fraction of physiological drive.

## 1. MBON32 to descending output

### Exact anatomy and functional evidence

All anatomical counts and locations in this table are `MEASURED` source observations. Functional interpretations have separate labels.

| Source connection | Contacts; postsynaptic primary ROI | Defensible effect hypothesis | Exact effect evidence |
| --- | --- | --- | --- |
| MBON32_R **519131** → DNa03_L **519624** | **38**: LAL(L) 30, VES(L) 3, unspecified central brain 5 | `INFERRED`: activity-suppressing GABAergic action in the declared operating state | `UNKNOWN`: target receptors, reversal potential, shunting versus hyperpolarizing action, efficacy and kinetics |
| MBON32_R **519131** → DNa02_L **523769** | **55**: LAL(L) 47, unspecified central brain 8 | `INFERRED`: activity-suppressing GABAergic action | Same exact-target gaps; a real parallel source path, not an artificial shortcut |
| DNa03_L **519624** → DNa02_L **523769** | **255**: LAL(L) 146, VES(L) 66, SPS(L) 16, IPS(L) 15, GNG 4, EPA(L) 2, WED(L) 1, unspecified 5 | `INFERRED`: activity-promoting cholinergic action | `UNKNOWN`: exact target receptor/effect and transfer dynamics |

**`MEASURED`:** The partner table independently reproduces the parent pair counts. MBON32 519131 has **zero retained contacts** to the other-side DNa03 **10975** or DNa02 **10360** in this traced parent. This is source absence, not proof of biological absence. DNa02→DNa03 has four retained contacts; their effect remains out of scope and UNKNOWN.

**`INFERRED`:** [Li et al., 2020, descending-pathway figures](https://elifesciences.org/articles/62576/figures) provides an independent connectomic precedent for contralateral MBON32 outputs to DNa03 and DNa02. That supports class homology and route choice, not a physiological assay in these MaleCNS bodies. The GABA source annotation and the published circuit interpretation together support an inhibitory hypothesis; neither measures the postsynaptic response.

**`LITERATURE-CONSTRAINED` / `INFERRED`, respectively:** [Rayshubskiy et al., version of record 2025](https://cdn.elifesciences.org/articles/102230/elife-102230-v1.pdf) records DNa02 in walking flies, while its Figure 7 MBON32/relay mechanism is a connectome-based interpretation. Its proposed learning-to-steering pathway therefore supports a mechanism to test, not exact MBON32→DN physiology. The present unilateral, reduced circuit also omits branches used in that paper's bilateral steering interpretation; it cannot claim to reproduce the whole mechanism.

**`INFERRED`:** [Westeinde et al., 2024, transmitter methods and network model](https://pmc.ncbi.nlm.nih.gov/articles/PMC10881397/) explicitly identifies DNa03 cholinergic identity using EM transmitter prediction. Positive relay coupling in its model follows that prediction. This is a useful prior, not direct DNa03→DNa02 synaptic pharmacology. Its fitted/heuristic model strengths are not imported here.

**`UNKNOWN`:** No exact-pair stimulation/recording or target-receptor evidence establishing these three effects was found in the reviewed primary sources. This is a bounded literature-search conclusion, not a claim that such evidence can never exist. Generic transmitter identity alone does not close it.

### Smallest bounded hypotheses for a later comparison

**`ENGINEERING ASSUMPTION`:** Keep source anatomy and biological `effect = UNKNOWN` separate from a named, optional experimental effect hypothesis. The candidate mechanism has three functional commitments: MBON32 suppresses each DN; DNa03 promotes DNa02 activity. “Suppresses” is a prediction about a postsynaptic response in a declared state, not a specified reversal potential or negative constant.

| Predeclared condition | Functional hypothesis or intervention | Question answered |
| --- | --- | --- |
| H-route | `INFERRED`: both MBON32 branches suppress; DNa03 relay promotes activity | Can this published circuit interpretation transmit modulation under the boundary contract? |
| H-no-MBON32→DNa03 | `ENGINEERING ASSUMPTION`: ablate only this functional coupling from H-route | Contribution of the indirect MBON32 branch |
| H-no-MBON32→DNa02 | `ENGINEERING ASSUMPTION`: ablate only this functional coupling | Contribution of the direct MBON32 branch |
| H-no-DNa03→DNa02 | `ENGINEERING ASSUMPTION`: ablate only relay coupling | Whether the effect at DNa03 reaches DNa02 |
| H-no-MBON-output | `ENGINEERING ASSUMPTION`: ablate both MBON32 outputs | Whether an apparent sensory/action association comes from the boundary/readout instead |

These are a finite mechanism comparison, not a sign/learning-rate search. An ablation is explicitly imposed zero coupling; it does **not** reinterpret biological UNKNOWN as absent. The three single-edge ablations distinguish the three commitments without enumerating arbitrary sign combinations. No condition is implemented or selected by task score. Quantitative efficacy bounds belong to a later model contract; this document bounds the hypotheses structurally and by predicted direction only.

**`INFERRED`:** Under H-route, stronger KC excitation of MBON32 should suppress descending activity; depression of eligible KC→MBON32 transmission can relieve that suppression. It cannot supply the absent target drive. This conditional disinhibition argument is why the DN boundary is critical. **`ENGINEERING ASSUMPTION`:** DNa02 activity-to-key mapping remains a fixed artificial interface; fly steering physiology does not prescribe an osu key or its ideal press time.

## 2. KC→MBON32 under PPL103

### New compartment/contact audit

**`MEASURED`:** Partner coordinates were mapped to the release-linked `malecns-subcompartments-v3` ROI volume. Source coordinates are in 8-nm units; the mask is 256 nm, so mask indices are `floor(xyz / 32)`. Individual pre- and postsynaptic endpoints were mapped separately. This is coarse compartment membership, not a receptor assay or a dopamine diffusion calculation.

| Contact block | All traced contacts / source pairs | Both endpoints in right γ2: contacts / pairs |
| --- | ---: | ---: |
| 107 selected KCs → MBON32 519131 | 1,129 / 105 | **808 / 104** |
| PPL103_R 14182 → selected KCs | 743 / 107 | **408 / 102** |
| PPL103_R 14182 → MBON32 519131 | 219 / 1 | **139 / 1** |
| Comparison: PPL103_L 11752 → selected right KCs | 620 / 107 | **352 / 96** |
| Comparison: PPL103_L 11752 → MBON32 519131 | 223 / 1 | **140 / 1** |

**`MEASURED`:** The 1,129 KC→MBON32 contacts partition into 808 with both endpoints in γ2(R), 8 with both in γ3(R), 282 with both unspecified, and 31 crossing the γ2/unspecified mask boundary (16 pre-only γ2; 15 post-only γ2). The 256-nm boundary and unspecified masks prohibit assigning every contact by the MBON's class name. They do not prove that the unspecified contacts lie outside the functional compartment.

**`ENGINEERING ASSUMPTION`:** Use a conservative *anatomical candidacy screen*, requiring:

1. Both endpoints of the KC→MBON32 contact lie in γ2(R).
2. That same KC receives at least one 14182→KC contact with both endpoints in γ2(R).

**`MEASURED`:** The intersection yields **796 contacts on 100 KC→MBON32 pairs**. Four additional KCs have strict γ2 output contacts but no strict same-KC 14182 contact: **39316, 49709, 62274, 78768**, together 12 output contacts. KC **76076** contributes to the original 105-pair block but not the 104-pair strict γ2 block. These exclusions are reproducible in [the summary and complete candidate KC IDs](figures/circuit_v1_route_closure_summary.json).

**`INFERRED`:** The 796 contacts are defensible candidates for compartmental PPL103 action. This is a conservative screen, not a biological rule that direct DAN→same-KC contact is necessary: extrasynaptic dopamine may act beyond such contacts. It also is not sufficient to prove release at the candidate terminal, receptor occupancy or plasticity. There is no invented diffusion radius.

**`MEASURED` / `ENGINEERING ASSUMPTION`:** Both PPL103 source cells contact the right γ2 circuit. Soma-side labels do not uniquely delimit dopamine access. Retaining only 14182 is an intentional single-DAN experimental boundary; 11752 is not added. A later claim about complete natural teaching would have to revisit that omission.

### Keep five claims separate

| Claim | Conclusion and classification |
| --- | --- |
| Anatomical contact | `MEASURED`: KC→MBON32, PPL103→KC and PPL103→MBON32 partner rows exist; all source IDs/counts are retained. |
| Compartment overlap | `MEASURED`: the specified contacts map to a common source γ2(R) mask. `INFERRED`: this supports the intended functional compartment despite coarse boundaries. |
| Dopamine access | `INFERRED`: same-compartment release-site contacts on the same KC and MBON make access plausible. Actual dopamine concentration, spread, receptor localization and time course at each candidate are `UNKNOWN`. A DAN→MBON contact is not itself proof that a KC terminal is modulated. |
| KC→MBON plasticity | `LITERATURE-CONSTRAINED`: dopamine-dependent KC/MBON learning mechanisms exist; γ2α′1 experiments constrain the compartment. Transfer to these visual KCs and MBON32 is `INFERRED`, not a direct MBON32 result. |
| Exact rule | `UNKNOWN`: polarity versus timing/state, eligibility window, requirement for postsynaptic spikes, release/recovery kinetics, magnitude, saturation and long-term persistence for these contacts. No scalar update is approved. |

**`LITERATURE-CONSTRAINED`:** [Berry et al., 2018](https://pmc.ncbi.nlm.nih.gov/articles/PMC6239218/) demonstrated learning-related depression and subsequent restoration of odor responses in **MBON-γ2α′1 (MBON12)** under cognate DAN manipulation. This constrains the compartment and illustrates state/history dependence; it is not a recording of MBON32 or isolated efficacy at these contacts. [Hige et al., 2015](https://pmc.ncbi.nlm.nih.gov/articles/PMC4674068/) provides direct KC→MBON plasticity evidence in another compartment and does not justify treating synthetic PRE→POST pairing as universally necessary. [Barnstedt et al., 2016](https://pmc.ncbi.nlm.nih.gov/articles/PMC4819445/) supports cholinergic KC transmission to MBONs, not this exact plasticity rule.

### Minimum correction, without a population change

**`ENGINEERING ASSUMPTION`:** Replace the blanket “1,129 plastic contacts” proposal with the 796-contact *candidate* set. Keep all 107 KCs, all 1,129 anatomical contacts and the same MBON/DAN. No cell substitution is currently justified. Substituting MBON12 would improve direct class plasticity evidence but would require a different downstream-route audit; it is not a free replacement preserving the audited route.

**`ENGINEERING ASSUMPTION`:** Future runtime representation must distinguish eligible-contact contribution from the other contacts on a shared source pair. A pair with at least one candidate contact must not silently make its whole anatomical count plastic. The saved candidate parquet is an analysis artifact, not an active learning mask. First frozen baseline: all learning disabled; exact-rule uncertainty cannot be interpreted as a positive synthetic dopamine update.

## 3. Missing descending input and the boundary choice

### Quantification

All counts and percentages in this section are `MEASURED` anatomy relative to the 115-body proposal and traced parent.

| Target | All incoming pairs / contacts | Retained pairs / contacts | Missing pairs / contacts | Missing contacts |
| --- | ---: | ---: | ---: | ---: |
| DNa03 519624 | 716 / 17,716 | 2 / 42 | **714 / 17,674** | **99.7629%** |
| DNa02 523769 | 1,138 / 23,957 | 2 / 310 | **1,136 / 23,647** | **98.7060%** |

DNa03's retained 42 comprise MBON32's 38 plus DNa02's four feedback contacts. DNa02's 310 comprise DNa03's 255 plus MBON32's 55. Together the DNs lose input from **1,420 distinct outside presynaptic bodies**. Every incoming pair and count was independently matched between the aggregated parent and contact table; [the complete input ledger](figures/circuit_v1_route_closure_dn_inputs.json) identifies each body, class and source row.

| Missing contacts by source consensus annotation (`MEASURED`) | DNa03 | DNa02 |
| --- | ---: | ---: |
| Acetylcholine | 10,369 | 15,642 |
| GABA | 3,504 | 4,328 |
| Glutamate | 3,648 | 3,470 |
| Dopamine | 49 | 23 |
| Octopamine | 36 | 76 |
| Histamine | 1 | 4 |
| Serotonin | 1 | 0 |
| Unclear | 66 | 104 |

**`UNKNOWN`:** These transmitter counts cannot be converted into E/I balance, tonic current, firing rates or missing conductance fractions. Glutamate is not automatically inhibitory, and annotation alone does not establish any exact target effect. Untraced parent omissions are additional unquantified inputs.

**`MEASURED`:** Large omitted classes include PFL2 (830 contacts), LAL112 (577) and LAL051 (495) into DNa03; AN03A008 (741), PS049 (492), PS059 (476) and PFL3 (356) into DNa02. **`INFERRED`:** Missing input is structured sensory, internal-state and motor-related activity rather than a known homogeneous noise source. **`LITERATURE-CONSTRAINED`:** DN recordings in [Rayshubskiy et al.](https://cdn.elifesciences.org/articles/102230/elife-102230-v1.pdf) establish behavior-dependent activity; they do not identify a unique replacement input process for this excised pair.

### Compare only A, B and C

| Policy | Evidence and consequences | Decision for the first frozen baseline |
| --- | --- | --- |
| **A. Expand the boundary** | `MEASURED`: adding all **24 PFL2/PFL3 direct donors** would add 1,081 contacts to DNa03 and 356 to DNa02. Retention becomes only **6.3389% / 2.7800%**. Adding all direct missing donors requires 1,420 extra cells and creates a new upstream cut. `INFERRED`: a small PFL expansion alone does not reconstruct the DN operating state. | `ENGINEERING ASSUMPTION`: do not expand for this first reduction. No cells were added. Revisit only for a separately scoped natural steering circuit. |
| **B. Explicitly omit missing input** | `ENGINEERING ASSUMPTION`: an intentional deafferentation, not a claim that absent source activity is zero in the fly. `INFERRED`: silence or weak modulation can reflect the cut, not failure of the biological route. | Keep as the required frozen control. It is defensible as an isolated/lesioned model, not a representative intact-fly baseline. Do not increase gain until it acts. |
| **C. Explicit background/boundary proxy** | `ENGINEERING ASSUMPTION`: a replacement process applied separately at DNa03 and DNa02. Actual omitted-input statistics remain `UNKNOWN`. `INFERRED`: it can expose whether suppression/disinhibition works in a declared state, without importing thousands of new cells. | **Recommended minimum for an interpretable reduced frozen baseline, conditional on the contract below.** Pair it with B and a proxy-present/MBON-output-ablated control. |

### Minimum C contract; still incomplete

The following restrictions are **`ENGINEERING ASSUMPTION`**, not reconstructed biology:

- The proxy stands for omitted DN afferents only, with separate accounting for each target. It does not replace retained source contacts or manufacture an MBON→DN bridge.
- Start with a declared fixed behavioral-state approximation. It must be cue-, reward-, future-note- and key-target-independent, with no hidden ideal timing or closed-loop adjustment to obtain presses. This deliberately omits natural task-correlated external input.
- Specify excitatory/inhibitory or net-drive representation, temporal dependence, and shared/private components explicitly. “Poisson noise” or “tonic bias” is not selected by default. Do not infer these features from transmitter contact fractions.
- Set an admissible envelope from independent class physiology or a bounded, explicitly acknowledged engineering operating-state assumption **before observing task performance**. Record the derivation and what biological claim is forfeited. Do not copy a published DN firing rate into an injected current or use inverse retained-contact fraction as gain.
- Keep this process and its predeclared random streams matched across motor-hypothesis conditions, source lesions and later controls. No rate targeting, reward feedback, post hoc stream selection or performance-based setting choice.
- Report B, C, and C with MBON output ablated. A cue-locked effect present only with the proxy is conditional on that proxy. Activity/presses without the MBON route do not demonstrate route function.

**`UNKNOWN` — the one remaining route blocker:** available anatomy and reviewed physiology do not yet specify the reduced pair's admissible boundary operating-state envelope. The temporal structure and coupling of the two missing-input streams, and an independent basis for their effective strength range, are absent. This document recommends the boundary *policy* but does not certify an unbounded proxy as defensible. No numerical currents are assigned.

**`ENGINEERING ASSUMPTION` — closure criterion for a later task:** write one auditable DN boundary contract choosing the represented state and a finite, independently justified envelope (or a plainly declared engineering envelope with restricted claims), with the matched B and disconnected controls fixed in advance. If no such justification is available, retain B as a deafferented negative control and keep the meaningful frozen-fly baseline gate closed. This does not require perfect fly electrophysiology or reconstruction of all missing cells.

## 4. Reproducibility and limits

**`MEASURED` — source provenance:** the parent neuron SHA-256 remains `7d9a410d61d4caa934fa3639f9d204291ff0d18c445b2384054b95286d6350eb`; edge SHA-256 remains `da21af867d4e8e4c627c9916e55af4332302b611a296de1d0a8bc7dd6ebcff7a`. Both were rechecked. The 115 IDs have the unchanged ascending-int64 hash `7b19610ab5c6ec6d295bde7de59da3898b7f27503e553a40b3ceee9e8ec12969`.

**`MEASURED`:** The downloaded [official traced partner object](https://storage.googleapis.com/flyem-male-cns/v1.0/connectome-data/flat-connectome/syn-partners-male-cns-v1.0-minconf-0.5-traced-only.feather?generation=1780494912394119) contains **124,025,046 rows**, matching summed parent contacts. Size: **2,965,367,002 bytes**; SHA-256: `3db100d3b4c7cfdc9b34506b3eb8b5ead2d9760b38952e5656285bb362327efc`. Published MD5 was verified. A 70,236-row critical extraction retains source row numbers and both contact endpoints. [MaleCNS download documentation](https://male-cns.janelia.org/download/) defines the coordinate/partner products.

**`MEASURED`:** The release database scene points to `rois/malecns-subcompartments-v3`. Metadata and fetched chunks have generation-pinned URLs, size, MD5 and SHA-256 receipts. Of 91 requested ROI chunks, 11 return HTTP 404 and remain `UNKNOWN_MISSING_CHUNK`; none affects the five critical KC/MBON/DAN contact blocks reported above. Unspecified mask values also remain unspecified. The decoder follows the [Neuroglancer compressed-segmentation specification](https://raw.githubusercontent.com/google/neuroglancer/master/src/sliceview/compressed_segmentation/README.md) and passed manually packed constant/nonconstant uint64 fixtures.

**`MEASURED`:** Eight independent exact-coordinate/body/pre-post/ROI checks against the release syn-point Feather file passed: pre and post examples for γ2(R), γ3(R), α′1(R) and unspecified. These validate the coordinate conversion and sampled labels; they are spot checks, not an independent reconstruction of every mask boundary. Remote range reads transferred 31,012,869 bytes, avoiding a full 13-GB point download. T-bar neurotransmitter probabilities were not treated as receptor evidence or a functional assay.

### Data-only artifacts and commands

- [Partner-source receipt and contact totals](figures/circuit_v1_route_closure_partners.json).
- [ROI receipts and compartment totals](figures/circuit_v1_route_closure_roi.json).
- [Independent source-point checks](figures/circuit_v1_route_closure_roi_checks.json).
- [Candidate mask/counts and DN summaries](figures/circuit_v1_route_closure_summary.json).
- [Complete DN parent-input ledger](figures/circuit_v1_route_closure_dn_inputs.json).
- Candidate contact rows: `data/processed/malecns_v1_route_closure/plastic_contact_candidates_anatomy_only.parquet`, with original partner row IDs; other analysis parquets sit beside it.

From the project root, after the pinned public source download:

```powershell
.venv\Scripts\python.exe -m scripts.audit_route_closure_partners
.venv\Scripts\python.exe -m scripts.audit_route_closure_roi
.venv\Scripts\python.exe -m scripts.check_route_roi_against_points
.venv\Scripts\python.exe -m scripts.summarize_route_closure
```

The ROI/source-point commands require public-source network reads. All are data audits. No neural experiment is invoked. The summary verifies both parent hashes and matches **every incoming DN source pair/count** against the independent partner table, along with the 796/100 candidate screen and absence of missing chunks in critical groups.

## Stop and handoff

**`ENGINEERING ASSUMPTION`:** This task ends with the three-blocker evidence assessment. The next scoped decision is the **DN boundary operating-state contract**, not an electrical run. APL reduction, non-critical UNKNOWN edges, class parameters, delays, sensory encoding and readout implementation were not changed. The current policy remains non-runnable, the all-positive overlay remains rejected, and no biological learning claim is approved. Resuming synthetic diagnosis still requires starting from [FUTURE_DIAGNOSTICS.md](FUTURE_DIAGNOSTICS.md).
