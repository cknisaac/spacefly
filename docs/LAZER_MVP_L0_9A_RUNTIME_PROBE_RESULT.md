# L0.9a pinned osu!mania replay-host probe

**Status:** **INCONCLUSIVE for full event-time parity**; judgement and playable
boundary subgates pass  
**Pinned release:** `2026.1001.0-tachyon`  
**Pinned commit:** `da27300fcbfa246f87c3ba1a14cbd00b68c7e9a9`  
**Biological learning:** none; no teacher, weight update, or training run

## Scope

This probe runs frozen OD8 note/action cases through osu!'s pinned Mania test
host, using its real `ReplayPlayer`, playfield, key-binding path and
`ScoreProcessor.NewJudgement` notifications. It complements the linked-source
timing and note-lock checks; it does not replace them or cover cumulative score
totals, holds, mods, rate changes or a graphical desktop session.

Run it with:

```powershell
python scripts/run_lazer_runtime_probe.py
```

The runner verifies the pinned Git commit, injects the test scene from
[`L0ParityProbe.cs`](../scripts/lazer_runtime_probe/L0ParityProbe.cs) into the
local pinned test project, and runs it serially. The C# project build and all
three discovered NUnit tests passed. The raw nine-line output is kept in the
ignored local artifact `work/lazer_runtime_reference_probe.jsonl` (SHA-256
`b09d15bfe4a14aba733dde7f9c80f7055ff2aa3e15ed646459a7a8420636f4d8`).

## Results

- The pinned Mania production project built with zero warnings and errors.
- The upstream `TestSceneOutOfOrderHits.TestPreviousHitWindowDoesNotExtendPastNextObject`
  passed in osu!'s test host.
- All eight frozen game scenarios passed for judgement identity, lane,
  judgement order and action-caused timing offset. This includes the early
  judged MISS, an ignored too-early press, late MEH at +127.500 ms, expiry
  before a press at +127.501 ms, no press, same-lane ordering and a four-lane
  chord.
- All 24 signed vectors passed against the pinned `HitWindows` methods in the
  linked-source runner. The full replay host also passed 24 playable input
  boundary cases: it recorded the expected direct result and offset when the
  note was still active, and no direct result when expiry ran first. The
  existing Python `GameEnvironment` returned the same reachable press outcomes
  for these 24 cases.
- The pure timing classifier's late MISS interval extends through +164.500 ms,
  but the playable note expires immediately after the last successful MEH
  window at +127.500 ms. A key arriving at +127.501 ms or later cannot use the
  classifier's remaining late MISS interval: the automatic MISS is applied
  first. This is why the method-level boundary vectors and game-input vectors
  must remain separate.

## Remaining mismatch

The judgement and direct-input results match, but the automatic MISS callback
time is the game time at which an update observes expiry. It changes with the
test host's frame schedule. Across repeated runs of the same null-press cases,
the too-early case reported offsets of 128.680 ms and 130.632 ms; the no-press
case reported 127.922 ms and 142.968 ms. The headless event queue records the
deterministic logical expiry at 127.501 ms.

These are two different times: the note's logical expiry and the frame when
Lazer reports the result. Current traces store one `event_time_us`, so exact
raw timestamp parity and a deterministic full trace have not passed. This is
not a judgement-label mismatch. The event contract needs separate logical
and observed timestamps while retaining the raw Lazer value.

The replay test scene also writes the scheduled input frames into the game and
observes scoring callbacks; it does not yet expose a standalone action-event
recorder from inside `Column`. Score totals and accuracy accumulation remain
unverified.

## Crash screenshot

The attached Windows dialog names `LazerRuntimeReference.exe`, the temporary
standalone probe, rather than the pinned osu!lazer game or test host. Rebuilding
and launching the current probe both directly and through `dotnet` returned
exit code 0; the failure did not reproduce, and the application event log had
no matching error. The standalone probe bypassed Lazer's object lifetime and
is not the authoritative parity path; use the replay-host command above. No
root cause can be assigned to the pictured crash from the available evidence.

## Decision and next gate

L0.9a remains **INCONCLUSIVE** for full event parity. Its timing-method,
note-lock, judgement-sequence and reachable-boundary subgates pass. Do not
start L0.9b adapter conformance or score-total implementation yet.

The sole next proposed gate is **L0.9a.1 — logical and observed event-time
contract**: record deterministic logical expiry time separately from
`JudgementResult.TimeAbsolute`, capture every key DOWN/UP input transition,
and compare repeated normalized traces. Require zero differences in logical
event identity/order/result, direct-press offset and action transitions while
keeping raw observed times as diagnostics. L0.6 remains **INCONCLUSIVE / NO-GO**
for biological teaching and training.
