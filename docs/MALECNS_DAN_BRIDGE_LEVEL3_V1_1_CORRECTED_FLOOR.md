# MaleCNS Level 3 v1.1 — corrected original-weight floor

## Run identity

- Result: **FAIL** under the existing frozen contract.
- Config: `configs/malecns_dan_bridge_level3_v1_1.json` (SHA-256 `647414cb059a3b01d93a55ddd7ab56112b3fde48bc5ce6df4be40b116e3425f6`).
- Action threshold: `0.00557233599533` mV-equivalent.
- Corrected semantics: every LocalLTD presentation receives the current weights plus an immutable copy of the arm’s run-start weights; all lower bounds use `0.20 × original_weight`.
- Eligibility still resets at each presentation. No model or protocol parameter changed.
- Historical result files were preserved; this is a new corrected-floor result.

## Contract criteria

| Criterion | Result |
|---|---|
| `all_120_blocks_and_1200_presentations_completed` | PASS |
| `all_scheduled_events_activated_real_dan` | PASS |
| `no_off_arm_dan_events` | PASS |
| `target_core_3_of_3_action` | FAIL |
| `wrong_core_3_of_3_action` | FAIL |
| `wrong_region_shift_away_from_target` | PASS |
| `plasticity_off_unchanged_and_no_action` | PASS |
| `target_action_locality` | PASS |
| `wrong_action_locality` | PASS |
| `target_frozen_retention` | FAIL |
| `wrong_frozen_retention` | FAIL |
| `no_update_without_dan_spike` | PASS |
| `all_updates_anatomically_reached` | PASS |
| `fixed_threshold_encoder_and_level2_parameters` | PASS |

## Controls and floor hits

| Arm | Weight changes | Floor hits | Action positions | Controls / checks |
|---|---:|---:|---|---|
| Target teacher | 4 | 2 | none | 600 scheduled DAN stimulations; 600 DAN gate events |
| Plasticity-off | 0 | 0 | none | 0 scheduled DAN stimulations; 0 DAN gate events; weights unchanged, no-action baseline retained |
| Wrong-region teacher | 3 | 0 | none | 600 scheduled DAN stimulations; 600 DAN gate events |

## Changed weights

### Target teacher

Changed weights: **4**.
| KC source ID | Original | Final | Change |
|---:|---:|---:|---:|
| 49160 | 0.0321167883212 | 0.0264774910004 | -0.00563929732075 |
| 49544 | 0.0262773722628 | 0.00525547445255 | -0.0210218978102 |
| 49867 | 0.029197080292 | 0.00583941605839 | -0.0233576642336 |
| 50411 | 0.0335766423358 | 0.0221705385688 | -0.011406103767 |

Floor hits (final weights at the original 20% floor): **2** — 49544, 49867.

### Plasticity-off control

Changed weights: **0**.

Floor hits (final weights at the original 20% floor): **0** — none.

### Wrong-region teacher

Changed weights: **3**.
| KC source ID | Original | Final | Change |
|---:|---:|---:|---:|
| 45460 | 0.0379562043796 | 0.0152128198286 | -0.022743384551 |
| 45620 | 0.0335766423358 | 0.0108073027505 | -0.0227693395852 |
| 47101 | 0.0262773722628 | 0.0149309026321 | -0.0113464696307 |

Floor hits (final weights at the original 20% floor): **0** — none.

## Final position → MBON/action maps

MBON values are maximum membrane voltages during the inherited fixed observation window; action is evaluated with the frozen threshold.

| Position | Target MBON (mV / action) | Plasticity-off MBON (mV / action) | Wrong-region MBON (mV / action) |
|---:|---:|---:|---:|
| 0 | 0.00801057912815 / no-action | 0.00801057912815 / no-action | 0.00801057912815 / no-action |
| 0.05 | 0.0142156099691 / no-action | 0.0142156099691 / no-action | 0.0142156099691 / no-action |
| 0.1 | 0.0158605655989 / no-action | 0.0158605655989 / no-action | 0.0124124240372 / no-action |
| 0.15 | 0.0150566649894 / no-action | 0.0150566649894 / no-action | 0.00841444321883 / no-action |
| 0.2 | 0.0093100050507 / no-action | 0.0093100050507 / no-action | 0.00679271490979 / no-action |
| 0.25 | 0.0111812162878 / no-action | 0.0111812162878 / no-action | 0.0103861368491 / no-action |
| 0.3 | 0.00962270261152 / no-action | 0.00962270261152 / no-action | 0.00766354575843 / no-action |
| 0.35 | 0.00994553671418 / no-action | 0.00994553671418 / no-action | 0.00994553671418 / no-action |
| 0.4 | 0.0168400306739 / no-action | 0.0168400306739 / no-action | 0.0168400306739 / no-action |
| 0.45 | 0.011751978448 / no-action | 0.011751978448 / no-action | 0.011751978448 / no-action |
| 0.5 | 0.014575050997 / no-action | 0.014575050997 / no-action | 0.014575050997 / no-action |
| 0.55 | 0.0150850337292 / no-action | 0.0150850337292 / no-action | 0.0150850337292 / no-action |
| 0.6 | 0.0153111578176 / no-action | 0.0163511099887 / no-action | 0.0163511099887 / no-action |
| 0.65 | 0.00759337716922 / no-action | 0.0113719902889 / no-action | 0.0113719902889 / no-action |
| 0.7 | 0.00824470389423 / no-action | 0.0135965896446 / no-action | 0.0135965896446 / no-action |
| 0.75 | 0.00842354542555 / no-action | 0.0128642671033 / no-action | 0.0128642671033 / no-action |
| 0.8 | 0.0117163888256 / no-action | 0.0135365203311 / no-action | 0.0135365203311 / no-action |
| 0.85 | 0.0156704643126 / no-action | 0.0156704643126 / no-action | 0.0156704643126 / no-action |
| 0.9 | 0.0136653349983 / no-action | 0.0136653349983 / no-action | 0.0136653349983 / no-action |
| 0.95 | 0.0167721465734 / no-action | 0.0167721465734 / no-action | 0.0167721465734 / no-action |
| 1 | 0.00894078151155 / no-action | 0.00894078151155 / no-action | 0.00894078151155 / no-action |
