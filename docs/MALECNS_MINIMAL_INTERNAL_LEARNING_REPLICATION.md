# MaleCNS minimal internal-learning replication

**2026-10-02 · MALECNS-MINIMAL-INTERNAL-LEARNING-REPLICATION-v1 · PASS for the reduced engineering fixture.** This is one outcome-blind replication of the original isolated MaleCNS-v1 run. It does not modify the original config, probe, result, or Branch A/B evidence.

## Frozen design

The new config was frozen before running the replication. It selects the next eight KC entries in the pinned B2 runtime-mask source order (rows 9–16, one-based), assigning the first four to STATE_A and the next four to STATE_B. The selection is independent of response outcomes. The selected source IDs are:

| State | KC source IDs | Audited plastic contacts |
|---|---|---:|
| A | 41920, 42140, 42744, 43354 | 90 |
| B | 43639, 43811, 44260, 44682 | 69 |

This gives eight aggregate KC→MBON05 edges and 159 audited plastic contact rows. The original MBON source ID (10495), encoder, LIF and synapse parameters, LTD parameters, three training repetitions, controls, observation window, and fixed threshold (**0.13266897755112178 mV-equivalent**) were retained. The threshold was copied from the original frozen config and was not selected or adjusted from replication responses. The recorded seed 31002 is a run identifier; no random draws are used.

## Pretraining gate

With plasticity off, STATE_A MBON maximum voltage decreased strictly with the declared multipliers. The unchanged threshold separated the 0.8 response (0.151622, no action) from the 0.6 response (0.113716, action). The gate **PASS**ed; deterministic replay and checkpoint continuation matched exactly across all ten state-by-multiplier probe rows. Training proceeded only after this gate passed.

## Learning result and controls

| Arm | STATE_A MBON activity / action | STATE_B MBON activity / action |
|---|---|---|
| Before training | 0.189527 / No | 0.189527 / No |
| STATE_A teacher training | 0.037905 / Yes | 0.189527 / No |
| Plasticity-off training | 0.189527 / No | 0.189527 / No |
| Wrong-state teacher (STATE_B) | 0.189527 / No | 0.037905 / Yes |

All four STATE_A weights reached their declared 20% floor; all four STATE_B weights remained unchanged in the primary STATE_A teaching arm. All nine predeclared criteria passed, including localized weight change, selective test response, plasticity-off control, wrong-state teacher control, fixed threshold, and no trainable external decoder.

## Interpretation and limits

The independent partition reproduces the original fixture's narrow engineering result: under the same fixed artificial encoder, contact-ratio voltage normalization, teacher-gated LTD, and threshold readout, the selected internal KC→MBON05 weights store a two-state association. The replication reduces the chance that the first result depended on its particular eight-KC partition.

It remains an engineering proof, not evidence that adult flies use this exact KC→MBON05 plasticity, voltage scale, encoder, teacher, readout, or behavior. The probe has subthreshold MBON voltage and no MBON spikes. This one deterministic replication does not estimate biological or across-seed reliability.

## Reproduction files

- [Frozen replication config](../configs/malecns_minimal_internal_learning_replication.json)
- [Pretraining controllability result](../runs/malecns_minimal_internal_learning_replication/controllability.json)
- [Training and matched controls](../runs/malecns_minimal_internal_learning_replication/result.json)
- [Replication tests](../tests/test_malecns_minimal_internal_learning_replication.py)

Verification: the targeted original-plus-replication suite passed **9/9 tests**. The full repository unittest suite passed **163/163 tests in 64.127 seconds** using the repository `.venv` and `PYTHONPATH=src`.

The original run remains documented at [the original experiment report](MALECNS_MINIMAL_INTERNAL_LEARNING.md), with its outputs under `runs/malecns_minimal_internal_learning/`.

## Disposition and sole next proposal

**Replication status: PASS.** No tuning, alternate partition, or further training run was performed.

**Proposed next stage: MaleCNS assumption-evidence review (document-only).**

- **Question:** Which of the current artificial encoder, teaching signal, and KC→MBON05 plasticity-locus assumptions has direct evidence that could support a narrower biological model?
- **Why next:** The engineering behavior repeated across two fixed partitions, while all three elements remain assumptions and dominate the biological interpretation.
- **Possible outcomes:** Evidence supports a specific element and justifies a separately frozen future design; evidence is indirect and the assumption remains labeled; or evidence is absent and the current engineering fixture remains the appropriate claim boundary.
- **Intervention and controls:** Read-only review of existing pinned primary sources and project anatomy; preserve the two configs/results and do not change circuitry or model parameters.
- **Primary endpoint:** An evidence table mapping each assumption to direct, indirect, or absent support and the exact claim each source permits.
- **Secondary endpoints:** Provenance links, cell/compartment alignment, developmental-stage alignment, and unresolved uncertainties.
- **Pass/interpretation:** Review is complete only if every assumption has a sourced support grade and no source is used to claim more than its experimental context allows; unsupported items stay ENGINEERING ASSUMPTIONS.
- **Do not:** Run simulation/training, choose another partition, tune the threshold/rule, infer dopamine function from historical overlap, or expand to visual/motor circuits.
- **Output:** A short evidence review linked from `ASSUMPTIONS.md`, plus any necessary correction to claim wording in `docs/BIOLOGY.md` and `docs/MODEL.md`.
- **Stop condition:** Stop after the document review; any new experiment requires a separate request and a new frozen protocol.
