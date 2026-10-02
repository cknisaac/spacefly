# MaleCNS continuous-position learning — Level 2

**2026-10-02 · MALECNS-CONTINUOUS-POSITION-LEARNING-v1 · overall FAIL under the frozen criteria.** Level 1 and the historical Branch A/B artifacts remain unchanged. Level 2 was implemented as an isolated experiment, its pretraining controllability gate passed, and one frozen training run with matched controls completed. The learning gate failed; no threshold, encoder, schedule, or learning parameter was changed afterward.

## 1. Circuit and fixed position encoder

MBON05 is source ID **10495**. The experiment selected the next 32 eligible KCs in source order (runtime-mask rows 17–48, one-based) after the 16 KCs used by Level 1 and its replication. Selection did not use activity or learning outcomes. The 32 KC IDs are:

`45199, 45259, 45380, 45434, 45460, 45467, 45620, 45950, 46497, 47101, 47117, 47287, 47694, 47758, 47988, 48337, 48596, 48759, 49124, 49160, 49526, 49544, 49545, 49867, 50411, 50568, 50591, 50791, 50820, 51053, 51055, 51330`.

These are 32 audited KC→MBON05 pairs containing **685 audited plastic contact rows**. One aggregate edge represents only each pair's pinned plastic contact rows. Starting weights equal each KC's audited contact count divided by 685. This contact-ratio voltage normalization is an engineering overlay, not a measured synaptic calibration.

For current position `x ∈ [0,1]`, each fixed KC receives external drive

`drive_i(x) = 1.2 mV-equivalent × exp(-0.5 × ((x - μ_i) / 0.08)^2)`

where preferred positions `μ_i` are the source-order ranks `i/31`. This is a fixed, overlapping, source-order code. Preferred positions are not measured anatomy. No future note timestamp, countdown, target label, future position, desired action time, or learned encoder enters this function. The complete activation audit across the 0.05-spaced grid is in the probe JSON.

## 2. Frozen pretraining response and controllability

The fixed evaluation grid is `0.00, 0.05, …, 1.00`; plasticity and teacher are off. Before training, every grid point produced no action. Baseline MBON05 maximum voltages ranged from **0.008011** to **0.016840 mV-equivalent**:

| x | MBON voltage | Action | x | MBON voltage | Action | x | MBON voltage | Action |
|---:|---:|:---:|---:|---:|:---:|---:|---:|:---:|
| 0.00 | 0.008011 | No | 0.35 | 0.009946 | No | 0.70 | 0.013597 | No |
| 0.05 | 0.014216 | No | 0.40 | 0.016840 | No | 0.75 | 0.012864 | No |
| 0.10 | 0.015861 | No | 0.45 | 0.011752 | No | 0.80 | 0.013537 | No |
| 0.15 | 0.015057 | No | 0.50 | 0.014575 | No | 0.85 | 0.015671 | No |
| 0.20 | 0.009310 | No | 0.55 | 0.015085 | No | 0.90 | 0.013665 | No |
| 0.25 | 0.011181 | No | 0.60 | 0.016351 | No | 0.95 | 0.016772 | No |
| 0.30 | 0.009623 | No | 0.65 | 0.011372 | No | 1.00 | 0.008941 | No |

The frozen task-independent controllability probe weakened by a fixed factor of 0.20 only the KCs whose preferred positions fell within ±0.10 of each of three predeclared probe centers (`0.20`, `0.50`, `0.80`). It tested local positions within ±0.05 and distant positions at least 0.20 away. The largest local weakened response was **0.003134**; the smallest distant baseline response was **0.008011**. Their midpoint froze the action threshold at **0.005572335995331903 mV-equivalent**. At all three probe regions, local responses crossed the threshold and distant positions stayed no-action. The gate also passed matched-response reduction and deterministic checkpoint/grid replay. **Pretraining controllability: PASS.**

## 3. Frozen target, learning rule, and training sequence

Primary target position region: **[0.65, 0.75]**. Wrong-teaching control region: **[0.15, 0.25]**. The fixed action rule is ACTION when MBON05 maximum voltage is at or below the probe-frozen threshold. The threshold remained unchanged in every evaluation.

The Level 1 local eligibility LTD implementation was reused without editing it: KC spikes add to local eligibility, eligibility decays exponentially with τ = **1,000,000 µs**, and an artificial teacher pulse depresses only eligible aggregate KC→MBON05 edges as `w_i = max(0.2 × w_i_initial, w_i - η e_i)`. The frozen Level 2 learning step is **η = 0.00005**. Training used eight blocks, each containing five fixed target positions (`0.65, 0.70, 0.75, 0.68, 0.72`) interleaved with five fixed wrong-region distractors (`0.15, 0.20, 0.25, 0.15, 0.25`). The sequence was saved before the run. The primary arm taught only target-region presentations; the plasticity-off arm had no teacher; the wrong-region arm taught only distractor presentations. Each block ended with the full grid evaluated with teacher and plasticity off.

One initial training invocation aborted before training because the human-readable policy descriptions in the config were not valid runner enum values. Those config labels were made explicit, the same controllability probe was rerun and passed at the same numerical threshold, and the one training run was then executed. No training input or outcome was generated by the aborted invocation.

## 4. Learning curve and frozen maps

Primary-arm target mean activity declined each block, with no KC weight reaching its floor. However, the target action count stayed **0/3** through all eight blocks:

| Block | Mean target-region MBON activity | Target grid actions | Weights at LTD floor |
|---:|---:|---:|---:|
| 1 | 0.012428 | 0/3 | 0 |
| 2 | 0.012156 | 0/3 | 0 |
| 3 | 0.011871 | 0/3 | 0 |
| 4 | 0.011585 | 0/3 | 0 |
| 5 | 0.011301 | 0/3 | 0 |
| 6 | 0.011018 | 0/3 | 0 |
| 7 | 0.010735 | 0/3 | 0 |
| 8 | 0.010451 | 0/3 | 0 |

Final frozen response/action maps (teacher and plasticity off):

| x | Baseline | Primary target teacher | Plasticity off | Wrong-region teacher |
|---:|---:|---:|---:|---:|
| 0.00 | 0.008011 / No | 0.008011 / No | 0.008011 / No | 0.008011 / No |
| 0.05 | 0.014216 / No | 0.014216 / No | 0.014216 / No | 0.014216 / No |
| 0.10 | 0.015861 / No | 0.015302 / No | 0.015861 / No | 0.015179 / No |
| 0.15 | 0.015057 / No | 0.013165 / No | 0.015057 / No | 0.012747 / No |
| 0.20 | 0.009310 / No | 0.007826 / No | 0.009310 / No | 0.007535 / No |
| 0.25 | 0.011181 / No | 0.009688 / No | 0.011181 / No | 0.009360 / No |
| 0.30 | 0.009623 / No | 0.008872 / No | 0.009623 / No | 0.008706 / No |
| 0.35 | 0.009946 / No | 0.009946 / No | 0.009946 / No | 0.009946 / No |
| 0.40 | 0.016840 / No | 0.016840 / No | 0.016840 / No | 0.016840 / No |
| 0.45 | 0.011752 / No | 0.011752 / No | 0.011752 / No | 0.011752 / No |
| 0.50 | 0.014575 / No | 0.014575 / No | 0.014575 / No | 0.014575 / No |
| 0.55 | 0.015085 / No | 0.015085 / No | 0.015085 / No | 0.015085 / No |
| 0.60 | 0.016351 / No | 0.015630 / No | 0.016351 / No | 0.015770 / No |
| 0.65 | 0.011372 / No | 0.009750 / No | 0.011372 / No | 0.010072 / No |
| 0.70 | 0.013597 / No | 0.010491 / No | 0.013597 / No | 0.011123 / No |
| 0.75 | 0.012864 / No | 0.011113 / No | 0.012864 / No | 0.011471 / No |
| 0.80 | 0.013537 / No | 0.013169 / No | 0.013537 / No | 0.013242 / No |
| 0.85 | 0.015671 / No | 0.015671 / No | 0.015671 / No | 0.015671 / No |
| 0.90 | 0.013665 / No | 0.013665 / No | 0.013665 / No | 0.013665 / No |
| 0.95 | 0.016772 / No | 0.016772 / No | 0.016772 / No | 0.016772 / No |
| 1.00 | 0.008941 / No | 0.008941 / No | 0.008941 / No | 0.008941 / No |

Primary training changed **12 of 32** selected KC→MBON05 weights; no changed edge reached its floor. Activity at the two neighboring positions 0.60 and 0.80 fell by only **4.41%** and **2.72%**, below the predeclared 10% overlap criterion. All evaluated positions remained no-action. The plasticity-off control changed zero edges. Wrong-region teaching changed 12 edges and reduced activity around both regions, but produced no action in either region and did not shift the action region.

### Focused eligibility carry-over audit

Because the failed controls showed off-target changes, one focused agent audited only the saved ledger and implementation; it ran no simulations and changed no files or parameters. **Audit PASS:** immediately after an `x=0.15` wrong-region presentation, the first target teacher at `x=0.65` updated three KCs with preferred positions 0.129, 0.161, and 0.194. Those KCs emitted no spikes during the target trial, but retained eligibility values 1.573603, 1.566490, and 0.792154, respectively, after the expected `exp(-200,000/1,000,000)` decay; their weights changed by −7.868×10⁻⁵, −7.832×10⁻⁵, and −3.961×10⁻⁵ mV-equivalent. This confirms that the frozen one-second trace and 200-ms presentation spacing allow preceding non-target activity to receive a later target teacher. It explains a concrete localization leak and is consistent with the distant-position changes, but does not prove it caused every failed criterion or represent biological eligibility.

## 5. Gate decision and limits

**Level 2: FAIL.** The probe establishes that substantial local KC→MBON05 weight weakening can control this fixed MBON voltage threshold across three position regions. The frozen training schedule produced a gradual MBON response decrease, but not enough to create an action region. Neighbor generalization failed its magnitude criterion, distant responses changed in the primary arm, and wrong-region teaching did not create a shifted action region. The plasticity-off control remained unchanged and no-action. The encoder, threshold, and all learning updates stayed inside the fixed encoder, fixed threshold, and selected internal edges; there is no external trainable decoder.

The complete predeclared gate is in the result JSON. Important qualifications: MBON05 produced no spikes in this fixture; action is a subthreshold-voltage proxy. The Gaussian preferred-position assignment, voltage scale, contact normalization, LIF parameters, teacher, LTD rule/rate, and fixed threshold are engineering assumptions. The evidence concerns this one deterministic fixture, not adult fly learning or behavior.

**Strongest honest claim:** this frozen connectome-constrained simulation shows that a continuous Gaussian KC drive and local LTD can gradually lower subthreshold MBON05 responses near taught positions, but the declared training schedule did not store an actionable position region and wrong-region teaching did not shift one.

Targeted Level 2 protocol tests passed **3/3**. The full repository unittest suite passed **166/166 tests in 64.178 seconds** using the project `.venv` and `PYTHONPATH=src`. Tests validate encoder math, source-order/config integrity, and the saved pretraining PASS/learning FAIL receipt; the full suite did not rerun the frozen Level 2 training stage.

## 6. Reproduction and disposition

- [Frozen config and full sequence](../configs/malecns_continuous_position_learning_v1.json)
- [Pretraining probe, encoder audit, and threshold](../runs/malecns_continuous_position_learning_v1/controllability.json)
- [Training presentations, block curves, maps, controls, and criteria](../runs/malecns_continuous_position_learning_v1/result.json)
- [Level 2 implementation](../src/project_b/malecns_continuous_position_learning/)
- [Protocol integrity tests](../tests/test_malecns_continuous_position_learning.py)

Level 1 config and result artifacts were not modified. The Level 2 test suite and full repository tests are recorded in `CURRENT.md`. **Stop after Level 2 as requested. No parameter search, second training run, new pathway, or follow-on stage was performed.**
