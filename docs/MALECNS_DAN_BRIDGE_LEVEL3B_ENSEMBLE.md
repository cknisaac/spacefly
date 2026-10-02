# MaleCNS Level 3B — anatomy-selected PAM08 ensemble

**Result: FAIL** under the frozen target/wrong/control contract.

## Frozen design

- Cohort: same 32 KC→MBON05 pairs; MBON05 source ID 10495.
- Ensemble: 87177, 107285, 55210, selected as the exact minimum γ4 cover within the complete 25-body PAM08 roster.
- Fixed threshold: `0.0055723359953319` mV-equivalent; η = `0.00005`; immutable original-weight floor = `20%`.
- Gaussian encoder, LIF/contact model, target/wrong regions, 120 blocks, presentation-local eligibility, and frozen readout inherited unchanged.
- Each scheduled teacher event stimulated all three isolated DAN LIF models with the inherited 2.0-mV-equivalent, 20-ms pulse. Per KC, the gate required local eligibility and a spike from at least one anatomically connected DAN.

## Step 1 — capacity gate

**PASS**; no learning was run for this step. Target and wrong cores both reached 3/3 with all eligible, reachable edges at their exact 20% original-weight floors.

| Region | Positive-eligibility KCs | Clamped eligible/reachable KCs | Core actions |
|---|---:|---:|---:|
| target | 6 | 6: 49160, 49526, 49544, 49545, 49867, 50411 | 3/3 |
| wrong | 6 | 6: 45460, 45467, 45620, 45950, 46497, 47101 | 3/3 |

### Target ceiling position map

| Position | L3B ensemble capacity |
|---:|---|
| 0 | 0.008010579 / no-action |
| 0.05 | 0.014215610 / no-action |
| 0.1 | 0.015860566 / no-action |
| 0.15 | 0.015056665 / no-action |
| 0.2 | 0.009310005 / no-action |
| 0.25 | 0.011181216 / no-action |
| 0.3 | 0.009622703 / no-action |
| 0.35 | 0.009945537 / no-action |
| 0.4 | 0.016840031 / no-action |
| 0.45 | 0.011751978 / no-action |
| 0.5 | 0.014575051 / no-action |
| 0.55 | 0.015085034 / no-action |
| 0.6 | 0.008374376 / no-action |
| 0.65 | 0.002274398 / ACTION |
| 0.7 | 0.002719318 / ACTION |
| 0.75 | 0.002572853 / ACTION |
| 0.8 | 0.010783171 / no-action |
| 0.85 | 0.015670464 / no-action |
| 0.9 | 0.013665335 / no-action |
| 0.95 | 0.016772147 / no-action |
| 1 | 0.008940782 / no-action |

### Wrong-region ceiling position map

| Position | L3B ensemble capacity |
|---:|---|
| 0 | 0.008010579 / no-action |
| 0.05 | 0.014215610 / no-action |
| 0.1 | 0.011274847 / no-action |
| 0.15 | 0.003011333 / ACTION |
| 0.2 | 0.001862001 / ACTION |
| 0.25 | 0.002236243 / ACTION |
| 0.3 | 0.001975958 / ACTION |
| 0.35 | 0.009945537 / no-action |
| 0.4 | 0.016840031 / no-action |
| 0.45 | 0.011751978 / no-action |
| 0.5 | 0.014575051 / no-action |
| 0.55 | 0.015085034 / no-action |
| 0.6 | 0.016351110 / no-action |
| 0.65 | 0.011371990 / no-action |
| 0.7 | 0.013596590 / no-action |
| 0.75 | 0.012864267 / no-action |
| 0.8 | 0.013536520 / no-action |
| 0.85 | 0.015670464 / no-action |
| 0.9 | 0.013665335 / no-action |
| 0.95 | 0.016772147 / no-action |
| 1 | 0.008940782 / no-action |

## Step 2 — pretraining gate

Pretraining gate: **PASS**. All three DANs activated on 3/3 stimulated checks; none spiked in 3/3 unstimulated checks. Paired KC/DAN activity reached the local gate. No-DAN control changed zero weights.

## Step 2 — training results

| Arm | Blocks / presentations | DAN-stim / gate events | Changed KC weights | Floor hits | Final action positions |
|---|---:|---:|---:|---:|---|
| target | 120 / 1200 | 600 / 600 | 6 | 3: 49544, 49545, 49867 | 0.7, 0.75 |
| wrong-region | 120 / 1200 | 600 / 600 | 6 | 2: 45467, 45950 | 0.15, 0.2, 0.25, 0.3 |
| DAN-on/plasticity-off | 120 / 1200 | 600 / 600 | 0 | 0: none | none |

### Changed weights

#### Target teaching

| KC source ID | Original weight | Final weight |
|---:|---:|---:|
| 49160 | 0.0321167883212 | 0.0264774910004 |
| 49526 | 0.0277372262774 | 0.010794530683 |
| 49544 | 0.0262773722628 | 0.00525547445255 |
| 49545 | 0.0379562043796 | 0.00759124087591 |
| 49867 | 0.029197080292 | 0.00583941605839 |
| 50411 | 0.0335766423358 | 0.0221705385688 |

#### Wrong-region teaching

| KC source ID | Original weight | Final weight |
|---:|---:|---:|
| 45460 | 0.0379562043796 | 0.0152128198286 |
| 45467 | 0.0248175182482 | 0.00496350364964 |
| 45620 | 0.0335766423358 | 0.0108073027505 |
| 45950 | 0.0175182481752 | 0.00350364963504 |
| 46497 | 0.0394160583942 | 0.0167754767659 |
| 47101 | 0.0262773722628 | 0.0149309026321 |

#### Matched control

No weights changed.

### Final position → MBON/action map

MBON values are maximum voltage in the fixed observation window; actions use the inherited threshold.

| Position | Target teaching | Wrong-region teaching | Matched DAN-on/plasticity-off |
|---:|---|---|---|
| 0 | 0.008010579 / no-action | 0.008010579 / no-action | 0.008010579 / no-action |
| 0.05 | 0.014215610 / no-action | 0.014215610 / no-action | 0.014215610 / no-action |
| 0.1 | 0.015860566 / no-action | 0.012412424 / no-action | 0.015860566 / no-action |
| 0.15 | 0.015056665 / no-action | 0.004835311 / ACTION | 0.015056665 / no-action |
| 0.2 | 0.009310005 / no-action | 0.002590160 / ACTION | 0.009310005 / no-action |
| 0.25 | 0.011181216 / no-action | 0.004730512 / ACTION | 0.011181216 / no-action |
| 0.3 | 0.009622703 / no-action | 0.004811955 / ACTION | 0.009622703 / no-action |
| 0.35 | 0.009945537 / no-action | 0.009945537 / no-action | 0.009945537 / no-action |
| 0.4 | 0.016840031 / no-action | 0.016840031 / no-action | 0.016840031 / no-action |
| 0.45 | 0.011751978 / no-action | 0.011751978 / no-action | 0.011751978 / no-action |
| 0.5 | 0.014575051 / no-action | 0.014575051 / no-action | 0.014575051 / no-action |
| 0.55 | 0.015085034 / no-action | 0.015085034 / no-action | 0.015085034 / no-action |
| 0.6 | 0.012771232 / no-action | 0.016351110 / no-action | 0.016351110 / no-action |
| 0.65 | 0.005878657 / no-action | 0.011371990 / no-action | 0.011371990 / no-action |
| 0.7 | 0.002719318 / ACTION | 0.013596590 / no-action | 0.013596590 / no-action |
| 0.75 | 0.005306915 / ACTION | 0.012864267 / no-action | 0.012864267 / no-action |
| 0.8 | 0.011716389 / no-action | 0.013536520 / no-action | 0.013536520 / no-action |
| 0.85 | 0.015670464 / no-action | 0.015670464 / no-action | 0.015670464 / no-action |
| 0.9 | 0.013665335 / no-action | 0.013665335 / no-action | 0.013665335 / no-action |
| 0.95 | 0.016772147 / no-action | 0.016772147 / no-action | 0.016772147 / no-action |
| 1 | 0.008940782 / no-action | 0.008940782 / no-action | 0.008940782 / no-action |

## Contract criteria

| Criterion | Result |
|---|---|
| `all_120_blocks_and_1200_presentations_per_arm` | PASS |
| `all_scheduled_teaching_events_activate_all_three_dans` | PASS |
| `target_core_3_of_3` | FAIL |
| `wrong_core_3_of_3` | PASS |
| `target_action_locality` | PASS |
| `wrong_action_locality` | PASS |
| `matched_dan_on_plasticity_off_unchanged_and_no_action` | PASS |
| `target_frozen_retention` | FAIL |
| `wrong_frozen_retention` | PASS |
| `no_update_without_anatomically_connected_active_dan` | PASS |
| `all_updates_have_local_eligibility_and_connected_active_dan` | PASS |
| `all_updates_within_union_anatomical_mask` | PASS |
| `immutable_20_percent_floor_respected` | PASS |
| `fixed_threshold_encoder_and_inherited_learning_parameters` | PASS |

Target and wrong actions were local; the matched DAN-on/plasticity-off arm kept baseline weights and no-action map. Wrong-region learning achieved 3/3 and persisted frozen. Target teaching achieved 2/3 (0.70 and 0.75; 0.65 remained no-action), so target retention under the strict contract failed and overall Level 3B is **FAIL**. No tuning followed.

## Receipts

- Frozen ensemble config: `configs/malecns_dan_bridge_level3b_ensemble.json`.
- Capacity gate result: `runs/malecns_dan_bridge_level3b/capacity.json`.
- Training result: `runs/malecns_dan_bridge_level3b/result.json`.
- Pinned anatomy source: `docs/figures/l3_gamma4_dan_cohort_coverage_audit.json`.
