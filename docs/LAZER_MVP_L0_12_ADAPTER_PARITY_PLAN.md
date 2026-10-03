# L0.12 — 4K position-frame adapter and in-process parity plan

**Status:** DEFERRED BEFORE VERIFICATION by the 2026-10-03
[recreation-first priority](OSU_MANIA_RECREATION_FIRST_PLAN.md). The partial
adapter work does not establish a PASS. This policy-facing plan is no longer
the next implementation step.  
**Reference:** osu! `2026.1001.0-tachyon`, commit
`da27300fcbfa246f87c3ba1a14cbd00b68c7e9a9`; mania OD8; no mods; rate 1.

## 1. Question

Can the headless policy/game boundary deliver one simultaneous 4K frame of
current visible note positions per tick, and can its resulting timestamped
keys produce the same normalized events and Score V2 state in the pinned
osu!lazer ReplayPlayer running in-process?

## 2. Why this follows L0.11

L0.11 verified that the game model judges a small 4K tap corpus like the pinned
runtime. The existing policy adapter still processes exactly one note and one
lane per call. Repeating that call once per lane would advance the policy clock
four times as fast as the game clock. A frame contract is needed before the
policy can be connected to a 4K game episode.

## 3. Hypothesis and outcomes

- **PASS:** simultaneous current-position frames preserve causal policy input,
  and both runtime paths produce identical captured key transitions, normalized
  event order/results, and per-judgement score snapshots on both frozen cases.
- **FAIL:** an action, judgement, ordering, or score field differs after
  normalization, or the frame schema leaks schedule, note identity, result, or
  score into the policy.
- **INCONCLUSIVE:** the pinned test host cannot produce repeatable captures or
  the event normalizer cannot assign a cause to an observed judgement.

## 4. Intervention

Add a frame record containing only a tuple of visible `{lane, position}` pairs
and a headless 4K tap adapter that calls the policy once per frame. Exercise it
with a deterministic position-threshold fixture policy; this is an adapter
test double, not a fly-learning result. Generate frames at the frozen 1-ms
cadence from a 500-ms moving-note display trajectory. Capture the resulting
policy trace, then feed the exact game notes and DOWN/UP transitions to the
pinned in-process ReplayPlayer test host and compare outputs.

The two frozen cases are a simultaneous four-lane chord and one independently
triggered note in each of four lanes at staggered times. Each action is driven
by current visible position alone. No same-lane overlaps are present in this
adapter gate; L0.11 separately covers note lock and same-lane force-Miss.

## 5. Controls

Pin ruleset, OD, mods, rate, beatmap notes, visible lead, frame cadence, policy
threshold/hold, episode origin, and runtime commit. Use a fresh game, policy,
score processor, and C# player for each episode and repeated capture. The
one-note L0.9b adapter and L0.9/L0.11 runtime probes remain regressions.

## 6. Primary endpoint

Zero differences between the Python headless episode and each pinned Lazer
capture for all DOWN/UP lane/timestamp transitions, normalized ordered action
and judgement events, judgement labels/direct offsets, and each Score V2
snapshot. Floating fields compare within `1e-12`.

## 7. Secondary endpoints

Confirm the frame contains no note IDs, scheduled time, time-to-contact,
judgement, score, or target-key field; verify actions anchor to the episode
clock; verify all four lane triggers and Good-or-better first actions; verify
two identical runtime captures; retain raw observed automatic-MISS time if any.

## 8. Interpretation

Pass only if both frozen cases and repeated in-process captures meet the primary
endpoint, the policy schema audit passes, and the one-note/4K focused regression
suite passes. Any game-semantic or score mismatch is FAIL. Nondeterministic
runtime capture or unresolved event ordering is INCONCLUSIVE. Do not generalize
to arbitrary maps or four-lane biological performance.

## 9. Do not

Do not add a biology teacher, train weights, clone the current fly circuit once
per lane, expose note timing to policy, tune the threshold from results, add
holds/mods/rate changes, or claim this harness is a released osu!lazer plugin.

## 10. Output

Keep the input scenario fixture and test source under version control; keep
generated long frame traces and raw repeated captures under `work/`. Add
headless adapter tests, an in-process Lazer probe runner, a parity report,
update the minimum-MVP plan, environment contract, assumption ledger, catalog,
and append the outcome/failures to `CURRENT.md`.

## 11. Stop condition

Record PASS/FAIL/INCONCLUSIVE and exactly one evidence-based next stage after
this comparison. Do not launch that later stage as part of L0.12.
