# Larval L2 nociceptive-context probe v3

**Gate: FAIL for this frozen engineering model.** Adding the anatomy-backed fixed nociceptive-context input did not produce Ipsigoro or Goro spikes, so the fixed Goro action remained uncontrollable across the predeclared KC→MBON-d1 sweep. No learning was implemented or run.

## Evidence basis and frozen design

The read-only context-input gate found two measured first-instar S1 connections from annotated `noci 2nd_order PN` neurons to Ipsigoro: 11,361,875→3,979,181 (4 contacts) and 14,493,841→5,794,678 (7 contacts). Third-instar primary physiology independently supports a net excitatory nociceptive effect at Ipsigoro and context-dependent rolling. This supports adding the fixed context route, not its unitary weights or simulator scale. See [context-input evidence gate](LARVAL_L2_CONTEXT_INPUT_GATE.md).

The v3 manifest adds only those two source neurons and measured edges to the frozen L2 manifest. The v3 model inherits the v2 neuron constants, edge scale, delays, downstream signs, KC sensory drive, and Goro action threshold. The fixed context pulse targets only the two annotated second-order PNs, concurrently with the KC position code. Its 12 mV-equivalent amplitude and 5 ms duration reuse the already frozen sensory pulse and remain an **ENGINEERING ASSUMPTION**; they were not selected from outcomes. The KC→MBON-d1 sweep is unchanged: `[0, 0.25, 0.5, 1, 2, 4]` across eight position states. Each of the 48 cells was replayed twice.

| Frozen input | SHA-256 |
|---|---|
| v3 context manifest | `97560028444a02c8bb0c68c6608fd68dcfc5c103276b67debd30b059d0f6003b` |
| v3 electrical model | `c5f9adcf02378ded60ad66f11f8e1e03738955b94a1ab0a1089cc99b3033f60e` |
| v3 protocol | `8f7d01e5d7fe9023c5ff467292d6df6327ab0b06a8eceb40037dd917c19f45dc` |
| Context-input evidence gate | `095fc155026f436b4198a1474bea06bb5f2df64d5687b3a4e20098f94f032d21` |

## Results

| KC→MBON-d1 factor | Noci-PN spikes across states | KC spikes/state | MBON-d1 spikes across states | Ipsigoro spikes | Goro actions |
|---:|---:|---:|---:|---:|---:|
| 0–1× | 4 | 28–30 | 0 | 0 | 0 |
| 2× | 4 | 28–30 | 0–1 | 0 | 0 |
| 4× | 4 | 28–30 | 0–1 | 0 | 0 |

The zero-drive baseline was silent and finite. The factor-1 result matched the parent v1 neutral result for shared roles; the additional Noci-PN activity is separately reported. All 48 replay pairs were deterministic and finite. No tested factor yielded an Ipsigoro spike or Goro event.

**Interpretation:** the anatomically supported input and net functional direction do not rescue the frozen model at the inherited contact scale. The tested version fails Phase 4. It does not refute the biological pathway: the pulse-to-PN encoding, exact PN-edge efficacy, developmental transfer, and modeled Goro threshold remain uncalibrated. Do not increase scale or action sensitivity based on this outcome. More evidence is needed to set those values independently, or the candidate should remain stopped.

## Artifacts

- Reproducible manifest builder: `scripts/build_larval_l2_context_manifest.py`
- Manifest: `configs/larval_l2_context_subgraph_manifest_v1.json`
- Frozen model/protocol: `configs/larval_l2_electrical_model_v3.json`, `configs/larval_l2_context_probe_v3_protocol.json`
- Runner: `scripts/run_larval_l2_context_probe_v3.py`
- Neutral baseline: `runs/larval_l2_neutral_dynamics_v3.json` (SHA-256 `76d6f4b28ae152d10164ea553063919f64bc664ccba0aa38e1f6be121a1c6979`)
- Probe result: `runs/larval_l2_context_probe_v3.json` (SHA-256 `54decac4309faa697d11666ad6a6a4d30c9c381146bbdd7e060d573bbb2c5a4f`)

The manifest builder was rerun and reproduced its hash. The probe runner was rerun and reproduced its result hash; Python compilation passed. Verification covers data/protocol identity and simulator determinism, not biological efficacy.
