# Candidate fly circuit and data source

## MaleCNS minimal internal-learning fixture — 2026-10-02

The reduced fixture uses measured MaleCNS v1.0 source IDs and audited KC→MBON05 contact rows. Its artificial state encoder and teacher are not biological sensory or dopamine pathways. The experiment's contact-normalized electrical overlay, local LTD, and threshold action map remain **ENGINEERING ASSUMPTIONS**. The positive result is evidence of internal storage in the simulation only. See [the complete result and evidence boundary](MALECNS_MINIMAL_INTERNAL_LEARNING.md).

**2026-10-01 B2.1 active addendum:** The new [Candidate 1 executable-dynamics specification](B2_1_CANDIDATE1_EXECUTABLE_DYNAMICS.md) fixes chemical-current, boundary-flip and graded APL time laws as **ENGINEERING ASSUMPTIONS**. It audits selected MaleCNS source-pair coverage but does not establish exact synaptic effects, APL compartment physiology, task control or learning. Historical Circuit V1 evidence below remains valid for its separate cohort.

**Status: concrete anatomical route and explicit unresolved-effect policy; physiology and electrical runtime remain unvalidated.** The user selected **MaleCNS v1.0**. Its official full and traced-only source products have been validated, with statistics in [the active dataset report](MALECNS_V1_DATASET_REPORT.md). The [failed non-learning scale stress](MALECNS_V1_SCALE_PROFILE.md) must not be tuned into a passing biological model. The design in [CIRCUIT_V1.md](../CIRCUIT_V1.md) identifies the historical 140 source bodies and the subsequent 115-body proposal. The [data-only subset](CIRCUIT_V1_SUBSET.md) and [effect policy](CIRCUIT_V1_EFFECT_POLICY.md) remain unchanged, including 10,960 UNKNOWN pairs. The latest [route closure](CIRCUIT_V1_ROUTE_CLOSURE.md) localizes conservative plastic-contact candidates but leaves exact effects, intrinsic constants and boundary drive unresolved. No proposed Circuit V1 dynamics or fly-task training were run. Synthetic learning remains below its declared reliability gate.

## Critical-route evidence update — 2026-09-30

The [critical-route assessment](CIRCUIT_V1_CRITICAL_ROUTE_EVIDENCE.md), refined by [route closure](CIRCUIT_V1_ROUTE_CLOSURE.md), proposes **115 bodies**: inputs 13285/13707/13874 → all 107 right KCg-d cells → MBON32_R 519131 → DNa03_L 519624 → DNa02_L 523769, retaining MBON32's direct DN connection, with APL_R 10540 and PPL103_R 14182. The induced anatomy is 10,009 pairs / 45,010 contacts (`MEASURED`). This is an audited design alternative (`ENGINEERING ASSUMPTION` boundary); it has not replaced the 140-body subset or policy.

PPL103's proposed γ2 modulation of KC→MBON32 is **INFERRED**. Per-contact source ROI localization is now audited: 808 of 1,129 KC→MBON32 contacts have both endpoints in γ2(R); **796 contacts / 100 KC pairs** also satisfy the conservative same-KC γ2 contact screen for PPL103 14182 (`MEASURED` counts; `ENGINEERING ASSUMPTION` screen). Dopamine access at each terminal and exact MBON32 plasticity remain **UNKNOWN**. General KC/MBON learning and γ2α′1/MBON12 experiments are **LITERATURE-CONSTRAINED**, not exact MBON32 demonstrations. Detailed primary citations and scope are in the route closure report.

Motor activity suppression from MBON32 and activity promotion from DNa03 remain **INFERRED** testable hypotheses, with exact target effects **UNKNOWN**. The candidate route can therefore be studied conditionally without asserting those effects as facts. A fixed keyboard interface remains an **ENGINEERING ASSUMPTION**.

DNa03 omits **17,674 contacts (99.7629%)** and DNa02 **23,647 (98.7060%)** of incoming traced-parent contacts (`MEASURED`). The subsequent [DN boundary contract](DN_BOUNDARY_OPERATING_STATE_CONTRACT.md) now specifies a bounded proxy, omitted-input and disconnected-MBON controls (`ENGINEERING ASSUMPTION`). This closes the remaining boundary design/evidence blocker under a restricted engineering interpretation. Actual missing drive remains **UNKNOWN**. Exact plasticity still blocks later biological learning claims; it does not block specification of a frozen electrical baseline. No physical currents or electrical model were implemented.

## DN boundary evidence and modelling choice — 2026-09-30

**MEASURED:** 430 omitted presynaptic bodies contact both DNs, supplying 81.48% and 73.29% of their omitted contacts. The parent audit also records hundreds of distinct cell types and mixed transmitter annotations. Confidence values are for individual presynaptic transmitter predictions, not the consensus label or receptor-resolved target sign. Detailed source statistics and hashes are in [the boundary audit](figures/dn_boundary_input_audit.json).

**LITERATURE-CONSTRAINED:** DNa02 activity changes with locomotor state, with primary references in [the contract](DN_BOUNDARY_OPERATING_STATE_CONTRACT.md). **INFERRED:** a shared active-state surrogate is a useful reduced hypothesis. **UNKNOWN:** actual input correlation, magnitude, kinetics and shunting for this DN pair. Parent overlap does not measure electrical covariance.

**ENGINEERING ASSUMPTION:** a fixed active-like state is represented by tonic net depolarization plus bounded common/private telegraph fluctuations (50-ms autocorrelation, nominal boundary correlation 0.5). Low/nominal/high strengths are 0.50/1.00/1.50 times each independently specified DN model's passive voltage-margin current scale. These are engineering bounds, not biological measurements. There is no slow state switching, note/reward/readout input or rate adaptation. A matched-marginal independent-background diagnostic checks the common-drive assumption.

**Ready for Electrical Model V1 specification, not a validated electrical run.** The later neutral gate has predefined membrane, spiking, saturation and reproducibility criteria, with the keyboard/readout detached. It may fail without changing the chosen setting. Biological fidelity, full-circuit activity and learning remain unestablished; the unchanged source policy still preserves UNKNOWN explicitly.

KC ACh consensus is consistent with MaleCNS's experimental cell-type override semantics and class transmitter evidence. Preserve the disagreeing raw classifier predictions without treating them as equally supported physiology. Also, source `receptorType` describes sensory receptor annotations, not target synaptic receptors. Its null values cannot diagnose postsynaptic receptor absence. Detailed primary references and the complete mechanism classifications are in the evidence report.

## Candidate source

Use the [official MaleCNS v1.0 release](https://male-cns.janelia.org/release/) for one adult male brain and ventral nerve cord. The [official download page](https://male-cns.janelia.org/download/) publishes both the full segment graph and a traced-only graph, neuron annotations, neurotransmitter predictions and body statistics. The selected internal graph uses `status == Traced` and the release's traced-only edge product. It preserves an anatomical brain-to-cord source without stitching specimens together. Its exact object generations and checksums are pinned in `data/raw/malecns_v1/source_manifest.json`.

Do not combine MaleCNS edges with BANC, FAFB or other specimens as though they were measured in the same animal. The full MaleCNS file contains untraced fragments; use the traced-only source product for the neuron graph and keep the distinction visible. The flat neuron annotation provides `somaNeuromere` for a minority of traced neurons and does not provide per-synapse ROI locations. Do not infer regions or synaptic effect from superclass or transmitter labels.

## Remaining functional route audit

| Segment | Candidate | Evidence needed before use |
| --- | --- | --- |
| Artificial game input | A labelled, causal overlay onto identified upstream sensory or projection cells | Source IDs, anatomical region, injection strengths and latency; no ideal press/action signal. |
| Learning circuit | Kenyon cells to MB output neurons within specified mushroom-body compartments | Source edge IDs, compartment/synapse locations, coverage, plastic mask and cut-edge count. |
| Modulatory route | Selected DANs projecting to those compartments | Source IDs and compartment targets; distinguish anatomical synapses from an artificial game-to-DAN reward overlay. |
| Output | Source-connected downstream/descending and cord motor candidates | Reachability and path audit from MBONs to chosen outputs; fixed readout must be stated as an interface. |

The anatomical source-ID and induced-edge audit is complete for Circuit V1; the table identifies remaining functional evidence. KC→MBON plasticity and compartment-specific DAN effects have experimental support, but the current scalar `Δw = η e D` is an engineering rule rather than a measured universal fly rule. Anatomical connection counts alone do not establish sign, efficacy or timing. Unknown postsynaptic effects remain **UNKNOWN** until receptor/function evidence or an explicitly labelled prior is supplied.

## Go/no-go audit

1. Reconcile neuron IDs, edge counts and filtering with the exact source manifest; retain source-to-runtime ID mapping and unmodified source topology.
2. Resolve candidate KC, MBON and DAN annotations to source IDs; inspect compartment assignments and the intended plastic edge mask. Report missing and ambiguous annotations.
3. Check sensory→KC/MBON→downstream output reachability in the retained graph, including paths lost at extraction boundaries. If the path is absent, report that limitation and label any bridge as an overlay.
4. Record unknown sign/weight/delay fractions, overlay edges, lesion masks and a source checksum. Validate activity and queue growth on a subgraph before large simulation.
5. Only after the synthetic gate passes and this route is audited should fly-data task learning begin. No route in this document is yet a validated fly circuit for osu.
