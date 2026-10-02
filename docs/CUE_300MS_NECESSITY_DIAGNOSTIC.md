# Is the 300-ms cue-bin change necessary at outcome 373?

**Status:** complete, 2026-09-30. This is one diagnostic intervention at the already selected **synthetic** seed-2002 outcome-373 checkpoint. It is not a production learning-rule change, parameter search, additional training run or fly-circuit result. The [protocol](../configs/cue_300ms_necessity_diagnostic.json) was saved before the omission-branch probe. The [machine-readable result](figures/cue_300ms_necessity/result.json), [checkpoint files and source manifest](figures/cue_300ms_necessity/meta.json), and [independent audit](figures/cue_300ms_necessity/audit.json) retain the evidence.

## Exact checkpoint and three branches

Deterministic replay reconstructed the exact pre-dopamine event used in A3/A4: time **371.725 s**, `GREAT_300` training judgement **25 ms late**, utility **+0.875**, expected utility **−0.16280149**, and positive RPE/dopamine amplitude **+1.03780149**. All **480** pre-update weights and eligibility values, raw proposals, bounds and real clipped/applied weights matched [A4](ELIGIBILITY_TIMING_CREDIT_DIAGNOSTIC.md) exactly. Separately hashed neural state, queued arrivals, reward predictor, RNG, topology and motor/readout state also matched A4. Both no-update and full-update frozen probes reproduced A4 **exactly**, including every event and DOWN action.

The only branches were **no update**, **real full update through the production method**, and **real update except the 300-ms preferred-cue source bin**. The last branch began with the real full post-dopamine checkpoint and restored only that bin's **48 selected edge weights** to their pre-update values. The full real proposal and clipping on the other **432** edges were unchanged; no removed L1 was redistributed or rescaled. The 300-ms bin supplied **38.486106 mV** of the full **62.170043-mV applied L1**. The omission branch retained **23.683936 mV** of applied L1. Returning each branch's weights to the no-update values produced the same post-dopamine coupled state; the independent audit verified this field by field from saved checkpoints.

Each branch immediately ran the same existing **32-note A4 panel**, with plasticity and exploration off. The result saves every note event, every DOWN, all signed scored-attempt errors, every motor-spike tick batch, all readout threshold-crossing times and all readout decisions. This was a fixed-weight probe; it did not feed training.

## Predeclared interpretation

The [protocol](../configs/cue_300ms_necessity_diagnostic.json) made the mean **paired signed scored-attempt shift versus no update** primary. A negative value means earlier pressing. Before viewing the omission result, it declared a qualitatively changed branch ambiguous if it lacked all 32 paired scored attempts, did not have 64 DOWN actions, or changed the 32-null/32-scored action pattern. With comparable actions, removing at least **50%** of the full **61.71875-ms** advance would make the 300-ms bin a major necessary contributor **in this state**. Retaining at least **75%** of the early shift would mean other far-cue components suffice here. An intermediate result would be contributory without established necessity. No other bin omission or scale was tested.

## Frozen result

| Branch | Applied L1 (mV) | GOOD+/32 | Mean utility | Judgements | Mean scored-attempt error (ms) | Paired shift vs no update (ms) | DOWN actions |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| No update | 0 | **17** | **−0.111328** | 4 GREAT, 13 GOOD, 15 MEH | **−83.0000** | 0 | 64 |
| Real full update | 62.170043 | **0** | **−1.000000** | 32 MISS | **−144.7188** | **−61.7188** | 64 |
| Real except 300-ms bin | 23.683936 | **17** | **−0.111328** | 4 GREAT, 13 GOOD, 15 MEH | **−82.9375** | **+0.0625** | 64 |

The omission branch's 32 paired scored-attempt errors differed from no update by only **−1 to +2 ms** each. It has the **same judgement distribution and utility** as no update. It removes essentially **100%** of the 61.719-ms early advance; the tiny +0.063-ms residual is later, not earlier. The full update shifted every scored attempt **38–106 ms earlier** and made all 32 early MISS. There was no silence, extra DOWN, missing scored attempt or altered null/scored-action pattern after omission.

| Branch | Hit MAE (ms) | Mean all-DOWN nearest-note offset (ms) | Median all-DOWN offset (ms) | Motor spikes | Upward on-threshold crossings |
| --- | ---: | ---: | ---: | ---: | ---: |
| No update | 83.000 | −183.000 | −173.0 | 6,307 | 229 |
| Real full update | undefined: no hits | −244.719 | −245.5 | 4,644 | 303 |
| Real except 300-ms bin | 82.938 | −182.938 | −172.0 | 6,420 | 234 |

Each branch made exactly **32 early null presses followed by 32 scored presses**, with each scored press **200 ms after** its corresponding null press, matching the fixed readout cooldown. Full-update DOWN times were 38–106 ms earlier than no update; omission DOWN times were within **−1 to +2 ms** of no update. The saved readout trace gives every threshold-crossing timestamp and spike-window count. For example, the first upward on-threshold crossing and DOWN were at **372.456 s** for no update and omission, versus **372.383 s** for full update. The complete trace, not this example, supports the timing comparison. More motor spikes did not imply earlier presses: omission had slightly more motor spikes than no update yet almost identical DOWN timing.

## Interpretation and limits

**The 300-ms bin is a major necessary contributor to the harmful shift in this exact combined update.** Omitting its 48 applied changes while retaining every other real change returned action timing, GOOD+ and utility to the no-update level. This proves a causal necessity statement for this **one selected checkpoint and tested combination**. It does not prove that every 300-ms edge is individually necessary, that the 300-ms component alone is sufficient, or that any other seed/checkpoint behaves similarly. The retained 23.684-mV update had little timing effect here; applied L1 alone is not a behavioral attribution rule.

The threshold/readout record suggests the next **single mechanistic question**: **Does the 300-ms potentiation cause the earlier *first* motor threshold crossing/null press, with the fixed 200-ms cooldown carrying that advance to the scored press?** The present traces show the temporal alignment, but do not causally separate early motor drive from cooldown mediation. No further intervention was run.

## Verification and execution record

The independent [audit](figures/cue_300ms_necessity/audit.json) passed **3 branches, 96 frozen note outcomes, 192 DOWN actions, 48 omitted edges and 766 upward on-threshold crossings**. It loaded every saved checkpoint; independently reapplied zero and real dopamine from the pre-state; checked all 480 raw proposals and applied weights; verified that only the 300-ms edges differ between full and omission; compared all other coupled state fields; reran each frozen probe; and reconstructed every readout threshold crossing and decision from the motor-spike batches. It independently recomputed judgements, utility, hit errors, DOWN nearest-note offsets and paired timing.

The first reconstruction attempt stopped **before any probe** because whole-session pickle bytes differed across processes despite identical component state, a previously observed serialization issue. The replay check was repaired to require exact A3/A4 update geometry plus separate neural, queue, RNG, reward, topology and readout-state equality. The first audit attempt also compared whole-session pickle bytes after loading; it was repaired to compare every coupled session field independently. Both failures and repairs left the one-bin protocol unchanged. The full `unittest` suite passed **107 tests**. No additional training, other omission or production-rule change occurred.
