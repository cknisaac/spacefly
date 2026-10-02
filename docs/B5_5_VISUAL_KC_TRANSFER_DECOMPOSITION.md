# B5.5 — visual→KC amplitude versus temporal integration

**2026-09-30. Diagnostic result: AMPLITUDE-LIMITED / GROSSLY UNDERPOWERED under the frozen V1.1 surrogate.** This is an *effective-drive* classification, not identification of a biological visual-synapse current. V1 and V1.1 production configurations were unchanged. The complete sensory-entry/B5 route gate remains **FAIL**.

## Question, frozen evidence and method

The [B5.4 result](ELECTRICAL_MODEL_V1_1_VISUAL_BOUNDARY_VALIDATION.md) established exact visual-cell spiking, causal added `aMe12_R`→KC events and subthreshold depolarization, yet **0/107 KC spikes**. B5.5 asked whether existing total visual charge would become sufficient with better event concentration, or whether the frozen effective drive remained too small. It kept separate, anatomical cohorts fixed before looking at transfer outcomes: **20 KCs newly contacted by 12740/13190**, **59 KCs contacted by original IDs 13285/13707/13874**, and **28 other selected KCs** with no direct contact from the five. The 20 and 59 are disjoint; 17 of the old-contact KCs also receive new `aMe12_R` contacts.

First, the [read-only observed reanalysis](figures/b5_5_visual_kc_transfer_decomposition/observed_summary.json) reconstructed all **30** saved V1.1 nominal connected trials from the exact per-source-row B5.4 arrivals. It reproduced each of **3,210** saved KC voltage/current/charge records to floating-point precision. Fresh neutral V1.1 checkpoints for all seeds/onsets matched the saved B5.4 common-state hashes; every KC began at frozen rest, with zero synaptic current, APL state and refractory occupancy. The saved source events and the frozen 500-µs threshold grid, 5-ms current decay and class KC LIF equation are thus sufficient for a local *first-spike* calculation. There was no visual, KC or MBON32 production parameter change.

The [locked B5.5 matrix](../configs/b5_5_visual_kc_transfer_decomposition.json) was written **after** that observed-only reconstruction and **before** any counterfactual spike probe. It pinned the observed-data hashes, 30 nominal B5.4 event trains, all 107 selected KCs, original V1/V1.1 hashes, and four families:

| Family | Exactly changed for this diagnostic | Preserved |
| --- | --- | --- |
| A: observed | Nothing | Exact V1.1 nominal event amplitudes/times |
| B: amplitude | Multiply only postsynaptic visual→KC event steps by the reused B5.1 ladder **1, 2, 4, 8, 16, 32, 64, 128, 256, 512×** | Source rows, event counts/timestamps, KC model |
| C: compression | Move each KC's existing events toward that KC's original first/last midpoint by fixed **2, 4, 8, 16×** factors, rounded half-even to the 500-µs grid | Each event's source row, current step, count and integrated charge |
| D: perfect synchrony | Put all of each KC's existing events at its original first/last midpoint | The same total current impulse and infinite-horizon delivered charge; deliberately unrealistic timing |

For C/D, **5 ms × summed delivered current steps** is exactly conserved for every KC. Finite 500-ms charge differs only by negligible kernel tail because all observed events arrive before 200 ms. The model is integrated only until each cell's **first threshold crossing**; the readout records first-spike time, pre-first-spike peak voltage and threshold gap. Counterfactual first spikes are **local potential responses**, not a full-network claim: once any KC spikes, later APL feedback and recurrent effects could change other cells. The actual B5.4 observed arm had no KC spike, so its APL contribution was exactly zero. MBON32 was neither manipulated nor used to interpret B5.5. There was no game, motor readout, reward, dopamine, plasticity or training.

## Observed five-source drive: all contacted KCs

Values are per KC per nominal pulse; the corresponding distributions across all 30 trials and the exact event timestamps/source contacts for every KC are in the [machine-readable observed records](figures/b5_5_visual_kc_transfer_decomposition/observed_meta.json). The 30 fixed neutral checkpoints give the same feedforward values.

| Observed quantity | New-contact 20, median [min–max] | Old-contact 59, median [min–max] | No-contact 28 |
| --- | ---: | ---: | ---: |
| Anatomical contacts from selected five | 12 [1–48] | 25 [1–76] | 0 |
| Delivered visual events | 15 [15–30] | 15 [15–60] | 0 |
| Arrival span | 182 ms | 182 ms | none |
| Largest 5-ms share of event impulse | 6.67% | 6.67% | none |
| Peak fast current | 0.389 [0.032–1.556] pA | 0.810 [0.032–2.463] pA | 0 |
| Integrated fast charge | 27.00 [2.25–108.00] fC | 56.25 [2.25–171.00] fC | 0 |
| Minimum threshold gap | 13.685 [12.741–13.974] mV | 13.344 [12.006–13.974] mV | 14 mV |

At each cell's closest threshold approach, median integrated leak loss was **94.0%** of delivered fast charge in both contacted cohorts. No KC was refractory and no APL local inhibition was present in the observed trials. The long **182-ms** source volley and 5-ms current decay cause delivered charge to leak away instead of accumulating. This describes the frozen engineering dynamics; anatomical contacts do not measure current, and the observed charge is not a physiological measurement.

## Diagnostic first-spike results

The counts below are **distinct KC source IDs per nominal trial**. Each of the 30 matched seed/onset trials gave the same count. The full **107-cell** count is the sum of the two contacted columns because the other 28 have zero selected visual events and never spike in these local probes.

| Family at original total charge unless noted | New 20 | Old 59 | Full 107 |
| --- | ---: | ---: | ---: |
| A: observed 1× | 0/20 | 0/59 | 0/107 |
| C: 2× timing compression | 0/20 | 0/59 | 0/107 |
| C: 4× timing compression | 0/20 | 0/59 | 0/107 |
| C: 8× timing compression | 0/20 | 0/59 | 0/107 |
| C: 16× timing compression | 0/20 | **2/59** | **2/107** |
| D: perfect synchrony upper bound | 0/20 | **5/59** | **5/107** |

The only finite-compression first spikes occur at **16×** in old-contact KC IDs **60829/520204**. Perfect synchrony adds **49710/72230/74269**. Even under the synchronous upper bound, the nearest new-contact KC remains **3.201 mV** below threshold; the new cohort's median gap is **11.300 mV**. For old-contact KCs, 54/59 remain silent under perfect synchrony (median clamped gap **8.375 mV**). Thus present total charge is insufficient for **all 20 new KCs and 54/59 old-contact KCs even with maximal temporal concentration in this surrogate**. It is sufficient for five old-contact KCs only under the nonbiological synchronous bound. The 28 no-contact KCs have no delivered charge through this five-cell boundary.

The complete reused amplitude ladder, at *unchanged observed timing*, gave:

| Amplitude step | New 20 spiking | Old 59 spiking | Full 107 spiking |
| ---: | ---: | ---: | ---: |
| 1× / 2× / 4× | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| 8× | 0 | 3 | 3 |
| 16× | 2 | 17 | 19 |
| 32× | 6 | 44 | 50 |
| 64× | 13 | 51 | 64 |
| 128× | 17 | 54 | 71 |
| 256× | 17 | 56 | 73 |
| 512× | 18 | 57 | 75 |

**Distribution of the first tested spiking step**, per distinct KC rather than counting the 30 repeated trials:

| Cohort | 8× | 16× | 32× | 64× | 128× | 256× | 512× | >512× |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| New 20 | 0 | 2 | 4 | 7 | 4 | 0 | 1 | 2 |
| Old 59 | 3 | 14 | 27 | 7 | 3 | 2 | 1 | 2 |

The exact passive **continuous critical multiplier** (a sensitivity statistic, not a selected production weight) is **median 44.77×**, range **11.12–533.56×**, for new-contact KCs; **median 21.34×**, range **7.02–533.56×**, for old-contact KCs; and **median 24.25×** over the 79 contacted cells. **71/79** contacted KCs have a continuous critical multiplier at least **10×**. Four cells exceed the ladder's 512× endpoint; they are reported as censored by the tested panel, not discarded. Full per-KC first-spike times, peak voltages, threshold gaps and remapped event trains for all conditions are indexed in the [raw result](figures/b5_5_visual_kc_transfer_decomposition/result.json).

## Mechanism, scientific limit and gate

The predeclared classification required fewer than 8/79 KCs recruited by any finite charge-preserving compression, fewer than 40/79 under perfect synchrony, a median observed critical amplitude multiplier ≥10×, and amplitude-ladder first spikes. Results were **2/79**, **5/79**, **24.25×**, and yes. Therefore **effective amplitude/total drive is the dominant limitation of V1.1 visual→KC recruitment**, with a small timing-dependent exception in the old-contact cohort. This is also **grossly underpowered in the frozen surrogate**. Temporal dispersion contributes to leak loss, but timing concentration alone cannot recruit most contacted KCs at existing charge. The experiment does **not** distinguish an underestimated per-contact effect from wrong KC intrinsic excitability, missing co-input, receptor dynamics or an inappropriate LIF/sensory surrogate. Those biological/model causes remain `UNKNOWN`.

**Production-revision decision: NO.** Neither 8×, 16×, 32× nor the continuous critical distribution is an independently calibrated current. The [B5.3 physiology audit](B5_3_EXTERNAL_FEEDFORWARD_TRANSFER_CONSTRAINT_AUDIT.md) found no transferable exact `aMe12_R`→selected `KCγ-d_R` efficacy or intrinsic parameter. B5.5 only shows what would make this engineered local model spike. It cannot justify V1.2, an effect increase, a threshold reduction or a new event-time policy. V1/V1.1 and the `UNKNOWN` policy stay frozen.

The [independent audit](figures/b5_5_visual_kc_transfer_decomposition/audit.json) **PASSed**: all **30** matched checkpoints, **3,210** KC records, **334,800** event terms, source/protocol/observed-data hashes, per-event count/charge conservation, exact timing remaps, amplitude and first-step summaries, and **2,568** separately computed scalar KC-family responses sampled across first/last pulses in two seeds. The complete regression suite passed **115 tests**. The audit's scientific label is about local transfer only; it is not a B5 sensory-entry pass.

### One proposed next Branch B stage — B5.6, not run

| Required element | Specification |
| --- | --- |
| Stage / name | **B5.6 — independent sensory-transfer identifiability gate.** |
| Question / why next | Can an *independent* class-relevant recording or constrained model jointly bound adult visual→`KCγ-d` effective input and KC excitability tightly enough to choose one falsifiable production hypothesis? B5.5 rules out a simple timing-only explanation but cannot locate the wrong number. |
| Hypotheses / outcomes | A transferable bounded constraint exists; it excludes a numeric revision; or the transfer remains unidentifiable under available evidence. |
| Intervention | Targeted source/data audit only, restricted to direct visual-KC response and selected KC intrinsic/excitability evidence **not already resolved in B5.3**; record preparation, cell subclass, stimulation protocol, units, confidence and transfer gap to MaleCNS IDs. |
| Frozen controls | V1/V1.1 hashes, B5.3 reviewed-source ledger, B5.4/B5.5 raw data and UNKNOWN classifications; no simulator run or parameter selection from spike thresholds. |
| Primary / secondary endpoints | Primary: existence or absence of a source-supported numerical *joint* transfer envelope. Secondary: which specific measurement is missing (synaptic effect, intrinsic excitability, or natural source timing). |
| Predeclared interpretation | Only independently bounded class-relevant measurements can support a future named V1.2 hypothesis; otherwise declare sensory entry unidentifiable and require a separately authorized engineering modelling policy. A nontransferable preparation or contact count alone is insufficient. |
| Do not | No KC→MBON32 diagnosis, new numerical policy, visual-source shopping, task/readout, reward, training or performance fitting. |
| Output / stop | Evidence ledger, provenance audit, `CURRENT.md` decision. Stop before any electrical revision or B5 route rerun. |
