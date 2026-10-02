# B5.4 — Electrical Model V1.1 visual-boundary validation

**2026-09-30. Result: FAIL for the predeclared sensory-entry gate.** The two traced right `aMe12_R` cells, **12740** and **13190**, added 20 anatomically contacted KCs and produced a measurable, connection-dependent subthreshold voltage response. **No KC spiked** in any V1.1 connected trial, including all 30 nominal trials. This is a failure of recruitment under the frozen Electrical Model V1 effect policy, not evidence that the anatomical connections are absent or that the fly circuit cannot recruit KCs.

## Versioned revision and provenance

The [V1.1 configuration](../configs/electrical_model_v1_1.json) and [manifest](../data/processed/malecns_v1_electrical_v1_1/manifest.json) add exactly source bodies **12740/13190** to the 115-body V1 set. The resulting 117-body induced graph contains **10,071 directed source pairs / 45,613 contacts**, versus V1's **10,009 / 45,010**. The +62 pairs/+603 contacts consist of **48 added `aMe12_R`→selected-KC pairs / 569 contacts** and **14 other new pairs / 34 contacts**. All 10,009 pre-existing source rows retain their endpoints, counts, candidate flags, effects and numerical values. The other 14 new pairs remain `UNKNOWN` and electrically inactive. The candidate plastic mask is unchanged. Direct visual→KC anatomical coverage rises **59/107→79/107**, with the 20 newly contacted KCs fixed before testing; 28 KCs still have no direct selected-visual contact.

**MEASURED:** MaleCNS source IDs, cell annotations, parent graph, pair/contact counts and direct coverage. The pinned parent neuron/connections SHA-256 values are `7d9a410d61d4caa934fa3639f9d204291ff0d18c445b2384054b95286d6350eb` and `da21af867d4e8e4c627c9916e55af4332302b611a296de1d0a8bc7dd6ebcff7a`. **LITERATURE-CONSTRAINED:** `aMe12` is a plausible visual input class. **INFERRED:** these exact added pairs can be represented by a fast positive functional effect for this test; their exact biological effect remains `UNKNOWN`. **ENGINEERING ASSUMPTION:** each new contact inherits V1's **0.03-pA/contact** fast step, **5-ms** decay and **1-ms** delay, and both new source cells inherit the V1 sensory-cell surrogate. These numbers are neither measured `aMe12` physiology nor fitted to B5 failure. The artificial pulse drives all five selected visual cells together; natural cue tuning/correlation is `UNKNOWN`.

The unchanged [V1 configuration](../configs/electrical_model_v1.json) has SHA-256 `fe7e0c488e5ce1beb3642cd003a19198e4f1d0758c6e6dd7ecb6c714bb935d0c`; V1.1 has SHA-256 `43d5b05c575d6baa595deadd5e86a21e02e8f4f632f6f1558781101432065c7a`. The manifest records exact source-row and artifact hashes. No cell constant, pre-existing edge effect, delay, APL rule, threshold, DN boundary contract, UNKNOWN policy or non-visual topology was changed. No learning, reward, readout or task code was enabled.

## Locked matched probe

The [B5.4 protocol](../configs/electrical_v1_1_visual_boundary_validation.json) was fixed before the runs (SHA-256 `1aba6197243b158f02b77b497462470192973a5ab4b8b3a21770260aa44af67b`). Seeds **31001–31003**, ten independent pulse onsets **11, 13, …, 29 s**, 200-ms rectangular pulses and a 500-ms poststimulus observation give **30 matched checkpoints per level**. Low/nominal/high drive is the existing V1 artificial sensory reference at **15/22.5/30 pA per stimulated cell**. Each arm starts from the same neutral checkpoint and DN boundary state for its seed/onset/level:

| Arm | Stimulation | Functional source rows |
| --- | --- | --- |
| V1 reference | Original three visual cells | Original 76 visual→KC pairs active |
| V1.1 connected | Original three plus 12740/13190 | Original 76 plus added 48 `aMe12_R`→KC pairs active |
| V1.1 disconnected | All five cells | Added 48 effects disabled; source cells still present and stimulated |

The 14 newly induced non-KC pairs stay `UNKNOWN`/inactive in both V1.1 arms. There were **270 trials** (3 seeds × 10 checkpoints × 3 levels × 3 arms). Every trial stores all five visual-cell spikes, delivered events with source row, 107 per-KC event/current/charge/voltage/threshold/spike records, APL state, MBON32 voltage/spikes, DN spikes and traces, safety counters, and matched-state hashes in the [compressed seed records](figures/electrical_v1_1_visual_boundary_validation/result.json). The V1 reference also matched all 90 corresponding saved B5 visual spike/event records.

## Results

All entries below are **per trial** and identical across the 30 matched checkpoints at a given level; KC counts are out of 107. Visual→KC events count delivered fast events. `New events` arise only from 12740/13190.

| Level | Arm | Visual spikes | Old / new visual→KC events | KCs receiving input | KCs spiking | MBON32 spikes | APL peak |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Low | V1 / connected / disconnected | 0 / 0 / 0 | 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 |
| Nominal | V1 | 45 | 1,140 / 0 | 59 | **0** | 0 | 0 |
| Nominal | Connected | 75 | 1,140 / **720** | **79** | **0** | 0 | 0 |
| Nominal | Disconnected | 75 | 1,140 / 0 | 59 | **0** | 0 | 0 |
| High | V1 | 66 | 1,672 / 0 | 59 | **0** | 0 | 0 |
| High | Connected | 110 | 1,672 / **1,056** | **79** | **0** | 0 | 0 |
| High | Disconnected | 110 | 1,672 / 0 | 59 | **0** | 0 | 0 |

At nominal, each of the 20 newly contacted KCs receives added events in the connected arm. Their summed delivered visual charge over the first representative pulse is **659.25 fC**, with peak added synaptic current up to **1.556 pA** in an individual KC. Their closest-to-onset voltage gaps have **12.741-mV minimum / 13.685-mV median**, versus **14.000/14.000 mV** in both disconnected and V1; the nominal peak effect is therefore subthreshold by a wide margin. At high, the new cohort's minimum/median gaps are **12.293/13.573 mV** versus **14/14 mV** in controls. Across all 107 KCs, the nominal closest gap is **12.006 mV** in each arm, inherited from the old three-cell route. This supports a causal *subthreshold* effect of the added functional contacts. It does not satisfy the predeclared **spike recruitment** endpoint.

Disabling only the 48 added effects abolishes all 720/1,056 new nominal/high arrivals and returns the newly contacted KCs' electrical response to V1, despite identical five-cell spiking and artificial stimulus. The disconnected arm's full 107-KC records, MBON32 response and DN spikes match the V1 functional circuit at every paired checkpoint. DN spike counts may reflect the unchanged autonomous boundary; there is no V1.1-specific route effect. No APL response appears because no KC spiked. MBON32 remains silent, as expected upstream of the separately documented KC→MBON32 deficit.

## Independent audit and decision

The [independent audit receipt](figures/electrical_v1_1_visual_boundary_validation/audit.json) reports `status=pass` for data integrity and `stage_result=FAIL` for the scientific gate. It checked **270 trials / 90 matched groups / 306,360 visual event terms**, source and artifact hashes, all pre-existing source rows, exact lesion rows, presynaptic spike→arrival arithmetic, per-KC input/charge/spike/threshold records, matching initial/boundary state, V1/disconnected identity and **nine independent first-nominal-pulse reintegrations**. The [full regression suite](../tests) passed **115 tests**. The first runner launch stopped before trials because its canonical JSON encoder did not handle a boundary checkpoint dataclass; serialization alone was fixed and the unchanged locked protocol rerun. No trial or model parameter was changed in response to the observed result.

**B5.4 decision:** the readiness contract required ≥1 of the 20 newly contacted KCs to spike in **every one of the 30 nominal connected trials**, with no added-source-caused spike in matched disconnected trials and no safety failure. The connected count was **0/20 in every trial**. V1.1 is implemented exactly as the boundary-only hypothesis but **fails sensory-entry validation**. The immediate causal blocker is **visual→KC effective drive/excitability under the unchanged numerical policy**, not lack of anatomy or visual-cell firing. The previously exposed **KC→MBON32 spiking deficit also remains**; therefore there is no single claim that fixing sensory entry alone would complete sensory→DN transmission. The direct MBON32→DN response established in B5 was not modified or investigated here.

### One proposed next stage — B5.5, not run

| Element | Specification |
| --- | --- |
| Question and rationale | In the fixed five-source circuit, is the new-contact KC failure primarily limited by total delivered drive or its timing/integration? The new contacts are active but leave a ≥12.741-mV nominal gap. |
| Competing outcomes | A distributed low-amplitude drive deficit; a temporal-dispersion deficit despite adequate integrated charge; or unresolved mixed limitation. None implies a calibrated biological replacement value. |
| Intervention and frozen controls | Reanalyse the saved B5.4 matched current, voltage and event traces for the 20 new-contact and 59 old-contact KCs; if transfer probes are needed, use separately predeclared diagnostic-only inputs in cloned frozen states. Retain V1, connected and disconnected arms, same seeds and pulse times. |
| Primary / secondary endpoints | Primary: explained peak-voltage gap decomposition by synaptic drive, leak and event timing. Secondary: per-KC charge/current distributions, APL absence and required diagnostic transfer scale with uncertainty. |
| Interpretation and prohibitions | Distinguish amplitude from timing without choosing a winning parameter. Do not edit V1.1, enable learning/readout, vary sources after seeing results, or treat diagnostic multipliers as production calibration. |
| Outputs and stop | A versioned B5.5 protocol, task-independent analysis, independent audit and `CURRENT.md` status. Stop before any new electrical model version. |
