# Branch A — learning and experiment infrastructure roadmap

**Active plan, expanded 2026-10-01.** Branch A establishes trustworthy, deterministic and auditable tools for fly learning. It has **no synthetic performance requirement**. Old M2 and A10–A11.2 results remain historical diagnostics in [LEGACY_SYNTHETIC_STATUS.md](LEGACY_SYNTHETIC_STATUS.md); A11.3 is not scheduled. Branch B pathway-and-rule selection may proceed while infrastructure is completed.

The **model / effort** entries are recommended **Codex assistant settings for doing each step**, not biological model parameters or simulation settings. `low`, `medium` and `high` refer to reasoning effort. GPT-6 Luna suits bounded inventory work, GPT-6.1 Sol suits implementation and tests, and GPT-6 Astra suits demanding cross-component audit or gate decisions. Use the smallest setting that reliably completes the step; account availability may vary. See [official OpenAI model-selection guidance](https://developers.openai.com/api/docs/guides/model-selection).

| Stage | Model | Revised effort |
| --- | --- | --- |
| **A0 — Legacy synthetic freeze** | GPT-6 Luna | Medium — complete |
| **A1 — Plasticity / learning plumbing** | GPT-6.1 Sol | High — generic and B2 candidate seam PASS |
| **A2 — Checkpoint / replay** | GPT-6.1 Sol | High — A2.1/A2.2/A2.3 PASS for infrastructure |
| **A3 — First-action evaluation** | GPT-6.1 Sol | A3.1–A3.3 PASS; infrastructure only |
| **A4 — Matched control framework** | GPT-6.1 Sol | A4.1–A4.3 PASS; infrastructure only |
| **A5 — Cross-state diagnostics** | GPT-6.1 Sol | Medium |
| **A6 — Infrastructure-ready decision** | GPT-6 Astra | High |

**A0 — legacy synthetic freeze: COMPLETE (2026-10-01).** Old code, configs, reports, raw ledgers, checkpoints, audits and failed gates remain in place. A SHA-256 inventory in [LEGACY_SYNTHETIC_FREEZE_MANIFEST.json](LEGACY_SYNTHETIC_FREEZE_MANIFEST.json) covers the synthetic implementation, configs, scripts/tests, reports and selected A/M2 raw result folders. The manifest records exact paths, sizes and hashes. The synthetic learner remains available for reproduction; its performance is not an A6 criterion or a Branch B prerequisite.

## A1 — plasticity and learning plumbing

**Goal:** Prove the simulator makes exactly the intended local updates under a declared teaching event. Experimental support for a chosen fly rule belongs to Branch B.

| Step | Work and output | Model / effort | Question answered |
| --- | --- | --- | --- |
| **A1.1 — inventory** | Map selected edge slots, eligibility, teaching delivery, weight application and tests. Save a gap checklist. **Existing:** `ThreeFactorPlasticity`, `SpikingSimulator.apply_dopamine`, four causal tests. | **GPT-6 Luna / medium** | Which mechanisms are already proved, and which are assumed? |
| **A1.2 — local invariants** | Check pre/post order, delayed teaching, zero teaching/eligibility, selected masks, bounds, clipping, deterministic arithmetic and unchanged unselected state. Save exact before/after records. | **GPT-6.1 Sol / medium** | Does only eligible, selected state change for the declared cause? |
| **A1.3 — candidate integration** | Define a narrow DAN/modulatory interface and fly-edge mask; integrate the actual rule only after Branch B selects pathway and rule. Keep the generic scalar fixture labelled as engineering. | **GPT-6.1 Sol / high** | Can the chosen fly candidate use the audited plumbing without hidden updates? |

**A1 status (2026-10-01):** [A1.1 inventory, A1.2 invariant results and A1.3 integration contract](A1_PLASTICITY_PLUMBING.md) are recorded. Generic invariants **PASS** with 31 relevant regression tests. Candidate integration remains **pending B2** because the γ4 trace equations, teaching semantics and exact mask are not fixed. No repair mini-step is needed before A2.1. A plumbing failure in later integration calls for a repair, not a synthetic performance search.

**A1.3 update after B2 (2026-10-01):** The source-contact runtime mask, B2 γ4 KC/PAM rule and simulator seam now **PASS** local invariant checks; the full suite passed 124 tests. The preceding pending-B2 statement is historical. [A1.3's resumed result](A1_PLASTICITY_PLUMBING.md#a13-resumed-after-b2--2026-10-01) records the source-cohort correction and limits. **A2.1 state/checkpoint schema** is the sole proposed next Branch A step. Full task feedback and electrical-circuit integration remain dependencies before B3.

## A2 — checkpoint and deterministic replay

**Goal:** Resume a coupled run exactly and evaluate frozen policies from a standardized initial state.

| Step | Work and output | Model / effort | Question answered |
| --- | --- | --- | --- |
| **A2.1 — state schema** | Enumerate neural/electrical state, weights, eligibility, DAN, queued events, RNG, boundary, readout, game, training index, config and source checksums. Define version and compatibility rules. **Existing:** trusted same-version synthetic serialization and Electrical V1 checkpoint tests. | **GPT-6.1 Sol / high** | Is every variable needed for exact continuation saved? |
| **A2.2 — exact continuation** | Restore at several event boundaries, including pending arrivals and delayed feedback; compare uninterrupted and resumed event, weight, action and judgement ledgers bit-for-bit on deterministic CPU. | **GPT-6.1 Sol / high** | Does resumed execution produce exactly the same future? |
| **A2.3 — frozen snapshot** | Define a policy snapshot and standardized neural, boundary and motor initial state. Replay fresh sequences with plasticity and exploration off and identical interfaces. | **GPT-6.1 Sol / high** | Does evaluation measure retained internal learning rather than residual activity or continued updates? |

**A2 exit:** complete coupled replay and frozen-snapshot tests pass. A trusted Python pickle roundtrip alone is partial evidence.

**A2.1 status (2026-10-01): PASS for the [MVP-C1 checkpoint schema](A2_1_MVP_CHECKPOINT_SCHEMA.md).** The committed tick cut, eight dynamic-state owners, 15 identity fields, exact encoding and strict restore rules are specified in a [machine-readable contract](../configs/a2_1_mvp_checkpoint_contract.json). This is a design result, not a writer/restore or replay pass. **A2.2 exact continuation (GPT-6.1 Sol / High)** is the sole next proposed Branch A stage. It needs the coupled MVP owner interfaces, including A3 first-action and B2 feedback state, before its decisive replay can run; build and test those within A2.2 rather than treating their absence as a replay success.

**A2.2/A2.3 update (2026-10-01):** [Component continuation and frozen-policy results](A2_2_A2_3_CHECKPOINT_PROGRESS.md) pass local tests, including minimum first-action/feedback owners, delayed sensory cancellation, queued-weight arrival replay and selected-weight freeze. The full A2.2 and A2.3 endpoints remain **INCONCLUSIVE** because there is no complete electrical/task runner or fresh frozen run. [MVP-B2.1](B2_1_CANDIDATE1_EXECUTABLE_DYNAMICS.md) now fixes chemical-current, boundary-waiting and graded APL timing laws as a versioned design; it does not pass A2 replay. The sole next proposed infrastructure stage is **resume A2.2 full coupled continuation**, then separately evaluate A2.3.

**A2.2/A2.3 full-coupled update (2026-10-01):** The later [result](A2_2_A2_3_COUPLED_RESULT.md) supersedes the component-only gate status above. **A2.2 PASS:** the 718-cell source-derived runner restored exactly at a committed cut with pending chemical/APL/sensory events, then matched future raw ledgers and complete state through motor/game/feedback events. A controlled pending-feedback cut also replayed exactly. **A2.3 PASS for infrastructure:** a policy-only selected-weight snapshot ran on two fresh notes from standardized zero activity with teaching and updates disabled. This is not learned retention evidence. **A2 exit PASS.** Sole next Branch A proposal: **A3.1 first-action identity (GPT-6.1 Sol / High)**; stop before its execution.

## A3 — first-action evaluation

**Goal:** The first DOWN for each note is the primary behavioral record. A later good press cannot repair a bad first press in the primary metric.

| Step | Work and output | Model / effort | Question answered |
| --- | --- | --- | --- |
| **A3.1 — action identity** | Lock causal note assignment for DOWN, null/too-early action, no-DOWN, simultaneous notes, expiry and ties. Specify signed error and disposition. **Existing:** historical first-action replay, but no reusable primary contract. | **GPT-6.1 Sol / high** | What counts as a note's first action, including failure to act? |
| **A3.2 — per-note ledger** | Emit first DOWN/time/error/disposition, no-DOWN, extra DOWN count and later actions for every note. Recompute independently from raw game/key events. | **GPT-6.1 Sol / medium** | Can every primary result be reconstructed from raw events? |
| **A3.3 — primary summaries** | Define first-DOWN ±73-ms rate, missing-action denominator, signed-error distribution and secondary judged scores before training. Check a good second press after a bad first press. | **GPT-6.1 Sol / medium** | Can scored judgements or later presses falsely inflate the main claim? |

**A3 exit:** every note has an auditable first-action record; secondary score cannot change the primary outcome.

**A3 completed (2026-10-01):** [The result](A3_FIRST_ACTION_EVALUATION.md) and [final receipt](figures/a3_first_action/receipt_v2.json) establish the isolated-note first-DOWN identity, independent reconstruction of pinned A2 raw game/key events, a per-note ledger and predeclared ±73-ms primary summaries. The A2 untrained and controlled-policy frozen fixtures yielded 0/1 and 0/2 primary success despite later positive game judgements; these are infrastructure examples, not learned-retention results. Targeted tests and the 148-test full suite pass. **A3.1/A3.2/A3.3 PASS; A3 exit PASS.** Sole next Branch A proposal: **A4.1 matched-condition manifest (GPT-6.1 Sol / Medium)**; stop before running it.

## A4 — matched control framework

**Goal:** Change only the declared condition while preserving initial state, input, sequence, seeds and fixed interfaces.

| Step | Work and output | Model / effort | Question answered |
| --- | --- | --- | --- |
| **A4.1 — condition manifest** | Record parent checkpoint, seed streams, sequences, encoder/motor hashes, intervention and allowed differences. Reject undeclared differences. **Existing:** synthetic on/off/shuffled and selected exact-state branches. | **GPT-6.1 Sol / medium** | Are runs actually matched before seeing outcomes? |
| **A4.2 — control switches** | Support plasticity on/off, shuffled or wrong-note teaching, DAN disabled and eligibility disabled in one runner. Log source feedback, DAN delivery and selected-synapse updates. | **GPT-6.1 Sol / high** | Which part of the learning chain is necessary for an effect? |
| **A4.3 — paired audit** | Use small deterministic fixtures to verify shared start, observations, seed policy, encoder and motor map, with only declared differences; save an audit receipt. | **GPT-6 Astra / high** | Are causal comparisons interpretable rather than confounded? |

**A4 exit:** every control is runnable, paired and auditable. No condition needs to learn successfully for this infrastructure gate.

**A4 completed (2026-10-01):** [The result](A4_MATCHED_CONTROL_FRAMEWORK.md) and [final receipt](figures/a4_matched_controls_v2/receipt.json) verify one checkpoint-matched baseline plus plasticity-off, wrong-note teaching, DAN-disabled and eligibility-disabled arms. Source feedback, actual PAM delivery/spikes and selected updates have distinct ledgers; undeclared seed/note/motor/allowlist differences fail closed. The synthetic short fixture exercises selected updates but is not a task-learning or B3 result. Four focused tests and the 152-test full suite pass. **A4.1/A4.2/A4.3 PASS; A4 exit PASS.** Sole next Branch A proposal: **A5.1 cross-state sampling rule (GPT-6 Luna / Medium)**; stop before running it.

## A5 — cross-state diagnostic tooling

**Goal:** Save representative states without choosing them because they show an interesting effect.

| Step | Work and output | Model / effort | Question answered |
| --- | --- | --- | --- |
| **A5.1 — sampling rule** | Build and test a deterministic checkpoint-selection rule that accepts a predeclared training horizon and run set, then derives early/middle/late indices. Save the rule before activity or reward is inspected. Instantiate a candidate-specific schedule once its run length is fixed, before those runs begin. | **GPT-6 Luna / medium** | Can states be selected independently of outcomes for any valid predeclared horizon? |
| **A5.2 — automatic capture** | Save each checkpoint with config/source/interface hashes and selection reason; restore and reproduce each continuation. | **GPT-6.1 Sol / medium** | Can cross-state observations be recovered and audited? |
| **A5.3 — common panel** | Run the same prespecified frozen observations/interventions at every state; report silent, saturated and failed states too. Keep this panel secondary to full-run evidence. | **GPT-6.1 Sol / high** | Does a proposed mechanism recur across runs and training phases? |

**A5 exit:** sampling, capture, replay and complete-state ledger work automatically across fixture runs, regardless of performance. A5 can proceed in parallel with Branch B; B4 results are not required. Applying the tooling to actual B4 training states requires a candidate-specific horizon and run set fixed before those runs begin. Fixture tests establish infrastructure readiness, not recurrence of a mechanism during learning.

**A5 completed (2026-10-01):** [The result](A5_CROSS_STATE_DIAGNOSTICS.md) and [receipt](figures/a5_cross_state/receipt.json) record six outcome-blind cuts across two fixture runs, exact checkpoint continuation for every cut, and a common two-arm frozen panel for all six states. **A5.1/A5.2/A5.3 PASS for infrastructure; A5 exit PASS.** No actual B4 learning states were inspected. Sole next Branch A proposal: **A6.1 integration dry run (GPT-6.1 Sol / High)**; stop before running it.

## A6 — infrastructure-ready decision

**Goal:** Decide whether A1–A5 can support an auditable Branch B development and confirmation study.

| Step | Work and output | Model / effort | Question answered |
| --- | --- | --- | --- |
| **A6.1 — integration dry run** | Exercise plumbing, checkpoint, first-action ledger, controls and scheduled snapshots together on a small deterministic fixture. This checks integration, not learning performance. | **GPT-6.1 Sol / high** | Do the pieces work together without state loss or inconsistent metrics? |
| **A6.2 — independent readiness audit** | Review manifests, exact replay, raw-event reconstruction, matched controls, unintended-update checks, failure cases and regressions. Publish PASS/FAIL/INCONCLUSIVE and remaining gaps for A1–A5. | **GPT-6 Astra / high** | Is infrastructure trustworthy enough for Branch B, and what is still open? |

**A6 passes only when A1–A5 are deterministic, auditable and regression-tested.** It has no synthetic hit-rate or timing target. Biological validity, controllability and learning performance belong to Branch B.

## Sequencing

The practical order is **A1 generic audit → A2 state/replay → A3 first-action metric → A4 controls → A5 cross-state capture → A6 integration audit**. Independent parts can proceed without a chosen fly pathway. Candidate-specific A1/A2/A4 integration waits for Branch B's B1/B2 design and must be checked before that candidate's learning runs. A5 and A6 infrastructure can proceed alongside B work without waiting for B3 or B4 results. This roadmap itself does not authorize a scientific experiment.

The [old Branch A contract roadmap](BRANCH_A_CONTRACT_ROADMAP.md), [M2 path](M2_PATH_TO_PASS.md) and [future diagnostic handoff](FUTURE_DIAGNOSTICS.md) remain historical records, not active prerequisites.
