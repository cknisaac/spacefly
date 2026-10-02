# M0 osu!mania environment contract

## Scope and references

M0 judges generated 4K tap-note scenarios without graphics, audio, neural simulation, reward, or training. It supports native stable mania as the canonical profile (`OD=8`) and stable converted-map windows as a separately selected profile. Lazer, ScoreV2, rate-changing mods, native `.osu` parsing, scoring/accuracy, and hold-note judgement are not implemented. Hold-note records are rejected, never silently reduced to taps. The [official osu!mania judgement page](https://osu.ppy.sh/wiki/en/Gameplay/Judgement/osu!mania), [overall-difficulty page](https://osu.ppy.sh/wiki/en/Beatmap/Overall_difficulty), and [note page](https://osu.ppy.sh/wiki/en/Gameplay/Hit_object/Note) are the rules references. The Project B master specification supplies the OD8 canonical values.

## Time and window contract

- All note, action, expiry, and judgement times are signed 64-bit **integer microseconds**. Only OD formulas use exact decimal arithmetic. No accumulated frame delta controls judgement.
- `ManiaHitWindows.from_od(od, ruleset)` accepts OD 0 through 10. Native stable integer-ms thresholds are `MAX=16`, `GREAT=int(64-3*OD)`, `GOOD=int(97-3*OD)`, `OK=int(127-3*OD)`, `MEH=int(151-3*OD)`, and early `MISS=int(188-3*OD)`. `int` truncates the positive formula toward zero. OD8 is 16/40/73/103/127/164 ms.
- The stable-convert profile has thresholds 16/34/67/97/121/158 ms for OD > 4 and 16/47/77/97/121/158 ms otherwise, per the official judgement page. The converted profile is a window choice for generated notes; native `.osu` conversion is not in M0.
- Absolute microsecond error is rounded to a whole millisecond using nearest, **ties to even**. This is an explicit interpretation of the wiki's rounded-hit-error statement; the half-millisecond tie mode is not specified there. The exact tie choice must be checked against stable-client evidence before claiming sub-ms client parity. Threshold equality is included.
- A press in the early `MEH` band earns 50. A press after early `MEH` but within the early `MISS` band consumes that note as MISS. A press before the early `MISS` band is a `NULL_PRESS` and does not consume a note. On the late side, a note expires at the **first microsecond** whose rounded error exceeds the `OK` threshold. No late MEH is possible. Expiry events are processed before key actions at the same timestamp. The OD8 late expiry is at note time +103,500 µs under the chosen tie rule.
- The displayed ±127 ms MEH number is therefore **not** a symmetric usable hit band. The engine preserves this stable-native asymmetry rather than treating +127 ms as a 50.

## Event and key semantics

Each lane holds tap notes in timestamp order. The earliest unresolved note in a lane has priority when a fresh key-down arrives; this is the explicitly chosen same-lane overlap/notelock approximation. Other lanes are independent. Same-lane duplicate notes at one timestamp are rejected. Cross-lane chords are separate notes and can be judged simultaneously.

A key-down from the up state attempts a judgement and leaves the key down. A repeated down while held is recorded as `repeat_down` and makes no second judgement. A key-up releases; repeated up is recorded as `repeat_up`. A press with no candidate judgement is `null_press`, which is **not** an osu MISS. Only an early press within the MISS band or automatic expiry emits a MISS. This state behavior is a deliberate M0 contract where the references do not settle every same-time input case.

Event order is deterministic: scheduled expiries first, ordered by `(expiry_time_us, lane, note_id)`, then actions ordered by `(time_us, original input index)`. One action can produce a judgement followed by its action record in the event log. An automatic miss has no hit error; an early pressed MISS retains its signed hit error. The API's `advance_to()` requires nondecreasing time. `play()` sorts supplied actions stably by time, so the input list is the tie-order authority. Replaying the same config, notes, and ordered actions produces an identical event sequence and JSON log.

## Separation and remaining assumptions

`ManiaJudgement` holds game hit values 320/300/200/100/50/0. No biological reward, score, accuracy, or action-cost function is present in M0. The engine validates config, timestamps, note identity, and key transitions before use. It reports resolved judgements and action dispositions independently.

Remaining client-parity questions are the exact half-millisecond tie mode, fractional-OD truncation details, same-lane overlap priority in unusual dense patterns, and stable's behavior for simultaneous release/repress hardware events. These are documented rather than silently presented as measured client behavior. Native `.osu` parsing and long-note mechanics remain M12 or a separate later gate.
