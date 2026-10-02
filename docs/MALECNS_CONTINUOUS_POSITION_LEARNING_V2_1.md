# MaleCNS continuous-position learning — Level 2 v2.1

**2026-10-02 · MALECNS-CONTINUOUS-POSITION-LEARNING-v2.1 · FAIL.** This is one frozen continuation of Level 2. It preserves the v1 circuit, encoder, initial contact normalization, LIF parameters, target/wrong regions, action threshold, LTD learning rate and weight floor. It changes only eligibility reset scope and training duration. The full 32-block run completed in all three arms; there was no early stopping or post-result parameter change.

## Frozen changes and retained settings

Every stimulus presentation starts with zero eligibility, updates eligibility only from that presentation's KC spikes, applies the arm's teacher pulse, then discards those traces. KC→MBON05 weights carry forward. This is implemented by creating a fresh Level 1 `LocalLTD` state per presentation with the carried weight vector.

The predeclared Level 1 sequence pattern was repeated for **32 blocks**. Each arm completed **320 presentations**; target-teacher and wrong-region arms each applied 160 pulses. The plasticity-off arm applied none. No run stopped early.

Fixed settings: the same **32 audited KCs**, MBON05 source ID **10495**, **685** audited plastic contact rows, source-order Gaussian encoder (σ **0.08**, peak drive **1.2 mV-equivalent**), contact-ratio initial weights, LIF/synaptic timing, primary region **[0.65, 0.75]**, wrong region **[0.15, 0.25]**, η **0.00005**, eligibility τ **1,000,000 µs** within each presentation, and 20% initial-weight floor. The threshold was inherited unchanged from the v1 PASS probe: **0.005572335995331903 mV-equivalent**.

The inherited pretraining probe remains tied by checksum to its v1 config and probe receipt; it was not recomputed or changed for v2.1. The frozen v2.1 config records both input hashes and the exact inherited threshold. The 32 KC IDs and the full fixed schedule are in that config.

## Result

All three arms completed all 32 blocks. In the target-teacher arm, **6/32** weights changed and none reached the floor. Target mean MBON05 response decreased from **0.012611** at baseline to **0.009613** after block 32, but remained above the fixed action threshold at every target grid point. Wrong-region teaching changed **6/32** weights, also without floor saturation. The plasticity-off control changed no weights and exactly retained the baseline map.

The final full-grid maps below show maximum MBON05 voltage and action with teacher and plasticity off. Every value is in mV-equivalent; `No` means above the fixed threshold.

| Current x | Baseline | Target teacher | Plasticity off | Wrong-region teacher |
|---:|---:|---:|---:|---:|
| 0.00 | 0.008011 / No | 0.008011 / No | 0.008011 / No | 0.008011 / No |
| 0.05 | 0.014216 / No | 0.014216 / No | 0.014216 / No | 0.014216 / No |
| 0.10 | 0.015861 / No | 0.015861 / No | 0.015861 / No | 0.014921 / No |
| 0.15 | 0.015057 / No | 0.015057 / No | 0.015057 / No | 0.011885 / No |
| 0.20 | 0.009310 / No | 0.009310 / No | 0.009310 / No | 0.006931 / No |
| 0.25 | 0.011181 / No | 0.011181 / No | 0.011181 / No | 0.008816 / No |
| 0.30 | 0.009623 / No | 0.009623 / No | 0.009623 / No | 0.008322 / No |
| 0.35 | 0.009946 / No | 0.009946 / No | 0.009946 / No | 0.009946 / No |
| 0.40 | 0.016840 / No | 0.016840 / No | 0.016840 / No | 0.016840 / No |
| 0.45 | 0.011752 / No | 0.011752 / No | 0.011752 / No | 0.011752 / No |
| 0.50 | 0.014575 / No | 0.014575 / No | 0.014575 / No | 0.014575 / No |
| 0.55 | 0.015085 / No | 0.015085 / No | 0.015085 / No | 0.015085 / No |
| 0.60 | 0.016351 / No | 0.015370 / No | 0.016351 / No | 0.016351 / No |
| 0.65 | 0.011372 / No | 0.009149 / No | 0.011372 / No | 0.011372 / No |
| 0.70 | 0.013597 / No | 0.009269 / No | 0.013597 / No | 0.013597 / No |
| 0.75 | 0.012864 / No | 0.010420 / No | 0.012864 / No | 0.012864 / No |
| 0.80 | 0.013537 / No | 0.013030 / No | 0.013537 / No | 0.013537 / No |
| 0.85 | 0.015671 / No | 0.015671 / No | 0.015671 / No | 0.015671 / No |
| 0.90 | 0.013665 / No | 0.013665 / No | 0.013665 / No | 0.013665 / No |
| 0.95 | 0.016772 / No | 0.016772 / No | 0.016772 / No | 0.016772 / No |
| 1.00 | 0.008941 / No | 0.008941 / No | 0.008941 / No | 0.008941 / No |

## Predeclared decision

**PASS criteria not met; v2.1 is FAIL.** The primary arm did not create an action region near 0.65–0.75. The wrong-region arm did not shift the learned response into 0.15–0.25; its minimum there was 0.006931, still above threshold. The plasticity-off control remained unchanged. Evaluation retained weights while teacher and plasticity were off, but no learned action region existed to retain. Distant positions were all no-action (12/12), and fixed settings plus internal-weight-only adaptation were preserved.

The sequence-local reset resolves the documented eligibility carry-over mechanism from v1: no trace survives a presentation boundary. It does not make the chosen η and fixed 32-block schedule strong enough to cross the inherited readout threshold. This is a result of this frozen engineering fixture, not evidence against fly learning. MBON05 remains a subthreshold voltage proxy here; the Gaussian preferred positions, contact normalization, LIF effects, local artificial teacher, LTD rule/rate, and threshold are engineering assumptions.

## Reproduction and stop

- [Frozen v2.1 config and complete 32-block sequence](../configs/malecns_continuous_position_learning_v2_1.json)
- [Full results, per-presentation eligibility/weight logs, 32 block maps, and final maps](../runs/malecns_continuous_position_learning_v2_1/result.json)
- [Presentation-local implementation](../src/project_b/malecns_continuous_position_learning/experiment_v2_1.py)
- [v2.1 protocol tests](../tests/test_malecns_continuous_position_learning_v2_1.py)

The v1 report/config/result and Level 1 artifacts remain unchanged. **Stopped after this v2.1 run as requested; no tuning, new threshold, alternate schedule, or further stage was run.**
