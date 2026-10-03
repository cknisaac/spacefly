# M0 osu!mania environment contract

## Scope and references

M0 judges generated 4K tap-note scenarios without graphics, audio, neural simulation, reward, or training. It supports native stable mania as the canonical profile (`OD=8`), stable converted-map windows, and a source-derived unmodded lazer mania timing profile. Lazer tap timing, late expiry, and no-mod Score V2 now match a small frozen 4K corpus against the pinned runtime. Rate-changing mods, native `.osu` parsing, and hold-note judgement are not implemented. Hold-note records are rejected, never silently reduced to taps. The [official osu!mania judgement page](https://osu.ppy.sh/wiki/en/Gameplay/Judgement/osu!mania), [overall-difficulty page](https://osu.ppy.sh/wiki/en/Beatmap/Overall_difficulty), and [note page](https://osu.ppy.sh/wiki/en/Gameplay/Hit_object/Note) are the rules references. The Project B master specification supplies the stable OD8 canonical values. The lazer profile targets release `2026.1001.0-tachyon` (`da27300fcbfa246f87c3ba1a14cbd00b68c7e9a9`). Exact automatic-MISS observation timestamps remain frame-dependent. See the [one-lane MVP plan](LAZER_MINIMUM_MVP_PLAN.md), [L0.9a runtime probe](LAZER_MVP_L0_9A_RUNTIME_PROBE_RESULT.md), and [L0.11 4K parity result](LAZER_MVP_L0_11_4K_SCORE_PARITY.md).

## Time and window contract

- All note, action, expiry, and judgement times are signed 64-bit **integer microseconds**. Only OD formulas use exact decimal arithmetic. No accumulated frame delta controls judgement.
- `ManiaHitWindows.from_od(od, ruleset)` accepts OD 0 through 10. Native stable integer-ms thresholds are `MAX=16`, `GREAT=int(64-3*OD)`, `GOOD=int(97-3*OD)`, `OK=int(127-3*OD)`, `MEH=int(151-3*OD)`, and early `MISS=int(188-3*OD)`. `int` truncates the positive formula toward zero. OD8 is 16/40/73/103/127/164 ms.
- The stable-convert profile has thresholds 16/34/67/97/121/158 ms for OD > 4 and 16/47/77/97/121/158 ms otherwise, per the official judgement page. The converted profile is a window choice for generated notes; native `.osu` conversion is not in M0.
- The source-derived unmodded lazer profile uses `ManiaHitWindows` difficulty ranges and the floor-plus-0.5-ms rule. OD8 half-windows are 16.5/40.5/73.5/103.5/127.5/164.5 ms (Perfect/Great/Good/Ok/Meh/Miss); offsets are compared without integer-ms rounding. Lazer's base `HitWindows.CanBeHit()` allows hits through the largest successful window (Meh), so auto-expiry is the first late microsecond beyond +127.5 ms. A pressed early Miss (through −164.5 ms) differs from a too-early null press. The pinned C# timing methods and `OrderedHitPolicy` methods pass source-subset checks; the full `ReplayPlayer` probe matches normalized logical event traces, all replayed DOWN/UP transitions, reachable boundary outcomes and direct-press offsets. `JudgementRecord` keeps deterministic `logical_event_time_us` separate from optional `observed_game_time_us`. Automatic-MISS observation time varies with game-frame updates, and score totals remain unverified. See the [L0.9a.1 result](LAZER_MVP_L0_9A_1_DUAL_TIME_ACTION_TRACE.md) and [runtime probe report](LAZER_MVP_L0_9A_RUNTIME_PROBE_RESULT.md).
- In stable profiles, absolute microsecond error is rounded to a whole millisecond using nearest, **ties to even**. This is an explicit interpretation of the wiki's rounded-hit-error statement; the half-millisecond tie mode is not specified there. The exact tie choice must be checked against stable-client evidence before claiming sub-ms client parity. Threshold equality is included.
- Stable-native early `MEH` earns 50. A press after early `MEH` but within early `MISS` consumes that note as MISS. A press before early `MISS` is a `NULL_PRESS` and does not consume a note. On the late side, a stable-native note expires at the first microsecond whose rounded error exceeds the `OK` threshold; no late MEH is possible. Expiry runs before same-time key actions. OD8 stable-native expiry is note time +103,500 µs.
- The displayed ±127 ms MEH number is not a symmetric usable hit band in the stable-native profile. The stable profile preserves that asymmetry; lazer uses its own symmetric per-result windows and late expiry as documented below.

## Event and key semantics

Each lane holds tap notes in timestamp order. The lazer profile follows the pinned `OrderedHitPolicy`: an earlier note is no longer hittable at or after the next note's start time, and a successful hit on a newer note force-misses earlier unresolved notes whose end time precedes it. The headless lazer profile implements this rule; its timing and note-lock source methods pass C# subgates, and the pinned `ReplayPlayer` probe matches frozen normalized event traces, actual replay transitions, and no-mod Score V2 on the small L0.11 4K corpus. Automatic-MISS observed times remain frame-dependent. Stable profiles retain the M0 oldest-unresolved-note approximation and are not claimed to match stable-client note lock. Other lanes are independent. Same-lane duplicate notes at one timestamp are rejected by this M0 model. Cross-lane chords are separate notes and can be judged simultaneously. Do not extend the small-corpus pass to arbitrary dense maps.

A key-down from the up state attempts a judgement and leaves the key down. A repeated down while held is recorded as `repeat_down` and makes no second judgement. A key-up releases; repeated up is recorded as `repeat_up`. A press with no candidate judgement is `null_press`, which is **not** an osu MISS. Only an early press within the MISS band or automatic expiry emits a MISS. This state behavior is a deliberate M0 contract where the references do not settle every same-time input case.

The headless logical event order is deterministic: scheduled expiries first, ordered by `(expiry_time_us, lane, note_id)`, then actions ordered by `(time_us, original input index)`. One action can produce a judgement followed by its action record in the event log. An automatic miss has no hit error; an early pressed MISS retains its signed hit error. `JudgementRecord.logical_event_time_us` is the canonical judgement time; `event_time_us` remains a compatibility alias. `observed_game_time_us` is optional and remains `None` for Python-generated records. The API's `advance_to()` requires nondecreasing time. `play()` sorts supplied actions stably by time, so the input list is the tie-order authority. Replaying the same config, notes, and ordered actions produces an identical logical event sequence and JSON log. In the pinned playfield, an automatic MISS is applied on a game update; its observed `TimeAbsolute` can be later than logical expiry and vary with the update schedule. Keep logical and observed times separate in cross-runtime traces.

## Game feedback and evaluator audit

`project_b.osu.feedback` provides two deliberately separate projections. A `GameFeedbackEvent` contains only the headless logical time when a game judgement becomes available and its result label; `GameFeedbackCursor` releases it to a later reinforcement component only when the game clock reaches that time. This event is not part of the position-to-action sensory input. It does not contain note identity, scheduled time, signed hit error, action disposition, or observed frame time. A null press produces no immediate feedback event. An automatic MISS appears at its logical expiry; the pinned playfield may observe it on a later update. The normalized logical/observed mapping and DOWN/UP capture now pass L0.9a.1; raw frame-observation times still vary. The evaluator-only `FirstActionAuditOutcome` can retain scheduled timing and classify the first DOWN as too-early-null, judged miss, late, good-or-better, or no-DOWN. Never pass that audit record to the policy or learning pathway. This is an engineering event boundary; actual lazer HUD visibility and any biological response to it remain unverified. See the [L0.5 contract result](LAZER_MVP_L0_5_FEEDBACK_CONTRACT_RESULT.md) and the [L0.9a.1 result](LAZER_MVP_L0_9A_1_DUAL_TIME_ACTION_TRACE.md).

## Separation and remaining assumptions

`ManiaJudgement` holds game hit values 320/300/200/100/50/0. The tap-only `project_b.osu.scoring` layer computes pinned no-mod lazer Score V2 after the game produces a complete `GameResult`; it stays outside policy input and biological reward. The engine validates config, timestamps, note identity, and key transitions before use. It reports resolved judgements and action dispositions independently.

Remaining client-parity questions are the exact half-millisecond tie mode, fractional-OD truncation details, same-lane overlap priority in unusual dense patterns, and stable's behavior for simultaneous release/repress hardware events. These are documented rather than silently presented as measured client behavior. Native `.osu` parsing and long-note mechanics remain M12 or a separate later gate.

## Headless MVP policy adapter

`project_b.osu.adapter` defines the one-note L0.9b seam. A policy receives
`PositionObservation(visible, lane, position)` one sample at a time and returns
episode-relative `PolicyKeyTransition` values. It is not passed scheduled note
time, judgement, feedback, score, evaluator cues, or a target key. The
`HeadlessManiaTapAdapter` anchors policy time to the episode's game-time origin,
runs the game only after policy execution is complete, and then produces the
evaluator-only first-action audit. Replaying the same config, policy weights,
and observation sequence yields an identical normalized episode trace. The
current adapter supports one tap note only; it is not yet an in-process Lazer
adapter and does not establish biological learning. The separate game engine
has bounded frozen-corpus 4K event and score parity, but this adapter has not
been generalized to 4K episodes. See the
[L0.9b result](LAZER_MVP_L0_9B_ADAPTER_RESULT.md).

## Tap-only Score V2

`calculate_tap_score()` implements no-mod mania Score V2 for fully resolved
lazer tap notes. It records per-note base accuracy points, current numerator
and denominator, combo changes, combo score portion, cumulative score, and the
score delta after each judgement. The headless adapter evaluates this only
after the policy has finished. Frozen results from the pinned
`ManiaScoreProcessor` cover Perfect through Miss, a combo break/recovery, and
fresh-run reset behavior, and two 4K event/score cases. The scorer rejects
stable profiles and incomplete runs. Score multipliers, holds, Classic/Score
V1, ranking, score-frame restore, arbitrary-map parity, and in-process Lazer
integration are not implemented. See the
[L0.10 result](LAZER_MVP_L0_10_SCORE_PARITY_RESULT.md) and
[L0.11 result](LAZER_MVP_L0_11_4K_SCORE_PARITY.md).
