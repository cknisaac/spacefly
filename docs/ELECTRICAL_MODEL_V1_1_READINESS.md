# Electrical Model V1.1 readiness contract — boundary-only hypothesis

**Design-ready on 2026-09-30; not implemented and not gate-passed.** This contract follows the [B5.2 MaleCNS source audit](B5_2_VISUAL_INPUT_BOUNDARY_AUDIT.md) and [B5.3 physiological transfer audit](B5_3_EXTERNAL_FEEDFORWARD_TRANSFER_CONSTRAINT_AUDIT.md). It defines the smallest source-supported V1.1 change that can be tested without choosing a numerical setting from B5's failure. “Ready” means the change, provenance, controls and failure interpretation are specified. It does **not** mean V1.1 will propagate, pass B5, represent measured fly physiology, or be fit for one-lane play.

## Exact allowed revision

1. Preserve all **115** V1 source IDs, source-row topology and the frozen [V1 config](../configs/electrical_model_v1.json) as the comparison baseline (SHA-256 `fe7e0c488e5ce1beb3642cd003a19198e4f1d0758c6e6dd7ecb6c714bb935d0c`). Add only traced MaleCNS v1.0 right `aMe12` bodies **12740** and **13190** to make a **117-body** selected source-ID set. Record a new version/manifest and all new induced source pairs/contacts from the pinned parent; do not claim that only their 48 KC pairs exist in the induced graph.
2. Retain every new induced pair anatomically. Activate only their **48 direct `aMe12_R`→selected `KCγ-d_R` pairs / 569 contacts** under one explicitly named **hypothetical fast positive effect**. Preserve `UNKNOWN` as the biological exact-pair state and keep all other new induced effects inactive unless they were already covered by a V1 named policy. `MEASURED`: source pair/contact/body annotations. `LITERATURE-CONSTRAINED`: `aMe12` visual-input class. `INFERRED`: exact MaleCNS positive functional effect. `ENGINEERING ASSUMPTION`: using the unchanged V1 sensory→KC **+0.03-pA/contact** step, 5-ms decay and 1-ms delay for this new class. No contact count is interpreted as conductance.
3. Give the two added source cells the **unchanged V1 selected-sensory surrogate** (C10 pF, g1 nS, rest/onset/reset −60/−45/−61 mV and 1.5-ms refractory). This is a declared *copied engineering surrogate*, not `aMe12` electrophysiology. Under V1 neutral input, add no external current. In the later matched sensory probe, expose the new cells to the same predeclared current waveform as the old three, explicitly labelled artificial boundary input. This assumes shared cue drive across five cells; natural selectivity/correlation is `UNKNOWN`.
4. Freeze everything else: the 107 KCs, APL, PPL103, MBON32, both DNs, candidate plastic mask, effect signs and values, neuron constants, delay/grid, DN proxy and RNG streams, source checksum, UNKNOWN-inactive policy, learning-off state and no key readout. The MBON32 near-threshold direct-KC failure and 28 KCs still without a direct source among these five remain visible. No V1.1 gain, lowered threshold, changed synchrony, added MBON background or new sign is authorized by this contract.

## Required first gate for any later implementation

**Single question:** does the independently justified `aMe12_R` boundary expansion recruit at least one of the **20 newly contacted** KCs under the *unchanged* artificial V1 sensory/electrical policy? This asks about a source-boundary effect under a declared model, not natural cue tuning or task performance.

Use the same B5 seeds **31001–31003**, pulse checkpoints **11–29 s**, 200-ms pulse shape, 500-ms observation, neutral DN stream and nominal sensory current as the primary matched probe. Preserve old-three stimulation in every arm. Compare (i) V1 old three, (ii) V1.1 five stimulated, and (iii) V1.1 with the two added sources stimulated but their 48 KC effects disconnected. All arms must begin from matched neutral checkpoints/replay streams; group (iii) distinguishes new source spiking from transmission. The 20 newly reached KCs are a predeclared endpoint, not a post-hoc best subgroup. Report all 107 KC spike counts, per-KC voltage gaps, delivered events/current/charge, APL state, MBON32 voltage/spikes, DN traces, queue and safety diagnostics. Preserve V1's B5 direct-KC arm as a separate frozen reference for the unchanged KC→MBON32 bottleneck.

**Predeclared interpretation:** an anatomy-specific recruitment signal requires at least one of the 20 newly contacted KCs to spike in the nominal five-cell arm at every matched checkpoint/seed, with zero *added-source-caused* recruitment in the disconnected arm and no safety failure. The threshold is intentionally modest and applies to the new-contact cohort only; it is **not** a full-route gate. If it fails, report that the boundary expansion is anatomically valid but electrically insufficient under the frozen policy; do not raise gain, change current shape, add other candidate visual classes or select a favorable level. If it passes, continue to the separately failed KC→MBON32 gate under a new stage. Any spontaneous effect from new non-KC pairs, mismatch in old three's V1 replay, or unsafe activity invalidates the comparison and must be audited before inference.

## Stop and scope

This document **does not implement V1.1**. It is ready as a narrow, fail-capable first revision. It cannot supply a calibrated numerical repair for visual→KC, the direct KC→MBON32 volley, or the one-lane task. The next stage is **B5.4**, a separately versioned boundary-only implementation plus the fixed task-independent matched gate above. Stop after B5.4 and decide from its result; do not proceed automatically to motor readout, dopamine, learning or gameplay.

### Proposed B5.4 stage specification (not run)

| Required element | Predeclared content |
| --- | --- |
| Stage / name | **B5.4 — V1.1 boundary-only causal revalidation.** |
| Question / why next | Does the B5.2 source-backed two-cell addition recruit the 20 newly contacted KCs under the unchanged V1 policy? B5.3 found no calibrated numerical replacement. |
| Hypothesis / outcomes | Added-contact KC recruitment; no recruitment despite new delivery; or invalid comparison from replay/safety failure. Any outcome leaves the old direct-KC→MBON32 deficit unresolved until tested separately. |
| Intervention | Add exactly bodies 12740/13190 and their source rows with the one named inherited `aMe12_R`→KC fast-effect hypothesis; apply the same fixed sensory pulse to all five sources in the new arm. |
| Frozen controls | V1 old-three, V1.1 five-source and V1.1 effect-disconnected arms; matched B5 seeds/checkpoints, pulse/current, DN streams, all old policy values, learning off and no task readout. |
| Primary endpoint | Newly contacted 20-KC spike recruitment at nominal input under the criterion above. |
| Secondary endpoints | Full 107-KC voltage/spike distributions, exact new events/current/charge, APL, MBON32, DN and numerical safety. |
| Predeclared interpretation | Recruitment in every matched nominal seed/checkpoint with no added-source effect in the disconnected arm supports a boundary effect only; zero recruitment is a clean failure; replay or safety mismatch is inconclusive. |
| Do not | Alter amplitudes, thresholds, timings, signs, DN proxy, other visual classes or effect mask after seeing results; no task/game, reward, plasticity or training. |
| Output | Versioned V1.1 config/manifest, resolved source rows and provenance, regression tests for V1 preservation and UNKNOWN inactivity, raw matched gate records, independent audit, B5.4 report, `ASSUMPTIONS.md` and `CURRENT.md` status. |
| Stop | Report `PASS`/`FAIL`/`INCONCLUSIVE` for this narrow question and propose one next stage; do not launch it. |
