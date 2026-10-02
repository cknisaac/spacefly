# B5 — task-independent sensory-to-DN causal route

**2026-09-30. Decision: FAIL for complete visual→KC→MBON32→DN transmission under frozen Electrical Model V1.** The first failure is **visual→KC sensory entry**. A separately predeclared direct KC probe reveals a second functional failure at **KC→MBON32 spiking** under this model. A direct MBON32 probe does suppress both DNs, so the tested descending effect is functional *when MBON32 is driven artificially*. None of these statements establishes the exact biological effect of the MaleCNS synapses. No osu, key readout, reward, exploration, plasticity or PPL103 teaching was used.

## Frozen scope and protocol

The [B5 protocol](../configs/electrical_v1_sensory_route_causality.json) was saved before route activity was observed. It pinned Electrical Model V1 at config SHA-256 `fe7e0c488e5ce1beb3642cd003a19198e4f1d0758c6e6dd7ecb6c714bb935d0c`, nominal shared `dn-boundary-v1`, and seeds **31001/31002/31003**. The source graph, numerical connection effects, intrinsic values, delays and DN boundary were unchanged from the [model](ELECTRICAL_MODEL_V1.md) and its passed [neutral gate](ELECTRICAL_V1_NEUTRAL_GATE_RESULT.md).

All perturbations were **ENGINEERING ASSUMPTIONS**, not visual physiology. The three selected input bodies **13285/13707/13874** each received a 200-ms rectangular injected current. Their independently frozen passive reference is `I_ref = g_leak(V_onset−V_rest) = 15 pA`; the fixed visual panel was **low 15 pA**, **nominal 22.5 pA**, **high 30 pA** per cell. The direct diagnostic probes used **3×** the corresponding frozen class reference: **21 pA** to each of all 107 right KCs (E/E_off), or **45 pA** to MBON32 (F/F_off). These strong direct probes diagnose stages and are not candidate sensory interfaces.

Ten pulse onsets were fixed at **11, 13, …, 29 s** on each seed's autonomous boundary clock. For each onset, every arm was independently cloned from the **same unperturbed neural/boundary checkpoint**, so earlier pulses could not change a later trial. The prestimulus window was 500 ms and the poststimulus window 500 ms; current was on for the first 200 ms of the post window. All paired arms had identical current waveform, onset, duration, initial state, numerical tick and boundary trajectory. Endogenous synaptic events were allowed to differ as a *consequence* of the named functional disconnection. Source anatomy was never deleted.

| Arm | Injected population | Only functional change from full route |
| --- | --- | --- |
| A | Three visual cells | None |
| B | Same visual cells | Disable 76 visual→KC active source pairs |
| C | Same visual cells | Disable 105 KC→MBON32 active source pairs |
| D | Same visual cells | Disable both MBON32→DN active source pairs |
| E / E_off | All 107 KCs | E_off disables the 105 KC→MBON32 pairs |
| F / F_off | MBON32 | F_off disables the two MBON32→DN pairs |

The [runner](../scripts/run_electrical_v1_sensory_route_causality.py) saved **480 trials** (3 seeds × 10 onsets × 16 arm/level cases), including every stimulus, prespike/postspike record, delivered event with source row and amplitude, selective DN voltage/current and APL traces, lesion row list, initial/terminal boundary hashes and queue counts. There are **48** exact first-pulse replay comparisons. [Metadata](figures/electrical_v1_sensory_route_causality/meta.json) records the complete protocol/config and code/source hashes; [result index](figures/electrical_v1_sensory_route_causality/result.json) points to all three durable compressed seed files. The [machine-readable analysis](figures/electrical_v1_sensory_route_causality/analysis.json) contains every paired stage comparison and rollup. No seed, visual level or failed branch was omitted.

The primary full-route criterion was predeclared at **nominal**, with low/high reported as sensitivity conditions. Each upstream stage required the downstream response in at least **8/10** paired pulses *per seed*, absence under its matching lesion and at least the frozen **1-ms** chemical delay. A DN effect required an inhibitory spike loss or ≥500-µs first-spike delay in at least **5/10** pulses per seed, no excess summed post-window spikes and no divergence before the first MBON arrival. The direct probes use the same stage logic. These are engineering causal criteria, not biological firing targets.

## Full visual route: response stops before KCs

| Visual level | Visual-cell spikes per 10 trials, each seed | KC spikes / distinct KCs | MBON32 spikes | APL local response | DN A–D paired difference |
| --- | ---: | ---: | ---: | ---: | --- |
| Low, 15 pA | 0 | 0 / 0 | 0 | 0 | None |
| Nominal, 22.5 pA | **450** | **0 / 0** | 0 | 0 | None |
| High, 30 pA | **660** | **0 / 0** | 0 | 0 | None |

Nominal produced **15 spikes per visual cell per pulse**; high produced **22**, in each of all three seeds. Thus the artificial visual-cell stimulus worked reproducibly. At nominal, visual spikes generated **11,400 delivered visual→KC events per seed across ten trials**; high generated **16,720**. The events arrived after the frozen 1-ms delay, but **no KC reached spike onset**. The APL local state remained zero because there were no KC spikes. MBON32 was silent, and the complete DN spike trains in A, B, C and D were identical under each matched seed/level. Pre/post DN counts alone vary with the autonomous boundary; the matched-lesion equality is the relevant causal result.

The first failed stage is therefore **functional sensory entry from these visual cells into KCs under V1**, not a failure to stimulate the visual cells or a missing anatomical arc. The raw source retains all 76 visual→KC pairs. B removed their *functional* arrivals while leaving the visual spikes unchanged, but there was no KC spike response in A for B to abolish. C and D likewise could not abolish an MBON or DN effect that never arose in the full route. High visual current did not rescue this stage; it was part of the fixed panel, not a post hoc adjustment.

## Direct KC and MBON probes localize additional limits

Direct E made **all 107 KCs spike in every pulse**, producing **32,360 KC spikes per seed across ten trials** (about 3,236 per pulse). APL's recorded local-state peak was **1.314 model units**, confirming that the approved graded KC→APL treatment responded. E delivered **31,760 KC→MBON32 fast events per seed**; E_off removed exactly those functional events. **MBON32 produced zero spikes in both E and E_off, in all three seeds.** This fails the predeclared KC→MBON32 spiking-stage criterion even under synchronous, strong direct KC drive. It identifies a *second* V1 functional bottleneck; it does not show that the anatomical KC→MBON32 contacts are absent, nor that biological KCs naturally fire this way. The exact membrane/current margin at MBON32 was not recorded and remains the smallest useful follow-up measurement.

Direct F produced **180 MBON32 spikes per seed across ten trials** (18 per pulse). The F_off lesion preserved those MBON spikes but removed both functional MBON32→DN outputs. No paired DN spike divergence occurred before the first MBON spike's scheduled **1-ms** synaptic arrival. The inhibitory timing/count criterion passed for **both** DNs in all three seeds:

| Seed | DNa03 inhibitory pulses / 10 | DNa03 post-spike difference F−F_off | DNa02 inhibitory pulses / 10 | DNa02 difference F−F_off |
| --- | ---: | ---: | ---: | ---: |
| 31001 | 8 | −2 | 8 | −7 |
| 31002 | 9 | −5 | 9 | −6 |
| 31003 | 8 | −3 | 7 | −5 |

Thus the **frozen, inferred MBON32→DN suppressive hypothesis can change DN output when MBON32 is directly driven**. F_off abolished that paired change. This is model-level causality under the artificial boundary; exact postsynaptic GABA receptors, reversal potentials and natural MBON firing remain `UNKNOWN`. It does not rescue the failed upstream route or authorize a motor readout.

## Audit, interpretation and stop

The [independent audit](figures/electrical_v1_sensory_route_causality/audit.json) passed **480 trials, 30 matched initial checkpoints, 24,480 trace samples, 219,700 recorded pre/post spikes and 544,450 delivered synaptic/graded events**. It checked the unchanged config/protocol hashes, exact lesion source-row sets **76/105/2**, source anatomy, class-normalized stimulus currents, paired stimulus and boundary trajectories, finite states, every event's source row/amplitude and presynaptic spike at a 1-ms lag, and all stagewise comparisons. Its first attempt stopped on a verifier bookkeeping error: APL_INPUT is anatomically KC→APL but is delivered to the KC-indexed local APL state. Correcting only that audit mapping made the saved data pass; no protocol, model, trial or result changed. The audit does not independently integrate the membrane ODE or establish biology.

**B5 full-route gate: FAIL, consistently across all three boundary seeds.** The ordered failure is visual→KC; the direct E test also shows KC→MBON32 fails to elicit an MBON spike under its declared strong diagnostic perturbation. The direct F test shows that the downstream MBON32→DN effect is detectably inhibitory under V1 when MBON32 is forced to spike. These are different causal claims and must remain separate.

**Smallest next task-independent diagnostic, if authorized:** record subthreshold membrane voltage relative to onset and the separated retained synaptic/APL currents in the contacted KCs and MBON32 during these **same frozen stimuli**. That would distinguish a near-threshold timing issue from a large current/integration deficit at each of the two failed stages, without searching for an amplitude or changing a sign. Any later electrical revision needs an independent biological or explicit engineering rationale, a new model version and a new predeclared gate. **Branch B is not ready for a fixed motor/key readout. Stop before task coupling or learning.**
