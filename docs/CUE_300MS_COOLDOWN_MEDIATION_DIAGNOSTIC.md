# First threshold crossing and cooldown mediation at outcome 373

**Status:** complete, 2026-09-30. This is a readout diagnostic on the previously selected synthetic seed-2002 outcome-373 checkpoint. It uses the saved A5 no-update and real-full post-dopamine checkpoints. No training, weight change, production-readout edit or parameter search was performed. The [one-intervention protocol](../configs/cue_300ms_cooldown_mediation_diagnostic.json) was fixed before the new probes; the [raw result](figures/cue_300ms_cooldown_mediation/result.json), [source manifest](figures/cue_300ms_cooldown_mediation/meta.json) and [independent audit](figures/cue_300ms_cooldown_mediation/audit.json) contain complete event, motor-spike and readout traces.

## Question and causal comparison

A5 showed that omitting the 300-ms cue-bin update returned first-note and panel timing almost exactly to no update. In the original 32-note probes, each scored DOWN followed an earlier null DOWN by exactly the readout's fixed **200-ms cooldown**. This test asked whether the **first scored press is actually gated by that cooldown**, rather than merely occurring 200 ms later by coincidence.

Four frozen probes used the same two saved checkpoints, 32 notes and cue gains: no update and real full update under the unchanged readout, then those two states under one diagnostic readout perturbation. Immediately **after the first null DOWN**, the perturbation extended `cooldown_us` from **200,000 to 201,000 µs** until the next DOWN, then restored 200,000 µs. One millisecond is the simulator's existing tick, selected before results. It did not change the first DOWN, spike input, sensory encoding, scoring windows, hold/off thresholds or any synaptic weight. Plasticity and exploration stayed off. The unmodified probes reproduced A5 exactly.

The [locked interpretation](../configs/cue_300ms_cooldown_mediation_diagnostic.json) required an unchanged first upward threshold crossing and null DOWN, followed by an **exactly +1-ms** second DOWN in **both** weight states, with motor activity still above threshold at the original second-DOWN tick. A missing, extra or later-than-expected action would instead indicate nonlinear or drive-limited behavior. The **first note** was primary; later panel outcomes are secondary because shifting a judgement can change subsequent closed-loop state.

## First-note result

| Weight state / readout | First on-threshold rise and null DOWN (s) | First scored DOWN (s) | Gap (ms) | Scored error (ms) | Judgement |
| --- | ---: | ---: | ---: | ---: | --- |
| No update / unchanged | 372.456 | 372.656 | **200** | −69 | GOOD |
| No update / first cooldown +1 ms | 372.456 | 372.657 | **201** | −68 | GOOD |
| Real full update / unchanged | 372.383 | 372.583 | **200** | −142 | MISS |
| Real full update / first cooldown +1 ms | 372.383 | 372.584 | **201** | −141 | MISS |

The real update advanced the **first motor on-threshold crossing and null DOWN by 73 ms**, and the first scored DOWN by the **same 73 ms**. The diagnostic extension left the first threshold crossing/null DOWN **exactly unchanged** and delayed the scored DOWN **exactly 1 ms** in both states. Motor-spike batches were identical to their respective reference through the original scored-DOWN tick. At that tick, the motor readout had **32 spikes** in its 20-ms window with no update and **26** after the real update, both above its on-threshold of **10**. The extended cooldown alone prevented DOWN at that tick; the DOWN occurred on the next tick, with the spike-window count still above threshold.

The full 32-note runs remained the same category distribution as their respective references: no-update branches **17/32 GOOD+**, mean utility **−0.111328**; real-full branches **0/32 GOOD+**, mean utility **−1**. All four produced **64 DOWN actions**. The one-tick intervention shifted first-note scoring by 1 ms and each branch's panel mean scored-attempt error by only **+0.03125 ms** (no update **−83.000→−82.96875 ms**; real full **−144.71875→−144.6875 ms**). These whole-panel values are descriptive, not another optimization target.

## Conclusion and boundary

At the first note of this exact checkpoint, the **300-ms-dependent full weight update caused an earlier motor threshold crossing and first null press**. The readout's **200-ms cooldown was the binding gate for the following scored press**: a one-tick cooldown extension delayed only that second press by one tick in both weight states. This supports a concrete local chain: earlier motor drive → earlier null DOWN → cooldown expiry → earlier scored DOWN/MISS. The cooldown **transmits** the advance; it does not explain why the 300-ms weight change made motor drive cross threshold earlier.

This is one selected synthetic checkpoint and one first-note causal perturbation. It does not prove that the same cooldown gate controls every note, that the 300-ms component alone is sufficient, or that changing cooldown would improve learning. No production cooldown change is proposed. The next single mechanism question is **which 300-ms relay→motor changes produce the earlier first motor threshold crossing**, without choosing a favorable edge mask by post hoc score.

## Verification and execution record

The independent [audit](figures/cue_300ms_cooldown_mediation/audit.json) passed **4 frozen branches, 128 note outcomes, 256 DOWN actions and 1,064 upward on-threshold crossings**. It verified source checkpoint/result hashes; reran all four frozen probes, including the diagnostic wrapper; independently reconstructed every readout threshold crossing and decision from recorded motor-spike ticks; recomputed first-note events and utility/judgement counts; and checked the prespecified 1-ms effect and unchanged upstream spikes. The full project `unittest` suite passed **111 tests**. No new training replay or production code edit was needed.
