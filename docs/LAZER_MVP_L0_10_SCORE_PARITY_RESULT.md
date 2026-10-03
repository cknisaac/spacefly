# L0.10 — one-note osu!mania score, accuracy, and combo parity

**Date:** 2026-10-03  
**Status:** **PASS** for fully resolved, no-mod lazer mania tap scoring.

This validates the software score layer. It does not show that the fly policy
has learned to play, and it does not cover holds, mods, rate changes, or
general `.osu` maps.

## Pinned reference

The C# probe ran the actual `ManiaScoreProcessor` and base `ScoreProcessor`
from osu! commit `da27300fcbfa246f87c3ba1a14cbd00b68c7e9a9`
(`2026.1001.0-tachyon`). It applied pinned `HitResult` values to tap-note
judgements on no-mod Score V2 maps. The existing L0.9a replay probe separately
verifies how lazer timing inputs become those judgement labels.

The key source files are pinned locally under `work/osu_lazer_reference/`:

- `osu.Game/Rulesets/Scoring/ScoreProcessor.cs` — accuracy accounting,
  combo changes, rounding, and the 1,000,000-point score formula.
- `osu.Game.Rulesets.Mania/Scoring/ManiaScoreProcessor.cs` — mania's
  150,000 combo / 850,000 accuracy weighting, Perfect's 305 accuracy points,
  and the combo multiplier cap.
- `osu.Game/Rulesets/Scoring/HitResult.cs` — which outcomes increase or break
  combo and which outcomes count toward accuracy.

Pinned source SHA-256 values:

| File | SHA-256 |
| --- | --- |
| `ScoreProcessor.cs` | `344B496983638A98C61DD3F60143BD6C025457A0C4CA1EA73C0A904DD7E7031B` |
| `ManiaScoreProcessor.cs` | `9F60DB67026BD8297800A9AF4FBB8316831F4719AD400B09FF54D02BD33C7495` |
| `HitResult.cs` | `8C6C2E6954B49D11E195A6EB9620878B3ABF3517F7ABFE89AFD0D5C13CB4C768` |

## Implemented behavior

`project_b.osu.scoring.calculate_tap_score()` accepts a complete lazer tap-note
result and computes a score snapshot after every judgement. It records each
note's score delta, actual and maximum accuracy points, numerator and
denominator, accuracy and remaining range, combo before and after, highest
combo, score components, and cumulative total.

The headless adapter computes this object only after policy execution and game
judgement finish. It appears in the post-run episode trace; it is not an
observation or callback to the policy. The game judgement and the score
evaluation remain separate data.

For the pinned no-mod mania profile:

- Accuracy points per tap are Perfect 305, Great 300, Good 200, OK 100,
  MEH 50, and Miss 0. Every completed tap judgement adds 305 to the current
  accuracy denominator, including a Miss.
- A non-Miss increases combo; Miss resets combo to zero. Highest combo is
  retained through the break.
- The combo component uses the result's base score multiplied by
  `clamp(log(combo_after, 4), 0.5, log(400, 4))`; Perfect uses 300 combo
  points even though it contributes 305 accuracy points.
- Final no-mod total score follows Mania's 150,000-point combo share and
  850,000-point accuracy share, with the exponent and rounding behavior taken
  from the pinned score processor.

## Verification

The frozen reference vectors are in
`tests/fixtures/lazer_score_v2_vectors.json`. They cover each of the six tap
results, a mixed sequence with a combo break and recovery, and processor reset
after a scored run. The Python tests replay actual headless tap actions to
produce those result labels, then compare every per-judgement score field to
the C# vectors.

The C# probe was run twice from the pinned source; both runs matched each
other and the frozen fixture:

```text
python scripts/run_lazer_score_probe.py
PASS: pinned score vectors repeated identically and match the frozen fixture.
```

Focused Python verification passed **56 tests** covering score vectors,
adapter score separation, current-position policy/readout, capacity contracts,
feedback, event parity, and the game environment. The first expanded run had
one incorrect test expectation: a 50-ms-early press is a GOOD at OD8, not a
GREAT. The expectation was corrected to the pinned GOOD result and 310,148
score; the complete run then passed. `git diff --check` and
`python scripts/build_docs_catalog.py --check` also passed.

The episode score function is stateless, so a new game result starts with a
fresh combo and accuracy ledger. The pinned C# reset vector additionally
preserves its UI bindable quirk (`TotalScore` is reset to 0 while
`TotalScoreWithoutMods` temporarily remains at 1,000,000); that transient
between-run display state is outside the completed-episode score interface.

## Remaining scope

This pass is tap-only and no-mod. Score multiplier mods, Score V1/Classic,
holds, replay-frame score restoration, and ranking are not implemented. The
existing adapter still handles one lane-0 note; 4K event and score parity and
an in-process Lazer adapter remain downstream work. L0.6 remains
**INCONCLUSIVE / NO-GO** for biological teaching and training.
