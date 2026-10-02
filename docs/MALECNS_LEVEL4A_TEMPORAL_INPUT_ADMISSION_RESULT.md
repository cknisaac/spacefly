# MaleCNS Level 4A — temporal-input admission result

**Result:** **PASS**  
**Shortest admitted duration:** **500 ms**  
**Learning runs:** 0  
**DAN teaching events:** 0

## Protocol and fixed settings

The single moving note traversed linearly from `x=1.0` to `x=0.0`. The only
varied setting was traversal duration: 100, 250, 500, 750, or 1,000 ms. Every
duration was run twice from fresh resting state. The input at each 1-ms step
was the current note position only. We kept the same 32 KCs, MBON05, Gaussian
encoder (`σ=0.08`, 1.2 mV-equivalent peak drive), LIF/contact model, immutable
original weights, fixed threshold (`0.005572335995331903`), position grid,
readout, and DAN identities. No DAN was stimulated and no weight changed.

“Meaningful MBON response” was frozen before the sweep as activity above the
fixed action threshold in at least three adjacent 0.05-wide position bins.
Replay equality required exact agreement in KC spike events/counts, per-tick
position and MBON trace, position map, and action positions.

## Duration results

| Duration | Total KC spikes | Spiking KCs | Peak MBON05 (mV) | Action positions | Action everywhere? | Deterministic | Admission |
|---:|---:|---:|---:|---|---|---|---|
| 100 ms | 0 | 0 | 0.000000 | all 21 bins, 0.00–1.00 | Yes | Pass | **Fail** |
| 250 ms | 0 | 0 | 0.000000 | all 21 bins, 0.00–1.00 | Yes | Pass | **Fail** |
| 500 ms | 30 | 30 | 0.012560 | 0.95, 1.00 | No | Pass | **Pass** |
| 750 ms | 57 | 31 | 0.017854 | 1.00 | No | Pass | **Pass** |
| 1,000 ms | 60 | 31 | 0.015944 | 1.00 | No | Pass | **Pass** |

The longest contiguous run of above-threshold bins was 0, 0, 19, 20, and 20
for durations 100, 250, 500, 750, and 1,000 ms respectively.

The 30 KCs spiking at 500 ms were source IDs:

`45199, 45259, 45380, 45434, 45460, 45467, 45620, 45950, 46497, 47101, 47117, 47287, 47694, 47758, 47988, 48337, 48596, 48759, 49124, 49160, 49526, 49544, 49545, 49867, 50411, 50568, 50591, 50791, 50820, 51053`.

At 750 and 1,000 ms, those 30 cells plus KC `51055` spiked. Total spike counts
include repeat spikes from the same KC.

### Position → MBON/action map at the selected 500-ms duration

| Position | MBON05 max voltage (mV) | Action |
|---:|---:|---|
| 0.00 | 0.0104195 | no-action |
| 0.05 | 0.0125500 | no-action |
| 0.10 | 0.0118227 | no-action |
| 0.15 | 0.0093996 | no-action |
| 0.20 | 0.0096167 | no-action |
| 0.25 | 0.0100097 | no-action |
| 0.30 | 0.0090440 | no-action |
| 0.35 | 0.0116832 | no-action |
| 0.40 | 0.0113785 | no-action |
| 0.45 | 0.0119541 | no-action |
| 0.50 | 0.0120813 | no-action |
| 0.55 | 0.0109014 | no-action |
| 0.60 | 0.0104115 | no-action |
| 0.65 | 0.0108778 | no-action |
| 0.70 | 0.0118873 | no-action |
| 0.75 | 0.0123836 | no-action |
| 0.80 | 0.0125603 | no-action |
| 0.85 | 0.0120725 | no-action |
| 0.90 | 0.0109742 | no-action |
| 0.95 | 0.0000000 | ACTION |
| 1.00 | 0.0000000 | ACTION |

At 500 ms, 19 adjacent bins from 0.00 through 0.90 exceed the threshold,
satisfying the predeclared meaningful-response criterion. The baseline is not
action everywhere. Exact MBON timecourses and position maps for every
duration, along with every KC spike event and replay digest, are in the full
JSON receipt.

## Admission decision

The 100- and 250-ms durations fail because no KC spikes occur, MBON05 remains
at zero, and all positions are actions. The 500-ms duration is the shortest
tested duration that passes all four admission gates. The Level 4 moving-note
speed is frozen at **500 ms per traversal**. The 750- and 1,000-ms runs are
reported only as predeclared comparisons; they do not replace the shortest
passing duration.

This is an input-admission result only. It does not demonstrate learning and
does not authorize a learning run. Level 3B's recorded strict FAIL remains
unchanged and frozen.

## Receipts

- [Frozen Level 4A config](../configs/malecns_level4a_temporal_input_admission.json)
- [Level 4A full result and timecourses](../runs/malecns_level4a_temporal_input_admission/result.json)
- [Frozen selected-speed Level 4 config](../configs/malecns_level4_moving_note_admitted_500ms.json)
- [Level 4A protocol](MALECNS_LEVEL4A_TEMPORAL_INPUT_ADMISSION.md)
- Focused Level 4A tests: **2 passed**; module/test compilation passed.

Config SHA-256: `87c32e77e054948049ae89e685024d29d5653ada98c7d3834e694364d4e7baaf`  
Result SHA-256: `2e78ba9c64375cad707b920b32455151f011fdc95fad67fcf0eb6940dd41829f`  
Selected-speed config SHA-256: `95abdc36736bcdb8f890ab2ff48a5e64ba2aefd41f48a920d21c6ac110ba18af`
