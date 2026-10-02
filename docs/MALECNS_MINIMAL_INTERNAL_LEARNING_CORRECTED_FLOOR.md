# Tiny MaleCNS Level 1 rerun — corrected LocalLTD floor

**Result: PASS**. The frozen Level 1 config and threshold were reused; result saved to a new receipt.

- The corrected LocalLTD primitive was used. This original Level 1 runner keeps one LTD object for the full arm, so its baseline was already stable across the three repetitions; the rerun confirms the fixed implementation without changing the experiment.
- Fixed threshold: `0.132668977551122` mV. All nine criteria passed.

| Frozen map | A state (MBON mV / action) | B state (MBON mV / action) |
|---|---|---|
| A teacher | 0.0379054221575 / ACTION | 0.189527110787 / no-action |
| Plasticity-off | 0.189527110787 / no-action | 0.189527110787 / no-action |
| B teacher | 0.189527110787 / no-action | 0.0379054221575 / ACTION |

Changed weights (four taught-state edges per teacher arm):

| Arm | KC source ID | Original | Final |
|---|---:|---:|---:|
| A teacher | 19083 | 0.131578947368 | 0.0263157894737 |
| A teacher | 33808 | 0.25 | 0.05 |
| A teacher | 37916 | 0.289473684211 | 0.0578947368421 |
| A teacher | 38113 | 0.328947368421 | 0.0657894736842 |
| B teacher | 38549 | 0.25 | 0.05 |
| B teacher | 38962 | 0.181818181818 | 0.0363636363636 |
| B teacher | 39531 | 0.284090909091 | 0.0568181818182 |
| B teacher | 41131 | 0.284090909091 | 0.0568181818182 |

Historical result hash unchanged: `c964b9ef9dc3a92001476ab247bb5815383951831de1e6f61165f14d0e63bfdd`. New corrected-floor result SHA-256: `9860b0cd0dd5a23263884b08a32adac4e1facdd44547f3c5400cd87b452af3e1`.
- The four selected weights in each teaching arm reached their immutable 20% original floors. Plasticity-off changed zero weights.
- Receipt: `runs/malecns_minimal_internal_learning_corrected_floor/result.json`.
