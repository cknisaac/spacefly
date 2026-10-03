# EA-MVP — first non-learning implementation result

**2026-10-03.** The user approved the EA-MVP engineering-assumption categories. This report covers only the causal headless bridge and the frozen present-position/fixed-readout capacity panel. **No teacher, DAN stimulation, synaptic update, training, or confirmation run occurred.** Strict biological results and the saved playable recreation retain their earlier statuses and files.

## Question and frozen inputs

Can the separate EA-MVP branch stream present-position observations and timestamped key transitions through the headless game, deliver stripped judgements only after they occur, and show task-free control of first DOWN through selected MaleCNS KC→MBON05 weights with the existing fixed readout?

The [frozen non-learning protocol](../configs/ea_mvp_task_free_admission.json) was saved before its probe. It pins the source configuration at SHA-256 `528ac42f04bd7f3e254ee187b32f2279fa337ce47a370eb364411b59ae87f870`, 32 audited source-order KCs, MBON05, a Gaussian current-position encoder, contact-ratio normalized weights, existing LIF/effect overlay, inverse 0.05-position-bin readout, 1-ms tick, and the pretraining-probe threshold `0.005572335995331903 mV-equivalent`. All of those non-anatomical choices are **ENGINEERING ASSUMPTIONS**. The task-free intervention scales only the six KCs with preferred positions within ±0.10 of each of the predeclared centers 0.2, 0.5 and 0.8 to 20% of initial weights. It does **not** train them or inspect game score. Baseline and each arm replay twice.

The primary gate required a quiet initial-weight traversal, first DOWN within 0.10 position of its own center in at least two of three local arms, and exact repeated traces. No gain, threshold, cohort, center or window could be changed after seeing a result.

## Result

| Task-free arm | First DOWN | Position at first DOWN | Changed KCs |
| --- | ---: | ---: | ---: |
| Initial weights | None | — | 0 |
| Local 0.2 | 388,000 µs | 0.22 | 6 |
| Local 0.5 | 263,000 µs | 0.47 | 6 |
| Local 0.8 | 113,000 µs | 0.77 | 6 |

**Task-free capacity subgate: PASS (3/3 local arms, baseline quiet, exact repeats).** Raw [receipt](../runs/ea_mvp/task_free_admission.json) SHA-256: `ebc0b8938964b5d34f1097b981c15f8aa686dccfbdeb724bf06a9c5bd590266a`. This is direct fixed-weight intervention, not learned action acquisition. It supports only the selected reduced model and readout, not the full Branch B Candidate 1 downstream route or a biological motor pathway.

## Streaming bridge result

New code lives only under `src/project_b/ea_mvp/`; `ManiaGame` and the saved playable recreation were not edited. The bridge starts the policy with a present observation, advances one integer-µs game clock on 1-ms ticks, accepts only current-tick lane-0 key transitions, and delivers `GameFeedbackEvent` records containing only the result label and its availability time. A result caused by an action is delivered on the next tick. The policy never receives note ID, scheduled time, signed error or score.

Focused checks passed **5/5**:

- A fixed position-triggered key DOWN at 450,000 µs received GOOD at the next tick, not before its action.
- A too-early null DOWN produced no immediate result and later received only an automatic MISS.
- A no-DOWN trial received the same label-only MISS, exposing the unresolved teaching ambiguity rather than hiding it.
- The initial-weight frozen fly stayed silent, received the later MISS, and kept identical weights.
- The predeclared local-0.2 fixed-weight fly emitted DOWN at 388,000 µs through the bridge, received the headless game's MEH judgement, and kept identical weights.

The first bridge version advanced the policy once at the initial observation, creating a one-tick phase mismatch with the existing online fly policy. This was corrected before the focused checks: `begin` owns the first observation and the first `step` occurs one tick later. No model parameter or score criterion changed.

## Scope, limitation and next stage

**EA-2 streaming bridge: PASS for the one-lane tap contract and focused checks. EA-3 task-free selected-weight capacity subgate: PASS; full EA-3 admission remains INCOMPLETE.** The panel has not yet tested a true no-cue neural baseline, an MBON-output-off lesion, or full source-tagged voltage/arrival attribution. It also cannot establish teacher polarity or useful learning from a game MISS. The old L0.6 biological teaching NO-GO remains unchanged.

**Exactly one next proposed stage: EA-3.1 no-cue/output attribution.** From the same frozen source config, compare matched no-cue, initial-cue, local-0.5 weight, and MBON-output-off conditions with source-tagged neural/readout traces. Require no-cue silence; selected-weight changes reaching MBON voltage and first DOWN; output-off abolishing DOWN; identical repeated traces. Keep score, DAN, plasticity and teaching off. Record PASS/FAIL/INCONCLUSIVE and stop before EA-4 or any training. No result in this report authorizes a learning run.
