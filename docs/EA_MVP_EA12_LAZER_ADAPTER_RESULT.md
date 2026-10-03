# EA-MVP EA-12 — pinned osu!lazer runtime adapter

**Decision: PASS for the tested headless event-adapter contract against the pinned in-process osu!lazer runtime.**

## Reference and method

The comparison used osu!lazer source revision `da27300fcbfa246f87c3ba1a14cbd00b68c7e9a9` (tag `2026.1001.0-tachyon`) and its in-process `ReplayPlayer` test host. A C# test harness received timestamped key actions and returned judgement and score events. The Python headless game replayed the same map objects and actions; the harness compared event count, judgement, combo, score, and accuracy.

The hold adapter exercised three exact EA-11 generated traces:

| Hold | Lane | Note interval | Actions sent to lazer | Result |
| --- | ---: | --- | --- | --- |
| Short | 0 | 500–800 ms | DOWN 501 ms; UP 800 ms | 4/4 events matched; 1,000,000 score |
| Medium | 1 | 1,500–2,500 ms | DOWN 1,501 ms; UP 2,500 ms | 4/4 events matched; 1,000,000 score |
| Long | 3 | 3,300–6,800 ms | DOWN 3,301 ms; UP 6,800 ms | 4/4 events matched; 1,000,000 score |

Each case matched the head, tail, body, and parent events, including combo and score. The runner also repeated six pre-existing hold timing/control cases. Separately, the pinned four-key adapter probe passed twice for the frozen position-frame episodes, matching actions, normalized events, and Score V2.

Relevant code is `scripts/run_ea_mvp_lazer_hold_adapter.py`, `scripts/lazer_hold_probe/EA11ModelHoldProbe.cs`, and `scripts/run_lazer_4k_adapter_probe.py`. The pinned upstream source is held under `work/osu_lazer_reference`.

## Limits

This validates event translation and judgement parity inside lazer's replay test runtime. It did **not** launch or send input to the desktop osu!lazer client, test operating-system key injection or display timing, or run the full chord map through the lazer host. Therefore it is an adapter/runtime parity result, not evidence of live-client play. The EA-10 chord and EA-11 hold learner results remain headless game results, with the hold actions independently checked against the pinned runtime.
