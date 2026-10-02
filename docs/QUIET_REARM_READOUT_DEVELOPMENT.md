# Quiet-rearm readout development test

**Status: FAIL under the predeclared progression rule.** Synthetic Branch A only, 2026-09-30. The [locked protocol](../configs/quiet_rearm_readout_development.json), [32-run raw ledger](figures/quiet_rearm_readout_development/runs.jsonl), [cohort result](figures/quiet_rearm_readout_development/result.json), [source manifest](figures/quiet_rearm_readout_development/meta.json) and [independent audit](figures/quiet_rearm_readout_development/audit.json) preserve the experiment. Seeds 1000–1007 are reused development seeds, with 24 training and 16 frozen notes each; they are not fresh M2 confirmation data.

## Declared intervention

The legacy fixed readout can issue another DOWN after its 200-ms cooldown while the 20-ms motor-spike window remains above its on threshold of 10. The diagnostic readout disarms on every DOWN and rearms only after that window falls to or below the existing off threshold of 2. On threshold, off threshold, cooldown, motor population, game rules, plasticity, reward, exploration construction, map generator and train/frozen split were otherwise unchanged. No production readout file was edited.

Four matched conditions were run: unchanged plasticity-on, quiet-rearm plasticity-on, quiet-rearm plasticity-off and quiet-rearm shuffled reward. The eight unchanged summaries exactly reproduce historical development rows. The rule was promising only if quiet-rearm on had at least 6/8 strict GOOD+ wins against each comparator, lower pooled hit MAE, fewer null-first and extra DOWNs, and no increase in silent notes.

| Frozen measure across 128 notes per condition | Legacy on | Quiet-rearm on | Quiet-rearm off | Quiet-rearm shuffled |
| --- | ---: | ---: | ---: | ---: |
| Mean GOOD+ | 57.03% | **7.03%** | 0% | 19.53% |
| Pooled hit timing MAE | 59.43 ms | **97.87 ms** | undefined | 70.31 ms |
| Null DOWN actions | 66 | **0** | 0 | 5 |
| Extra DOWN actions | 66 | **0** | 0 | 2 |
| Early-MISS DOWN actions | 26 | **32** | 0 | 0 |
| Notes with no DOWN | 0 | **36** | 128 | 80 |

Quiet-rearm on strictly beat legacy in **0/8** seeds, off in **2/8**, and shuffled reward in **2/8**. It removed the repeated-press route in its true-reward branch but did not produce accurate first actions. Seed 1005 retained 43.75% GOOD+ on both readouts; several previously high-score seeds became silent or early. The shuffled branch exceeded the true-reward mean. This is a failed method, not a candidate production fix. No threshold, cooldown or rearm-duration search was made.

The result supports a narrow causal interpretation: the legacy cooldown/retrigger path accounted for much of the old GOOD+ score, but merely disabling repeated DOWNs does not correct the learner's timing credit. This intervention changes training trajectories as well as frozen readout behavior, so the cohort contrast does not isolate the readout's evaluation-only contribution. The earlier unchanged held-out action audit independently showed that 233/236 GOOD+ judgements followed a null DOWN.

## Audit and limits

The independent auditor checked protocol and source hashes, all 32 maps/configs, eight historical legacy summaries, all **2,438** saved game actions, **512** frozen outcomes, weight bounds, **747** quiet-readout disarms and **747** rearms, and recomputed cohort metrics and strict wins. It passed. A direct state-machine unit test verifies disarm, quiet rearm and subsequent DOWN. No new held-out M2 run or production learning-rule change occurred. This is evidence against this one readout intervention on these development seeds, not proof that every readout or signed-credit design must fail.
