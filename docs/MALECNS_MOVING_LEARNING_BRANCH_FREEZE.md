# MaleCNS moving-learning branch freeze

**Date:** 2026-10-03  
**Branch status:** **Mechanistic success / behavioral robustness incomplete.**  
**Freeze point:** Level 4D is the end of this moving-learning development branch. No further Level 4 tuning or learning runs are authorized by this record.

## 1. Demonstrated mechanisms

- The anatomy-selected PAM08 ensemble (DANs 87177, 107285, 55210) was stimulated during moving-note trials and produced recorded DAN spikes.
- A KC→MBON05 weight changed only when current-note KC eligibility was present and at least one anatomically connected DAN was active. The 50 ms eligibility window excluded earlier same-note KC spikes; the immutable 20% original-weight floor held.
- Matched DAN-on/plasticity-off trials made no weight changes. After training, evaluation with DAN and plasticity off retained the trained weights and the wrong-region action.
- The output gate waited for a nonzero MBON05 response. No external trained decoder was used.

These are results of the implemented, connectome-constrained model and its logged controls; they do not establish that the same plasticity rule or timing occurs in the fly.

## 2. Engineering assumptions

- A one-dimensional moving position (x=1→0 over 500 ms) is the sensory input, encoded by the fixed Gaussian KC encoder.
- LIF/contact dynamics and contact-to-voltage scaling are model choices. They are not calibrated measurements of this animal's membrane voltages.
- External events set teaching time. DAN stimulation amplitude/duration, the DAN-spike gate, local eligibility trace and its 50 ms cutoff, LTD update, η=0.00005, and weight floor form an engineered plasticity implementation.
- The inherited MBON05 threshold (0.005572335995331903 mV-equivalent), 0.05-position-bin maximum readout, and validity gate define the action interface. Level 4D logs an action event but no physical keyboard key code, osu! timing judgment, or biological motor output.

## 3. Successful behaviors

- Wrong-region teaching produced a first action at **x=0.20**. It remained present on a fresh moving-note evaluation with DAN and plasticity off.
- The naive baseline produced no action.
- The target-timed DAN-on/plasticity-off control retained unchanged weights and produced no action.
- Anatomical gating, eligibility locality, floor enforcement, and frozen evaluation checks passed.

## 4. Failed robustness criteria

- Target teaching did not produce the required first action near **x≈0.70**.
- The frozen strict target/wrong contract therefore remains **FAIL** overall, despite the wrong-region result and passing controls.
- The result establishes behavior for this fixed model and protocol. Robust target acquisition across repeated runs, broader inputs, and biological contexts was not demonstrated.

## 5. Strongest honest MVP claim

A 32-KC→MBON05 MaleCNS connectome-constrained fixture, gated by an anatomy-selected three-cell PAM08 ensemble, can learn and retain a wrong-region-localized first action at x=0.20 during a fixed one-dimensional moving-note task, while the naive and matched plasticity-off controls remain action-free. It failed to acquire the target action near x=0.70, so behavioral robustness is incomplete; this is a mechanistic learning demonstration, not a validated fly motor-learning model.

## Frozen evidence

- [Level 4D protocol](MALECNS_LEVEL4D_FINAL_REPAIR_PROTOCOL.md)
- [Level 4D result](MALECNS_LEVEL4D_FINAL_REPAIR_RESULT.md)
- [Frozen Level 4D config](../configs/malecns_level4d_final_moving_note_repair.json)
- [Level 4D receipt](../runs/malecns_level4d_final_moving_note_repair/result.json)
