# One-lane Lazer MVP L0.9b — headless adapter result

**Date:** 2026-10-03  
**Status:** **PASS** for the one-note headless policy/game contract. This is
engineering interface evidence, not evidence that the fly learned to play.

## Question and gate

Can the current-position fly policy run through a reusable headless game
adapter without receiving the scheduled note time or game results, while the
adapter preserves its key transitions, deterministic game trace, and
evaluator-only first-action audit?

The policy input contract is exactly `{visible, lane, position}`. The policy
uses its own episode-relative clock; the adapter anchors the returned key
transitions to the game episode's absolute start time. The adapter does not
send beatmap notes, evaluator cues, judgements, feedback, or score to policy
methods.

## Implementation

- Added `PositionObservation`, `PolicyKeyTransition`, the
  `PositionOnlyPolicy` protocol, and `HeadlessManiaTapAdapter` in
  `src/project_b/osu/adapter.py`.
- Changed `OnlineFlyPolicy.begin()` and `.step()` so they accept only an
  observation. The policy advances its neural clock by its fixed integration
  interval and returns episode-relative transitions. Stable config and weight
  hashes, source IDs, lane, and timing parameters are recorded as replay
  metadata.
- Moved the shared observation schema out of the biological policy module;
  the old import path remains available through the imported name.
- Routed the capacity harness through the same adapter to keep its action
  timestamps and game result on the shared seam.
- Added adapter coverage for a position-triggered press, relative-to-absolute
  timestamp translation, GOOD-or-better first-action audit, schema rejection,
  and identical normalized replay objects across two runs.
- Kept the evaluator's note cue and full judgement trace post-run only. The
  policy is finished before `play()` and the evaluator audit run.

## Verification

The first targeted unittest command failed to import `project_b` because the
repository's `src` directory was not on `PYTHONPATH`; this was a test-command
environment issue. Rerunning with `PYTHONPATH=src` passed:

```text
python -m unittest tests.test_lazer_adapter tests.test_online_position_policy 
Ran 6 tests — OK
```

The expanded focused regression run also passed:

```text
python -m unittest tests.test_lazer_adapter tests.test_online_position_policy \
  tests.test_online_position_readout tests.test_lazer_capacity \
  tests.test_lazer_feedback tests.test_lazer_parity_corpus \
  tests.test_environment
Ran 52 tests — OK
```

The real fly policy's one-note run has no DOWN, produces the expected
automatic MISS, and replays identically. The scripted contract policy sees
only position observations and emits a DOWN at episode time 450,000 µs and an
UP at 451,000 µs. With the episode starting at game time 100,000 µs, the
adapter records the transitions at game times 550,000 and 551,000 µs; the
first-action audit measures −50,000 µs relative to the note and classifies it
GOOD-or-better. Repeated runs produce equal complete normalized trace dicts.

## Limits and next gate

This adapter accepts exactly one mania tap note and uses the Python headless
game model. It does not yet calculate osu! score/accuracy/combo totals, parse
`.osu` maps, capture live Lazer playfield observations, or connect to the
in-process Lazer input boundary. L0.6 remains **INCONCLUSIVE / NO-GO** for
biological teaching and training; this interface result does not change that
decision.

**Next proposed stage:** L0.10 — verify one-note tap score, accuracy, and
combo semantics against the pinned Lazer runtime. Do not start that stage
without the user's authorization.
