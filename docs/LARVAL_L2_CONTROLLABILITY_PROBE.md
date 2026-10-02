# Candidate L2 pre-training controllability probe

**Result: FAIL for the frozen electrical reference (2026-10-02).** No learning, teaching, or exploration ran.

## Frozen protocol

The probe used the 127-node/131-edge anatomy manifest and electrical model v1 without changing either. It replayed each of the eight fixed current-position KC patterns for 100 ms and varied only the KC→MBON-d1 edge-weight multiplier over the predeclared set `[0, 0.25, 0.5, 1, 2, 4]`. The sensory pulse, downstream weights, positive-sign electrical overlay, delays, LIF parameters, zero background, and one-Goro-spike action threshold remained fixed. Plasticity, teaching, and exploration were off.

Hashes: manifest `84fb7af5160a405a072170466ea19e134cd12bc61ed1a7c565f301972da07c89`; model `76a6f2612ed1361f86b061f8a4da117715456d748f3aa7d8384bdb4db9291952`; result `runs/larval_l2_controllability_probe_v1.json`.

## Measurements

| KC→MBON-d1 multiplier | KC spikes across 8 states | MBON-d1 spikes | Ipsigoro spikes | Goro spikes | Action states |
|---:|---:|---:|---:|---:|---:|
| 0 | 238 | 0 | 0 | 0 | 0/8 |
| 0.25 | 238 | 0 | 0 | 0 | 0/8 |
| 0.5 | 238 | 0 | 0 | 0 | 0/8 |
| 1 | 238 | 0 | 0 | 0 | 0/8 |
| 2 | 238 | 1 | 0 | 0 | 0/8 |
| 4 | 238 | 7 | 0 | 0 | 0/8 |

All 48 state/multiplier cells reproduced deterministically. Frozen hashes matched, the factor-1 condition exactly matched the neutral-dynamics artifact, all recorded voltages and drives were finite, and no safety stop occurred.

## Decision and limits

**FAIL:** the intended weights can occasionally evoke MBON-d1 spikes at the upper tested multipliers, but no tested state produces Ipsigoro/Goro activity or a fixed action. Therefore the frozen pathway lacks demonstrated control authority to expose KC→MBON learning as behavior. Do not begin plasticity or task learning on this model. Do not tune beyond the predeclared range to force a pass.

This is a failure of the explicitly artificial electrical reference, not evidence that the living larval circuit lacks learning. The probe does not isolate whether failure comes from assumed synaptic scaling/signs, omitted inputs, the measured downstream contact route, or the fixed Goro-to-action interface. Any new candidate/model requires a separately versioned, independently justified design before another confirmation attempt.
