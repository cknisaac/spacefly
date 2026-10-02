# Larval L2 signed-effect electrical probe v2

**Gate: FAIL for this frozen electrical reference.** The independently constrained downstream effect classes do not restore controllability of the current restricted L2 path. No learning was implemented or run.

## Motivation and frozen inputs

The v1 controllability failure used a uniform-positive transform on every chemical edge. A separate read-only literature audit identified third-instar functional evidence that MBON-d1 activation suppresses Ipsigoro/Goro, Ipsigoro activation excites Goro and promotes context-dependent rolling, and Goro has command-like rolling evidence. A further focused review admits DAN-d1-gated KC→MBON-d1 LTD only as an **INFERRED** hypothesis; no exact synaptic plasticity measurement exists. See [L2 electrical evidence gate](LARVAL_L2_ELECTRICAL_EVIDENCE_GATE.md) and [L2 LTD inference admission](LARVAL_L2_LTD_INFERENCE_ADMISSION.md).

Model v2 was frozen before its simulator runs. It preserves the v1 topology, cell constants, contact scale, delays, sensory code, pulse, response duration, and Goro event threshold. Only direction-specific signs changed: KC→MBON-d1 remains positive as an engineering assumption; MBON-d1→Ipsigoro is negative and Ipsigoro→Goro positive as simplified signed representations of independently reported net effect classes. These are not unitary edge measurements. Exact KC→MBON-d1 plasticity remains inferred and disabled.

| Frozen input | SHA-256 |
|---|---|
| L2 manifest | `84fb7af5160a405a072170466ea19e134cd12bc61ed1a7c565f301972da07c89` |
| L2 v2 electrical model | `9b017e0df5a3d9e71e6224ba1c2c35343dee67cbf50a45fff62ab0ae88c1301c` |
| Probe protocol | `77c8de4c0c617637602fe50becc788b3e854a7a8baf8cc12daf2e8454a6610ba` |
| Original v1 neutral file (duration only) | `788104431186ab0b329dc7801eee8a41a46a844b9bf904ff2d6cf5d726b3ecf9` |

The fixed sweep used KC→MBON-d1 multipliers `[0, 0.25, 0.5, 1, 2, 4]` across eight existing state codes. Plasticity, teaching, and exploration were off. Every state/factor cell was replayed twice.

## Results

| Weight factor | KC spikes per state | MBON-d1 spikes across states | Ipsigoro spikes | Goro events/actions |
|---:|---:|---:|---:|---:|
| 0–1× | 28–30 | 0 | 0 | 0 |
| 2× | 28–30 | 0–1 | 0 | 0 |
| 4× | 28–30 | 0–1 | 0 | 0 |

The zero-drive v2 baseline was silent, finite, and produced no action. The factor-1 sensory responses matched the existing v1 neutral measurements for all compared roles/actions. All 48 probe replays were deterministic and finite. No tested factor produced Ipsigoro or Goro activity.

**Interpretation:** signs constrained by the cited functional effect classes do not make the narrow feed-forward pathway controllable under this frozen model. This rejects the v2 electrical reference for local-learning experiments. It does not disprove biological L2. The result suggests the current subgraph lacks an excitatory/contextual drive needed to recruit the inhibitory gate; adding such input requires an independent anatomical and functional basis, not gain tuning. Do not proceed to learning on this v2 model.

## Artifacts

- Frozen model: `configs/larval_l2_electrical_model_v2.json`
- Frozen protocol: `configs/larval_l2_signed_effect_probe_v2_protocol.json`
- Runner: `scripts/run_larval_l2_signed_effect_probe_v2.py`
- Zero-drive baseline: `runs/larval_l2_neutral_dynamics_v2.json` (SHA-256 `caadbb134b53335bf2eb9612f31f95c7b7e5f9f92fc2d272b049aa390236733d`)
- Probe results: `runs/larval_l2_signed_effect_probe_v2.json` (SHA-256 `6f82f360b329ab8ef57533187374b9661c6974cf333962ac106db9bad61a8787`)

The runner was executed twice and reproduced the same result hash. It independently checks manifest/model/protocol hashes, writes the zero-drive baseline, and checks replay equality for each cell. `py_compile` passed. This validates the run record and software determinism, not biology.
