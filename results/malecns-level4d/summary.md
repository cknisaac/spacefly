# Level 4D: frozen moving-note result

**Declared contract:** FAIL. **Branch classification:** Mechanistic success / behavioral robustness incomplete.

A note moved from position 1 to 0 over 500 ms. The model used 32 Kenyon cells, MBON05, and three selected PAM08 dopamine neurons. It completed all 120 training blocks in each arm. Afterward, teaching stimulation and plasticity were off during fresh evaluation.

| Condition | First action | Weight changes |
| --- | --- | ---: |
| Naive baseline | None | Not trained |
| Target teaching near x≈0.70 | None | 1,506 |
| Wrong-region teaching near x=0.20 | x=0.20 at 413 ms | 1,432 |
| Matched DAN-on / plasticity-off control | None | 0 |

The wrong-region action remained when the learned weights were frozen. Every recorded update met the model's anatomical and local-eligibility gates, and the original-weight floor held. The target action was absent, so the strict behavioral criterion failed. No new learning run was performed to create this bundle.

## Published compact evidence

- [metrics.json](metrics.json): fixed settings, criteria, controls, and arm summaries extracted from the frozen receipt.
- [position-map.csv](position-map.csv): all 21 evaluated position bins for each of the four conditions, including disabled bins.
- [artifacts.json](artifacts.json): paths, sizes, and hashes for the exact local full receipt, frozen config, runner, and playback.
- [Offline playback](../../visualization/malecns-level4d-playback.html): saved moving-note and neural traces. Training-note DAN and weight events and post-training MBON voltage/output are shown as separate recorded phases.

The full 43 MB receipt at `runs/malecns_level4d_final_moving_note_repair/result.json` is excluded from normal Git history. Its SHA-256 in `artifacts.json` allows comparison to a separately shared copy. See the [protocol](../../docs/MALECNS_LEVEL4D_FINAL_REPAIR_PROTOCOL.md), [original result report](../../docs/MALECNS_LEVEL4D_FINAL_REPAIR_RESULT.md), and [plain-language branch summary](../../docs/MALECNS_MOVING_LEARNING_BRANCH_FREEZE.md).
