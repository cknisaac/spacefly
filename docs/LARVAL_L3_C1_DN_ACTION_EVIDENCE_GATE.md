# L3 MBON-c1 target action evidence gate

**Result: INCONCLUSIVE for biological action readout; the frozen `DN spike → KEY_DOWN` mapping is unsupported.** This read-only audit found an identity/annotation conflict and no exact-cell functional evidence assigning either target a motor action or direction. Do not treat the current simulator action boundary as a biological motor readout.

## Frozen inputs checked

| Input | SHA-256 |
|---|---|
| `configs/larval_l3_c1_subgraph_manifest_v1.json` | `b54a8a7ec9e3b18f21f8df91584c33f875c3302c8e534b6020dec7290f004895` |
| `configs/larval_l3_c1_electrical_v1.json` | `5e32171707409a5dffc66f0c93d48bec307d442a01ace8b8554fa82e23c91f6e` |

## Exact-ID resolution and evidence

The L3 S1 audit reports two MBON-c1 postsynaptic targets under the combined label `CN-28; PL-17`, assigned by S1 to the broad `DN-VNC` class: **10,411,574** (20 contacts from MBON-c1 ID 16,223,537) and **17,379,420** (9 contacts from MBON-c1 ID 8,980,589). These are first-instar anatomical observations, not functional experiments. The S1-derived candidate audit contains the exact source IDs, class label and pair counts; the source archive SHA-256 is `8c1f43809ed5d527ba61b154e377cc21da26383a75eda8aab85ce05607a72a4c`.

Virtual Fly Brain resolves **L1EM:17379420** (the same numeric ID as 17,379,420) to **CN-28**, classified as a larval mushroom-body/lateral-horn convergence neuron. Its ontology description says it receives input from an MB output neuron and a lateral-horn neuron; it does not identify a motor command or action direction. [Virtual Fly Brain: larval MB-LH convergence neuron](https://jupyter.virtualflybrain.org/blog/2022/01/01/larval-mushroom-body-lateral-horn-convergence-neuron-fbbt_00051207/)

The primary study defining this convergence-neuron system used larval EM anatomy and functional experiments on selected neurons. It describes CNs as sites where learned MB and innate LH pathways converge, and reports behavioral roles for two selected neurons, not for every CN or these exact IDs. Therefore its class-level results cannot assign CN-28 a particular motor action. [Eschbach et al., 2021, eLife 10:e62567](https://elifesciences.org/articles/62567)

The Winding et al. first-instar whole-brain connectome publication establishes the dataset context and its anatomical scope. The available sources reviewed here did not resolve **L1EM:10411574** to a functional cell identity beyond the source matrix's `CN-28; PL-17` label, nor find an exact-ID recording or perturbation for either target. [Winding et al., 2023, Science](https://doi.org/10.1126/science.add9330)

## Evidence labels

| Claim | Label | What the evidence supports |
|---|---|---|
| MBON-c1 contacts IDs 10,411,574 and 17,379,420 | **MEASURED anatomy** | 20 and 9 first-instar EM contacts in Winding S1; no sign, efficacy, or behavioral meaning follows from contact counts. |
| ID 17,379,420 is CN-28 | **DATABASE-RESOLVED identity** | VFB maps exact L1EM ID 17379420 to CN-28 / larval MB-LH convergence neuron. |
| CNs integrate learned and innate-valence pathways | **MEASURED at class/circuit level** | Primary study establishes convergence and functional roles for selected neurons. This does not show CN-28's action or sign. |
| Either exact ID triggers a motor program, turn, approach, avoidance, or escape | **NOT FOUND** | No exact-ID manipulation, recording, motor-direction result, or valence assignment located in the primary sources reviewed. |
| A spike in either target means `KEY_DOWN` | **ENGINEERING OVERLAY ONLY** | The simulator config defines this as an action threshold; no biological source validates the mapping. |

## Decision and limits

This gate is **INCONCLUSIVE**, rather than PASS: exact-ID behavioral evidence for a task-relevant action and direction is absent. The CN-28 convergence identity for 17,379,420 also cautions against reading the S1 `DN-VNC` superclass label as a demonstrated descending motor command. It does not prove this neuron cannot influence behavior downstream. The exact identity and function of 10,411,574 remain unresolved beyond the S1 class/type labels.

Developmental alignment is also imperfect: the frozen wiring comes from a first-instar larva. The functional convergence-neuron study concerns larval circuitry, but does not test these exact S1 cells as action readouts. There is no evidence here for adult equivalence, third-instar action tuning, synaptic sign, or a spike-to-movement threshold.

Accordingly, the L3 simulator may retain the existing binary event as a **model-internal engineering metric**, but it must not be described as a biologically grounded `KEY_DOWN`, approach, avoidance, escape, or motor output. A biological action gate would require exact-ID functional mapping (or a documented homolog/lineage bridge plus direct action evidence) before task learning is interpreted behaviorally.
