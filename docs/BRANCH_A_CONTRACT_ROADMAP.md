# Branch A contract roadmap

> **Historical synthetic roadmap after the 2026-10-01 pivot.** Preserve the findings and old contract IDs below. The active [Branch A infrastructure roadmap](BRANCH_A_INFRASTRUCTURE_ROADMAP.md) has no synthetic performance gate; A11.3 is not the next active task. See [legacy status](LEGACY_SYNTHETIC_STATUS.md).

Status after [A11.1](A11_1_THRESHOLD_MARGIN_IDENTIFIABILITY.md): A11 and A11.1 are **INCONCLUSIVE** for signed perturbation → first-action timing. A10 remains **FAIL** for its centered-participation candidate. The original synthetic M2 gate remains **FAIL**. These contracts concern the synthetic fixture, not MaleCNS biology. A later contract cannot pass by bypassing a failed prerequisite.

```text
A-C1 action identity → A-C2 action eligibility → A-C3 signed credit
    → A-C4 local first-crossing control → A-C5 short retention
    → A-C6 development reliability → A-C7 fresh held-out M2
```

| Contract | Question and input → output contract | Primary endpoint and controls | PASS / FAIL / INCONCLUSIVE | Failure blocks |
| --- | --- | --- | --- | --- |
| A-C1 | Can a DOWN be associated with its visible note and exact causal neural/readout state? Input: timestamped game/readout events and local state. Output: immutable first-action record, including null, early MISS, hit or no DOWN. | Exact deterministic replay of first DOWN identity; independent game action replay and no future note information. | PASS: every selected action/absence agrees exactly. FAIL: wrong or missing identity. INCONCLUSIVE: unresolvable event ordering. | C2–C7. |
| A-C2 | Can first-action eligibility be retained without replacement by a later scored DOWN? Input: C1 record and selected-edge local trace at that tick. Output: one immutable per-note 480-slot vector through resolution. | Exact trace snapshot and later-action invariance; legacy trace and no-action controls. | PASS: snapshot matches causal trace and remains fixed. FAIL: leakage/replacement. INCONCLUSIVE: replay unavailable. | C3–C7. |
| A-C3 | Can a signed local credit vector and first-action reward be computed from available events? Input: C2 vector, causal motor participation, first-action disposition, saved predictor. Output: signed raw vector and clipped applied vector on selected slots only. | Both signs, no future scored-action substitution, zero trace/zero RPE tests; historical scalar update and no-update controls. | PASS: arithmetic, signs, bounds and event ordering audit exactly. FAIL: unavailable information, sign collapse or leakage. INCONCLUSIVE: all relevant entries zero. | C4–C7. |
| A-C4 | Does that vector move the first motor threshold crossing in the prespecified direction? Input: identical exact checkpoint and locked candidate vector. Output: three frozen branches and complete action traces. | First on-threshold rise; no update, historical update, identical notes/RNG/state and no probe learning. | PASS: all prespecified cases delay ≥5 ms relative to no update without silence/extra action switching. FAIL: any case advances ≥1 ms or silences. INCONCLUSIVE: no meaningful movement or mixed cases. | C5–C7. |
| A-C5 | Does a locally useful rule retain first-action behavior over a short unchanged continuation? Input: C4-passing rule and locked short sequence. Output: paired early/late frozen panels. | First-DOWN timing and retention, plus silence/extra actions; legacy/off/shuffled controls. | PASS: prespecified retention and noncollapse criterion met. FAIL: regression/collapse. INCONCLUSIVE: insufficient effect/uncertainty. Thresholds must be locked in its separate protocol. | C6–C7. |
| A-C6 | Is improvement reliable on locked development seeds/maps? Input: C5-passing implementation, fixed cohort. Output: per-seed paired results. | First-action timing and retained behavior; legacy, off, shuffled, identical maps/exploration, no score-only selection. | PASS: a separately locked reliability criterion with no null-first score dependence. FAIL: misses it. INCONCLUSIVE: incomplete or unauditable cohort. | C7. |
| A-C7 | Does the mechanism satisfy M2 on new untouched seeds? Input: frozen C6-passing code/config/seed policy. Output: complete audited held-out ledger. | Original ≥24/32 strict wins over both off and shuffled, ≤40-ms hit MAE, plus locked first-action criterion; no-learning frozen probes and independent audit. | PASS: every gate passes. FAIL: any gate fails. INCONCLUSIVE: invalid/missing audit. | M2 pass. |

## Fault tree

| Hypothesis | Discriminating observation | Contract/stage |
| --- | --- | --- |
| H1: first action cannot be causally identified | Action/replay mismatch before eligibility is considered | C1 / A10 |
| H2: action identified, but eligibility cannot be action-specific | Snapshot changes with later scored action or cannot be retained | C2 / A10 |
| H3: action-specific eligibility lacks usable sign information | Signed vector collapses, leaks future feedback, or moves crossing opposite prediction while C4 weight control remains possible | C3–C4 / A10; a later targeted sign experiment if needed |
| H4: credit adequate, but selected weights cannot usefully move first-action timing | Candidate vector is signed and correct yet matched crossing cannot move; structural A9 witness did move crossing, but not to a valid first action | C4 / A10, conditional structural reachability test |
| H5: local update works but successive ones destabilize it | C4 passes and C5 fails under fixed continuation | C5, only after A10 pass |
| H6: local and short continuation work but seed/map reliability fails | C4–C5 pass and C6/C7 fail | C6–C7, only after upstream passes |

A10 distinguishes H1/H2/H3 readiness from a local C4 effect. It cannot test H5/H6. A passed local displacement does not prove an unbiased reward gradient, useful long-run learning or fly biological validity. If A10 fails or is inconclusive, stop and specify one fault-tree experiment; if it passes, stop and request separate authorization for C5.

## Current contract position after A11

| Contract | Current evidence | Gate status |
| --- | --- | --- |
| A-C1 action identity | First DOWN and game disposition are exactly available in selected deterministic replay states. | Diagnostic feasibility shown; production interface unbuilt. |
| A-C2 action-specific eligibility | First-action trace can be captured and retained independently of later scored action in the diagnostic. | Diagnostic feasibility shown; production interface unbuilt. |
| A-C3 signed credit | A10 centered participation vanished at two synchronous states. A11 exogenous motor signs produced both positive and negative first-action tags in one fixed state. Whether those signs provide **useful timing credit** is unresolved. | **OPEN**; no validated learning rule. |
| A-C4 local timing control | A10 candidate delayed one crossing 48 ms but not two others. A11 signed/inverse pulse patterns drove different motor spikes but crossed the readout threshold on the same tick. Removing the pulse delayed crossing 66 ms. A11.1 reused the same pattern at a 5/10 pre-count, but even its no-pulse reference crossed on the next tick; all four branches crossed together. | **OPEN**; no signed local update gate pass. |
| A-C5 short retention | Requires a C3/C4-passing rule. | Not run. |
| A-C6 development reliability | Requires retained first-action behavior and matched controls. | Not run. |
| A-C7 fresh held-out M2 | Original gate failed; fresh seeds remain untouched for a future locked rule. | Not run; M2 **NO**. |

One proposed next stage is **A11.2 perturbation dynamic-range audit**, specified in the A11.1 report. It is not authorized or run by this roadmap.

## A11.2 update, 2026-10-01

[A11.2](A11_2_BIDIRECTIONAL_HEADROOM_GATE.md) tested the unchanged ±20 signed vector and inverse at one exact state with 11 ms before the natural first crossing. Both pulse branches crossed on the first available tick, 10 ms before no pulse, despite 19 versus 8 new motor spikes. The locked **bidirectional** criterion is **INCONCLUSIVE**: readout saturation persists even with temporal headroom. The exact-state LIF audit derived an immediate readout-separation amplitude interval, but no other amplitude was applied and no delay was demonstrated. A-C3 useful timing credit and A-C4 local *weight-update* control remain **OPEN**; A-C5–A-C7 are still blocked and M2 remains **NO**. One next proposed, unrun stage is **A11.3 single model-derived unsaturated amplitude** at the same checkpoint.
