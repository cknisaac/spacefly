# Larval L3 C1 local-rule direction gate

**Gate verdict: INCONCLUSIVE.** No primary experiment located here measures a DAN-c1-gated plasticity equation or polarity at the exact first-instar KC→MBON-c1 contacts. The frozen engineering simulator can produce its fixed DN-VNC action when those weights increase, but cannot by itself tell us which way the biological synapses change or whether the DN readout is the behavior DAN-c1 teaches.

## Question and decision rule

The question is whether evidence supports a specific local learning rule at KC→MBON-c1, and whether that rule’s sign moves the frozen simulator toward its fixed action output. A biology-supported rule would need evidence for the relevant presynaptic KC, DAN-c1 teaching source, postsynaptic MBON-c1/lower-peduncle compartment, and update polarity. Results from other compartments or adult animals are related evidence, not an exact rule for this pathway.

The gate is **INCONCLUSIVE** if that exact rule is not established, even when one engineering update direction creates an output. It would be **FAIL** only if an established biological sign contradicted the required direction.

## Evidence audit

| Claim | Evidence label | What the primary work establishes | What it does not establish |
|---|---|---|---|
| DAN-c1 participates in larval aversive learning | **MEASURED behavior / causal manipulation** | Qi et al. report a DAN-c1 role in larval aversive olfactory learning and a D2-receptor-dependent mechanism. The identified DAN-c1 innervation is in the lower peduncle. [Qi et al., eLife 100890](https://elifesciences.org/articles/100890) | A weight-update sign at KC→MBON-c1, or that MBON-c1 is the relevant postsynaptic cell for the tested behavior. |
| DAN-c1 can act as a larval teaching signal | **MEASURED behavioral effect** | Saumweber et al. report that selectively silencing DAN-c1 during training impairs aversive taste associative memory; activating the identified DANs can support memory. [Saumweber et al., eLife 91387](https://elifesciences.org/articles/91387) | The local KC→MBON-c1 plasticity locus, timing window, or potentiation/depression sign. |
| Candidate anatomy | **MEASURED anatomy; functional effect unknown** | The L3 anatomy audit reports first-instar KC→MBON-c1 contacts, direct DAN-c1→MBON-c1 contacts, and MBON-c1→annotated DN-VNC edges. The selected connectome is first-instar; the cited DAN-c1 learning tests are larval behavioral experiments, including third-instar evidence. | Synaptic efficacy, KC contact localization within the learning compartment, the sign of the MBON-c1→DN edge, or the behavioral meaning of a DN-VNC spike. |
| Dopamine can modulate KC→MBON signaling | **Adjacent physiological evidence** | Hige et al. measured dopamine-dependent bidirectional plasticity at adult fly KC→MBON synapses in other mushroom-body compartments. [Hige et al., Neuron 2015](https://pmc.ncbi.nlm.nih.gov/articles/PMC4732734/) | Transfer of that rule or sign to larval DAN-c1/MBON-c1 contacts. Bidirectionality across other compartments does not select the polarity here. |
| DAN-c1’s exact rule at KC→MBON-c1 | **NOT MEASURED in sources reviewed** | The 2025 DAN-c1 paper discusses a mechanistic hypothesis involving D2 receptors and cAMP regulation. | It does not report direct paired stimulation or a measured synaptic update equation at these exact KC→MBON-c1 contacts. A D2/cAMP mechanism is not itself a sign measurement of KC→MBON-c1 efficacy. |

Thus the evidence supports the **teaching-neuron / compartment association** more strongly than it supports the **plasticity locus and polarity**. Canonical aversive KC→MBON depression in other systems is only an analogy; applying that sign here would be an unverified transfer. Conversely, selecting potentiation because the simulator needs it would be outcome-driven rule selection. Neither sign is admitted as biology-supported for L3.

## Frozen-simulator direction test

The read-only audit script replays each of the same eight frozen position-bin states at KC→MBON-c1 weight factors 0.5, 1.0, and 2.0. Factor 1.0 is the frozen reference. A factor below 1 represents a negative effective weight change (Δw<0); a factor above 1 represents a positive change (Δw>0). All other values, inputs, and boundaries are held fixed. Each cell is replayed twice. No teaching signal, plasticity, task training, or parameter search is enabled.

Frozen input hashes:

| Input | SHA-256 |
|---|---|
| `configs/larval_l3_c1_subgraph_manifest_v1.json` | `b54a8a7ec9e3b18f21f8df91584c33f875c3302c8e534b6020dec7290f004895` |
| `configs/larval_l3_c1_electrical_v1.json` | `5e32171707409a5dffc66f0c93d48bec307d442a01ace8b8554fa82e23c91f6e` |
| `runs/larval_l3_c1_neutral_dynamics_v1.json` | `8fa83febee7812f5ba3435592a9a4dc390f156ccd9ba929e25486bbf9b4ce7bc` |
| `runs/larval_l3_c1_controllability_v1.json` | `f3d224242f6dd0b7c526acdbf905fa43eda3d16182736473be359551e4c6f340` |

| Direction relative to reference | Factor | MBON-c1 spikes by states 0–7 | Fixed DN-VNC action states |
|---|---:|---|---|
| decrease (Δw<0) | 0.5 | 3, 3, 2, 2, 2, 2, 3, 2 | none |
| reference | 1.0 | 5, 7, 4, 6, 4, 5, 4, 4 | none |
| increase (Δw>0) | 2.0 | 6, 9, 8, 8, 5, 7, 5, 7 | state 6 |

All 24 replays were deterministic. The existing frozen sweep already showed additional action states at 4× (states 1, 3, 5, 6, and 7). Under this electrical assumption set, **increasing KC→MBON-c1 weight is the direction that moves toward the engineered DN action boundary; decreasing it moves away**. These are only simulator measurements. DAN-c1 generated zero spikes in the pre-training sweep, and this audit did not supply a teaching signal.

## Result and next gate

**INCONCLUSIVE; do not start Phase 5.** The engineering direction is known (positive Δw), but there is no literature-supported polarity for the exact local rule, and no source-grounded relationship between the fixed DN action and DAN-c1-mediated aversive learning. A canonical LTD analogy would point opposite the present action-producing direction only if one additionally assumed that this MBON/DN route encodes the same aversive action; that assumption is not established, so it cannot support a biological FAIL verdict either.

Next progress requires primary evidence resolving at least one of these: (1) the local KC→MBON-c1 plasticity sign during DAN-c1 pairing, or (2) a justified MBON-c1/DN-VNC behavioral valence and action mapping that determines how local updates should affect this readout. Until then, either choosing LTD or LTP would be an unsupported design choice.

## Reproducibility

- Script: `scripts/audit_larval_l3_c1_rule_direction.py`
- Direction result: `runs/larval_l3_c1_rule_direction_audit_v1.json`
- Direction result SHA-256: `3dbb1999e5cf9f50763425c8f64122685252889eebbb86d4ad4d2921e5144028`
- Method imports the already-frozen simulator runner and asserts all four frozen hashes before replay; it writes a separate result and does not alter frozen inputs.
