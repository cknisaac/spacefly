# MVP-B3.1 — MBON05 input-transfer diagnosis

**2026-10-01 · FAIL under the predeclared B3.1 gate.** Removing only the declared graded APL current to MBON05 increased its cue-period peak voltage but did not make it spike. The result rejects APL inhibition alone as the cause of MBON05 silence in this frozen `MVP-C1` seed-31001 model. It does not establish a physiological explanation or justify changing any gain.

## Question and fixed comparison

After [B3](B3_CANDIDATE1_CONTROLLABILITY.md) found MBON05 silent in 39 arms, the [B3.1 protocol](../configs/b3_1_mbon05_input_transfer.json) fixed one nominal **seed 31001** isolated cue, a committed **1,000-µs** parent cut, and two frozen arms: baseline and APL→MBON05-output-off. The second arm omits only the continuous `−0.2 L` current on MBON05; the graded APL state, measured APL arrivals, other APL targets, selected weights, source graph, current-position encoder, autonomous boundary, motor readout and game rules remain intact. Plasticity, task teaching and exploration are off.

The primary endpoint was whether MBON05 crossed its fixed threshold **1.0** and spiked before the **900,000-µs** cue end. Baseline-silent/APL-off-spiking would support APL suppression as this model's local bottleneck; two silent arms fail that explanation; a start or current-balance mismatch would make the stage inconclusive. No seed, gain, threshold, sign or mask was adjusted after B3.

## Result

| Matched arm | Peak MBON05 voltage during cue | MBON05 cue spikes | First DOWN |
| --- | ---: | ---: | ---: |
| Baseline | **0.616388** | **0** | 524,000 µs |
| APL→MBON05 output off | **0.665515** | **0** | 524,000 µs |

Both peaks occurred at **653,000 µs**. Removing the APL term raised the peak by about **0.0491** normalized voltage units but left a **0.3345** gap to threshold. The arms had the same **6,713** source-tagged chemical arrivals to MBON05, including a cue-period amplitude sum of **8.880717**, and the same raw spike/action ledger. The cue remained an early null first action. This is a diagnosis of the declared model's input-transfer margin: its current KC drive, other currents and intrinsic dynamics together did not recruit MBON05 even without the one APL output term. It does not identify a unique biological cause.

## Attribution and verification

The two arms loaded an identical committed parent checkpoint and had matching selected-weight and boundary RNG identities. The baseline raw ledger exactly reproduced B3 seed-31001 nominal 1×. A selective trace sampled MBON05 at every 1-ms integration endpoint through cue end and accumulated all finer interval terms. At each interval, the saved diagnostic checked the production membrane equation's base, external, chemical and APL contributions; maximum absolute balance residual was **0** in baseline and **5.6×10⁻¹⁷** in APL-off. The APL current integral was negative in baseline and exactly zero in the target-off arm. Chemical arrivals, APL graded state, external input and synaptic state at all sampled ticks matched across arms; the only different modeled current was the declared target's APL output. Neither arm emitted a task PAM pulse.

The [receipt](figures/b3_1_mbon05_input_transfer/receipt.json), [independent audit](figures/b3_1_mbon05_input_transfer/independent_audit.json), parent checkpoint, two raw ledgers, source-tagged MBON05 arrivals, first-action audits and selective voltage/current traces are saved under `docs/figures/b3_1_mbon05_input_transfer/`. The independent audit verified source file hashes, parent identity, exact B3 baseline reproduction, raw first-action reconstruction, all target arrivals, matched non-target trace inputs and the two subthreshold maxima. The diagnostic scripts compiled and their audit passed. No production simulator source or model parameter was changed; the full regression suite was not rerun for this diagnostic-only instrumentation.

The connectome contacts are source-derived anatomy. The APL coefficient, KC couplings, intrinsic dynamics and autonomous boundary are **ENGINEERING ASSUMPTIONS**; physiological efficacy and exact MBON05 transfer are **UNKNOWN**. This result is one fixed model seed and one omitted-output counterfactual. B3's three-seed controllability gate remains **FAIL**; B4 learning and B5 retention were not run. Branch A A5/A6 are still open.

## Sole next proposed stage — B6 Candidate 1 go/no-go decision

**Question:** Given B3's failed controllability and B3.1's rejection of APL-only suppression, should frozen `MVP-C1` be retired before training, or is there an independently supported, explicitly versioned revision worth testing within the candidate budget? **Why next:** A local causal route from selected weights to MBON05 spikes and first action is absent under the frozen design; B4 training would consume development time without that prerequisite. **Hypothesis/outcomes:** If no evidence supports a specific change to the engineering model, retire Candidate 1 and preserve its negative result; if a source- or literature-supported change exists, specify its evidence, version and new falsifiable gate before any run; if the budget or evidence cannot be audited, report inconclusive readiness for another candidate.

**Intervention:** Read-only audit of B1/B2/B2.1, A1–A4, B3/B3.1 evidence, unresolved physiology and the Candidate 1 active-time ledger; make one explicit go/no-go decision. **Controls:** Preserve the frozen B3/B3.1 protocols and all raw results; retain the 8-hour per-candidate and 24-hour overall caps. **Primary endpoint:** an evidence-linked, budget-accounted decision to retire or version a specific revision, with no numerical setting chosen from B3/B3.1 outcomes. **Secondary:** list unknown effect signs, omitted inputs and infrastructure gates. **Interpretation:** PASS for a complete auditable decision, FAIL for an unsupported or cap-breaking continuation, INCONCLUSIVE if essential time/provenance remains unresolved. **Do not:** rerun B3, tune gains/thresholds, launch B4/B5, or start Candidate 2 automatically. **Output:** decision report, budget reconciliation, branch status update. **Stop** after the decision. Suggested Codex setting: **GPT-6 Astra / Medium**.
