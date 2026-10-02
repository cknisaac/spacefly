# Larval L2 LTD inference admission

**Review date:** 2026-10-02  
**Verdict:** **PASS — admit as an explicitly inferred, independently motivated LTD hypothesis only**  
**Scope:** Read-only primary-source audit of the direction of a proposed DAN-d1-gated KC→MBON-d1 learning rule. This decision does not establish that the exact synapse or rule has been measured.

## Frozen artifacts checked

The current files match the supplied SHA-256 hashes. No model, simulation, or training artifact was changed or run for this review.

| Artifact | SHA-256 |
| --- | --- |
| `configs/larval_l2_subgraph_manifest_v1.json` | `84fb7af5160a405a072170466ea19e134cd12bc61ed1a7c565f301972da07c89` |
| `configs/larval_l2_electrical_model_v1.json` | `76a6f2612ed1361f86b061f8a4da117715456d748f3aa7d8384bdb4db9291952` |
| `runs/larval_l2_controllability_probe_v1.json` | `97e6f526fbc4e6f46b5b0dbeb6fb32287dc531ebbb6a4ef0e0ee8d343c9cf381` |

The frozen L2 v1 controllability probe remains **FAIL**. This inference review does not reinterpret that result or change the model.

## Causal chain and evidence labels

| Link | Evidence | Label and limit |
| --- | --- | --- |
| **DAN-d1 can provide aversive teaching** | Optogenetic pairing of individual larval DANs with odor established aversive odor memory for DAN-d1 ([Eschbach et al., 2020](https://www.nature.com/articles/s41593-020-0607-9)). Timing experiments found DAN-d1 activation supported punishment memory but not relief-memory reversal ([Weiglein et al., 2021](https://pubmed.ncbi.nlm.nih.gov/32965036/)). | **MEASURED at the behavioral teaching level** in larvae. This does not measure the cellular update rule or identify which KC→MBON-d1 synapses store memory. |
| **MBON-d1 activity suppresses Ipsigoro and Goro** | In third-instar ex-vivo CNS experiments, optogenetic MBON-d1 activation lowered Ipsigoro calcium (N=6) and Goro calcium (N=12). The primary research thesis reports these as functional inhibitory effects ([Jones, 2024, Ch. 6](https://api.repository.cam.ac.uk/server/api/core/bitstreams/737cafca-8765-40b0-869e-a7756817d803/content), pp. 50–53). | **MEASURED functional effect class** under population optogenetic stimulation. It is not a calibrated unitary synaptic current, and the thesis is primary research but not a peer-reviewed journal article. |
| **Ipsigoro excites Goro and promotes rolling** | In third-instar preparations, optogenetic Ipsigoro activation increased Goro calcium (N=8); thermogenetic Ipsigoro activation increased heat-evoked rolling, while activation alone was insufficient without noxious context ([Jones, 2024, Ch. 4](https://api.repository.cam.ac.uk/server/api/core/bitstreams/737cafca-8765-40b0-869e-a7756817d803/content), pp. 30–35). Independently, selective Goro activation evoked rolling in larvae ([Ohyama et al., 2015](https://doi.org/10.1038/nature14297)). | **MEASURED** for the functional effect class and context-dependent behavioral contribution. Does not provide an L1 spike threshold or justify a one-spike simulated action criterion. |
| **Aversive conditioning can increase learned-odor rolling in noxious context** | The same primary thesis reports greater heat-evoked rolling after forward odor–Basin punishment pairing than after backward pairing (Ch. 3, pp. 23–27). | **MEASURED behavioral compatibility** for the sign of the proposed chain, using Basin punishment rather than selective DAN-d1 manipulation. It does not localize the memory to the proposed KC→MBON-d1 edge. |
| **DAN-d1-gated depression at KC→MBON-d1** | Jones discusses that MBON-d1 is an approach-promoting output, receives DAN-d1 in the lateral-appendix compartment, and inhibits Ipsigoro. The thesis proposes that aversive conditioning may depress conditioned-stimulus responses in MBON-d1, reducing inhibition of Ipsigoro and increasing learned-odor rolling (Ch. 6, pp. 54–56). This is motivated by larval MBON-m1 response depression after aversive conditioning ([Eschbach et al., 2021](https://elifesciences.org/articles/62567)) and, as supporting precedent only, adult KC→MBON plasticity. | **INFERRED, independently motivated direction.** The exact KC→MBON-d1 synaptic locus, DAN-d1 gating rule, expression mechanism, magnitude, and persistence remain **UNMEASURED**. Do not present this as an established biological rule. |

## Direction check

The proposed sign is internally coherent across the independently supported effect classes:

1. DAN-d1 activation can serve as an aversive teaching event in larvae.
2. If that event depresses the odor-active KC→MBON-d1 drive, MBON-d1 odor responses would decrease.
3. Because MBON-d1 activation suppresses Ipsigoro and Goro, reducing MBON-d1 output would release that suppression.
4. Ipsigoro excites Goro and promotes rolling when noxious input is present; Goro activation can evoke rolling.

Thus **DAN-d1-gated LTD is a coherent, evidence-motivated hypothesis for increasing conditioned-odor contribution to context-dependent escape**. The causal chain does not prove that LTD occurs at KC→MBON-d1. The connectome is first-instar and the key downstream physiological results are third-instar; developmental transfer to an L1 electrical model remains an explicit assumption.

## Decision and boundary

**PASS for admitting the inferred LTD direction as a labeled hypothesis.** The direction is independently motivated by larval DAN-d1 teaching, measured MBON-d1 downstream inhibition, measured Ipsigoro→Goro excitation and rolling contribution, and a larval conditioned-rolling result. There is no evidence contradicting the proposed direction in those sources.

This PASS does **not** overturn the v1 controllability failure, demonstrate biological L2 controllability, or validate an exact plasticity mechanism. It does not authorize tuning parameters to obtain performance, task training, or a claim that the precise KC→MBON-d1 rule is measured. Any later model that represents the rule must label the locus and update law **INFERRED**, retain the frozen v1 artifacts, and keep the first-/third-instar mismatch visible. The next biological discriminator remains a selective larval test that localizes conditioning-induced change to KC→MBON-d1 transmission or otherwise falsifies that inferred locus.
