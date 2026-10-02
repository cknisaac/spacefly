# MVP-B1 — pathway and learning-rule selection

**2026-10-01. B1 PASS for candidate selection; implementation, controllability and learning remain untested.** This is the new roadmap's B1, not a relabeling of historical Branch B. The [pre-research protocol](../configs/b1_mvp_pathway_rule_selection.json) fixed scope and criteria. The decision selects **Candidate 1: a γ4 KC→MBON05 learning circuit with a measured MBON05→MBON20→DNp42 output route**. It replaces MBON32/PPL103 as the primary MVP candidate. The old visual-circuit evidence remains intact.

## Selected coherent package

| Component | B1 selection | Evidence label and limit |
| --- | --- | --- |
| Sensory population | All **689 left KCg-m** cells in the pinned MaleCNS traced graph; direct fixed current-visible-position input. | Population/IDs **MEASURED** source annotation; artificial position code **ENGINEERING ASSUMPTION**. Olfactory-class KCs are intentional because direct artificial input is allowed. |
| Plastic locus | The γ4 contribution of KCg-m_L→**MBON05 10495**, annotated `MBON05(y4>y1y2)_R`. | **689 measured pairs / 16,398 contacts** are anatomical candidates. They are not yet an active plastic mask. Contact-local γ4 assignment and separation from any off-compartment component must be locked at B2. |
| Teaching population | The complete **25 PAM08_L** cells that supply the selected KC class; model their local γ4 modulation. | Their edges are **MEASURED**. Transfer from experimentally stimulated γ4/γ5 PAM populations to this precise PAM08 subset is **INFERRED**; the study did not isolate these MaleCNS cells. |
| Rule family | Local KC/DAN temporal-order plasticity: a recent KC trace supports depression on subsequent dopamine; a recent dopamine trace supports potentiation on subsequent KC activity. | Timing-dependent opposing plasticity is **LITERATURE-CONSTRAINED**; the chosen causal two-trace approximation, gains, kernels and clipping are **ENGINEERING ASSUMPTION**. No calibrated equation is claimed. |
| Fixed downstream route | **10495 MBON05 → 11145 MBON20_L → 10713 DNp42_L**. Keep measured parallel and recurrent edges within the candidate boundary. | **169 and 191 source contacts**, respectively, **MEASURED**. Exact pair effects/receptors are **UNKNOWN**. An inhibitory effect hypothesis for each output edge must be explicitly declared as an engineering policy informed by class evidence. |
| Motor interface | DNp42 spike-window activity → fixed threshold/hysteresis → one key DOWN/UP; parameters fixed before training. | Entire keyboard mapping **ENGINEERING ASSUMPTION**. It observes no note timestamp, reward, target action time or learned decoder weights. B2 fixes the window, thresholds, release and cooldown policy. |
| Additional retained circuit | **APL_L 10977**, the selected KCs and PAM08s, MBON05, MBON20 and DNp42: **718 source neurons** total. | Roster **MEASURED**; selecting this boundary is **ENGINEERING ASSUMPTION**. APL remains a separately justified graded/inhibitory model. |

Source labels must not be mistaken for functional laterality: **10495 has a right soma label but its γ KC inputs are left-sided**. We choose it with the matched left KC/PAM compartment based on actual source edges. Both hemispheres of all five candidate families were screened (12 MBON bodies); this is a bounded comparison, not proof of a globally optimal brain circuit.

## Why this candidate

The strongest combination in this review is named-compartment temporal plasticity plus a short measured route to an experimentally motor-related DN. The γ4 candidate improves the plasticity evidence over the legacy MBON32 choice. It still needs electrical hypotheses; anatomical contact count is neither synaptic efficacy nor evidence of behavioral control.

| Candidate family | Plasticity evidence | Local anatomical comparison | Decision |
| --- | --- | --- | --- |
| **γ4 / MBON05 / PAM08** | Handler's γ4 preparation provides temporal-order reversal at the relevant class/compartment. | Both MBON05 cells reach DNp42 through MBON20. Selected side has 169/191 contacts; the opposite side has 156/143. | **Select for Candidate 1**, conditional on B2 design and B3 control authority. |
| **γ1pedc / MBON11 / PPL101** | Hige provides unusually direct electrophysiological LTD evidence. | In this bounded screen, direct DN contacts are sparse and the strongest two-hop bottleneck is 18 contacts on either side. Longer routes remain possible. | Strong biological alternative, but weaker short-route support and no justification here for simply assigning an arbitrary opposite update sign. |
| **γ2α′1 / MBON12 / PPL103** | Berry supports learning-related depression and recovery in the named MBON class. | Four source MBON12 bodies; strongest screened two-hop bottleneck is 83 contacts, with additional relay/effect uncertainty. | Credible alternative; γ4 offers a more explicit temporal-order rule and the selected output route. |
| **γ5β′2a / MBON01 / PAM01/PAM15** | Handler's supplementary γ5 result supports temporal reversibility. | Mixed γ5/β′2a inputs and multiple relevant PAM types; best screened two-hop bottleneck is 79 contacts. | Reserve; more compartment/DAN attribution burden for this first candidate. |
| **γ2 / MBON32 / PPL103** | Legacy transfer of γ2α′1 findings to MBON32 remains indirect. | Excellent documented DN routes and existing engineering runtime; no new activity evidence here. | Preserve as legacy/reference. Existing implementation convenience does not establish its learning rule. |

The route score above is only the smaller contact count of the two edges, used to describe anatomical routes. It is not a fitted objective, physiological score or automatic selection rule. No candidate was simulated or judged on task performance.

## Primary-source evidence ledger

| Source and inspected location | Supported conclusion | Transfer limit |
| --- | --- | --- |
| [Handler et al., 2019](https://pmc.ncbi.nlm.nih.gov/articles/PMC9012144/), Results on γ4 temporal pairing; Figures 2, 4, 6 and S3; genotype table | In adult fly preparations, KC-before/concurrent-DAN pairing depresses γ4 KC→MBON signaling; DAN-before-KC pairing potentiates it. Opposing receptor pathways and reversible learning accompany this temporal sensitivity. | Readout is largely calcium; experiments use broad PAM drivers and olfactory/KC stimulation. They do not identify exact MaleCNS weights, PAM08-only sufficiency, a ±73-ms motor learning kernel, signed reward-error multiplication, or instrumental first-action credit. |
| [Hige et al., 2015](https://www.janelia.org/sites/default/files/Labs/1-s2.0-S0896627315009824-main.pdf), Figures 1, 3, 4 | γ1pedc odor/DAN pairing produces input-specific depression, including reduced synaptic current; postsynaptic spiking is dispensable in that preparation. | A different compartment. Its old backward-pairing condition showed no effect; a universal signed pre/post-spike rule is not justified. |
| [Berry et al., 2018](https://pmc.ncbi.nlm.nih.gov/articles/PMC6239218/), Figures 2–5 | Named γ2α′1 MBON responses are depressed by learning and can recover after subsequent cognate DAN activation. | Recovery depends on stimulus/history conditions; neither exact KC terminal efficacy nor MBON32 plasticity is established. |
| [Li et al., eLife 62576](https://elifesciences.org/articles/62576/figures), Figures 7, 8 supplement 2 and 23 | Supports MBON05 γ4 nomenclature, MBON feedforward organization and the MBON20–DNp42 anatomical route in another reconstruction. | Those counts are not imported into MaleCNS. Putative inhibitory effects remain distinct from demonstrated pair physiology. |
| [Descending networks, Nature 2024](https://www.nature.com/articles/s41586-024-07523-9), Extended Data Figure 10 | DNp42 activation produces backing behavior in intact animals, with dependence on the broader descending network. | Supports motor relevance, not a keyboard mapping or natural behavior from our reduced circuit. |
| [Barnstedt et al., 2016](https://pubmed.ncbi.nlm.nih.gov/26948892/), primary abstract | KC transmission can activate MBONs through nicotinic cholinergic signaling. | Supports a family-level excitatory KC output hypothesis; no exact efficacy for the selected contacts. |

**Access limits:** Hige's author-hosted PDF, the Nature page and the official [MaleCNS release page](https://male-cns.janelia.org/download/) were opened. PMC direct pages returned a browser challenge; Handler/Berry text and Handler methods/genotypes were inspected through indexed primary-source excerpts. eLife direct access was challenged, so indexed primary article/figure text was used. An attempted Europe PMC full-text retrieval returned HTTP 500. This is a bounded review with these access limits, not a claim to have inspected every supplementary image. Exact sex/preparation transfer to the adult MaleCNS specimen is not established by this audit.

## Learning-rule and information boundary

Select a **causal two-trace heterosynaptic rule family**. Each selected KC terminal carries a recent-KC state; the γ4 modulatory compartment carries a recent-DAN state. Current dopamine interacting with prior KC activity contributes depression; current KC activity interacting with prior dopamine contributes potentiation. B2 must specify how the competing contributions behave at coincidence, how traces decay, and how weights remain bounded. A postsynaptic spike is not imposed as a universal biological requirement. These are local neural/modulatory states; the interface and decoder remain fixed.

The observed temporal polarity constrains the model. It does **not** make a particular pair of exponential kernels, 80-ms eligibility constant, learning rate, full pair mask or molecular receptor simulation experimentally measured. Literature subsecond/second pairing intervals must not be silently rescaled into the game's ±73-ms target.

The teacher may consume **resolved first-action outcome → utility → reward expectation/error → artificial PAM drive**, with each stage logged. It may not supply a future countdown through sensory input. Dopamine release is represented as nonnegative local activity, possibly with a stated baseline. **Do not convert a negative reward error directly into negative dopamine concentration or assume it reverses the biological update sign.** B2 must design early, late and no-DOWN feedback causally and show how it can produce useful weight changes under this rule. This is an unresolved candidate-design question; the rule's temporal reversibility does not by itself solve bidirectional action-timing correction. If no defensible mapping can be specified within the budget, reject or revise the candidate before training.

## Anatomical audit and practical risks

The [comparison](figures/b1_mvp_pathway_rule_selection/anatomy_comparison.json) and [selected anatomy](figures/b1_mvp_pathway_rule_selection/selected_anatomy.json) retain cell IDs, source rows, counts and hashes. All **8,202 unique critical aggregate rows** were independently compared against the raw traced source, and both normalized parent hashes match their existing validation receipt. The raw aggregate source hash is also checked against the source manifest. The [analysis script](../scripts/audit_b1_mvp_anatomy.py) imports only data libraries, never the simulator.

| Block | Pairs | Contacts |
| --- | ---: | ---: |
| Selected KCg-m → MBON05 | 689 | 16,398 |
| Selected PAM08 → selected KCs | 6,900 | 10,601 |
| Selected PAM08 → MBON05 | 25 | 918 |
| Selected KCs → MBON20 (fixed bypass) | 586 | 1,588 |
| MBON05 → MBON20 | 1 | 169 |
| MBON20 → DNp42 | 1 | 191 |

All 689 selected KCs receive a source contact from the selected PAM population. This supports anatomical access, not release/receptor colocalization at every candidate synapse. The anatomy-only 718-cell proposal has **153,854 induced pairs / 333,380 contacts** and cuts **51,789 incoming pairs / 266,094 contacts**. Retained incoming contacts are **17,886/23,058** for MBON05, **1,773/6,133** for MBON20, and **191/8,422** for DNp42. Thus the output circuit loses most of its natural input and requires an explicit fixed boundary policy. No tonic current or effect strength has been selected.

The KC→MBON20 bypass, KC recurrence, APL and retained feedback must be accounted for rather than erased to obtain a clean chain. The major B3 risk is that the plastic KC→MBON05 pathway has insufficient control over DN activity relative to those fixed inputs. Selected-weight-off, MBON05-output-off and background-only controls will distinguish these cases. A source-derived circuit that fails under one set of declared assumptions does not disprove the biological pathway.

## Exact next stage — B2, complete candidate design

**Question:** Can this γ4 package be specified as one causal, reproducible learning system with useful first-action feedback and a tractable electrical boundary?

**Why next / possible outcomes:** B1 supplies the best-supported package among the reviewed families. B2 may produce a complete design, identify a bounded revision, or reject it because the feedback/rule/effect assumptions cannot be reconciled. A B1 selection pass does not imply a B2 or B3 pass.

**Intervention:** Design only: establish contact/compartment mask, local trace equations and event order, nonnegative PAM teaching semantics for early/late/no-DOWN, numerical assumptions, fixed current-position encoder, DN boundary and fixed readout; list every tunable value and permitted development change. Specify a fixed first-action metric including absent/extra actions and a predeclared multi-state B3 panel.

**Frozen controls:** Preserve source release, historical evidence, current code and all B1 records. Require identical input, initial state, seeds and interfaces across later plasticity-off, DAN-off, eligibility-off and shuffled/wrong-note controls.

**Primary endpoint:** A complete auditable candidate specification with no hidden timing channel and experimentally constrained rule polarity. **Secondary endpoints:** parameter/evidence registry, implementation checklist, A1–A5 dependency checklist, B3 rejection criteria and development-time ledger.

**Interpretation / prohibitions:** PASS only when all required terms are defined and assumptions labeled. Otherwise record FAIL/INCONCLUSIVE and the precise gap. No performance-based value selection, sign search, new neural run or claim of biological first-action learning.

**Output / stop:** Candidate design document plus resolved non-executable specification, followed by a single proposed implementation/controllability stage. Stop before implementation unless that future request separately authorizes it. User's usage defaults: **B2 GPT-6.1 Sol / Medium**. B1 research time is charged to Candidate 1's **8 active hours**; no second candidate has started, and the three-candidate/24-hour limit remains.

## Development budget and verification receipt

B1 charged **15.4 minutes** of conservative elapsed active time to Candidate 1, leaving approximately **7.74 hours** at this record. See the [time ledger](figures/b1_mvp_pathway_rule_selection/budget_ledger.json) and [artifact receipt](figures/b1_mvp_pathway_rule_selection/artifact_receipt.json). This includes research, analysis and documentation; no simulation or training ran.
