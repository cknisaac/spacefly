# One-lane lazer MVP L0.5 feedback-event contract

**Stage:** L0.5 — causal feedback-event contract  
**Status:** **PASS for event-contract engineering only**  
**Learning/teaching:** none; no utility, DAN signal, or weight change

## Contract

The reinforcement-facing record is `GameFeedbackEvent(available_at_us,
judgement_label)`, delivered by `GameFeedbackCursor` only once the current
game clock reaches that time. It is separate from the policy's sensory input,
which remains current note position only. The event deliberately omits note
ID, scheduled note time, signed hit error, action disposition, and derived
timing target. A judged result is available at the event timestamp emitted by
the headless game engine. A `NULL_PRESS` itself produces no feedback event. An
automatic MISS becomes available only when the note expires.

The evaluator has a separate `FirstActionAuditOutcome` record. It can contain
the note identity, scheduled time, first-DOWN timestamp and signed error, the
game disposition, later-DOWN count, and final judgement. This record is for
test and analysis only; it must not be passed to the policy or a biological
teacher.

## Frozen cases and results

| Case | First-action audit | Policy-facing feedback |
|---|---|---|
| Press at −160 ms | `early_judged_miss`; first action judged MISS | MISS at the press time |
| Press at +90 ms | `late_judged`; result OK | OK at the press time |
| Press at −200 ms, release, then on-time retry | `too_early_null`; later retry does not rewrite first action | No event at the null press; PERFECT at retry time |
| No press | `no_down`; automatic expiry | MISS at expiry |
| Press at −200 ms, no retry | `too_early_null`; later automatic expiry | Same public MISS event as no-press, at expiry |
| Press exactly at expiry | `late_null`; expiry is ordered before the action | MISS at expiry; no judgement information on the null press |

The primary first-action audit uses the pinned 73,500-µs Good window. The
reinforcement-facing projection contains exactly two fields and has no way to
tell a null-then-expiry MISS from a no-press MISS using game feedback alone.
The action system can retain its own motor history, but no timing-specific
teacher interpretation is implemented.

## Verification and limits

Nine focused tests cover the frozen cases, note/event timing, retry behavior,
expiry ordering, hidden-field separation, signed negative timestamps and
input validation. The same-time expiry test confirms the headless engine
emits expiry before a same-time action. Cursor tests confirm no event is
returned before its timestamp, events are delivered only once, and the game
clock cannot move backwards.

This is a headless interface contract, not verification of lazer's rendered
judgement UI. It establishes when the model's game engine emits a result; it
does not establish that a biological fly can perceive that result, or how a
result should alter dopamine, PAM firing, utility, or synaptic plasticity.
The distinction between too-early null and no press remains evaluator-only
unless an independently justified observable signal is added.

## Stop and next proposal

No teacher signal or learning run followed. The next proposed gate is a
read-only research audit of whether primary evidence supports a timing- and
outcome-specific teaching rule for the frozen MaleCNS γ4 KC→MBON05 fixture.
If evidence does not justify the rule, stop the biological learning route
here rather than assigning a convenient reward polarity.
