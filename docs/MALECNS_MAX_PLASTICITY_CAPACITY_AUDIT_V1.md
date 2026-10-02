# Task-free maximum-plasticity capacity audit v1

## Protocol and classification

- No learning function, teacher schedule, external DAN stimulation, or weight-update rule was run. Each ceiling is an in-memory counterfactual: union KC edges with positive recorded presentation eligibility in that region, clamp only those edges to exactly 20% of immutable original weights, and evaluate with the frozen Level 2 position-grid evaluator.
- Frozen action threshold: `0.0055723359953319` mV-equivalent. Floor: `20%` of original weights.
- **Target-region ceiling:** L2 3/3; DAN 87177 L3 0/3.
- **Classification:** L2 ceiling 3/3 and L3 ceiling <3/3. Single-DAN coverage/authority is structurally insufficient under this model and eligibility contract; do not extend training.
- Wrong-region repeat: L2 3/3; DAN 87177 L3 0/3.

## Target region [0.65, 0.75]

- **L2:** 6 edges set exactly to 20% of original: 49160, 49526, 49544, 49545, 49867, 50411.
- **L3 DAN 87177:** 4 edges set exactly to 20% of original: 49160, 49544, 49867, 50411.

| Position | L2 all eligible edges at floor | L3 DAN 87177 reachable+eligible at floor |
|---:|---|---|
| 0 | 0.008010579 / no-action | 0.008010579 / no-action |
| 0.05 | 0.014215610 / no-action | 0.014215610 / no-action |
| 0.1 | 0.015860566 / no-action | 0.015860566 / no-action |
| 0.15 | 0.015056665 / no-action | 0.015056665 / no-action |
| 0.2 | 0.009310005 / no-action | 0.009310005 / no-action |
| 0.25 | 0.011181216 / no-action | 0.011181216 / no-action |
| 0.3 | 0.009622703 / no-action | 0.009622703 / no-action |
| 0.35 | 0.009945537 / no-action | 0.009945537 / no-action |
| 0.4 | 0.016840031 / no-action | 0.016840031 / no-action |
| 0.45 | 0.011751978 / no-action | 0.011751978 / no-action |
| 0.5 | 0.014575051 / no-action | 0.014575051 / no-action |
| 0.55 | 0.015085034 / no-action | 0.015085034 / no-action |
| 0.6 | 0.008374376 / no-action | 0.011662294 / no-action |
| 0.65 | 0.002274398 / ACTION | 0.005898516 / no-action |
| 0.7 | 0.002719318 / ACTION | 0.008244704 / no-action |
| 0.75 | 0.002572853 / ACTION | 0.006982825 / no-action |
| 0.8 | 0.010783171 / no-action | 0.010783171 / no-action |
| 0.85 | 0.015670464 / no-action | 0.015670464 / no-action |
| 0.9 | 0.013665335 / no-action | 0.013665335 / no-action |
| 0.95 | 0.016772147 / no-action | 0.016772147 / no-action |
| 1 | 0.008940782 / no-action | 0.008940782 / no-action |

## Wrong region [0.15, 0.25]

- **L2:** 6 edges set exactly to 20% of original: 45460, 45467, 45620, 45950, 46497, 47101.
- **L3 DAN 87177:** 3 edges set exactly to 20% of original: 45460, 45620, 47101.

| Position | L2 all eligible edges at floor | L3 DAN 87177 reachable+eligible at floor |
|---:|---|---|
| 0 | 0.008010579 / no-action | 0.008010579 / no-action |
| 0.05 | 0.014215610 / no-action | 0.014215610 / no-action |
| 0.1 | 0.011274847 / no-action | 0.011274847 / no-action |
| 0.15 | 0.003011333 / ACTION | 0.006648472 / no-action |
| 0.2 | 0.001862001 / ACTION | 0.006428508 / no-action |
| 0.25 | 0.002236243 / ACTION | 0.009708152 / no-action |
| 0.3 | 0.001975958 / ACTION | 0.006610906 / no-action |
| 0.35 | 0.009945537 / no-action | 0.009945537 / no-action |
| 0.4 | 0.016840031 / no-action | 0.016840031 / no-action |
| 0.45 | 0.011751978 / no-action | 0.011751978 / no-action |
| 0.5 | 0.014575051 / no-action | 0.014575051 / no-action |
| 0.55 | 0.015085034 / no-action | 0.015085034 / no-action |
| 0.6 | 0.016351110 / no-action | 0.016351110 / no-action |
| 0.65 | 0.011371990 / no-action | 0.011371990 / no-action |
| 0.7 | 0.013596590 / no-action | 0.013596590 / no-action |
| 0.75 | 0.012864267 / no-action | 0.012864267 / no-action |
| 0.8 | 0.013536520 / no-action | 0.013536520 / no-action |
| 0.85 | 0.015670464 / no-action | 0.015670464 / no-action |
| 0.9 | 0.013665335 / no-action | 0.013665335 / no-action |
| 0.95 | 0.016772147 / no-action | 0.016772147 / no-action |
| 1 | 0.008940782 / no-action | 0.008940782 / no-action |

## Read-only γ4 DAN coverage audit

The complete local γ4 audit within the pre-existing 25-body PAM08 B1/B2 roster finds the exact minimum set below covers all 32 frozen KCs with strict same-compartment γ4 DAN→KC and KC→MBON05 contacts. Each member and its KC coverage are listed.

| DAN body | Annotation | γ4 KCs covered | KC source IDs |
|---:|---|---:|---|
| 87177 | PAM08 `PAM08(y4)_L` | 20 | 45259, 45380, 45434, 45460, 45620, 47101, 47117, 47287, 47758, 47988, 48337, 48596, 49124, 49160, 49544, 49867, 50411, 50591, 50791, 50820 |
| 107285 | PAM08 `PAM08(y4)_L` | 18 | 45259, 45380, 45434, 45467, 47287, 47694, 48337, 48596, 49526, 49544, 49545, 49867, 50411, 50568, 50591, 51053, 51055, 51330 |
| 55210 | PAM08 `PAM08(y4)_L` | 15 | 45199, 45434, 45460, 45950, 46497, 47101, 47988, 48337, 48596, 48759, 49544, 49867, 50411, 50591, 50820 |

- Exact minimum within that roster: **3 DANs**, covering **32/32** KCs. Their union also covers the six L2 target-region eligible KCs listed above.
- The expanded scan over all annotated DANs found 72 bodies with known strict γ4 overlap and a known union of 32/32, with the same observed three-body cover. However, 15 ROI chunks were unavailable for 35 broader-scan candidate edges (a queried chunk returned HTTP 404 from the pinned volume endpoint). Therefore the global all-DAN optimum is **inconclusive**; the exact three-body minimum is established only for the complete 25-body PAM08 roster.
- Anatomy establishes compartmental contact overlap only. It does not establish DAN release, dopamine diffusion, receptor function, or a multi-DAN learning effect. No combined-DAN capacity response was evaluated.

## Receipts

- Capacity maps and edge lists: `runs/malecns_max_plasticity_capacity_audit_v1/result.json`.
- Anatomy coverage details: `docs/figures/l3_gamma4_dan_cohort_coverage_audit.json`.
- Reproducible read-only scan: `scripts/audit_l3_gamma4_dan_coverage.py`.
- Frozen inputs: `configs/malecns_continuous_position_learning_v2_5.json`, corrected-floor Level 2 and Level 3 run receipts. No config or prior result was changed.
