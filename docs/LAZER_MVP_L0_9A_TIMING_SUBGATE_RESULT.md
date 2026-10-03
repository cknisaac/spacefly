# L0.9a timing-window subgate

**Status:** **PASS for the pinned C# timing classes only**  
**Full L0.9a runtime parity:** **INCOMPLETE**  
**Learning:** none; no teacher, weight update, or training run

## Question and scope

Do the Python OD8 judgement windows match the executable C#
`HitWindows`/`ManiaHitWindows` implementation in osu!lazer release
`2026.1001.0-tachyon`, commit
`da27300fcbfa246f87c3ba1a14cbd00b68c7e9a9`?

This subgate compiles the pinned upstream `HitWindows.cs`,
`ManiaHitWindows.cs`, and `IBeatmapDifficultyInfo.cs` directly into a small
standalone C# runner. A compatibility enum provides the same first seven
`HitResult` values in the same numeric order as that commit; a namespace stub
resolves an XML-documentation-only import. The runner invokes the pinned
`ManiaHitWindows.SetDifficulty(8)` and `HitWindows.ResultFor()` methods. It
does not compile or execute `DrawableNote`, the playfield, key routing,
judgement scheduling, or total score accumulation.

## Frozen test and result

The runner consumed all 24 signed OD8 vectors in
`tests/fixtures/lazer_od8_parity_corpus.json`: exact edges and the adjacent
microsecond on both sides of Perfect, Great, Good, Ok, Meh, and Miss windows.
The Python comparator reported **zero timing-window mismatches**.

The temporary source checkout was at the exact pinned commit. Its `global.json`
requires SDK 10.0.100 with `latestFeature` roll-forward; the installed .NET
10.0.401 SDK built the runner. The commands were:

```powershell
python scripts/run_lazer_csharp_windows.py `
  --source-root work/osu_lazer_reference `
  --output runs/lazer_mvp_l0_9a/csharp_hit_windows.json

python scripts/compare_lazer_reference.py `
  --windows-reference-output runs/lazer_mvp_l0_9a/csharp_hit_windows.json
```

The raw C# output SHA-256 is
`2efbb0721ecfde1cce2642fc33fbe3c4633a6d47d83e4454d473bee4d4611bba`.
The generated files under `runs/lazer_mvp_l0_9a/` are ignored local run
artifacts; the frozen inputs and harness source are tracked with the project.

## Interpretation and remaining work

This is executable evidence for the pinned timing-window classes and their
OD8 boundaries. It is not full osu!lazer runtime parity. In particular, the
eight frozen game scenarios still need a runner through the actual mania note
and playfield event path, covering early MISS vs null, expiry/action ordering,
same-lane note selection, and four-lane simultaneous input. Until that passes,
describe the headless game as **source-derived**, not runtime-verified.

The complete L0.9a gate remains open. The event corpus now contains eight
scenarios, including a source-derived check that at the next note's exact start
the new note is hit before earlier unresolved notes are force-missed. This
subgate does not validate that event behavior through the actual playfield,
total score/accuracy accumulation, mods, holds, `.osu` parsing, or four-lane
learning. The L0.6 biological teaching-rule no-go remains unchanged.
