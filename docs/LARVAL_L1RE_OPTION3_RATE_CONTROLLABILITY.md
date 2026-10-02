# L1R-E Option 3 — anatomy-weighted rate MBON controllability

**Date:** 2026-10-02  
**Decision:** **PASS for engineering rate-model controllability only**

## Why Option 3 followed Option 2

The Option 2 LIF membrane average decreased substantially at low weights, but reset dynamics broke monotonicity at intermediate factors. Option 3 replaces the MBON electrical cells with continuous rate variables. It preserves the measured KC→MBON-m1 adjacency and makes the reduced biological scope explicit.

This is an **ENGINEERING MODEL REDUCTION**. MBON rates are not spikes, voltage, or a claim about measured larval physiology.

## Frozen equation and boundary

For each current-position state, the 88 annotated KCs are sorted by source ID and divided into eight fixed groups of eleven. The state activates its group with binary rate activity. Each measured contact count is transformed by exponent α, summed into each MBON-m1, and divided by the maximum bilateral drive among the eight anatomical states for that α. The fixed rate gain and the KC→MBON weight factor multiply that normalized drive.

The frozen 12-member family used α `[0.75, 1.0, 1.25, 1.5]` and rate gains `[0.75, 1.0, 1.25]`. All are engineering assumptions. No MBON time dynamics were included. The artificial teacher and plasticity were disabled.

The fixed inverse action interface uses two cutoffs per configuration, calculated only from the eight full-weight anatomical rates before evaluating weight changes: 0.2 times the second-smallest and sixth-smallest rates. These cutoffs deliberately test transitions for two and six states as the uniform weight factor falls to 0.2. The rule is non-trainable and uses no task target or reward.

## Repaired gate record

The first Option 3 policy contained a contradiction: it defined the lower cutoff to yield two transitions while requiring at least three transitions for both cutoffs. Its raw output remains preserved as `runs/larval_l1re_rate_mbon_v1.json` (SHA-256 `E97FC7036245B80F45DB34428EFF57D142269A381359F096CCE5CCA82E03FC92`) and is **INCONCLUSIVE**, not a valid model failure.

Policy v2 repairs only that logic: lower cutoff requires at least two transitions; upper cutoff requires at least three. Rate equation, anatomy, cutoffs, family values, and computed observations are unchanged. Policy v2 was frozen before its repair run:

- policy: `configs/larval_l1re_rate_mbon_v2_policy.json`
- policy SHA-256: `FAFF370A2EF7F87586F72EC407949B24E6E0119E83E1C5206F1456B876CF9ACA`

## Result

- 12/12 rate configurations qualified.
- All four α values and all three gains were represented.
- Largest face-adjacent component: **12** (required ≥8).
- Members passing both adjacent anatomy-derived cutoffs: **12** (required ≥6).
- Every state had positive source-derived drive to at least one MBON-m1.
- Rates were exactly proportional to the local weight factor; factor 0.2 produced an 80% reduction in every state.
- Both exact deterministic calculations matched for all state/factor/configuration records.

Raw result: `runs/larval_l1re_rate_mbon_v2.json`, SHA-256 `07D15F22B1EDD1A2B8BA66452E8A307973076B4C6495D746847CAB3E8AFE158A`.

## Scope of the pass

This pass establishes that the declared anatomy-weighted rate equation has robust deterministic controllability under the disclosed engineering assumptions. The action transition follows directly from the frozen monotonic scalar equation and anatomy-derived cutoffs; it is not independent evidence of a fly motor pathway.

It admits a separately frozen local-plasticity design gate for an engineering rate model. It does **not** establish internal learning, storage, retention, artificial-teacher efficacy, a dopamine pathway, spiking MBON dynamics, larval behavior, or biological quantitative validity. Stop here until the next learning gate is separately specified.

