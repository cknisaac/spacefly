# EA-MVP EA-8: fixed four-lane mapping admission

**2026-10-03 — PASS.** This is a separate engineering-assumption result. Strict biology decisions and the saved osu! recreation were not changed.

## Frozen assumption

The fixed observation-to-key lane mapping is `0→0`, `1→1`, `2→2`, `3→3`. **ENGINEERING ASSUMPTION:** the renderer's currently visible lane number reaches the fixed readout unchanged. The connectome-constrained 32-KC→MBON05 circuit controls press timing; it does not represent or learn lane identity. This was needed because the admitted source subgraph contains a single MBON timing output, not four demonstrated motor channels. It adds no learned decoder or adaptive state outside the selected fly synapses.

## Probe and result

The frozen no-game probe used the retained weights from the first predeclared fixed-speed seed (907). It presented the same 500-ms position sweep twice for each lane, with no game, reward, DAN teaching or weight update. Every sweep emitted one DOWN at 501,000 µs and one UP at 511,000 µs on the input lane. All four lanes replayed exactly; the weights were unchanged.

| Input lane | DOWN | UP | Result |
|---:|---:|---:|---|
| 0 | 501 ms, lane 0 | 511 ms, lane 0 | PASS |
| 1 | 501 ms, lane 1 | 511 ms, lane 1 | PASS |
| 2 | 501 ms, lane 2 | 511 ms, lane 2 | PASS |
| 3 | 501 ms, lane 3 | 511 ms, lane 3 | PASS |

Receipt: `runs/ea_mvp/lane_mapping_admission_v1.json`. Frozen protocol: `configs/ea_mvp_lane_mapping_admission_v1.json`.

## Claim boundary

This establishes deterministic four-lane key selection around a timing response already learned on lane 0. It does not establish four separate neural lane pathways, lane-specific learning, simultaneous note handling, holds, or live osu!lazer play. This admission permits the sequential four-lane tap check; it does not justify expanding the biological claim.
