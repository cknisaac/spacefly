# MaleCNS Level 4C — moving-note learning result

**Date:** 2026-10-02  
**Protocol:** `MALECNS-LEVEL4C-MOVING-NOTE-LEARNING-v1`  
**Result:** **FAIL** under the frozen first-action criteria

## Protocol and completion

The run used the frozen Level 4B 500-ms x=1.0→0.0 moving note, 32 KCs,
MBON05, Gaussian encoder, LIF/contact model, PAM08 DANs 87177/107285/55210,
presentation-local eligibility, η=0.00005, immutable 20% original-weight
floor, inherited 0.005572335995331903-mV threshold, and first-KC-spike
validity rule. It completed the predeclared **120 blocks / 1,200 presentations
in each arm**, with 600 target-timed DAN events in the target and control arms
and 600 wrong-position events in the wrong arm. All three DANs spiked at every
scheduled event.

The external pulse began at the requested position crossing: 150,000 µs for
x=0.70 and 400,000 µs for x=0.20. The first DAN spike was at 164,000 µs and
414,000 µs, respectively. The local eligibility gate used current-note KC
spikes through the first connected DAN spike. Updates were committed at note
end; each next note used the updated weights.

## Primary first-action result

| Evaluation | First action | Result |
|---|---|---|
| Naive baseline | 41,000 µs, x=0.92, MBON05 = 0 mV | Fails no-action baseline |
| Target teaching, frozen weights | 41,000 µs, x=0.92, MBON05 = 0 mV | Not near target |
| Wrong-region teaching, frozen weights | 41,000 µs, x=0.92, MBON05 = 0 mV | Not shifted toward wrong region |
| DAN-on / plasticity-off control | 41,000 µs, x=0.92, MBON05 = 0 mV | Fails no-action control |

The first KC spike and first action share the same 41,000-µs timestamp. There
was no action at an earlier sample, so the strict “no action before the first
KC spike” check passes. At the first-spike sample itself, however, the
validity gate becomes enabled and the recorded MBON05 voltage is still 0 mV;
the unchanged threshold therefore emits action. All arms have the same first
action, so the target and wrong-region training did not shift the primary
metric. This is the decisive blocker under the frozen contract.

## Position-to-action maps

Map rule frozen before the run: a position bin is action if any enabled 1-ms
sample in that bin is at or below threshold; bins with no enabled samples are
disabled. The full voltage timecourses and sample counts are in the JSON
receipt.

| Position | Naive baseline | Target trained | Wrong-region trained | DAN-on / plasticity-off |
|---:|---|---|---|---|
| 0.00 | No action | No action | No action | No action |
| 0.05 | No action | No action | No action | No action |
| 0.10 | No action | No action | No action | No action |
| 0.15 | No action | No action | Action | No action |
| 0.20 | No action | No action | Action | No action |
| 0.25 | Action | Action | Action | Action |
| 0.30 | Action | Action | Action | Action |
| 0.35 | No action | No action | Action | No action |
| 0.40 | No action | No action | Action | No action |
| 0.45 | No action | No action | Action | No action |
| 0.50 | No action | No action | Action | No action |
| 0.55 | No action | No action | Action | No action |
| 0.60 | No action | Action | Action | No action |
| 0.65 | No action | Action | Action | No action |
| 0.70 | No action | Action | Action | No action |
| 0.75 | No action | Action | Action | No action |
| 0.80 | No action | Action | Action | No action |
| 0.85 | No action | Action | Action | No action |
| 0.90 | Action | Action | Action | Action |
| 0.95 | Disabled | Disabled | Disabled | Disabled |
| 1.00 | Disabled | Disabled | Disabled | Disabled |

The map shows threshold crossings after the validity gate opens, but those
later crossings do not change the first-action result: each arm first acts at
x=0.92. Target teaching adds actions over a broad region, and wrong-region
teaching produces a still broader map; neither meets the localized first-action
criterion.

## Plasticity and controls

| Arm | Weight changes | Final weights at immutable floor | DAN events | Control outcome |
|---|---:|---:|---:|---|
| Target teaching | 4,718 | 6 KC slots | 600/600; all 3 DANs spiked | Learning updates were anatomically gated and had positive local eligibility |
| Wrong-region teaching | 12,585 | 12 KC slots | 600/600; all 3 DANs spiked | Learning updates were anatomically gated and had positive local eligibility |
| DAN-on / plasticity-off | 0 | 0 | 600/600; all 3 DANs spiked | Weights stayed exactly at baseline; action behavior did not satisfy control gate |

The saved receipt's independent checks confirm all 120 blocks and 1,200 notes
per arm, no action before the first KC spike, anatomical DAN gating with
positive current-note eligibility for every weight update, and the immutable
20% original-weight floor throughout. The control weights are unchanged.

## Gate summary

| Criterion | Result |
|---|---|
| Naive baseline has no first action | FAIL |
| Target first action lies in `[0.65, 0.75]` | FAIL |
| Wrong-trained first action lies in `[0.15, 0.25]` | FAIL |
| DAN-on / plasticity-off has no action | FAIL |
| No action before first KC spike | PASS; action occurs at the same timestamp as the first spike |
| Updates are locally eligible and anatomically DAN-gated | PASS |
| Immutable original-weight floor is respected | PASS |
| All predeclared training completes; all DAN events activate | PASS |

## Frozen artifacts

- [Level 4C protocol](MALECNS_LEVEL4C_MOVING_NOTE_LEARNING_PROTOCOL.md)
- [Frozen config](../configs/malecns_level4c_moving_note_learning.json)
- [Complete result receipt](../runs/malecns_level4c_moving_note_learning/result.json)
- [Runner](../src/project_b/malecns_continuous_position_learning/experiment_level4c_moving_note_learning.py)

This is the one authorized Level 4C run. It is preserved as **FAIL**; no tuning
or rerun was performed. No osu timing scoring or biological downstream motor
neurons were added.
