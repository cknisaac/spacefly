# MaleCNS Level 2 v2.5 — corrected original-weight floor

## Run identity

- Result: **FAIL** under the existing frozen contract.
- Config: `configs/malecns_continuous_position_learning_v2_5.json` (SHA-256 `e81a9da42f28be4ad288f8f416a8186b2443230c012d1563bc827c3f0c8b5485`).
- Action threshold: `0.00557233599533` mV-equivalent.
- Corrected semantics: every LocalLTD presentation receives the current weights plus an immutable copy of the arm’s run-start weights; all lower bounds use `0.20 × original_weight`.
- Eligibility still resets at each presentation. No model or protocol parameter changed.
- Historical result files were preserved; this is a new corrected-floor result.

## Contract criteria

| Criterion | Result |
|---|---|
| `all_120_blocks_and_1200_presentations_run_in_every_arm` | PASS |
| `target_teaching_creates_action_core_at_0_65_to_0_75` | FAIL |
| `wrong_region_teaching_creates_action_core_at_0_15_to_0_25` | PASS |
| `wrong_region_teaching_shifts_away_from_target_core` | PASS |
| `plasticity_off_weights_and_map_are_unchanged` | PASS |
| `plasticity_off_remains_no_action` | PASS |
| `target_teacher_actions_local_to_target_halo` | PASS |
| `wrong_region_teacher_actions_local_to_wrong_halo` | PASS |
| `target_learned_region_persists_frozen` | FAIL |
| `wrong_region_learned_region_persists_frozen` | PASS |
| `inherited_threshold_is_fixed_on_all_evaluations` | PASS |
| `encoder_and_fixed_readout_preserved` | PASS |
| `circuit_and_learning_parameters_unchanged_from_v2_3` | PASS |

## Controls and floor hits

| Arm | Weight changes | Floor hits | Action positions | Controls / checks |
|---|---:|---:|---|---|
| Target teacher | 6 | 3 | 0.7, 0.75 | 120 blocks / 1200 presentations |
| Plasticity-off | 0 | 0 | none | 120 blocks / 1200 presentations; weights unchanged, no-action baseline retained |
| Wrong-region teacher | 6 | 2 | 0.15, 0.2, 0.25, 0.3 | 120 blocks / 1200 presentations |

## Changed weights

### Target teacher

Changed weights: **6**.
| KC source ID | Original | Final | Change |
|---:|---:|---:|---:|
| 49160 | 0.0321167883212 | 0.0263979855987 | -0.00571880272247 |
| 49526 | 0.0277372262774 | 0.0105556647848 | -0.0171815614925 |
| 49544 | 0.0262773722628 | 0.00525547445255 | -0.0210218978102 |
| 49545 | 0.0379562043796 | 0.00759124087591 | -0.0303649635036 |
| 49867 | 0.029197080292 | 0.00583941605839 | -0.0233576642336 |
| 50411 | 0.0335766423358 | 0.0220097300832 | -0.0115669122526 |

Floor hits (final weights at the original 20% floor): **3** — 49544, 49545, 49867.

### Plasticity-off control

Changed weights: **0**.

Floor hits (final weights at the original 20% floor): **0** — none.

### Wrong-region teacher

Changed weights: **6**.
| KC source ID | Original | Final | Change |
|---:|---:|---:|---:|
| 45460 | 0.0379562043796 | 0.0148921731553 | -0.0230640312242 |
| 45467 | 0.0248175182482 | 0.00496350364964 | -0.0198540145985 |
| 45620 | 0.0335766423358 | 0.0104862901513 | -0.0230903521844 |
| 45950 | 0.0175182481752 | 0.00350364963504 | -0.0140145985401 |
| 46497 | 0.0394160583942 | 0.0164562794555 | -0.0229597789387 |
| 47101 | 0.0262773722628 | 0.0147709348959 | -0.0115064373669 |

Floor hits (final weights at the original 20% floor): **2** — 45467, 45950.

## Final position → MBON/action maps

MBON values are maximum membrane voltages during the inherited fixed observation window; action is evaluated with the frozen threshold.

| Position | Target MBON (mV / action) | Plasticity-off MBON (mV / action) | Wrong-region MBON (mV / action) |
|---:|---:|---:|---:|
| 0 | 0.00801057912815 / no-action | 0.00801057912815 / no-action | 0.00801057912815 / no-action |
| 0.05 | 0.0142156099691 / no-action | 0.0142156099691 / no-action | 0.0142156099691 / no-action |
| 0.1 | 0.0158605655989 / no-action | 0.0158605655989 / no-action | 0.0123645651486 / no-action |
| 0.15 | 0.0150566649894 / no-action | 0.0150566649894 / no-action | 0.00474122898841 / action |
| 0.2 | 0.0093100050507 / no-action | 0.0093100050507 / no-action | 0.00253042474792 / action |
| 0.25 | 0.0111812162878 / no-action | 0.0111812162878 / no-action | 0.00465618731273 / action |
| 0.3 | 0.00962270261152 / no-action | 0.00962270261152 / no-action | 0.00474413057179 / action |
| 0.35 | 0.00994553671418 / no-action | 0.00994553671418 / no-action | 0.00994553671418 / no-action |
| 0.4 | 0.0168400306739 / no-action | 0.0168400306739 / no-action | 0.0168400306739 / no-action |
| 0.45 | 0.011751978448 / no-action | 0.011751978448 / no-action | 0.011751978448 / no-action |
| 0.5 | 0.014575050997 / no-action | 0.014575050997 / no-action | 0.014575050997 / no-action |
| 0.55 | 0.0150850337292 / no-action | 0.0150850337292 / no-action | 0.0150850337292 / no-action |
| 0.6 | 0.012721157821 / no-action | 0.0163511099887 / no-action | 0.0163511099887 / no-action |
| 0.65 | 0.00584291604003 / no-action | 0.0113719902889 / no-action | 0.0113719902889 / no-action |
| 0.7 | 0.00271931792892 / action | 0.0135965896446 / no-action | 0.0135965896446 / no-action |
| 0.75 | 0.00527817621054 / action | 0.0128642671033 / no-action | 0.0128642671033 / no-action |
| 0.8 | 0.0116919652369 / no-action | 0.0135365203311 / no-action | 0.0135365203311 / no-action |
| 0.85 | 0.0156704643126 / no-action | 0.0156704643126 / no-action | 0.0156704643126 / no-action |
| 0.9 | 0.0136653349983 / no-action | 0.0136653349983 / no-action | 0.0136653349983 / no-action |
| 0.95 | 0.0167721465734 / no-action | 0.0167721465734 / no-action | 0.0167721465734 / no-action |
| 1 | 0.00894078151155 / no-action | 0.00894078151155 / no-action | 0.00894078151155 / no-action |
