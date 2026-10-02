# L1R-E Option 2 — continuous MBON membrane readout

**Date:** 2026-10-02  
**Decision:** **FAIL** under the frozen Option 2 gate

## Change tested

The LIF model and the 128-member v2 electrical family were preserved. The fixed action interface used the arithmetic mean of the two MBON-m1 `voltage_after_reset` traces across the response window, normalized by the fixed MBON spike threshold. It used three non-trainable cutoffs at 0.25, 0.50, and 0.75 of that threshold. Spikes remained secondary measures. Teaching and plasticity were disabled.

Frozen policy SHA-256: `77AB278A1EC24A314C1F29AD8E4A59C321FC509260AB14D1373F4DAEDF7DC60`.

## Result

- 0/128 configurations qualified.
- All zero-drive, replay, finiteness, and queue checks passed.
- KC cue activation and full-weight MBON activity passed for all 128.
- The continuous mean voltage decreased by at least 30% at low weight in all 128, but it was non-monotonic for the intermediate weight factors in every configuration. LIF spike resets caused those reversals.
- No configuration met the nested fixed-action transition rule.

Raw result: `runs/larval_l1re_continuous_readout_v1.json`, SHA-256 `61C3E6644F3F4B0CC969B128A99BF33B2C4BEF33EEDC9547CE0694F7B7ABE31F`.

## Decision

Option 2 **FAILS** for this LIF membrane-average readout. The result motivated the next listed abstraction: a monotonic rate-based MBON output. It does not establish that biological MBON membrane activity is non-monotonic.

