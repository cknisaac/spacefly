# L0.9a same-lane note-lock subgate

**Status:** **PASS for the pinned `OrderedHitPolicy` source method**  
**Full L0.9a runtime parity:** **INCOMPLETE**  
**Learning:** none; no teacher, weight update, or training run

## Question

Does the headless model's same-lane note lock match the pinned osu!mania
`OrderedHitPolicy` at the exact start time of the next tap note?

## Pinned source behavior

At [the pinned `OrderedHitPolicy.cs`](https://github.com/ppy/osu/blob/da27300fcbfa246f87c3ba1a14cbd00b68c7e9a9/osu.Game.Rulesets.Mania/UI/OrderedHitPolicy.cs), an earlier note is hittable only while the current time is strictly before the next note's start. When a note is hit, `HandleHit()` force-misses unresolved earlier objects whose end time is before the hit note's start. The pinned [mania `DrawableNote`](https://github.com/ppy/osu/blob/da27300fcbfa246f87c3ba1a14cbd00b68c7e9a9/osu.Game.Rulesets.Mania/Objects/Drawables/DrawableNote.cs) applies the timing result; the pinned [mania `Column`](https://github.com/ppy/osu/blob/da27300fcbfa246f87c3ba1a14cbd00b68c7e9a9/osu.Game.Rulesets.Mania/UI/Column.cs) calls the policy after a successful hit result.

That differs from a rule that always gives the earliest unresolved note priority.
The headless lazer profile had that gap. It now follows the strict next-start
lock and records the newer note's result before force-missing older unresolved
notes. Stable profiles retain their separate M0 approximation.

## Executable check

The linked-source C# harness compiles the exact pinned `OrderedHitPolicy.cs`
alongside the exact `ManiaHitWindows`, `HitWindows`, and
`IBeatmapDifficultyInfo` implementations. Minimal shims provide the ordered
drawable collection, note objects, and forced-miss sink; they do not implement
the policy being tested or the timing classifier.

The frozen case has notes at 1,000,000 µs and 1,050,000 µs. At 1,049,999 µs,
the old note remains hittable and its offset yields GOOD. At 1,050,000 µs,
the old note is locked, the new note is hittable and yields PERFECT, and
`HandleHit(new)` force-misses the old note. The source-subset comparator
reported **zero mismatches**, together with zero mismatches over all 24 timing
vectors. Raw output:
`runs/lazer_mvp_l0_9a/csharp_source_subset.json` (ignored local run artifact;
SHA-256 `df5d737a2c5548e22b47e21bbde947fb236d40d0ceec17ca595d02493bd90859`).

The Python headless regression corpus now contains an exact-onset scenario and
asserts event order `[new PERFECT, old forced MISS, DOWN action]`. Focused
environment and corpus tests pass.

## Limits and next gate

The harness invokes the actual timing and note-lock source methods, but it does
not start osu!'s full `Column`, key-binding propagation, drawable lifetimes,
or scoring pipeline. Thus it verifies those source methods, not full runtime
event ordering. Full L0.9a remains incomplete until the frozen game scenarios
are run through the pinned playfield or an equivalent full runtime adapter.
No total score/accuracy, mods, holds, beatmap parsing, or biological learning
was tested. L0.6's teaching-rule no-go remains unchanged.
