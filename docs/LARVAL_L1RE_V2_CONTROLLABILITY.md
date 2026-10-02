# L1R-E v2 spiking-family refinement result

**Date:** 2026-10-02  
**Decision:** **FAIL under the frozen family-level robustness gate**  
**Scope:** outcome-informed **ENGINEERING REFINEMENT**, not biological calibration

## Purpose

L1R-E v1 produced only two qualifiers at the maximum tested contact effect. At the user's direction, v2 tested the smallest spiking-model continuation before considering continuous or rate-based alternatives.

The measured 88-row / 437-contact KC→MBON-m1 anatomy, eight current-position KC groups, fixed inverse action interface, artificial-teacher boundary, and local candidate weight locus were preserved. Teaching, plasticity, training, reward, and exploration remained disabled.

## Frozen v2 changes

The v2 policy was written before the first v2 circuit response was generated:

- policy: `configs/larval_l1re_electrical_family_v2_policy.json`
- policy SHA-256: `A7497E9C25AA9313891A55D0E75FCEFFAE1E7DDCFC19812BD2E65FDA45F8E4B8`
- v1 predecessor result SHA-256: `509ADF1C06E30B22C4E823C0649F5552A3347A4889DFDC704F571727AB700FCA`
- contact effects: `[0.275, 0.4, 0.6, 0.9]` mV-equivalent/contact;
- fixed KC parameters: τm 10 ms, threshold 1, zero tonic drive, and pulses `[12, 16]` for 5 ms;
- separate MBON parameters: τm `[10, 20]` ms, thresholds `[0.5, 0.75, 1.0, 1.5]`, and zero tonic drive;
- response windows: `[100, 150]` ms;
- unchanged fixed action overlays: bilateral MBON-m1 spike count `≤0`, `≤1`, or `≤2`;
- unchanged weight interventions: `[1.0, 0.8, 0.6, 0.4, 0.2]`;
- unchanged family requirements: at least 12 qualifiers, coverage of at least two values on every axis, largest face-connected component at least 8, and at least 6 component members robust at an adjacent action threshold.

The family contained 128 configurations. Parameter separation and expanded ranges are explicit engineering choices informed by v1 behavior; they are not measured larval electrical values.

## Execution

- runner: `scripts/run_larval_l1re_controllability_family_v2.py`
- raw result: `runs/larval_l1re_controllability_family_v2.json`
- result SHA-256: `E41D414E11A5C7EAB3A6E743D7E68B7E8CDBA4FBA7C7C594C709BAFE93FC6C1A`
- raw result size: 12,548,256 bytes

The 128 × 5 × 8 design produced 5,120 condition cells, each executed twice for 10,240 driven simulations. Including one zero-drive baseline per configuration, v2 executed 10,368 simulations.

All 128 configurations passed the following checks:

- silent, disarmed, finite zero-drive baseline;
- every intended KC activated for every cue;
- exact deterministic replay for every condition cell;
- finite state and bounded event queues;
- full-weight MBON activity in at least six states;
- at least 30% MBON reduction at factor 0.2 in at least six states;
- monotonic response in at least seven states;
- no reversal larger than one spike.

The only per-configuration discriminator was the predeclared fixed-action transition rule. Forty-eight configurations passed it.

## Family result

| Requirement | Observed | Decision |
|---|---:|---:|
| Qualifying configurations | 48 / 128; required ≥12 | PASS |
| At least two values on all five axes | All axes covered | PASS |
| Largest face-connected component | 4; required ≥8 | **FAIL** |
| Adjacent-threshold-robust members in largest component | 4; required ≥6 | **FAIL** |

The 48 qualifiers form 12 disconnected components of four members each. Within each component, both KC pulse values and both response windows qualify. No component connects to an adjacent qualifying contact-effect, MBON-τm, or MBON-threshold coordinate. This means the working responses remain structurally brittle even though qualifiers are numerous and collectively span the complete family.

The lexicographically first largest component uses contact effect 0.275, MBON τm 10 ms, and MBON threshold 0.5. Its four pulse/window combinations all qualify at adjacent action thresholds 1 and 2. It is reported descriptively; it was not promoted to a nominal model because the family gate failed.

## Decision and stop

L1R-E v2 **FAILS** its frozen family-level gate. No `configs/larval_l1re_electrical_v2.json` was created. Plasticity and learning remain blocked.

This is substantially closer than v1, but passing isolated points or four-member pulse/window sheets is insufficient under the existing robustness standard. A v3 continuation would need a separately frozen, denser contact-effect/MBON-threshold grid to determine whether the islands are separated by coarse sampling or reflect genuine spike/action discontinuities. That new run may not retroactively change this decision.

Nineteen existing LIF, sparse-graph, and spiking-network unit tests passed after the run.

