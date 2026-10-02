# Experiment results

**Contract result** is the decision under the rule declared before a run. **Interpretation** describes what the run still showed. A partial mechanism does not turn a strict FAIL into PASS.

| Study | Contract result | Interpretation | Report |
| --- | --- | --- | --- |
| Synthetic randomized-map learning | FAIL reliability/timing gate | Engineering fixture only | [Legacy status](../docs/LEGACY_SYNTHETIC_STATUS.md) |
| MaleCNS Level 1 minimal association | PASS reduced fixture gate | Stored association under engineered input/teacher/readout | [Level 1](../docs/MALECNS_MINIMAL_INTERNAL_LEARNING.md) |
| MaleCNS Level 2 v2.5, historical semantics | PASS its corrected locality contract | Historical floor implementation later found flawed | [v2.5](../docs/MALECNS_CONTINUOUS_POSITION_LEARNING_V2_5.md) |
| Level 2 v2.5 corrected original floor | FAIL | Target core 2/3; wrong core 3/3 | [Corrected result](../docs/MALECNS_CONTINUOUS_POSITION_LEARNING_V2_5_CORRECTED_FLOOR.md) |
| Level 2R fresh 32-KC cohort | FAIL strict replication | Target core 2/3; wrong core 3/3 | [Level 2R](../docs/MALECNS_CONTINUOUS_POSITION_LEARNING_LEVEL2R.md) |
| Level 3 single-DAN bridge, corrected floor | FAIL | Single-DAN coverage insufficient under the model | [Level 3 v1.1](../docs/MALECNS_DAN_BRIDGE_LEVEL3_V1_1_CORRECTED_FLOOR.md) |
| Level 3B three-DAN ensemble | FAIL strict 3/3 target gate | Anatomically gated learning occurred; target core 2/3 | [Level 3B](../docs/MALECNS_DAN_BRIDGE_LEVEL3B_ENSEMBLE.md) |
| Level 4A temporal admission | PASS | 500 ms shortest admitted speed | [Level 4A](../docs/MALECNS_LEVEL4A_TEMPORAL_INPUT_ADMISSION_RESULT.md) |
| Level 4B output admission | PASS | Naive target/wrong regions action-free | [Level 4B](../docs/MALECNS_LEVEL4B_MOVING_OUTPUT_ADMISSION_RESULT.md) |
| Level 4C moving-note learning | FAIL | Startup action at first KC spike hid learning position | [Level 4C](../docs/MALECNS_LEVEL4C_MOVING_NOTE_LEARNING_RESULT.md) |
| **Level 4D final moving-note learning** | **FAIL strict target action** | **Mechanistic success / behavioral robustness incomplete** | [Compact bundle](malecns-level4d/summary.md), [full report](../docs/MALECNS_LEVEL4D_FINAL_REPAIR_RESULT.md) |

The original protocols and failure labels remain in the [document catalog](../docs/catalog.md). The [reproducibility guide](../docs/reproducibility.md) explains which full raw receipts are local-only.

The [local diagnostic manifest](local-artifact-manifest.csv) records paths, sizes, and hashes of large historical `docs/figures/` artifacts that are excluded from Git.
