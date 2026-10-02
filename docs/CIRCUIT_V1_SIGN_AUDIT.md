# Circuit V1 sign and effect coverage audit

**2026-09-29 · Data and graph diagnostics only.** MaleCNS v1.0, exact 140-body Circuit V1 subset. No electrical run, activity tuning, plasticity, or training was performed. The [machine-readable audit](figures/circuit_v1_sign_audit.json) is reproduced by `PYTHONPATH=src .venv/Scripts/python.exe scripts/audit_circuit_v1_signs.py` from the project root. Source contacts are reconstructed EM contact counts, **not** conductance or functional drive.

## Interpretation correction — 2026-09-30

The counts and unchanged policy audit below remain valid. The [critical-route evidence report](CIRCUIT_V1_CRITICAL_ROUTE_EVIDENCE.md) corrects two interpretations: MaleCNS consensus deliberately permits experimental cell-type evidence to override classifier predictions, so KC ACh consensus is not an equally unsupported alternative to the raw dopamine predictions; and `receptorType` is a sensory receptor annotation, not a postsynaptic transmitter-receptor inventory. Its null values do not establish absent target receptors. The metadata-conflict partition below is historical descriptive bookkeeping, not a causal explanation for unknown effects. No policy row was changed, and UNKNOWN coverage is still 78.09% of contacts.

## Result and reason for UNKNOWN

The policy has eight narrow pre-role/post-role rules and a deliberate `UNKNOWN` default. It classifies a role pair only when a class-level experiment or a named compartmental teaching hypothesis supports that effect. Merely knowing the presynaptic transmitter is insufficient. The [official MaleCNS release](https://male-cns.janelia.org/download/) supplies aggregate neuronal transmitter predictions and anatomical pairs; it does not provide a receptor-resolved response or fast-current sign for each connection. All 140 selected cells have a source transmitter row and a non-null consensus label, while **all 140 have null `receptorType`**. The current policy has no default ACh-positive, GABA-negative, glutamate-positive, or dopamine-fast-current rule.

| Policy state | Pairs | % of 12,153 | Contacts | % of 57,771 |
| --- | ---: | ---: | ---: | ---: |
| `EXCITATORY` | 214 | 1.76% | 4,146 | 7.18% |
| `INHIBITORY` | 107 | 0.88% | 5,488 | 9.50% |
| `MODULATORY` | 872 | 7.18% | 3,022 | 5.23% |
| **`UNKNOWN`** | **10,960** | **90.18%** | **45,115** | **78.09%** |

The next table is a **mutually exclusive metadata triage of the UNKNOWN pool**, using the first applicable reason in the listed order. A presynaptic conflict is an additional caution, not proof that it alone caused an edge to be UNKNOWN: those edges also lack target-specific functional evidence. Thus the table must not be read as “fix the KC transmitter label and 10,647 effects become known.” Percentages use the **whole 12,153-pair / 57,771-contact subset** as denominators; the three nonzero rows sum to the UNKNOWN row above.

| Triage category | Pairs | % total pairs | Contacts | % total contacts | Major presynaptic → postsynaptic populations by contacts |
| --- | ---: | ---: | ---: | ---: | --- |
| Presynaptic transmitter missing | 0 | 0% | 0 | 0% | None in selection; 502 traced parent cells lack a transmitter row. |
| Source annotation lost by importer/subset/policy join | 0 | 0% | 0 | 0% | None found. |
| **Predicted versus consensus transmitter conflict** | **10,647** | **87.61%** | **40,609** | **70.29%** | KC→KC 29,043; KC→APL 5,521; KC→MBON27 2,829; KC→PAM 1,517; KC→MBON32 1,129. |
| Dopamine-labeled but non-binary/target action unresolved | 128 | 1.05% | 724 | 1.25% | PAM/PPL→APL 447; PAM→MBON27 153; DAN→DAN 111. These are outside the eight compartment-specific rules. |
| Consensus transmitter known, no predictor conflict, target effect unresolved | 185 | 1.52% | 3,782 | 6.55% | Visual input→KC 1,427; APL→other targets 843; MBON11→APL 493; APL→MBON01 439; MBON/DN→DN 511. |
| Other | 0 | 0% | 0 | 0% | No additional distinct metadata category found. |

**Source-label conflict requires special care.** All 107 selected `KCg-d_R` cells have source `consensus_nt = acetylcholine`, yet individual `predicted_nt` is dopamine in 106 and GABA in one; the source's cell-type prediction is dopamine for all 107. Individual prediction confidence spans 0.544–0.826. None of these 107 has a ground-truth field. This is an **upstream annotation disagreement**, preserved by our importer, not a pipeline conversion. Experimental work supports cholinergic Kenyon-cell output and KC→MBON excitation as a class-level constraint ([Barnstedt et al.](https://pmc.ncbi.nlm.nih.gov/articles/PMC4819445/)); it does not directly assay these 107 MaleCNS bodies. The existing 214 KC→MBON `EXCITATORY` rows are therefore `LITERATURE-CONSTRAINED`, **not `MEASURED`**; their conflict should be reviewed before electrical use. Receptor-specific cholinergic effects can differ: [a primary study of inhibitory muscarinic receptors in KCs](https://elifesciences.org/articles/48264) illustrates why ACh is not a universal positive-sign rule.

The 9,370 KC→KC pairs alone contain 29,043 contacts, **50.27% of the whole selected graph**. This dominates pair coverage, but its functional effect remains unknown even if the KC transmitter disagreement is resolved: postsynaptic location/receptor and effective coupling are not established. `MODULATORY` is a compartment hypothesis, not an electrical sign.

## Metadata-path verification and engineering defects

`body-annotations-...feather` supplies body ID/type/instance/receptor; `body-neurotransmitters-...feather` supplies individual prediction, confidence, cell-type prediction, consensus and ground-truth annotation. [The importer](../src/project_b/connectome/malecns.py) joins by body ID into the normalized traced parent. [The subset builder](../src/project_b/connectome/circuit_v1.py) copies the complete selected node rows and exact induced source edges. [The effect resolver](../src/project_b/connectome/effect_policies.py) joins pre consensus and post receptor by stable source ID and applies role-specific rules; unmatched edges stay UNKNOWN.

The audit compared **140 raw annotation/NT IDs**, 700 raw→parent→subset values across prediction, confidence, consensus, ground-truth and receptor fields, **12,153** exact policy→subset anatomical rows, and **24,306** policy endpoint transmitter/receptor joins. All matched. Source `receptorType` is null on every selected cell; this is source absence, not a null introduced by our code. The policy edge table exposes only pre consensus and post receptor; individual prediction/confidence/ground truth remain available by source-ID join to the subset node table. The new read-only audit exposes that join and the source disagreement without changing the pinned policy product. **No propagation bug was found or fixed; no classification was broadened.** The absence of receptor/effect measurements and the source KC disagreement are biological/annotation limitations, not engineering loss.

## Coverage by population

Cells are grouped by the selected roles; MBON subgroups are also combined in `all MBON` and therefore should not be summed with those subgroup rows. Each cell entry is **directed pairs / source contacts**. `E`=excitatory, `I`=inhibitory, `M`=modulatory, `U`=UNKNOWN. Incoming/outgoing count only edges with both endpoints inside Circuit V1, not cut boundary contacts. Full 14-role counts are in the [machine-readable audit](figures/circuit_v1_sign_audit.json).

| Population (cells) | Direction | E | I | M | U |
| --- | --- | ---: | ---: | ---: | ---: |
| Candidate visual inputs (3) | In | 0 | 0 | 0 | 5 / 5 |
|  | Out | 0 | 0 | 0 | 77 / 1,428 |
| Kenyon cells (107) | In | 0 | 106 / 5,455 | 850 / 1,713 | 9,480 / 30,531 |
|  | Out | 214 / 4,146 | 0 | 0 | 10,647 / 40,609 |
| APL (1) | In | 0 | 0 | 0 | 133 / 6,495 |
|  | Out | 0 | 106 / 5,455 | 0 | 25 / 843 |
| DANs: PPL1+PAM (22) | In | 0 | 0 | 0 | 1,028 / 2,274 |
|  | Out | 0 | 0 | 872 / 3,022 | 128 / 724 |
| Learning MBON11/01 (2) | In | 214 / 4,146 | 1 / 33 | 22 / 1,309 | 6 / 704 |
|  | Out | 0 | 1 / 33 | 0 | 45 / 750 |
| Relay MBON26/27/32 (3) | In | 0 | 0 | 0 | 301 / 4,595 |
|  | Out | 0 | 0 | 0 | 34 / 499 |
| All MBONs (5) | In | 214 / 4,146 | 1 / 33 | 22 / 1,309 | 307 / 5,299 |
|  | Out | 0 | 1 / 33 | 0 | 79 / 1,249 |
| Descending DNa03/02 (2) | In | 0 | 0 | 0 | 7 / 511 |
|  | Out | 0 | 0 | 0 | 4 / 262 |

`UNKNOWN` within a group includes recurrent same-group edges (notably KC→KC); the in and out totals are not unique contacts. The output readout has **zero classified signed incoming pairs**.

## Critical route: exact source pairs and blockers

| Stage in proposed route | Pairs | Contacts | Classified effect | UNKNOWN proportion (pairs; contacts) | Electrical consequence |
| --- | ---: | ---: | --- | --- | --- |
| Three inputs → KC | 76 | 1,427 | None | 100%; 100% | **Blocks cue entry**. ACh consensus does not prove postsynaptic fast sign for these exact inputs. MeVP41 30/601, LoVP97 16/423, LoVP42 30/403. LoVP97 is additionally annotated `cb_intrinsic`, making its visual-input role an inference. |
| KC → MBON11/MBON01 plastic candidates | 214 | 4,146 | 214 `EXCITATORY`, class-level | 0%; 0% | Only currently signed feedforward learning stage. Source KC predicted/consensus conflict and synapse-compartment location need review. |
| KC → relay MBON26/27/32 | 269 | 4,096 | None | 100%; 100% | A large possible fixed or competing shortcut has unknown effect; KC→MBON27 alone is 106/2,829. |
| Learning MBON11/01 → relay MBONs | 5 | 96 | None | 100%; 100% | **Blocks learned signal leaving learning outputs**. MBON01 glutamate→MBON26 is 1/28 and →MBON32 is 1/58; glutamate is receptor dependent. |
| Relay MBON26/27/32 → DNa03/02 | 5 | 252 | None | 100%; 100% | **Blocks descending drive**. Focal connections: MBON26→DNa03 1/47, MBON27→DNa03 1/108, MBON32→DNa02 1/55. |
| DNa03 → DNa02 | 1 | 255 | None | 100%; 100% | **Blocks proposed final relay**. The two-DN block is 2/259 including the small reverse edge. |

The full source anatomy connects the named stages, which is `MEASURED` as reconstructed connectivity. Their fast signs and magnitudes are mostly `UNKNOWN`. Even resolving a large fraction of KC recurrence would not repair the absent signed sensory entry or MBON→DN route. Retained incoming contacts at DNa03 and DNa02 are only 1.11% and 1.31% of traced-parent incoming contacts respectively ([subset report](CIRCUIT_V1_SUBSET.md)); missing outside drive is another independent boundary blocker.

## DAN and plasticity route

| Stage | Pairs | Contacts | Classified effect | UNKNOWN proportion (pairs; contacts) | Interpretation |
| --- | ---: | ---: | --- | --- | --- |
| PPL101 → KCs | 95 | 260 | 95 `MODULATORY` | 0%; 0% | `LITERATURE-CONSTRAINED` γ1 teaching association, not receptor occupancy at each exact contact. |
| PPL101 → MBON11 | 1 | 781 | 1 `MODULATORY` | 0%; 0% | Compartment association; immediate electrical effect unknown. |
| PAM01 cohort → KCs | 755 | 1,453 | 755 `MODULATORY` | 0%; 0% | `INFERRED` for selected heterogeneous γ5 cohort. |
| PAM01 cohort → MBON01 | 21 | 528 | 21 `MODULATORY` | 0%; 0% | Selected cell subtype, release field and receptor action unresolved. |
| All DANs → learning MBONs | 24 | 1,311 | 22 `MODULATORY` / 1,309 contacts | 8.33%; 0.15% | Two 1-contact PAM→MBON11 off-compartment pairs remain UNKNOWN. |

The mapped DAN→KC/MBON anatomy supports a **candidate modulatory route**, not a calibrated reinforcement mechanism. The 214 plastic candidates were selected by cell role, without per-contact compartment validation. DAN subtype, dopamine release site, receptor sign/kinetics, eligibility interaction, and the artificial reward→DAN interface are `UNKNOWN` or `ENGINEERING ASSUMPTION`. The 128 other dopamine-labeled edges / 724 contacts are intentionally not given a generic effect. All DAN **incoming** selected edges are UNKNOWN (1,028/2,274), so endogenous teaching dynamics are also unconstrained. No claim is made that signed task error is dopamine concentration.

## Diagnostic graph policies — no simulation

Reachability below treats a retained directed edge as a **graph arc**, not a current. In B/C, a `MODULATORY` arc only demonstrates a potential DAN target; it must not be interpreted as fast excitation. “Isolated” means degree zero among **functionally active classified edges**, not anatomically disconnected.

| Diagnostic policy | Anatomical pairs / contacts retained | Classified active pairs / contacts | Sensory→KC→learning MBON→DNa02 | DAN→KC / learning MBON arc | Functional isolates |
| --- | ---: | ---: | --- | --- | --- |
| A: signed only (`EXCITATORY`+`INHIBITORY`) | 321 / 9,634 | 321 / 9,634 | **No**: sensory and DN disconnected | No / no | 30: 3 inputs, 22 DANs, 3 relay MBONs, 2 DNs. |
| B: signed + `MODULATORY` | 1,193 / 12,656 | 1,193 / 12,656 | **No** | Yes / yes as modulatory arcs, not electrical transmission | 8: 3 inputs, 3 relay MBONs, 2 DNs. |
| C: all anatomy retained, `UNKNOWN` inactive | 12,153 / 57,771 | 1,193 / 12,656 | **No** | Same as B | Same 8. |

Thus A/B/C are diagnostic masks only; none is a defensible circuit model. Policy C preserves the source graph for provenance while leaving 45,115 contacts functionally silent by construction. This should not be misreported as a fly lesion or intact baseline. The old all-positive overlay remains failed and is not revived.

## High-value unresolved classes and next gate

1. **Sensory→KC (76/1,427)** and the visual identity/tuning of source IDs 13285, 13707, 13874: these block cue entry despite moderate contact count. Seek target-specific visual/KC physiology or declare any sign and cue mapping as explicit testable inference; reconcile LoVP97's `cb_intrinsic` label.
2. **Learning MBON01→relay (notably 1/28, 1/58), relay MBONs→DN (5/252), and DNa03→DNa02 (1/255):** few pairs but every proposed motor path depends on them. Review target receptor/sign evidence and whether this output choice is defensible before any numerical model.
3. **KC output identity and recurrent KC→KC (9,370/29,043), KC→APL (106/5,521), KC→MBON27 (106/2,829), and KC→MBON32 (105/1,129):** large contact mass and possible recurrence/shortcut effects. Reconcile source individual/cell-type dopamine predictions versus ACh consensus using primary KC transmitter evidence and source annotation methods. Do not turn recurrence positive by default.
4. **DAN compartment and KC→MBON plastic locations:** the selected PPL/PAM contacts are only candidate modulation; use per-synapse ROI/partner evidence and subtype/receptor literature to establish whether the named teaching cells actually access the selected plastic contacts. The official release lists separate partner/ROI and t-bar prediction files; these were **not ingested** for this audit ([download page](https://male-cns.janelia.org/download/)).
5. **APL and missing boundary drive:** APL→KC is class-inhibitory but spatially graded, while KC→APL 5,521 contacts and APL→other MBONs remain UNKNOWN. DNs lose nearly all traced-parent input at the subset boundary. Resolve or explicitly bracket these effects before claiming closed-loop neural behavior.

**Recommendation / next gate:** perform a *critical-route evidence gate* before an electrical implementation. Verify KC transmitter consensus provenance; obtain target-specific evidence or explicit, separately labelled bounded hypotheses for sensory→KC, MBON→relay, relay→DN, and DNa03→DNa02; localize the proposed KC→MBON/DAN plastic compartments; and specify how missing boundary drive and graded APL are represented. Recompute the three masks and require a connected sensory-to-action route with each necessary effect provenance recorded. If evidence is insufficient, retain UNKNOWN and report that Circuit V1 cannot yet support a biologically defensible electrical baseline. Numeric weights, delays, intrinsic dynamics and task interfaces remain separate later gates.
