# MaleCNS Level 4B — moving-note output-admission repair

**Date:** 2026-10-02  
**Protocol:** `MALECNS-LEVEL4B-MOVING-OUTPUT-ADMISSION-REPAIR-v1`  
**Result:** **PASS**

## Frozen change

Level 4A selected the shortest admitted traversal, 500 ms. The naive baseline
still emitted threshold actions at x=1.00 and 0.95 before any KC had fired:
MBON05 was 0 mV there, below the inherited threshold. Level 4B added one fixed,
non-trainable validity rule: reset output validity at the start of each note,
disable action output until the first KC spike of that note, then apply the
existing MBON05 threshold unchanged. The threshold remains
0.005572335995331903 mV.

Everything else stayed fixed: the 32 KCs, MBON05, Gaussian encoder and
1.2-mV-equivalent peak drive, LIF/contact model, 500-ms x=1→0 trajectory, DAN
ensemble identity, learning rate, weight floor, and learning rule. DAN was not
stimulated; plasticity and learning were off. Weights did not change.

## Admission result

| Gate | Evidence | Result |
|---|---|---|
| KC activity | 30 spikes from 30 KCs; first spike at 41,000 µs (x=0.92) | PASS |
| MBON response | Peak MBON05 voltage 0.012560271403014864 mV | PASS |
| No startup action before sensory activity | Output disabled for every sample before the first KC spike | PASS |
| No naive action in target/wrong regions | No action at x=0.65/0.70/0.75 or x=0.15/0.20/0.25 | PASS |
| Deterministic replay | Both fresh runs have identical SHA-256 trace signature `fb4d82aaf0d4a585f6e2b35979831a8d18547c1dc80f8b9f771357f665420ec1` | PASS |

The old raw threshold map would label x=0.95 and 1.00 as actions. Under the
frozen validity rule those two bins are **disabled**, because they contain no
post-spike samples. In the enabled bins, the existing threshold produces
no-action throughout the naive trajectory. The output is not treated as an
action at disabled positions.

## Final position map

Values are maximum MBON05 voltage in the bin using enabled samples only.

| Position | MBON05 max (mV) | Output |
|---:|---:|---|
| 0.00 | 0.010419458 | No action |
| 0.05 | 0.012549959 | No action |
| 0.10 | 0.011822665 | No action |
| 0.15 | 0.009399618 | No action |
| 0.20 | 0.009616663 | No action |
| 0.25 | 0.010009680 | No action |
| 0.30 | 0.009044010 | No action |
| 0.35 | 0.011683159 | No action |
| 0.40 | 0.011378498 | No action |
| 0.45 | 0.011954121 | No action |
| 0.50 | 0.012081338 | No action |
| 0.55 | 0.010901448 | No action |
| 0.60 | 0.010411472 | No action |
| 0.65 | 0.010877795 | No action |
| 0.70 | 0.011887300 | No action |
| 0.75 | 0.012383630 | No action |
| 0.80 | 0.012560271 | No action |
| 0.85 | 0.012072456 | No action |
| 0.90 | 0.010974178 | No action |
| 0.95 | — | Disabled before first KC spike |
| 1.00 | — | Disabled before first KC spike |

## Frozen artifacts

- Protocol config: [`malecns_level4b_moving_output_admission_repair.json`](../configs/malecns_level4b_moving_output_admission_repair.json)
- Frozen 500-ms readout config: [`malecns_level4_moving_note_500ms_readout_validity_v1.json`](../configs/malecns_level4_moving_note_500ms_readout_validity_v1.json)
- Full replay receipt: [`result.json`](../runs/malecns_level4b_moving_output_admission_repair/result.json)
- Runner: [`experiment_level4b_output_admission.py`](../src/project_b/malecns_continuous_position_learning/experiment_level4b_output_admission.py)

Level 4B ends here. No Level 4 learning was run.
