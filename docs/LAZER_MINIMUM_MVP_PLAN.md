# Least one-lane lazer integration MVP

**Current priority (2026-10-03):** This document preserves the historical
one-note and L0.11 development path. The active next-work order is now
[osu!mania recreation first](OSU_MANIA_RECREATION_FIRST_PLAN.md): finish a
playable 4K game for the user's tap-dominant maps with general long-note
support, then report and stop for user review. Fly and policy experiments are
outside this plan. The L0.12 policy adapter is deferred before verification.

**Status:** L0.1–L0.5 passed within their stated engineering scope. L0.6 is
**INCONCLUSIVE / NO-GO for biological training under this task contract**.
L0.9a's pinned timing and note-lock source checks pass. The full osu!mania
replay host now matches the frozen judgement sequences, note identities,
direct-press offsets, and reachable timing-boundary outcomes. Full event parity
remains open because automatic-MISS observation times vary with the test
host's frame updates. The next gate is to define and test logical event time
separately from the time Lazer observes the event.
Do not describe this as a learned fly policy: the direct weight intervention
in L0.4 showed engineering controllability only.

## Goal

Build the smallest reproducible vertical slice that can later connect to
osu!lazer: one OD8 mania tap note in lane 0, current rendered position as the
policy's only game input, timestamped key transitions as output, and a
headless game evaluator that records the resulting judgement. Keep the game
clock and scheduled note time inside the evaluator.

The first deliverable is a **headless integration MVP**, not a training
result. It is ready when the Python environment matches the pinned lazer
runtime on the frozen one-note corpus and both a headless adapter and a later
in-process adapter can use the same observation/action/event contract. The
first-action timing score is an engineering metric. A separate
**fly-learning MVP** requires a supported teaching rule and frozen learning
protocol; it is not currently cleared to run.

The MBON05-to-key readout is an artificial fixed interface, not a measured fly
motor pathway. Level 4D remains frozen as **FAIL** for target action
acquisition; its wrong-region action is a regression case, not a successful
MVP policy.

## Pinned game reference

- osu!lazer release: `2026.1001.0-tachyon`
- Release commit: `da27300fcbfa246f87c3ba1a14cbd00b68c7e9a9`
- Ruleset: native osu!mania; four columns, lane 0 active; tap notes only.
- Difficulty: OD8, no mods, playback rate 1.0.
- Official sources reviewed: [`ManiaHitWindows`](https://github.com/ppy/osu/blob/da27300fcbfa246f87c3ba1a14cbd00b68c7e9a9/osu.Game.Rulesets.Mania/Scoring/ManiaHitWindows.cs), [`HitWindows`](https://github.com/ppy/osu/blob/da27300fcbfa246f87c3ba1a14cbd00b68c7e9a9/osu.Game/Rulesets/Scoring/HitWindows.cs), and [`DrawableNote`](https://github.com/ppy/osu/blob/da27300fcbfa246f87c3ba1a14cbd00b68c7e9a9/osu.Game.Rulesets.Mania/Objects/Drawables/DrawableNote.cs).

The selected OD8 half-windows are Perfect 16.5 ms, Great 40.5 ms, Good 73.5
ms, Ok 103.5 ms, Meh 127.5 ms, and Miss 164.5 ms. Lazer compares unrounded
timing offsets with those windows. `CanBeHit()` permits an unresolved note
through the largest successful window (Meh); this headless integer-microsecond
profile expires it at the first late microsecond after +127.5 ms. A too-early
pressed Miss and a press before the Miss window remain distinct from an
automatic miss.

The Python profile was checked against the exact pinned C# timing methods for
all 24 OD8 signed boundary vectors. A linked-source C# harness also checked
the pinned same-lane note-lock rule. These are source-subset checks, not a run
of the full osu!mania playfield and event pipeline, so full runtime parity is
still unverified. Per-note judgement and its base accuracy contribution are
in scope for this MVP; cumulative score/combo parity, `.osu` parsing, holds,
mods, and speed changes are later extensions.

## Policy boundary

The game owns the absolute clock and scheduled note time. On each 1-ms neural
tick, the policy receives only `{visible, lane, position}` from the current
rendered note. It may retain its own neural state and emits timestamped
`DOWN`/`UP` transitions. The policy input must not contain beatmap time,
scheduled hit time, time-to-contact, judgement, score, or target key.

The first fixture has one visible lane-0 note with a 500-ms approach to the
judgement line at x=0.0. The primary action metric is the first DOWN for that
note, judged from the note's scheduled time. Good-or-better means an absolute
timing error no greater than the pinned OD8 Good window. Later actions do not
rescue a failed first action.

## Implementation and test gates

| Gate | Work | Required evidence |
|---|---|---|
| **L0.1 — source-derived timing profile** | Separate `lazer` from stable-native and stable-convert profiles. | OD8 and fractional-OD windows; every integer-OD edge; pressed early Miss versus too-early null; late Meh and automatic expiry. Stable profile regressions unchanged. |
| **L0.2 — headless scenario contract** | Configure one lane-0 500-ms note and serialize game actions/results. | Deterministic fixture; action at -50 ms receives Good; exact event log preserved; timing profile named in run metadata. |
| **L0.3 — streaming fly adapter** | Turn one current-position sample at a time into fixed KC drive, simulate, and close position bins online. | Input schema contains only visibility/lane/position; online MBON pre-reset samples exactly match the independent batch moving-note simulator; bin closure waits until the current observation leaves the bin; action validity, fixed hold/release and deterministic replay tests pass. The causal output decision may lag the last sample in its bin by up to one 1-ms tick. |
| **L0.4 — causal capacity** | Test once whether a predeclared maximum-permitted local LTD intervention can move the first action into the actual Good window. | **PASS for engineering controllability only.** Target-floor first DOWN: 488,000 µs (−12 ms), PERFECT; baseline and plasticity-off emitted no DOWN; the matched out-of-window intervention produced a too-early null press; all replays were exact. See [L0.4 result](LAZER_MVP_L0_4_CAPACITY_RESULT.md). |
| **L0.5 — causal feedback-event contract** | Separate the game's judged result from the future reinforcement pathway; keep it out of the policy's position-only sensory input. | **PASS for event-contract engineering only.** Tests cover early judged Miss, late judged result, too-early null, retry, no-press expiry, and exact-expiry ordering. Reinforcement receives only judgement label and availability time; hidden note timing stays in evaluator audit. No biological teacher or learning. See [L0.5 result](LAZER_MVP_L0_5_FEEDBACK_CONTRACT_RESULT.md). |
| **L0.6 — evidence for a feedback/teaching rule** | **INCONCLUSIVE / NO-GO for biological training under the frozen contract.** Primary studies do not justify the task-specific observable outcome, valence, action credit, or ±73.5-ms teaching mapping. See [L0.6 audit](LAZER_MVP_L0_6_FEEDBACK_TEACHING_EVIDENCE.md). |
| **L0.7 — teacher implementation/capacity controls** | **HELD.** No versioned teaching rule passed L0.6; do not implement a biological teacher or run its causal controls. |
| **L0.8 — one-lane training MVP** | **HELD.** No task training until the learning rule and observable feedback path are independently justified or the model's claim is explicitly revised. |
| **L0.9a — pinned lazer runtime parity** | **PASS for normalized logical-event/action parity; raw observed times remain frame-dependent.** Exact pinned C# timing methods match all 24 OD8 classifier vectors; the pinned note-lock method matches its source-policy vector. The full replay host matches all eight scenario event traces and all 24 playable boundary outcomes. The dual-time contract preserves automatic-MISS logical expiry separately from observed update time, and all DOWN/UP transitions are captured. See [L0.9a.1 result](LAZER_MVP_L0_9A_1_DUAL_TIME_ACTION_TRACE.md). This does not clear the biological-learning no-go or establish score-total parity. |

Stop at each failed or inconclusive gate. Do not tune the encoder, threshold,
learning rate, teacher timing, or connectome cohort against held-out evaluation
notes. Preserve Level 4D artifacts and status.

## L0.6 evidence-audit contract and outcome

- **Question:** Does primary research justify mapping the observable outcomes
  in the frozen lazer task to distinct positive/negative teaching signals at
  the MaleCNS γ4 KC→MBON05/PAM08 fixture, including early judged error, late
  judged result, too-early null, retry, and no press?
- **Why this is next:** L0.4 demonstrated engineering controllability under
  direct weight manipulation; L0.5 now records when game results become
  available without exposing hidden timing. Neither says which outcome should
  cause plasticity, or whether the fly could observe the same feedback.
- **Hypothesis and outcomes:** If primary evidence supports the relevant
  outcome valence, timing, modulatory pathway, and local plasticity direction,
  write a versioned candidate rule with its limits. If those links are
  unmeasured or conflict, the result is INCONCLUSIVE/no-go for biological
  training; retain the simulator-only result without adding a convenient
  teaching signal.
- **Intervention:** Read primary studies and map each outcome category to
  evidence for perception, dopamine/PAM response, eligibility timing, and
  KC→MBON05 plasticity. Do not run the simulator or alter the model during
  the audit.
- **Controls:** Hold the selected adult MaleCNS cell identities, γ4
  compartment, connectome mask, game result categories and L0.5 feedback
  schema fixed. Distinguish direct evidence from analogy to other fly tasks,
  compartments, or behavioral paradigms.
- **Primary endpoint:** Evidence matrix stating, for each outcome, whether
  the exact circuit supports a teaching sign, timing, pathway, and plastic
  locus; include primary citations and explicit unknowns.
- **Secondary endpoints:** Whether the in-game result label is actually
  perceptible without visual HUD/score input, and whether no-press and null
  histories can be distinguished by observable fly signals.
- **Predeclared interpretation:** PASS only if all rule components needed by
  the frozen task are supported at the required level and a falsifiable rule
  can be specified. Otherwise keep teaching behavior an engineering
  assumption and do not train.
- **Do not:** Infer synaptic sign from anatomy or transmitter alone, transfer
  a rule from another compartment without explicit qualification, choose
  reward polarity to make the target intervention pass, or execute a learning
  run.
- **Output:** A cited evidence matrix, updated assumption ledger, and a
  versioned rule proposal or documented no-go. Update `CURRENT.md` and stop.
- **Stop condition:** Stop after this one evidence audit. If it passes, propose
  a separate rule implementation/causality gate before any training; do not
  run L0.7 automatically.

The audit is complete. Its result is **INCONCLUSIVE; NO-GO for biological
training under the frozen task contract**. Primary sources constrain temporal
order plasticity and some visual/operant learning, but they do not justify how
`PERFECT`, `OK`, `MISS`, a null press, retry, or no press should drive the exact
MaleCNS teacher circuit. Do not implement L0.7 or run L0.8 from this result.
The evidence matrix and limitations are in
[`LAZER_MVP_L0_6_FEEDBACK_TEACHING_EVIDENCE.md`](LAZER_MVP_L0_6_FEEDBACK_TEACHING_EVIDENCE.md).

## L0.9a.1 result: logical and observed event-time contract

**PASS for normalized logical-event and action-transition parity.** The game
record now has `logical_event_time_us` and optional
`observed_game_time_us`; the replay probe captures every DOWN/UP callback at
its replay-frame time and preserves raw `JudgementResult.TimeAbsolute` values.
Two runs match the normalized eight-scenario traces and all 24 playable
timing-boundary outcomes. Automatic-MISS observation time still varies by
update frame and remains in raw artifacts. See
[the stage result](LAZER_MVP_L0_9A_1_DUAL_TIME_ACTION_TRACE.md). This does not
resolve the biological feedback/teaching gap.

## Proposed after L0.9a.1: L0.9b one-lane headless vertical slice and adapter conformance

This was the proposed next stage after L0.9a.1. It is now completed with PASS;
see the L0.9b execution update below and the
[stage result](LAZER_MVP_L0_9B_ADAPTER_RESULT.md). The original gate used the
existing game state machine, single-note fixture, online policy adapter, and
evaluator audit through a shared observation/action/result interface. It
required replayable policy traces, ordered action/judgement results,
evaluator-only first-action audit, and a policy input that excludes future
timing, score, judgement, and target-key fields.

## Least-MVP implementation roadmap

This roadmap separates two claims that must not be conflated:

1. **Headless integration MVP:** a reproducible one-note game loop accepts the
   causal policy interface and judges its key transitions against the pinned
   lazer rules. L0.1–L0.5 implement and test most of this slice; normalized
   runtime event parity passes, while adapter conformance, raw frame-time
   equality and score totals remain open.
2. **Fly-learning MVP:** the frozen connectome-constrained fixture acquires
   and retains a first lane-0 action through a justified learning rule. This
   is **not achieved**: L0.4 only showed engineering controllability, and
   L0.6 put biological training on hold because the task-specific teaching
   rule is unsupported.

The minimum policy/game boundary stays deliberately small: one lane-0 tap,
one visible moving note, 1-ms observation ticks, policy input limited to
`{visible, lane, position}`, and timestamped `DOWN`/`UP` output. The game
owns note time and judgement. The policy does not receive scheduled hit time,
time-to-contact, score, judgement, or the target key. A Good-or-better first
action means an absolute error of at most 73,500 µs. A later press does not
rescue a failed first action. Do not claim learned performance from the L0.4
direct-weight intervention.

### Ordered implementation steps and test gates

| Step | Work and prerequisite | Tests to specify/run at that step | Acceptance / stop rule |
|---|---|---|---|
| **1. L0.9a — pin and verify lazer semantics** | Corpus is frozen in `tests/fixtures/lazer_od8_parity_corpus.json`. The exact timing methods and note-lock method pass the linked-source checks. `scripts/run_lazer_runtime_probe.py` runs the frozen vectors through the pinned Mania `ReplayPlayer` and score processor. | Compare the 24 signed `HitWindows` classifier vectors separately from 24 playable keypress boundary cases; the playfield expires a note after the successful MEH window, so the late classifier MISS band is not fully reachable. Run all eight scenario traces, compare identity/order/direct offsets, capture every replayed DOWN/UP, and preserve raw automatic-MISS frame times across repeated runs. | **PASS for normalized event/action parity.** The logical expiry is deterministic; automatic-MISS observation time varies and remains raw diagnostic data. See [L0.9a.1 result](LAZER_MVP_L0_9A_1_DUAL_TIME_ACTION_TRACE.md), plus the [timing subgate](LAZER_MVP_L0_9A_TIMING_SUBGATE_RESULT.md), [note-lock subgate](LAZER_MVP_L0_9A_NOTE_LOCK_SUBGATE_RESULT.md), and [runtime probe](LAZER_MVP_L0_9A_RUNTIME_PROBE_RESULT.md). |
| **2. L0.9b — complete the one-lane headless vertical slice and adapter contract** | Reuse the existing `GameEnvironment`, single-note fixture and online policy adapter. Make observation, action and result records the stable seam that a future in-process lazer adapter can implement. | Existing coverage in `tests/test_environment.py`, `tests/test_cli.py`, `tests/test_online_position_policy.py`, `tests/test_online_position_readout.py` and `tests/test_lazer_feedback.py`. Add one shared-trace contract test: same timestamped actions through the policy/game seam must preserve key transitions, ordered judgements, first-action audit and deterministic replay. Reject future-time, score, judgement and target-key fields in policy observations. | **PASS** when the one-note run is reproducible from config/seed and policy input is limited to current visibility, lane and position. This is the least headless MVP; it does not claim learned behavior. |
| **3. L0.10 tap score and accuracy parity** | After L0.9a verifies judgements and ordered events, implement the pinned no-mod Mania Score V2 fields for tap notes. Keep score evaluator output separate from policy input and biological feedback. | Frozen C# `ManiaScoreProcessor` vectors cover all six tap results, per-note total-score deltas, combo changes, accuracy numerator/denominator, mixed results, and a fresh-run reset. `tests/test_lazer_score.py` replays actual headless actions to each result label and compares every score field. | **PASS** at zero differences for completed no-mod tap results. Holds, mods, rate changes, ranking, and general `.osu` parsing are excluded. See [L0.10 result](LAZER_MVP_L0_10_SCORE_PARITY_RESULT.md). |
| **4. Reopen the learning rule only with new evidence** | L0.7/L0.8 remain held after L0.6. Before implementation, obtain evidence for observable feedback, its valence, credited action/eligibility interval and plausible pathway/locus—or explicitly revise the claim to an engineering learning model. | Research gate produces an outcome-by-outcome evidence matrix, measurable signal contract and versioned falsifiable rule. Review distinguishes direct findings from analogies and engineering assumptions. | **PASS** only if every rule component is supported at the stated claim level. Otherwise remain **NO-GO**: no teacher, DAN event, weight update or training. This is a decision gate, not a guessed signal design. |
| **5. L0.7 — implement and causally validate an admitted rule** | Conditional on Step 4 PASS and a separately frozen protocol; no current rule is admitted. | Unit tests for feedback availability/order, credited presentation, local plastic-edge mask, weight bounds, teacher-off/plasticity-off and wrong-time/wrong-outcome matched controls, deterministic replay, and no teacher/plasticity during evaluation. | **PASS** only if the rule changes eligible allowed edges and controls behave as predeclared. Any failure stops the stage; no parameter tuning. |
| **6. L0.8 — one-note learning and frozen retention** | Conditional on Step 5 PASS. Train on one moving lane-0 note, then freeze weights and evaluate on predeclared repeated/held-out presentations. | Matched baseline, admitted-rule, teacher-off/plasticity-off and wrong-rule arms; verified first-action timing; schema/no-leak audit; Good-or-better first action; locality; persistence with learning disabled; raw event/weight trace replay. | **PASS** only if the frozen first action meets the declared timing gate, controls separate as predicted and the result persists without online plasticity. No seed/threshold selection after results; otherwise FAIL/INCONCLUSIVE and stop. |
| **7. Minimal 4K headless readiness** | After one-lane game and adapter gates pass. Preserve one-lane cases as regressions. This extends the game boundary, not the neural task. | Extend the pinned tap corpus for per-lane independence, simultaneous chords/releases, same-lane overlap/priority, misses, retries, mixed judgements, combo breaks, score/accuracy totals and replay. Compare ordered records with the same lazer runtime. | **PASS** on the frozen two-scenario 4K corpus: captured DOWN/UP transitions, normalized event ordering, per-judgement results and no-mod Score V2 snapshots match the pinned runtime. This proves bounded 4K game parity, not that the fly learned 4K play. Holds/mods/rate changes remain out of scope. See [L0.11 result](LAZER_MVP_L0_11_4K_SCORE_PARITY.md). |
| **8. In-process osu!lazer adapter** | After headless 4K tap semantics pass. Extend the current single-note position-only adapter contract to 4K episodes, then integrate at the supported mania input/event boundary without exposing game-private timing to policy code. | Send identical frozen observation/action traces through the generalized headless and in-process adapters. Compare timestamps, key transitions, ordered judgements, score/accuracy/combo and deterministic replay. Smoke-test start, pause/resume, map end and safe key release. | **NOT RUN.** PASS when normalized outputs match on the pinned corpus. This is direct Lazer integration, not evidence of biological learning or four-lane policy performance. |

### Executed stage contract: L0.9a.1 logical and observed event-time contract

1. **Question:** Can the headless event contract retain exact, deterministic
   logical judgement times while also recording when the pinned Lazer runtime
   observes each event on its update clock?
2. **Why this is next:** The actual replay host matched judgement identities,
   ordering, and direct-press offsets. Repeated runs placed automatic MISS
   observations at different times after the same expiry, so one timestamp
   cannot represent both the logical event deadline and the frame observation.
3. **Hypothesis and possible outcomes:** Separate logical and observed times
   will preserve deterministic headless semantics without hiding Lazer's frame
   delay. If the runtime cannot expose both consistently, retain the raw game
   time as a diagnostic and keep exact event-time parity INCONCLUSIVE.
4. **Intervention:** Add `logical_event_time_us` and
   `observed_game_time_us` to the trace contract. Use the exact expiry
   timestamp for an automatic MISS's logical time; capture
   `JudgementResult.TimeAbsolute` as its observed time. Record DOWN/UP inputs
   at their replay timestamps and capture `ScoreProcessor.NewJudgement` from
   the pinned playfield.
5. **Controls:** Keep pinned commit, OD8, no mods, rate 1.0, frozen corpus,
   integer-microsecond policy inputs, and per-scenario initial state fixed.
6. **Primary endpoint:** Zero differences in logical event identity, order,
   judgement, direct-press offset, and action transition records across the
   24 boundary cases and eight scenarios.
7. **Secondary endpoints:** Raw observed-time delay after each automatic MISS,
   deterministic hash of the logical trace across repeats, and whether the
   runner can capture every UP transition.
8. **Interpretation:** PASS only for zero logical-trace differences and
   complete action capture; INCONCLUSIVE if raw/logic timestamps cannot be
   separated or action transitions are incomplete; FAIL for any semantic
   mismatch.
9. **Do not:** Change judgement windows or note-lock behavior, switch the
   pinned revision, extend to holds/mods, implement score totals, tune policy,
   or run a teacher/training experiment.
10. **Output:** Versioned event schema, repeated C# and Python traces, mismatch
    summary, raw observed timestamps, and a `CURRENT.md` update.
11. **Stop condition:** Stop after this event-contract comparison. If it
    passes, propose L0.9b adapter conformance; do not start it automatically.

### Current execution position

- Step 1 is complete for normalized event/action parity under L0.9a.1. The
  pinned timing and note-lock methods pass; the replay host matches all eight
  logical traces and 24 playable boundary outcomes, and repeated captures
  preserve every transition. Automatic-MISS `TimeAbsolute` remains
  frame-dependent by design. The local .NET SDK and pinned source are in
  `work/`.
- `python -m unittest discover -s tests -p 'test_lazer_parity_corpus.py'`
  checks Python behavior against frozen expectations. The linked-source
  harness can be run with `python scripts/run_lazer_csharp_windows.py`, then
  compared with `python scripts/compare_lazer_reference.py
  --source-policy-reference-output <csharp.json>`. Those checks do **not** run
  the full playfield event path; a full runtime differential is still needed.
- Steps 4–6 are biologically gated by the L0.6 no-go. Step 3 (tap scoring)
  remains software-only and can proceed after Step 1. Do not turn engineering
  controllability into a learning result.
- Steps 7–8 are downstream of verified one-lane rules and the shared adapter
  contract. They make the route to four-key Lazer explicit; they do not
  authorize broadening the current parity test.
- Run the full replay probe with `python scripts/run_lazer_runtime_probe.py`.
  Its result and limitations are in [the runtime probe report](LAZER_MVP_L0_9A_RUNTIME_PROBE_RESULT.md).
- At this historical point, the pinned timing/note-lock source subgates and
  normalized runtime event contract passed and L0.9b was the proposed next
  stage. That proposal is superseded by the execution update below.

### L0.9b execution update — one-note headless adapter contract

- **PASS:** `HeadlessManiaTapAdapter` now runs a one-note episode through the
  headless game using the shared position-only policy interface. The policy
  receives only `{visible, lane, position}`, keeps its clock episode-relative,
  and emits relative key transitions. The adapter anchors those transitions
  to game time and withholds game results and evaluator cues until policy
  execution is complete.
- The scripted causal trace produced DOWN/UP at relative 450,000/451,000 µs
  and game 550,000/551,000 µs from an episode start of 100,000 µs; the first
  action was 50,000 µs early and still within the OD8 Good-or-better window.
  The real current-position fly policy remains deterministic and produces no
  DOWN on the frozen one-note fixture.
- Seven focused suites passed 52 tests with `PYTHONPATH=src`, covering adapter,
  policy, readout, capacity contracts, feedback, parity corpus, and environment
  behavior. The adapter result is in
  [L0.9b result](LAZER_MVP_L0_9B_ADAPTER_RESULT.md).
- The least headless one-note vertical slice is now complete. Score/accuracy/
  combo totals, 4K shared input, native map loading and in-process Lazer
  integration remain unimplemented. L0.6 remains INCONCLUSIVE / NO-GO for
  biological teaching and training.
- At this historical point, L0.10 was the sole proposed next stage. It has
  since been executed; see the L0.10 update below.

### L0.10 execution update — tap Score V2 parity

- **PASS** for completed, no-mod lazer mania tap results. Added
  `calculate_tap_score()` and post-run score snapshots to the one-note
  adapter. The policy still receives only current position observations; score
  is computed after policy execution and game judgement.
- A pinned C# NUnit probe exercised all six result grades, a combo-break and
  recovery sequence, and a processor reset. Its eight scenario outputs were
  repeated twice and frozen in `tests/fixtures/lazer_score_v2_vectors.json`.
  `python scripts/run_lazer_score_probe.py` verifies the pinned source output
  against those vectors.
- The Python layer replayed headless actions for all result grades and the
  mixed sequence. Its per-note accuracy values, combo state, score component,
  per-note score delta and total score matched the C# vectors within
  1e-12 for floating-point fields. One erroneous GOOD/GREAT expectation was
  corrected after the first expanded test run; the final focused run passed
  56 tests.
- `CURRENT.md` records the initial failed assertion and its correction.
  Holds/mods/rate changes, score-frame restoration, general maps, multi-lane
  score replay, and in-process Lazer integration remain out of scope. L0.6 is
  still INCONCLUSIVE / NO-GO for teaching and training.
- **Sole next proposed stage:** L0.11 — expand tap score and event replay to a
  frozen 4K corpus with chords, misses, retries, and same-lane note overlap.

### L0.11 execution update — frozen 4K event and score parity

- **PASS** on the frozen two-scenario no-mod 4K tap corpus against the pinned
  osu!lazer ReplayPlayer and ScoreProcessor. Captured key transitions,
  normalized event ordering, lane judgements, and per-judgement Score V2
  snapshots match. Cases include a four-lane mixed-grade chord with an
  automatic miss; a too-early null and retry; same-lane note locking and
  force-Miss; a simultaneous two-lane chord; and combo break/recovery.
- The standalone pinned C# probe repeated identically twice. Python matched
  all events and score fields; the 73-test focused regression run passed. The
  existing L0.9 runtime probe also passed its three test cases twice after the
  new probe was isolated in its own class.
- The probe's first build exposed a missing `osu.Framework.Screens` import
  for `IsCurrentScreen()`. Adding the namespace fixed the build. No scoring or
  event-order mismatch remained.
- Scope remains bounded to the frozen no-mod tap corpus. The Python
  `HeadlessManiaTapAdapter` still accepts one tap note; arbitrary maps, holds,
  mods, rate changes, score restoration, raw automatic-MISS timestamp parity,
  and in-process Lazer integration are not covered. The current-position fly
  policy still produces no DOWN on the one-note 500-ms case. L0.6 remains
  **INCONCLUSIVE / NO-GO** for biological teaching and training.
- **Sole next proposed stage:** L0.12 — generalize the position-only adapter
  to 4K episodes and run identical frozen observations/actions through the
  headless game and an in-process osu!lazer test host. Compare normalized
  actions, events and score. Stop before starting it.
