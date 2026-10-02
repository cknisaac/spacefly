# Provisional larval Candidate L3: DAN-c1 / MBON-c1

**Gate: anatomy PASS for further evidence review only (2026-10-02).** This is a revised pathway hypothesis. The electrical reference and bounded simulator controllability tests have since run; neither validates biological efficacy or learning.

The original L1 specification paired DAN-c1 with MBON-m1 and labeled the circuit γ1pedc. Those identities/compartments do not match the lower-peduncle DAN-c1 learning evidence. A more anatomy-aligned hypothesis is **KC → MBON-c1 (CN-59) ← DAN-c1**, with a candidate direct MBON-c1 output to annotated descending neurons.

## Machine-readable first-instar anatomy

The reproducible audit script [`audit_larval_l3_c1_candidate.py`](../scripts/audit_larval_l3_c1_candidate.py) reads the pinned Winding et al. S1 matrix. The generated source-ID-preserving audit is `data/raw/larval_l1em/candidate_l3_c1_audit.json` (ignored raw data; SHA-256 `009b05fd773e3ba663e09ecf296da571d2691a2b73cfc57803d57054e707457a`). S1 archive SHA-256: `8C1F43809ED5D527BA61B154E377CC21DA26383A75EDA8AAB85CE05607A72A4C`.

| Role / edge | First-instar IDs or contacts | Evidence category |
|---|---|---|
| DAN-c1 | 15,592,096; 16,240,569 | **MEASURED** cell annotations in S1 |
| MBON-c1 / CN-59 | 16,223,537; 8,980,589 | **MEASURED** cell annotations in S1 |
| DAN-c1 → MBON-c1 | Four pairwise edges: 41, 45, 60, 63 contacts | **MEASURED** anatomy; no functional sign/efficacy implied |
| KC → MBON-c1 | 116 annotated KC→MBON pair rows; 2,504 contacts total (56 edges/1,155 contacts to one cell; 60/1,349 to the other) | **MEASURED** whole-cell anatomy; compartment-local plastic contact set remains unresolved |
| MBON-c1 → descending neurons | Direct S1 edges include 20 contacts to left DN-VNC CN-28/PL-17 (ID 10,411,574) and 9 to its right-side partner (ID 17,379,420); other DN-VNC and pre-DN-VNC targets also exist | **MEASURED** direct anatomy/type annotation; action function and sign are not established by counts |

## Functional fit and limits

The 2025 DAN-c1 study reports that DAN-c1 is required for third-instar aversive olfactory learning and places its mushroom-body innervation in the lower peduncle (LP). It also proposes, rather than directly measures, dopamine-dependent modulation of MBN→MBON synapses. [Deng et al., 2025](https://elifesciences.org/articles/100890). FlyBase’s current ontology identifies larval MBON-c1/CN-59 as postsynaptic in the LP and cholinergic, based on cited larval anatomy; that supports the identity match, not an effective electrical weight. [FlyBase FBbt:00047967](https://flybase.org/cgi-bin/cvreport.pl?childdepth=2&cvterm=FBbt%3A00047967&rel=is_a). The underlying connectome is first-instar, whereas the learning evidence is third-instar.

Remaining evidence gaps are substantial:

- No direct experiment here establishes that the exact KC→MBON-c1 contacts store the association or measures their learning-induced change.
- No measured local DAN-c1-gated plasticity equation, sign, amplitude, or eligibility window is available.
- The L1 matrix gives contact counts, not unitary weights or per-edge delays. Cell-level transmitter annotation does not assign every target’s effect.
- The DN-VNC CN-28/PL-17 edge is a plausible fixed descending route, but its task-relevant motor/action role, sign, and output threshold need evidence.
- The L2 electrical reference and its controllability failure do not transfer to L3; its all-positive contact transform must not be reused as a biological prior.

## Decision

L3 is a **better anatomy/teaching-compartment match** than the specified L1 pairing. Its assumption-labeled electrical reference is frozen at `configs/larval_l3_c1_electrical_v1.json`; it is not evidence-pinned biology. Neutral dynamics show no spontaneous action and activate KC/MBON-c1 under input, while DN-VNC remains silent at the reference weights. The bounded pre-training control sweep passes in this simulator: 2× activates one of eight states and 4× activates five of eight, with nested action sets and deterministic replay. See [controllability report](LARVAL_L3_C1_CONTROLLABILITY.md). This establishes engineering control authority only. Before plasticity, the outstanding gate is whether any evidence-supported local DAN-c1 rule and update direction is compatible with this output path. Exact KC→MBON-c1 storage plasticity and DAN-gated rule remain unmeasured; the DN-VNC task action role/sign also remains unknown.
