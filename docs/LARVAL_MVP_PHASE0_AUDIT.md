# Larval internal-learning MVP — Phase 0 audit

**Status: FAIL for proposed Candidate L1 as specified (2026-10-02).** This is a new larval branch. Adult MaleCNS and prior synthetic results remain preserved as legacy evidence; they are not treated as larval anatomy or validation.

## Repository audit (2026-10-02)

The bullets below record the initial Phase 0 point-in-time audit, before the larval source bundle and later manifests were added; they are retained as chronology, not current-state claims. Current larval artifacts and the electrical v1 result are summarized below and in the source audit.

- The active local connectome source is MaleCNS v1.0. Its configuration and imported datasets are adult male CNS products. They cannot be used to establish larval neuron identities, edges, contacts, or signs.
- The repository also contains a historical BANC v888 import, which is likewise not the larval dataset required here.
- No larval connectome source files or larval subgraph manifest are currently present under `data/`.
- Existing simulator, sparse graph, event, checkpoint, and experiment infrastructure may be reused only after a larval-specific data adapter and provenance checks are established.
- The old adult Branch B pathway decisions remain historical. They do not admit or reject the larval γ1pedc candidate.

## L1 anatomy claims to resolve from machine-readable source

| Claim | Current status | Required evidence |
| --- | --- | --- |
| γ-KC identities for γ1pedc | UNKNOWN | Source dataset neuron annotations and compartment membership |
| MBON-m1 identity/identities | UNKNOWN | Annotation crosswalk tied to source IDs |
| DAN-c1 identity/identities | UNKNOWN | Annotation crosswalk and compartment targeting evidence |
| γ-KC→MBON-m1 contacts | UNKNOWN | Directed source edge rows and contact counts |
| DAN-c1→MBON-m1 anatomical contacts | **No direct edge in inspected S1 matrix** | Directed source rows; see limits in the source audit |
| MBON-m1→Basin-4 path | UNVERIFIED | Exact IDs, edge direction, contact counts, and relay sequence in the larval graph |
| Strongest downstream action/premotor route | UNKNOWN | Bounded graph search followed by cell-type/evidence review |
| Transmitter and synaptic sign | UNKNOWN | Source annotations plus receptor/effect literature; transmitter alone will not determine sign |

## Candidate L1 decision — FAIL

The candidate definition conflates larval and adult mushroom-body nomenclature and teaching logic:

- The connectome-linked larval DAN-c1 identities reported by the anatomy review are L1EM **16240569** and **15592096**. They are associated with the adult PPL1-γ1pedc homology, but homology does not establish the same larval learning function.
- Larval MBON-m1 / CN-62 identities are L1EM **17016974** and **4022539**. This is a distinct, multi-compartment GABAergic neuron, not the larval counterpart of adult γ1pedc MBON11.
- The larval counterpart of adult MBON11 is MBON-d1. The larval d1 compartment is associated with DAN-d1, rather than the candidate's DAN-c1 teaching assignment.
- The evidence on DAN-c1 has evolved: an earlier screen reported no learning with DAN-c1 activation, while a later study (2025) reports DAN-c1-dependent third-instar aversive olfactory learning and places the relevant input in the lower peduncle (LP). That update supports a larval DAN-c1 learning role, but does not establish the proposed γ1pedc / MBON-m1 locus. The specified L1 combination still conflates the LP DAN-c1 route with the distinct MBON-m1/CN-62 identity and assumes a compartment-matched plastic pathway not shown by the supplied evidence. Adult γ1pedc physiology cannot be transferred by name alone.

These findings contradict the proposed `γ1pedc γ-KC → MBON-m1 ← DAN-c1` learning locus. Candidate L1 is therefore rejected before subgraph construction, electrical modeling, controllability, or training. Do not repair this candidate by renaming cells, substituting adult physiology, or tuning the output. Any different larval candidate requires a new, explicitly scoped design decision and its own anatomy/rule audit.

Sources: [Winding et al., 2023, larval CNS connectome](https://pmc.ncbi.nlm.nih.gov/articles/PMC7614541/); [Eschbach et al., 2021, larval learned/innate valence integration and MBON-m1](https://pmc.ncbi.nlm.nih.gov/articles/PMC8616581/); [Truman et al., 2023, metamorphosis of memory circuits](https://elifesciences.org/articles/80594); [Eschbach et al., 2020, initial DAN-c1 learning screen](https://elifesciences.org/articles/62567); [Deng et al., 2025, DAN-c1-dependent larval aversive learning and D2-like receptors](https://elifesciences.org/articles/100890).

## Phase 0 decision

Do not construct or simulate Candidate L1. The anatomy/functional evidence already rejects its specified identity and teaching combination. The anatomy agent's separate edge-level review of the claimed MBON-m1→Basin-4 route is still pending; it can refine the route record but cannot reverse the cell-identity and teaching contradiction. Preserve uncertainty where contact counts or physiological sign remain unresolved.

## L1 route audit status

The L1 direct-edge audit is complete: the inspected S1 axon-to-dendrite matrix contains 437 KC→MBON-m1 contacts across both annotated MBON-m1 cells and no direct DAN-c1→MBON-m1 edge among the selected IDs. It does not establish compartment-level KC boutons, effect signs, physiology, or the proposed Basin-4 route; the full CATMAID audit found no direct MBON-m1→Basin-4 edge, while a complete multihop Basin-4 search remains unrun. See [`LARVAL_CONNECTOME_SOURCE_AUDIT.md`](LARVAL_CONNECTOME_SOURCE_AUDIT.md). L1 does not advance.

## Replacement Candidate L2 — anatomy gate PASS for model design only

DAN-d1 / MBON-d1 passed anatomy admission only; the frozen electrical reference failed controllability, and a later evidence gate found insufficient direct support for an evidence-pinned v2. The machine-readable supplement contains 841 axon-to-dendrite KC→MBON-d1 contacts (60 KC IDs to one cell and 59 to the other) and four DAN-d1→MBON-d1 cell-pair edges (25–33 contacts each). MBON-d1 has direct matrix edges to Ipsigoro (4–9 contacts per cell pair). The immutable manifest at `configs/larval_l2_subgraph_manifest_v1.json` contains 127 nodes and 131 directed edge rows: 119 KC→MBON-d1, four DAN-d1→MBON-d1, four MBON-d1→Ipsigoro, and four Ipsigoro→Goro. Its builder and endpoint/count integrity checks pass. Compartment-specific plasticity, exact learning locus, and all physiological signs/effects remain unresolved. This gate permits electrical model design only; it does not establish controllability or qualify L2 for learning.


## Revised Candidate L3 — anatomy PASS for evidence review only

The original L1 identity pairing remains rejected. Newer third-instar literature supports DAN-c1 aversive learning at the lower peduncle (LP), so the next anatomy-aligned hypothesis is **KC→MBON-c1 (CN-59)←DAN-c1**, not MBON-m1/γ1pedc. The pinned first-instar S1 matrix confirms four DAN-c1→MBON-c1 edges (41, 45, 60, 63 contacts), 116 annotated KC→MBON-c1 edges (2,504 contacts), and direct outputs from MBON-c1 to annotated descending DN-VNC cells. Exact details are in [`LARVAL_CANDIDATE_L3_C1_ANATOMY.md`](LARVAL_CANDIDATE_L3_C1_ANATOMY.md) and reproducibly generated by [`audit_larval_l3_c1_candidate.py`](../scripts/audit_larval_l3_c1_candidate.py). The exact memory-storage synapses and local learning rule remain inferred/unknown; first-instar anatomy and third-instar learning evidence do not prove stage-matched function. This candidate is not yet admitted to electrical modeling or training.
