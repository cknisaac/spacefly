# B5.1 — task-independent feedforward drive adequacy

**2026-09-30. Diagnostic only. Electrical Model V1 remains frozen.** This follows the failed [B5 sensory-route causality gate](ELECTRICAL_V1_SENSORY_ROUTE_CAUSALITY.md) and stops at the two failed feedforward stages. It does not investigate or modify the MBON32→DN route, add a key readout, use osu outcomes, invoke dopamine, learn, or select a production parameter.

## Protocol, evidence and limits

The [locked B5.1 protocol](../configs/electrical_v1_feedforward_drive_adequacy.json) pins V1 config SHA-256 `fe7e0c488e5ce1beb3642cd003a19198e4f1d0758c6e6dd7ecb6c714bb935d0c` and B5 protocol SHA-256 `04e0d9c098fcd4acfd28b4d7cd441609032dd4a44663c2e97a3020b8ee53289b`. We used the **existing** B5 A visual low/nominal/high and E direct-KC branches: 3 seeds **31001–31003**, 10 independent pulse checkpoints per seed, 200-ms stimulus, 500-ms post window. Each group's 30 trials had the same feedforward event/voltage summary; autonomous DN boundary streams differ but are not inputs to these silent cells. The B5 event stream supplies exact source row, contact-scaled current step and timestamp. No saved B5 stimulus or spike event was changed.

For every target, the [runner](../scripts/run_electrical_v1_feedforward_drive_adequacy.py) reconstructed the **frozen** passive LIF trajectory from its saved arrivals, with exact exponential 5-ms fast-current decay, 500-µs threshold grid and tick ordering. It integrated the fast current analytically (`pA·ms = fC`) and obtained leak charge by `C ΔV − Q_fast − Q_APL`; this is exact for these nonspiking postsynaptic trials. The initial KC/MBON voltage and fast current were their frozen rest/zero values; the [independent audit](figures/electrical_v1_feedforward_drive_adequacy/audit.json) verified this reconstruction by replaying one nominal A trial and one E trial through the unchanged V1/B5 runtime, matching all saved deliveries/spikes and all 107 KC or MBON voltage/current peaks. The audit also independently recomputed arrival charge over **120 stage trials, 28,980 target/timing rows and 538,920 event-charge terms**. It does not prove exact biological intrinsic values.

**Evidence labels:** source bodies, selected pair/contact counts and delivered model events are `MEASURED` within the pinned source/run; the modeled current/voltage results and multipliers are consequences of `ENGINEERING ASSUMPTION` V1 values. KC→MBON cholinergic excitation and local APL inhibition are `LITERATURE-CONSTRAINED` at class level. The sensory→KC positive sign is `INFERRED`. Exact target efficacies, KC/MBON intrinsic physiology, receptor kinetics and natural visual/ KC spike timing remain `UNKNOWN` ([V1 policy](ELECTRICAL_MODEL_V1.md), [route closure](CIRCUIT_V1_ROUTE_CLOSURE.md)). The selected visual bodies are candidates, not established natural stimuli for all 107 KCs.

## Visual→KC: distribution across all 107 cells

The selected three visual bodies make **76 source pairs / 1,427 contacts** with **59/107 KCs** (`MEASURED` anatomy); **48 KCs have no direct selected visual pair**. Among the 59, **45** have one visual parent, **11** have two and **3** have three. Source-contact counts range **1–76**, median **22** among contacted KCs. A delivered event is one presynaptic spike on one source pair, with step `0.03 pA × contacts` (`ENGINEERING ASSUMPTION`); the contact count is not 1,427 independent event times.

| Existing B5 visual level, per trial | Low | Nominal | High |
| --- | ---: | ---: | ---: |
| Visual→KC delivered FAST events | 0 | 1,140 | 1,672 |
| KCs receiving an event / meaningful drive¹ | 0 / 0 | 59 / 31 | 59 / 32 |
| Event count per contacted KC | 0 | 15, 30 or 45 | 22, 44 or 66 |
| Peak fast current among contacted KCs, median / maximum | 0 | 0.713 / 2.463 pA | 0.791 / 2.732 pA |
| Integrated fast charge among contacted KCs, median / maximum | 0 | 49.5 / 171 fC | 72.6 / 250.8 fC |
| Peak depolarization among contacted KCs, median / maximum | 0 | 0.577 / 1.994 mV | 0.782 / 2.702 mV |
| Closest threshold gap among contacted KCs, median / minimum | 14 / 14 mV | **13.423 / 12.006 mV** | **13.218 / 11.298 mV** |
| Critical input multiplier among contacted KCs, median / minimum | unavailable | **24.25 / 7.02×** | **17.90 / 5.18×** |

¹ Predeclared *meaningful drive* means at least one delivered FAST event and peak fast current ≥10% of the frozen KC `I_ref=7 pA`. It is a reporting threshold, not a biological criterion or a stage pass.

Every KC starts at **−62 mV**, with frozen onset **−48 mV**, a **14-mV** rest-to-threshold gap. Across **all 107 KCs** under nominal input, peak voltage has median **−61.948 mV** and range **−62 to −60.006 mV**; the closest threshold distance has median **13.948 mV** and range **12.006–14 mV**. Contacted-cell peak-current interquartile range is **0.356–1.053 pA**, charge **24.75–73.125 fC**, and threshold gap **13.147–13.711 mV**. In the high arm, all-cell peak-voltage median is **−61.929 mV**, and the best KC remains **11.298 mV** below threshold. Low input makes no visual spike and therefore delivers no KC event, so no postsynaptic multiplier can rescue that arm without changing the presynaptic condition.

The nominal delivered arrivals occupy **182 ms** from first to last (15 distinct ticks for a single visual parent; 15/30/45 events depending on parent count). At most **6.67%** of a contacted cell's event impulse falls in its best 5-ms window. Every driven KC's closest threshold approach occurs **198.5 ms after pulse onset**; the other 48 remain at rest. The strongest KC (source **520204**, 76 contacts) has peak fast current **2.463 pA** but only **1.994 mV** peak depolarization. At its closest approach the still-decaying fast current is **+1.001 pA**, leak is **−0.997 pA**, and charge up to that time is **+165.993 fC fast** versus **−156.022 fC leak**. Its 500-ms total fast charge is **+171 fC** and leak approximately **−171 fC** as it relaxes to rest. **APL is exactly zero**: no KC fires to recruit the local graded APL state. No KC is refractory in the observation window. Thus leak and short fast-current decay absorb most delivered charge before it can accumulate into a spike; APL and refractory state do not explain the failure.

## Direct KC volley→MBON32

The existing E arm directly stimulates all **107** KCs at the frozen B5 3× reference current. **105 KCs** have a selected KC→MBON32 source pair, together **1,129 anatomical contacts** (`MEASURED`); there is no missing anatomical input at this particular postsynaptic node. Each trial delivers **3,176 FAST KC→MBON32 events**, corresponding to **341.01 pA** summed current-step impulse. The frozen per-contact step is **+0.01 pA** (`ENGINEERING ASSUMPTION`, with class excitation `LITERATURE-CONSTRAINED`). The full 500-ms fast charge is **1,705.05 fC**. Peak fast current is **15.264 pA**; this briefly exceeds MBON32's passive reference `I_ref=15 pA` but does not persist long enough to elicit a spike.

MBON32 starts at **−58 mV**, with onset **−43 mV**. Its peak is **−49.417 mV**, **6.417 mV below threshold**, at **100.0 ms** after onset. The **8.583-mV** peak depolarization is 57.2% of its 15-mV rest-to-onset gap. By that point the integrated fast charge is **+802.464 fC** and leak charge is **−630.811 fC**; instantaneous fast/leak currents are **+8.247/−8.583 pA**. By 500 ms, fast and leak charges nearly cancel as it returns to rest. Its 3,176 arrivals occupy **195.5 ms** across **255 distinct 500-µs ticks**; only **3.31%** of impulse falls in the busiest 5-ms window. Local APL rises elsewhere in E (saved local-state maximum **1.314** model units) because KCs spike, but **MBON32 has no direct APL current under V1**. Its APL charge and refractory occupancy are zero. Its failure cannot be assigned to APL or refractory reset.

## Frozen local transfer functions — diagnostic probes only

Before outcome inspection, the protocol fixed current-step multipliers **0, 0.5, 1, 2, 4, …, 512** and three timing regimes: original arrivals; moving each event only to its **20-ms bin midpoint**; and collapsing the entire existing volley to **onset+100 ms** as an extreme synchrony bound. Counts, source rows and summed impulses are preserved; no network feedback is added after a local postsynaptic first spike. The critical multiplier is computed from the exact pre-first-spike passive trajectory; the first panel value above it is an explicit bracket, not a production choice. Linear scaling applies only until the first spike. A timing remap is a counterfactual **ENGINEERING ASSUMPTION**, not an observed fly firing pattern.

| Stage / timing | Minimum critical multiplier | Median critical multiplier among contacted targets | First tested multiplier for strongest target | Interpretation |
| --- | ---: | ---: | ---: | --- |
| Nominal visual→KC, observed | 7.02× | **24.25×** | 8× (4× still silent) | 55/59 contacted KCs need ≥10×; 48 never receive input |
| Nominal visual→KC, 20-ms bins | 5.24× | **18.11×** | 8× | Median improvement 1.34×; **0/59** meet predeclared ≥2× timing criterion |
| Nominal visual→KC, whole volley at 100 ms | 0.82× | **2.83×** | 1× | Unrealistic upper bound; still cannot reach 48 no-contact KCs |
| High visual→KC, observed | 5.18× | **17.90×** | 8× | 48/59 contacted KCs need ≥10× |
| Direct KC→MBON32, observed | **1.748×** | same single target | **2×** (1× silent) | Near threshold by locked ≤2× rule |
| Direct KC→MBON32, 20-ms bins | **1.556×** | same | 2× | Improvement only 1.12×; below material-timing rule |
| Direct KC→MBON32, whole volley at 100 ms | **0.279×** | same | 0.5× | Total charge is sufficient if implausibly synchronized |

The nominal visual contacted-cell critical-multiplier range is **7.02–533.56×**. The first 8× visual response in the local probe would occur at **40.5 ms** for the strongest KC; the first 2× MBON32 response at **46.5 ms**. These are counterfactual single-cell first-spike times; they were **not** realized in B5. The 20-ms remap changes neither the strongest KC's nor MBON32's first tested panel bracket and produces no ≥2× improvement. The entire-volley remap proves that timing interacts with current amplitude and the 5-ms decay, but compressing ~200 ms of activity into one instant is not a defensible V1.1 timing parameter.

## Mechanistic classification and V1.1 decision

| Failed stage | Classification under predeclared A–E choices | Reason and identifiable limit |
| --- | --- | --- |
| Visual→KC, whole 107-KC population | **E — unresolved / combination**, with a definite **D — insufficient selected anatomical route** for 48 KCs | The 48 have no selected visual contact, so no multiplier can activate them through this route. Among 59 contacted KCs, 55/59 require ≥10× frozen effect at nominal input; this is a gross *effective-drive* shortfall. It may be an **A** effect-scale mismatch, a **B** intrinsic-excitability mismatch, missing/UNKNOWN co-input, or a combination. The 20-ms timing probe gives no ≥2× rescue, so **C alone** is not supported. |
| Direct KC→MBON32 | **E — unresolved / combination** | All 105 source pairs are active and MBON32 comes within 6.417 mV (critical **1.748×**), so **D** is not supported and this is near-threshold by the locked rule. The 20-ms probe gives only a 1.12× improvement; extreme synchrony can cross at 1×, so **C is relevant but uncalibrated**. V1's +0.01 pA/contact, 20-pF/1-nS cell and 5-ms current decay are all engineered. An **A** versus **B** assignment is not identifiable from this experiment. |

There is a **task-independent scientific rationale to reconsider V1**: well-verified source events produce almost no KC depolarization, and the direct KC volley produces substantial but insufficient MBON32 depolarization. This is an electrical transfer failure, not a task-score failure. The rationale does **not** establish which numerical quantity is biologically wrong. The contact table measures anatomy, not conductance or membrane threshold; class-level KC→MBON excitation does not calibrate this exact 0.01-pA step; and the repo's literature does not calibrate selected visual→KC efficacy, 107 KC thresholds, MBON32 rheobase or natural synchrony.

**Smallest defensible V1.1 production change now: none identifiable.** A later version should address the stages **separately** and be justified by independent visual-input population evidence and/or physiological efficacy/excitability/temporal-response constraints before choosing any value. It must keep the 48 no-contact KCs visible as an anatomical boundary, retain UNKNOWN edges as UNKNOWN, document any boundary expansion, freeze a new versioned protocol and rerun the causal gate. The diagnostic 8×/2× panel values and 100-ms collapsed volley are **not** recommended settings. V1 remains unchanged; no electrical V1.1 file was created.

Complete per-KC/per-trial numbers and timing panels are in [result.json](figures/electrical_v1_feedforward_drive_adequacy/result.json); grouped distributions are in [analysis.json](figures/electrical_v1_feedforward_drive_adequacy/analysis.json). The [audit receipt](figures/electrical_v1_feedforward_drive_adequacy/audit.json) documents source checks, analytical charge checks and the two exact dynamic replays.
