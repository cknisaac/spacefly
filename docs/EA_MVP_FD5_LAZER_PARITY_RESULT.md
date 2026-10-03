# EA-MVP FD-5 — pinned lazer replay parity

**Status: PARTIAL.** Input transitions and per-object judgements match; full-map score parity remains unverified.

The exact *Freedom Dive 4K Normal* chart (SHA-256 `ced99e231e7eee354feef04bbcde6889178814cb688325bccdeeeacb00dcbff9`) and frozen FD-4 trace were submitted to the in-process osu!lazer ReplayPlayer at pinned commit `da27300fcbfa246f87c3ba1a14cbd00b68c7e9a9`.

The host timed out when asked to play the full 261-second map in one ReplayPlayer episode. The parity harness therefore used 17 consecutive chart segments, each cut at a boundary with no hold crossing and given a fixed one-second neutral lead-in. These are runtime harness choices; they do not change the fly trace, map, or note timing. The segment inputs collectively contain the exact 2,618 actions from FD-4.

| Check | Result |
|---|---:|
| Captured key transitions | 2,618 / 2,618 exact, on both runs |
| Tap/head/tail chart judgements | 1,400 / 1,400 matched to the same objects and result labels |
| Non-miss judgement offsets | Exact |
| Normalized event replay repeat | Exact after ordering by chart object and excluding scheduler-dependent miss offsets |
| Per-segment accuracy/combo | Same on the compared recreation and lazer segments, except one segment's maximum-combo tie |
| Per-segment total score | Five of 17 segments differed; repeat runs also changed score on those segments |

The ReplayPlayer emitted 1,580 judgement callbacks: the 1,400 comparable taps/heads/tails plus 180 internal hold-body/parent events. The extra callbacks are lazer hold bookkeeping, not extra chart objects.

The score difference is confined to the ReplayPlayer test harness: individual chart-object outcomes and action transitions stay the same while callback order changes for misses and hits near one another. Because ScoreV2's combo-score portion depends on judgement order, five segment totals varied; one segment's maximum combo also varied by one. The host's time-limited segmented run cannot establish an uninterrupted full-chart score/accuracy/combo comparison. We preserve this limitation and do not tune the fly model to it.

This is pinned source/runtime test-host evidence, not a test of the installed lazer desktop app, physical keyboard injection, or audio/video synchronization. Raw receipts: `runs/ea_mvp/fd5_lazer_parity_probe_capture_v5.json` and `runs/ea_mvp/fd5_lazer_parity_v5.json`. Re-run with `python scripts/run_ea_mvp_fd5_lazer_parity_v5.py`, then regenerate the audit with `python scripts/audit_ea_mvp_fd5_lazer_parity.py`.
