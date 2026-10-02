# Circuit V1 effect and dynamics policy

**Date:** 2026-09-29. **Status:** resolved policy records for the exact [MaleCNS Circuit V1 anatomical subset](CIRCUIT_V1_SUBSET.md); **not a runnable neural simulation**. The fixed all-positive, same-LIF, 2 ms delay scenario in [the Session 7 scale report](MALECNS_V1_SCALE_PROFILE.md) remains a failed historical stress test. Its numbers and signs are not carried into this policy.

The executable contract is [configs/circuit_v1_effect_policies.json](../configs/circuit_v1_effect_policies.json). Four components in [effect_policies.py](../src/project_b/connectome/effect_policies.py) resolve it: `ConnectionEffectPolicy`, `NeuronParameterPolicy`, `DelayPolicy` and `BoundaryInputPolicy`. They classify **all** 140 selected neurons, 12,153 source connection pairs and 14 selected boundary roles. They do not change the anatomical subset.

**2026-09-30 interpretation note:** the [critical-route evidence gate](CIRCUIT_V1_CRITICAL_ROUTE_EVIDENCE.md) clarifies KC consensus provenance and source `receptorType` semantics. The policy's receptor annotation join is a preserved source field, not a postsynaptic receptor assay. The newly proposed 115-body route has no policy artifact yet; all counts and hashes in this report still describe the unchanged 140-body policy.

## Effect policy

The default state is the literal **`UNKNOWN`**, with no numeric weight. No rule maps a transmitter label or source contact count alone to a positive current. A supported class interaction needs a specified presynaptic role, postsynaptic role, matching transmitter annotation, evidence category and source. The stated effect is a class-level constraint or inference, not a measured conductance in this MaleCNS specimen.

| Source role → target role | Pairs | State | Evidence and limit |
| --- | ---: | --- | --- |
| KCg-d → MBON11/MVP2 and MBON01/M6 | 214 | `EXCITATORY` | `LITERATURE-CONSTRAINED` by [KC cholinergic physiology](https://pmc.ncbi.nlm.nih.gov/articles/PMC4819445/); exact visual KC conductances unknown. |
| APL → KCg-d | 106 | `INHIBITORY` | `LITERATURE-CONSTRAINED` local, graded GABAergic inhibition; a single point-spike current is not justified. [Amin et al.](https://elifesciences.org/articles/56954). |
| MBON11/MVP2 → MBON01/M6 | 1 | `INHIBITORY` | `LITERATURE-CONSTRAINED` feedforward inhibition, with unknown strength and state dependence. [Perisse et al.](https://pmc.ncbi.nlm.nih.gov/articles/PMC4893166/). |
| PPL101 → KCs/MBON11 | 96 | `MODULATORY` | γ1pedc teaching/plasticity is `LITERATURE-CONSTRAINED`; immediate effect of each anatomical contact is unknown. [Hige et al.](https://pmc.ncbi.nlm.nih.gov/articles/PMC4674068/). |
| PAM01(y5) → KCs/MBON01 | 776 | `MODULATORY` | Exact action for this cohort is `INFERRED`. γ5 DAN subtypes differ, so a uniform reward signal is not assigned. [Otto et al.](https://pmc.ncbi.nlm.nih.gov/articles/PMC7443709/). |
| All other pairs, including KC→KC, MBON01 glutamate→outputs, MBON32 GABA→DNs and MBON27 ACh→DNs | 10,960 | **`UNKNOWN`** | Target receptor/effect or local physiological evidence is missing. Their anatomy and transmitter fields remain intact. |

The policy therefore records **214 excitatory, 107 inhibitory, 872 modulatory and 10,960 UNKNOWN directed pairs**. UNKNOWN covers **90.18% of pairs** and **45,115 of 57,771 contacts (78.09%)**. These are classification coverage figures, not functional-drive fractions. In particular, glutamate is never treated as automatically excitatory, and the 9,370 KC→KC recurrent pairs receive no universal positive current.

`MODULATORY` means a candidate dopamine-related mechanism, not a fast signed weight. Dopamine release, receptor occupancy, compartment overlap and plasticity timing are separate unresolved states. The 214 [plasticity candidate pairs](CIRCUIT_V1_SUBSET.md) are not activated by this classification.

## Neuron parameter policy

| Population | Model family | Evidence for the family | Numeric intrinsic parameters |
| --- | --- | --- | --- |
| MeVP41, LoVP97, LoVP42 | External visual input source, adapter pending | `ENGINEERING ASSUMPTION`; natural cue tuning unknown | `UNKNOWN` |
| 107 KCg-d | Spiking KC proxy, not yet parameterized | Visual KC spiking is `LITERATURE-CONSTRAINED`; a reduced proxy is `INFERRED`. [Vogt et al.](https://elifesciences.org/articles/14009). | `UNKNOWN` |
| APL | **Graded, local, non-spiking** | `LITERATURE-CONSTRAINED`; local inhibition cannot be represented by the existing uniform point-LIF mechanism. [Amin et al.](https://elifesciences.org/articles/56954). | `UNKNOWN` |
| PPL101 and 21 PAM01 | Dopaminergic state, distinct from fast current | `LITERATURE-CONSTRAINED` class function, with subtype/kinetic limits | `UNKNOWN` |
| Five MBONs | Spiking output proxy, not yet parameterized | Class physiology constrains spikes; exact selected-body constants are `UNKNOWN` | `UNKNOWN` |
| DNa03 and DNa02 | Descending spiking proxy, not yet parameterized | Descending steering physiology constrains role; keyboard action remains an `ENGINEERING ASSUMPTION`. [Steering study](https://www.nature.com/articles/s41586-024-07039-2). | `UNKNOWN` |

No `tau_m_us`, `tau_syn_us`, threshold, reset, refractory or gain is assigned to the selected bodies. This is deliberate: a measured parameter from another MBON subtype is not automatically transferable to MBON01/11/26/27/32. Future numeric entries must each carry a value, a source and one of **`LITERATURE-CONSTRAINED`**, **`INFERRED`** or **`ENGINEERING ASSUMPTION`**. The resolver rejects bare numbers and inconsistent signed weights. It does not claim that a literature value measured in another animal is a measurement of these exact bodies.

## Delay policy

Each edge is classified as a candidate chemical, graded-local APL or dopamine-release pathway by presynaptic family. **Every biological delay remains `UNKNOWN` and `delay_us = null`.** The source graph has aggregate contacts, not a validated conduction path length, release latency or receptor kinetic model. The old flat 2 ms value is not retained. The policy schema permits a later explicitly sourced numerical delay; it requires positive integer microseconds and a provenance object.

## Boundary input policy

All incoming cut-edge drive is **`UNKNOWN`** with no substituted current. Visual-cue injection through the three selected inputs, reinforcement injection through PPL/PAM and a DNa02 one-lane readout are named **pending engineering interfaces**; their amplitude and latency are unassigned. Setting outside neurons to zero would be a lesion, and boosting the retained graph by inverse contact coverage would be an unvalidated intervention. The anatomical manifest reports 37,223 incoming cut pairs / 294,727 contacts and 30,005 outgoing cut pairs / 188,913 contacts; the policy carries these counts per role without interpreting them as electrical strength.

## Fail-closed runtime gate and reproducibility

`require_runtime_ready()` rejects the current product because it contains UNKNOWN and modulatory effects, unassigned weights/delays/intrinsic parameters, missing boundary drive and cell families that the existing all-LIF simulator cannot represent. Nothing in the policy product constructs `ArraySparseGraph` or runs `SpikingSimulator`. The historical scale profiler requires an explicit `--reproduce-failed-overlay` flag and remains available only to reproduce its failed stress scenario.

The output is gitignored under `data/processed/malecns_v1_circuit_v1_policy_v1/`:

| File | SHA-256 |
| --- | --- |
| `neuron_policy.parquet` | `065ecb9834aa5c309afaf68588518d3aae8bdb95be4025685cd8a9bc1ad82675` |
| `connection_policy.parquet` | `e7fb09ae59f2af0b2199c12be61fcff95a7a83c4011c1666031707c3e52bea7f` |
| `boundary_policy.json` | `e88aeab0603c1d07d50356cce46670ec6f1fd7ae36ca38f8132110da8bcbbda9` |
| `manifest.json` | `a77f5db453c3cabfb71d0162e4f78d3f07529b52189e7b920cc57c9d5801e804` |

The policy configuration SHA-256 is `25d4140dd0aac81e478ee65ffde2697b873497b8303e865cb222df2a1c18047a`; the anatomical subset manifest SHA-256 is `230ed9e467db1c7d158bf23a864e9de5265ce5aac6bd02935dd1112de6c9fdc5`.

From the project root in PowerShell:

```powershell
$env:PYTHONPATH = 'src'
.\.venv\Scripts\python.exe -m scripts.build_circuit_v1_policies
.\.venv\Scripts\python.exe -m scripts.audit_circuit_v1_policies
.\.venv\Scripts\python.exe -m unittest tests.test_circuit_v1_effect_policies -v
```

The independent audit checks every policy row against the saved anatomical source pair, preserves transmitter and receptor annotations, reconstructs role-based effect rules, verifies UNKNOWN has no weight, and compares boundary records to the anatomical manifest. It **passed**. A fresh build matched the saved manifest exactly. Five focused tests and the full **96-test** project suite passed. No fly-circuit simulation or training was run.
