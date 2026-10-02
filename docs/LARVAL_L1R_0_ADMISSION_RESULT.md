# L1R-0 — identity and learning-locus admission

**Date:** 2026-10-02  
**Decision:** **FAIL**  
**Candidate tested:** literal `selected KCs → MBON-m1`, with DAN-c1 as the local teaching source  
**Consequence:** Do not construct the L1R manifest, electrical model, controllability experiment, plasticity rule, or learning task.

## Question and predeclared gate

The [L1R roadmap](LARVAL_L1R_PROPOSED_ROADMAP.md) requires evidence that the exact larval MBON-m1 and DAN-c1 identities belong to one compartment-compatible learning locus. Passing requires more than two independently true observations—DAN-c1 can teach, and MBON-m1 can change after conditioning. Evidence must connect DAN-c1 modulation to the selected KC→MBON-m1 territory without substituting MBON-c1, MBON-d1, DAN-d1, or an adult homolog.

## Reproducible anatomy

The audit script [`audit_larval_l1r_admission.py`](../scripts/audit_larval_l1r_admission.py) reads the pinned Winding et al. Supplementary Data S1 archive and makes read-only coordinate queries to the VFB-hosted L1EM CATMAID project. Its machine-readable result is [`l1r_admission_audit.json`](../data/raw/larval_l1em/l1r_admission_audit.json), SHA-256 `1509A7B9FF6107517E9DD51BF4551B4A591239F65937DB81CAB8A3F16A934167`. Two complete reruns produced the same hash.

| Source fact | Result |
|---|---:|
| MBON-m1 / CN-62 IDs | `4022539`, `17016974` |
| DAN-c1 IDs | `15592096`, `16240569` |
| MBON-c1 IDs, positive control for lower peduncle | `8980589`, `16223537` |
| Annotated KC→MBON-m1 | 88 pair rows / **437 contacts** |
| DAN-c1→MBON-m1 | **0 direct contacts** |
| DAN-c1→MBON-c1 | 4 pair rows / **209 contacts** |

The critical KC→MBON-m1 and DAN-c1→MBON-c1 totals agree exactly between the pinned publication matrix and live CATMAID. The positive-control KC→MBON-c1 block has 2,504 contacts in the pinned matrix and 2,506 in the current live reconstruction; that two-contact live update is disclosed and does not affect the L1R decision.

Absence of a conventional DAN-c1→MBON-m1 edge is not sufficient by itself to reject dopamine modulation. The audit therefore also compares exact KC→MBON contact coordinates with DAN-c1 presynaptic territory:

| Spatial comparison | Median nearest distance | Within 1 µm | Within 2 µm |
|---|---:|---:|---:|
| KC→MBON-m1 contacts vs all DAN-c1 presynaptic sites | **7.156 µm** | **0 / 437** | **0 / 437** |
| KC→MBON-c1 contacts vs all DAN-c1 presynaptic sites | **0.636 µm** | **91.10%** | **99.92%** |
| KC→MBON-m1 contacts vs DAN-c1→MBON-c1 sites | **7.991 µm** | **0 / 437** | **0 / 437** |
| KC→MBON-c1 contacts vs DAN-c1→MBON-c1 sites | **0.678 µm** | **85.47%** | **99.92%** |

These distances are descriptive anatomy, not a physiological dopamine-radius threshold. Their value is the matched positive control: the same reconstruction and coordinate method recover tight DAN-c1 overlap with KC→MBON-c1 contacts, while no KC→MBON-m1 contact lies within 2 µm of a DAN-c1 presynaptic site.

## Primary functional evidence

| Claim | What is supported | What remains unsupported |
|---|---|---|
| DAN-c1 teaching | Qi et al. show that third-instar DAN-c1 innervates the lower peduncle; blocking its dopamine release impairs aversive learning, while activation during training can produce aversive memory. [Qi et al., eLife 2025](https://elifesciences.org/articles/100890) | The study does not identify MBON-m1 as the lower-peduncle output or measure DAN-c1-gated KC→MBON-m1 plasticity. Its local synaptic account is presented as a hypothesis. |
| MBON-m1 conditioning response | First-instar MBON-m1 response decreases on average for the conditioned odor after Basin-paired aversive training. [Eschbach et al., eLife 2021](https://pmc.ncbi.nlm.nih.gov/articles/PMC8616581/) | The authors explicitly describe two explanations: direct KC→MBON-m1 depression associated with DAN-g1/d1 activation, or indirect disinhibition through other MBONs. The result does not assign the effect to DAN-c1 or isolate the KC→MBON-m1 locus. |
| Lower-peduncle identity | Larval DAN-c1 is assigned to LP, and MBON-c1 is the named LP output; MBON-d1 is assigned to LA. [Truman et al., eLife 2023](https://elifesciences.org/articles/80594) | Adult PPL1-γ1pedc homology does not turn larval MBON-m1 into the DAN-c1-matched LP output. |
| First-instar connectome | The pinned S1/CATMAID sources directly pair DAN-c1 with MBON-c1 and provide KC inputs to both MBON-c1 and MBON-m1. [Winding et al., Science 2023](https://pmc.ncbi.nlm.nih.gov/articles/PMC7614541/) | Contact anatomy alone does not prove plasticity, but it contradicts treating MBON-m1 as the anatomy-matched DAN-c1 output when MBON-c1 is directly paired and spatially colocalized. |

## Gate result

| Required L1R-0 condition | Result |
|---|---|
| Exact bilateral identities source-linked | PASS |
| KC→MBON-m1 contacts reproducible | PASS |
| DAN-c1 teaching supported | PASS |
| MBON-m1 conditioning-related response change supported | PASS |
| DAN-c1 modulation supported at the same KC→MBON-m1 learning territory | **FAIL** |
| DAN-c1-gated local KC→MBON-m1 LTD coherent without cell substitution | **FAIL** |

The literal candidate fails because the two functional findings do not meet at one demonstrated or anatomy-aligned learning locus. The matched anatomical evidence instead identifies MBON-c1 as the DAN-c1-associated lower-peduncle output. Using MBON-c1 would be a different candidate and cannot be introduced as a silent repair to L1R.

## Decision and limits

**L1R-0 FAIL. Literal L1R is retired before implementation.** No manifest, electrical parameter family, output threshold, simulation, plasticity rule, or learning run was created.

This result does not show that DAN-c1 cannot influence MBON-m1 indirectly, that MBON-m1 cannot change with learning, or that a reduced-output larval MVP is impossible. It shows that the exact L1R claim—local DAN-c1-gated learning at selected KC→MBON-m1 synapses—does not satisfy its own admission criteria. Continuing would require either an explicitly engineering-only teaching assignment with a narrower claim, or a newly named anatomy-aligned candidate with its own roadmap and gates.

## Reproduction

From the project root with public network access:

```powershell
.\.venv\Scripts\python.exe scripts\audit_larval_l1r_admission.py
```

The audit fails closed if the pinned S1 and live CATMAID totals disagree for either critical block. It preserves live-source differences in the MBON-c1 positive control rather than rewriting the published source fact.
