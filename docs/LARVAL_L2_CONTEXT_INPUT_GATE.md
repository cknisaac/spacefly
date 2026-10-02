# L2 omitted context-input gate

**Review date:** 2026-10-02  
**Decision:** **PASS for a minimal, positively signed nociceptive-context drive to Ipsigoro, with an uncalibrated gain kept explicit**  
**Scope:** Read-only review of pinned first-instar Winding et al. S1 anatomy and CATMAID identities, plus primary larval physiology. No config, manifest, simulation, or training was changed or run.

## Frozen state verified

| Artifact | SHA-256 |
| --- | --- |
| `configs/larval_l2_subgraph_manifest_v1.json` | `84fb7af5160a405a072170466ea19e134cd12bc61ed1a7c565f301972da07c89` |
| `configs/larval_l2_electrical_model_v2.json` | `9b017e0df5a3d9e71e6224ba1c2c35343dee67cbf50a45fff62ab0ae88c1301c` |
| `configs/larval_l2_signed_effect_probe_v2_protocol.json` | `77c8de4c0c617637602fe50becc788b3e854a7a8baf8cc12daf2e8454a6610ba` |
| `runs/larval_l2_signed_effect_probe_v2.json` | `6f82f360b329ab8ef57533187374b9661c6974cf333962ac106db9bad61a8787` |
| Pinned `supplementary_data_s1.zip` | `8c1f43809ed5d527ba61b154e377cc21da26383a75eda8aab85ce05607a72a4c` |
| Pinned `edge_audit.json` | `b698b48f13876ace7e9297192dda4ee4ce4970ca5fc3780fc5183f4d5f3ed568` |
| Pinned `catmaid_route_audit.json` | `f0e6056a037d2d560c3784ec149f61e1d50c04c3f72b7cd88cf9de501fb276d4` |

The v2 probe remains a frozen failure: KCs activate and MBON-d1 sometimes spikes, but Ipsigoro and Goro remain silent across the predeclared sweep. This gate does not alter that result.

## Exact sensory/context input found

Winding et al. (2023) Supplementary Data S1 `ad_connectivity_matrix.csv` is directed axon-to-dendrite contact anatomy from a first-instar CNS. The corresponding annotation table identifies a bilateral pair as `PN-somato`, `FFN-27; noci 2nd_order PN`:

| Presynaptic S1 ID | Postsynaptic CATMAID Ipsigoro ID | Axon-to-dendrite contacts | Evidence label |
| ---: | ---: | ---: | --- |
| 11,361,875 | 3,979,181 | 4 | Measured S1 edge; presynaptic cell annotated nociceptive second-order PN |
| 14,493,841 | 5,794,678 | 7 | Measured S1 edge; presynaptic cell annotated nociceptive second-order PN |

Both postsynaptic IDs resolve in VFB/CATMAID as larval Ipsigoro neurons (MB2ON-39); the existing CATMAID audit records Ipsigoro→Goro contacts. The S1 table also records direct chordotonal/mechanosensory second-order input to Ipsigoro (4 and 3 contacts on the corresponding sides), but it is not needed for the minimal noxious-context channel described here.

**Primary functional evidence:** Jones (2024), a third-instar primary research thesis, reports that optogenetic MD-IV/class-IV nociceptor activation increases Ipsigoro calcium response (N=8), and that Ipsigoro inactivation significantly reduces rolling evoked by MD-IV activation. This supports a net excitatory nociceptive-input effect at Ipsigoro, while not proving that the two specific S1 PN→Ipsigoro contacts alone mediate the measured response. The same thesis finds Ipsigoro activation increases Goro calcium (N=8) and potentiates rolling in a heat context; activation alone was insufficient to evoke the same rolling response. These results are consistent with a context-dependent Ipsigoro contribution.

**Independent primary circuit evidence:** Ohyama et al. (2015) reconstructed multisensory nociceptive/mechanosensory pathways and measured calcium responses through Basin→A05q→Goro, including A05q activation increasing Goro calcium. This is a separate VNC context route, but the pinned Winding S1/CATMAID files do not contain an audited exact-ID A05q→Goro row for this gate; it is therefore corroborating physiology, not the basis for the exact edge claim above.

## Gate result and limits

**PASS for admitting one minimal net context input to Ipsigoro:** an explicitly annotated nociceptive second-order PN has measured direct S1 contacts to each Ipsigoro, and primary third-instar physiology independently shows net nociceptive activation raises Ipsigoro activity and that Ipsigoro participates in noxious-context rolling. Thus adding a *noxious-context drive at Ipsigoro* has both an anatomical path and a functionally supported positive net direction. It addresses the missing concurrent excitatory/context channel without altering KC→MBON-d1 weights or selecting a learning gain based on task performance.

The contact counts are anatomical, not efficacies. The exact unitary sign/strength of each PN→Ipsigoro edge, temporal response, first-to-third-instar transfer, and mapping from context stimulus to simulator units remain unmeasured. The supported claim is a positive **net context input**, not a calibrated synaptic conductance. Any fixed drive magnitude must be declared and frozen independently of task score/action success; absent independent calibration, report it as an engineering scale assumption. Do not adjust it until the previously failed probe passes.

This gate does **not** resolve KC→MBON-d1 physiological sign/plasticity, the local DAN-d1 update rule, or the overall L2 learning admission decision. It only shows that the missing context-input hypothesis has a measured route and a relevant net functional effect.

## Sources

- Winding et al. (2023), *The connectome of an insect brain*, [Nature](https://www.nature.com/articles/s41586-023-06683-4), with the pinned Supplementary Data S1 mirror listed above.
- Jones (2024), *Circuit Mechanisms of Context-dependent Memory-based Action Selection*, University of Cambridge thesis, [Chapter 4: Ipsigoro→Goro / context-dependent rolling](https://api.repository.cam.ac.uk/server/api/core/bitstreams/737cafca-8765-40b0-869e-a7756817d803/content) and Chapter 5: MD-IV input to Ipsigoro (pp. 39–49).
- Ohyama et al. (2015), *A multilevel multimodal circuit enhances action selection in Drosophila*, [Nature](https://www.nature.com/articles/nature14297).
- VFB crosswalk: [MB2ON-39 / L1EM:3979181](https://www.virtualflybrain.org/term/mb2on-39-l1em3979181-vfb_00100627/), [larval Ipsigoro](https://jupyter.virtualflybrain.org/blog/2022/01/01/larval-ipsigoro-neuron-fbbt_00111239/).
