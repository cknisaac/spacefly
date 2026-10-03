# L0.11 — frozen 4K tap event and score parity

**Date:** 2026-10-03  
**Status:** **PASS** for the frozen no-mod 4K tap corpus.

This stage checks the headless game's ordered lane actions, judgements and
Score V2 snapshots against osu!lazer's pinned `ReplayPlayer` and score
processor. It establishes a bounded game-engine result. It does not show that
the fly policy learned to play, or that an in-process Lazer adapter exists.

## Pinned reference and cases

The C# probe ran at osu! commit
`da27300fcbfa246f87c3ba1a14cbd00b68c7e9a9`
(`2026.1001.0-tachyon`), OD8, no mods, rate 1, default Score V2.
Input scenarios are frozen in
`tests/fixtures/lazer_mvp_4k_score_scenarios.json`; pinned runtime output is in
`tests/fixtures/lazer_mvp_4k_score_reference.json`.

The two cases cover:

- Four lanes with Perfect, Great, Good, and automatic Miss results, including
  one missed lane that does not stop the other lanes from resolving.
- A too-early null press followed by a same-lane retry at the next note's
  start, a simultaneous cross-lane chord, and the earlier same-lane note's
  force-Miss. Score snapshots include combo break and recovery.

Both inputs retain integer-microsecond timestamps and explicit key transitions.
The probe checks captured DOWN/UP transitions against those inputs and
normalizes frame-observed automatic-MISS time separately from deterministic
logical event time.

## Verification

The pinned C# NUnit probe passed twice. Its captured key transitions,
normalized event order, judgement labels, per-judgement score fields, accuracy
and combo state matched between runs and the frozen reference. The Python
headless output also matched every normalized event and score field in both
scenarios; float fields use a `1e-12` tolerance.

```text
python scripts/run_lazer_4k_probe.py
PASS: pinned 4K replay and Score V2 output repeat identically and match the frozen fixture.
```

Three Python parity tests and the focused regression set passed **73 tests**
across 4K score parity, score, adapter, current-position policy/readout,
capacity, feedback, frozen event corpus, game environment and timing windows.
The older L0.9 pinned runtime probe was rerun after isolating the new test
class; all three NUnit probe tests passed on both runs, and all nine normalized
scenario traces still matched.

The first C# build failed because the new probe lacked
`osu.Framework.Screens`, which provides the `IsCurrentScreen()` extension used
by the existing replay test pattern. Adding that namespace fixed compilation;
the subsequent repeated C# run and all parity checks passed.

## Scope limits and next gate

The corpus has two hand-written cases. It does not establish parity for
arbitrary maps, dense same-lane patterns, holds, mods, rate changes, score
restore, or raw automatic-MISS frame timestamps. The Python policy adapter
still accepts exactly one tap note, and this probe does not place the fly or
its policy inside the Lazer process. The real current-position policy still
produces no DOWN on the one-note 500-ms case. L0.6 remains
**INCONCLUSIVE / NO-GO** for biological teaching and training.

**L0.11 PASS** for the frozen no-mod 4K tap corpus.  
**Sole next proposed stage:** L0.12 — generalize the position-only adapter to
4K episodes and connect the same frozen observations/actions to an in-process
osu!lazer test host, comparing normalized event and score output.
