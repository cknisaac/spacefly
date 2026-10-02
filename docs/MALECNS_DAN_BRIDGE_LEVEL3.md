# MaleCNS Level 3 — one-neuron DAN bridge

**2026-10-02 · MALECNS-DAN-BRIDGE-LEVEL3-v1.1 · FAIL.** The read-only anatomy audit admitted one specific PAM08 body. A prelearning stimulus revision made its modeled LIF activity reliable; no learning was run under the failed first stimulus. The one 120-block learning run then failed to create an action region in either taught core. All Level 2 and Level 2R files were left unchanged, and no Level 2 setting was tuned.

## Inherited Level 2 record

- Cohort 1, Level 2 v2.5: **PASS** under its corrected, arm-specific action-map contract.
- Fresh cohort 2, Level 2R: **FAIL** strict 3/3 target-core replication. A partial local learning effect replicated, and the wrong-region core passed 3/3.
- Level 2 tuning stopped. Level 3 uses the cohort 1 32 KCs, Gaussian encoder, MBON05, LIF/contact normalization, position grid, target/wrong regions, inherited action threshold **0.005572335995331903 mV-equivalent**, 120 blocks, presentation-local eligibility, η = 0.00005, and the inherited LTD implementation.

## Read-only anatomy decision

The [new cohort-level anatomy audit](figures/l3_dan_bridge_anatomy_audit.json) scanned the pinned MaleCNS v1.0 traced-only syn-partner source and checked both synaptic endpoints against the cached 256-nm subcompartment volume. The source checksum is `3db100d3b4c7cfdc9b34506b3eb8b5ead2d9760b38952e5656285bb362327efc`; no ROI chunk was missing. The candidate was chosen from the 25 PAM08 bodies in the pre-existing B1/B2 roster by the most same-γ4 KCs shared with the exact frozen 32-KC cohort. The audit used anatomy only, before Level 3 learning outcomes.

| Anatomical observation | Result |
| --- | ---: |
| MBON05 | MaleCNS body **10495** |
| Frozen cohort KC→MBON05 contacts with both endpoints in γ4(L) | **685 contacts / 32 KC pairs** |
| Selected DAN | Body **87177**, `PAM08(y4)_L`, `DAN`, dopamine consensus and ground truth; annotation status `Prelim Roughly traced` |
| Body 87177→frozen KCs, traced pair graph | **32 contacts / 21 KC pairs** |
| Body 87177→frozen KCs, both endpoints in γ4(L) | **30 contacts / 20 KC pairs** |
| Same 20 KCs→MBON05, both endpoints in γ4(L) | **430 contacts** |
| Body 87177→MBON05 direct traced pair | **48 contacts**, physiological effect unknown and electrically excluded from this minimal bridge |

The next two PAM08 bodies in that audited roster reach 18 KCs / 26 strict γ4 contacts (107285) and 17 KCs / 29 contacts (90678). PPL103 has many aggregate edges into this KC cohort, but its annotation is γ2α′1, not the audited γ4 compartment; its edge count was not treated as evidence for this bridge. PAM07 remains an anatomical alternative requiring its own exact compartment audit. Body 87177 is the strongest **within the pre-audited PAM08 roster for this frozen cohort**, not a claim about every possible MaleCNS DAN.

Only the **20** same-γ4 KCs reached by body 87177 were allowed to pass its spike signal to the local LTD gate. The other 12 KC→MBON05 weights, the full 32-KC electrical input and all initial weights remained present. A shared KC and compartment supports an anatomical association; it does not measure dopamine release, receptor action or plasticity at the exact KC→MBON05 contact.

## Fixed bridge and prelearning tests

The external teaching event chose **when** to stimulate body 87177. The selected body was represented by the inherited engineering LIF parameters. A DAN spike then supplied a binary local gate to the inherited presentation-local LTD primitive. The rule and its η were unchanged; the spike-to-gate transform, stimulation current, and LTD interpretation remain **ENGINEERING ASSUMPTIONS**. No decoder, motor/visual route, reward prediction error or osu timing was added. The direct 87177→MBON05 synapses were recorded anatomically but not assigned a synaptic current because their effect is unknown and the reduced Level 2 readout was held fixed.

The first [pretraining-only receipt](../runs/malecns_dan_bridge_level3/pretraining_v0.json) is **INCONCLUSIVE**: a 1.2-mV-equivalent, 20-ms pulse produced zero DAN spikes in three trials. No learning was run. The separately [versioned stimulation config](../configs/malecns_dan_bridge_level3_v1_1.json) uses the 2.0-unit, 20-ms PAM pulse already documented in the earlier [B2 design](B2_CANDIDATE1_DESIGN.md); this changed only the new external DAN stimulation, before any Level 3 learning outcome. At τm = 20 ms its ideal no-synapse threshold time is about 13.9 ms.

The v1.1 pretraining gate **PASSed**:

| Check | Observation |
| --- | --- |
| Fixed stimulation activates DAN | 3/3 trials spiked at 115 ms from presentation onset; unstimulated 0/3 |
| DAN activity reaches local gate | Paired position 0.70 KC activity plus one DAN spike changed 2 anatomically reached weights |
| No weight change without DAN | Matched KC presentation with zero DAN spikes changed 0 weights |
| Locality of updates | Every pretraining weight update was on a KC reached by body 87177 in γ4(L) |

## One complete 120-block learning run

The original three arms completed the same 1,200-presentation schedule. The target and wrong-region arms each had 600 external stimulation events and 600 observed DAN gate events. The inherited Level 2 off policy omitted teaching stimulation, so that arm is a **DAN-off and plasticity-off** control. A separate [matched plasticity-off control](../runs/malecns_dan_bridge_level3/matched_plasticity_off.json) then completed the same 120 blocks and 1,200 presentations with plasticity disabled **and all 600 target teaching events stimulating the DAN**. All 600 produced a DAN spike; weights and the frozen map remained exactly at baseline, with no actions. This control completed the Level 3 comparison without another learning run. Frozen position evaluation had DAN stimulation and plasticity both off after each block and at completion.

| Arm | Changed KC weights | Final core actions | Final full-grid actions | Mean taught-core MBON05 response |
| --- | ---: | ---: | ---: | ---: |
| Target teacher | 4/32 | **0/3** at 0.65–0.75 | 0 | **0.00746056** mV |
| Inherited off: DAN off, plasticity off | 0/32 | 0/3 target, 0/3 wrong | 0 | unchanged baseline |
| Matched off: DAN on, plasticity off | 0/32 | 0/3 target, 0/3 wrong | 0 | unchanged baseline |
| Wrong-region teacher | 3/32 | **0/3** at 0.15–0.25 | 0 | **0.00853110** mV |

The target-core baseline mean was 0.01261095 mV and wrong-core baseline mean was 0.01184930 mV. Thus the DAN-gated weight changes reduced the taught responses, but the smallest final core voltages remained above the fixed action threshold: target 0.65 = 0.007108858 mV and wrong 0.20 = 0.006792715 mV. No learned action region existed to retain. Both off controls kept their exact initial weights and map, including the matched arm with active DAN stimulation. No update occurred in any trial without a DAN spike, and all updates were confined to the 20 reached KCs. Empty action sets meet the locality predicate only vacuously; they are not learning successes.

Sampled learning curves below show mean MBON05 voltage in each taught core. The [raw result](../runs/malecns_dan_bridge_level3/result.json) stores every block, trial, DAN spike/gate event, weight change and full frozen position map.

| Block | Target mean (mV) | Target actions / 3 | Wrong mean (mV) | Wrong actions / 3 |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 0.01254941 | 0 | 0.01181859 | 0 |
| 24 | 0.01115180 | 0 | 0.01111234 | 0 |
| 48 | 0.00972239 | 0 | 0.01043231 | 0 |
| 72 | 0.00850127 | 0 | 0.00979385 | 0 |
| 96 | 0.00790994 | 0 | 0.00915942 | 0 |
| 120 | 0.00746056 | 0 | 0.00853110 | 0 |

### Final position → MBON05 / action map

All 21 grid positions in both teacher arms and both off controls were **no-action**. The two off controls have the same baseline map, so the single off column covers both. The table gives the frozen maximum MBON05 voltage in mV-equivalent; action would require voltage ≤ 0.005572335995331903.

| Position | Target DAN | Plasticity off | Wrong-region DAN |
| ---: | ---: | ---: | ---: |
| 0.00 | 0.008010579 | 0.008010579 | 0.008010579 |
| 0.05 | 0.014215610 | 0.014215610 | 0.014215610 |
| 0.10 | 0.015860566 | 0.015860566 | 0.012412424 |
| 0.15 | 0.015056665 | 0.015056665 | 0.008414443 |
| 0.20 | 0.009310005 | 0.009310005 | 0.006792715 |
| 0.25 | 0.011181216 | 0.011181216 | 0.010386137 |
| 0.30 | 0.009622703 | 0.009622703 | 0.007663546 |
| 0.35 | 0.009945537 | 0.009945537 | 0.009945537 |
| 0.40 | 0.016840031 | 0.016840031 | 0.016840031 |
| 0.45 | 0.011751978 | 0.011751978 | 0.011751978 |
| 0.50 | 0.014575051 | 0.014575051 | 0.014575051 |
| 0.55 | 0.015085034 | 0.015085034 | 0.015085034 |
| 0.60 | 0.015311158 | 0.016351110 | 0.016351110 |
| 0.65 | 0.007108858 | 0.011371990 | 0.011371990 |
| 0.70 | 0.007220514 | 0.013596590 | 0.013596590 |
| 0.75 | 0.008052301 | 0.012864267 | 0.012864267 |
| 0.80 | 0.011716389 | 0.013536520 | 0.013536520 |
| 0.85 | 0.015670464 | 0.015670464 | 0.015670464 |
| 0.90 | 0.013665335 | 0.013665335 | 0.013665335 |
| 0.95 | 0.016772147 | 0.016772147 | 0.016772147 |
| 1.00 | 0.008940782 | 0.008940782 | 0.008940782 |

## Decision and model limit

**FAIL.** Anatomy association, DAN stimulation, DAN-to-gate causality, both off controls, update locality, and fixed parameters passed. The required target/wrong action cores and learned frozen retention failed. The single DAN reaches only 20/32 frozen KCs; the missing access to some high-impact KCs is a plausible explanation, not a demonstrated unique cause. No additional neuron, parameter, threshold, duration or cohort was tried after this result.

An implementation issue inherited from Level 2 limits interpretation of all its runs: each presentation creates a new `LocalLTD` with the **current** weights as its local `initial`, so its 20% floor is relative to that presentation rather than the original cohort baseline. This can permit weights below 20% of their original value. In this Level 3 target arm, KC 49544 ended at normalized weight `1.15×10^-119` (about `4.39×10^-118` of its original value) and KC 49867 at 2.7% of its original value. The same issue is visible in saved Level 2 v2.5 weights. The Level 2 statuses above are preserved as their recorded action-map results; this issue was not repaired or used for a follow-up run.

## Reproduction and receipts

- [Anatomy audit runner](../scripts/audit_l3_dan_bridge_anatomy.py) and [audit output](figures/l3_dan_bridge_anatomy_audit.json); audit SHA-256 `3094587cdc9c20fee2da742bd00833d116b0217b3d10857b49ca34873dd3f9d5`.
- [Bridge runner](../src/project_b/malecns_continuous_position_learning/experiment_level3_dan_bridge.py), [frozen v1.1 config](../configs/malecns_dan_bridge_level3_v1_1.json) and [full result](../runs/malecns_dan_bridge_level3/result.json); config SHA-256 `647414cb059a3b01d93a55ddd7ab56112b3fde48bc5ce6df4be40b116e3425f6`, result SHA-256 `c1d3d28d408de40f165f1e0aabc95c8cda44e8f25e28adbc11ba75157a857da8`.
- [Matched plasticity-off runner](../scripts/run_l3_matched_plasticity_off.py) and [receipt](../runs/malecns_dan_bridge_level3/matched_plasticity_off.json); receipt SHA-256 `8921933f25a06915156955d6ab01c6038614a4cc86b3f0a9bbb3fd15f5932db5`.
- The original Level 2 v2.5 config SHA-256 remains `e81a9da42f28be4ad288f8f416a8186b2443230c012d1563bc827c3f0c8b5485`.

No claim of measured DAN physiology, biological reward coding or fly behavior follows from this reduced engineering experiment.
