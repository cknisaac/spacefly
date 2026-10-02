# Project stage-generation protocol

**Standing project instruction, adopted from the user's 2026-09-30 request.** Use this protocol when proposing, executing, or reporting sequential scientific or engineering stages. A stage answers one specific question and produces evidence that determines what should be considered next; it is not merely a coding task. Examples and roadmap rows below illustrate format, not authorization to run a stage or proof that a named stage has occurred.

**2026-10-01 scope update:** The active [Branch A](BRANCH_A_INFRASTRUCTURE_ROADMAP.md) validates infrastructure without a synthetic performance requirement; the active [Branch B](BRANCH_B_FLY_LEARNING_ROADMAP.md) tests internal fly learning and first-action retention. Prior A1–A11.2 and B1–B5.6 identifiers remain historical; new-plan A0–A6/B0–B9 are explicitly namespaced by the pivot and do not rename old reports. The legacy synthetic and visual stage proposals are not automatic next work. New B1 selection and B2 Candidate 1 design have completed; B3 pre-training controllability is proposed only after candidate-specific infrastructure integration and separate authorization.

## Generate the next stage from evidence

Before proposing a stage, read `CURRENT.md` and the latest result/report for that branch. State what is established, what remains unresolved, and the **single most discriminating next question**. Design the smallest experiment that can answer it. New evidence, including a failed experiment, may redirect an older roadmap. Do not mechanically follow a stale plan.

Use identifiers from the **active, pivot-namespaced roadmaps** for new work; preserve historical IDs on all old reports and do not silently relabel them. Use decimal substages to diagnose or revise a blocker within an existing major stage. Branch A is **learning/experiment infrastructure** and Branch B is **connectome-constrained fly learning**. Evidence from one can motivate a hypothesis in the other, but it does not establish that hypothesis there.

## Required stage specification

Every proposed stage must state:

1. **Stage ID and name** — the next unused branch-local identifier.
2. **Question** — one precise scientific or engineering question.
3. **Why this is next** — which preceding result makes it the most discriminating test.
4. **Hypothesis and possible outcomes** — distinct possible results and what each would imply.
5. **Intervention** — exactly what changes or is tested.
6. **Controls** — states, inputs, randomness, settings, and data that remain matched or frozen.
7. **Primary endpoint** — the decisive measurement.
8. **Secondary endpoints** — supporting measurements only.
9. **Predeclared interpretation** — support, failure, and inconclusive criteria, fixed **before** running.
10. **Do not** — explicit prohibitions appropriate to the stage, including tuning, broad search, leakage, or post hoc selection.
11. **Output** — expected raw result, report, audit, and document updates.
12. **Stop condition** — stop after the stage; do not automatically launch the next experiment.

## Diagnostic experiment discipline

Prefer matched-state causal interventions, deterministic replay, one variable changed at a time, small predeclared cohorts, direct lesions or omissions, frozen probes, and continuous timing/activity measurements. Diagnostic work seeks mechanism, not the best score. Avoid blind seed sweeps, parameter searches, many candidate masks followed by selection of the best, tuning until performance improves, and simultaneous changes to several mechanisms.

If a predeclared test fails to explain an effect, report the negative result. Do not immediately test another subset, seed, threshold, learning rate, or parameter. First propose and justify a new stage from the evidence, possibly at a higher level of abstraction.

## Gates and claim scope

Major milestones need explicit gates. Branch A's A6 requires trustworthy A1–A5 infrastructure, **not** synthetic performance. Branch B's gates are pathway/rule selection, complete candidate design, controllability, short internal learning, frozen retention, candidate decision, design freeze and fresh confirmation. The old visual→KC electrical route is deferred and direct fixed KC input is allowed. Do not silently advance past an active gate or interpret a historical failure as erased.

Keep claims at the scale tested: one checkpoint, one seed, selected seeds, general mechanism, and validated gate are different statements. A local causal result is not a project-wide validation.

## After each completed stage

Summarize the actual evidence, mark **PASS / FAIL / INCONCLUSIVE** under its predeclared criteria, update the branch roadmap and `CURRENT.md`, and propose **exactly one** next stage with an explanation of why it is more discriminating than obvious alternatives. Provide a direct execution prompt if the user requests it. **Do not run the proposed next stage automatically.**

Maintain a compact, separate roadmap for each branch in `CURRENT.md`. Each row should contain the actual stage ID, short name, and status (for example, `PASS`, `FAIL`, `INCONCLUSIVE`, or `NEXT PROPOSED`). A roadmap is a revisable evidence-based plan, not permission to execute its next row. Verify the historical names and IDs rather than copying illustrative sequences from an earlier document.
