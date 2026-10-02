# Larval L1EM source and pathway audit

**Status: source audited; L1 specified circuit rejected; L2 anatomy admitted for model design only; electrical reference v1 FAILS controllability.** The retained source copy and SHA-256 are recorded in [`source_manifest.json`](../data/raw/larval_l1em/source_manifest.json). The edge extraction is reproducible with [`audit_larval_supplement_edges.py`](../scripts/audit_larval_supplement_edges.py); its machine output is [`edge_audit.json`](../data/raw/larval_l1em/edge_audit.json).

## Source and limits

The Winding et al. paper makes Supplementary Data S1 available and identifies the L1 Larval CNS CATMAID project as the raw reconstruction source. We retained the S1 archive from a public mirror that identifies it as the paper's data; the copy's hash is pinned. The axon-to-dendrite (`ad`) matrix has 2,952 individual neuron IDs. Rows are presynaptic IDs, columns are postsynaptic IDs, and values are synapse counts. These counts do not identify sign, efficacy, or plasticity.

The published S1 annotation table does not label Basin-4, and the two Goro IDs are absent from its matrix. A read-only query of the full [VFB-hosted L1EM CATMAID project](https://kbw.virtualflybrain.org/hosted/l1em-catmaid/) resolves the action route. It finds MBON-d1→Ipsigoro and Ipsigoro→Goro contacts. A direct MBON-m1→Basin-4 query returns no edge; this rules out the direct edge only, not every possible multihop route. The audit did not run a whole-graph multihop search to Basin-4.

## Verified identities and contacts

| Role | L1EM IDs | Evidence/status |
| --- | --- | --- |
| DAN-d1 | 3,886,356; 5,966,099 | S1 annotation; pair labels `DAN-d1` |
| MBON-d1 | 4,241,237; 7,055,857 | S1 annotation; pair labels `MBON-d1` |
| DAN-c1 | 15,592,096; 16,240,569 | S1 annotation; pair labels `DAN-c1` |
| MBON-m1 / CN-62 | 4,022,539; 17,016,974 | S1 annotation; pair labels `MBON-m1; CN-62` |
| Ipsigoro | 3,979,181; 5,794,678 | VFB crosswalk and full CATMAID connectivity query |
| Goro | 3,720,037; 5,206,247 | VFB crosswalk and full CATMAID connectivity query; absent from the S1 matrix |

Directed contact counts extracted from S1:

| Presynaptic → postsynaptic | Contacts | Interpretation |
| --- | ---: | --- |
| DAN-d1 3,886,356 → MBON-d1 4,241,237 | 32 | Direct anatomical edge |
| DAN-d1 3,886,356 → MBON-d1 7,055,857 | 29 | Direct anatomical edge |
| DAN-d1 5,966,099 → MBON-d1 4,241,237 | 33 | Direct anatomical edge |
| DAN-d1 5,966,099 → MBON-d1 7,055,857 | 25 | Direct anatomical edge |
| Annotated KC→MBON-d1 | 841 total (60 annotated KC IDs to left MBON-d1; 59 to right MBON-d1) | Both MBON-d1 cells combined; not a d-compartment contact mask |
| Annotated KC→MBON-m1 | 437 total (44 annotated KC IDs per MBON-m1 cell) | Both MBON-m1 cells combined; not a γ1pedc contact mask |
| MBON-d1 4,241,237 → Ipsigoro 3,979,181 / 5,794,678 | 4 / 5 | Direct anatomical edges |
| MBON-d1 7,055,857 → Ipsigoro 3,979,181 / 5,794,678 | 9 / 6 | Direct anatomical edges |
| Ipsigoro 3,979,181 → Goro 3,720,037 / 5,206,247 | 13 / 1 | Direct full CATMAID edges |
| Ipsigoro 5,794,678 → Goro 3,720,037 / 5,206,247 | 6 / 9 | Direct full CATMAID edges |
| MBON-m1 pair → any annotated Basin-4 (direct query) | 0 | No direct edge; multihop path not audited |

The S1 edge list does not identify which KC boutons lie inside a specific mushroom-body compartment. The 841 and 437 values are whole-cell annotated KC totals, not compartment-specific plastic masks. Treat the wiring as **MEASURED** anatomy from S1/CATMAID; treat signs and the precise plastic contact locus as **UNKNOWN** pending relevant physiological evidence and finer source data.

The highest-bottleneck two-hop route among the queried bilateral L2 nodes is `MBON-d1 7,055,857 → Ipsigoro 3,979,181 → Goro 3,720,037` (**9 then 13 contacts**). VFB/CATMAID identifies Goro as a rolling command neuron; mapping that larval action to a game key remains an **ENGINEERING OVERLAY**, not measured fly behavior in this task. The downstream circuit role is described in [Ohyama et al. (2015)](https://www.nature.com/articles/nature14297); the cell crosswalks are available from [VFB Ipsigoro](https://jupyter.virtualflybrain.org/blog/2022/01/01/larval-ipsigoro-neuron-fbbt_00111239/) and [VFB Goro](https://mayo.inf.ed.ac.uk/blog/2022/01/01/larval-goro-neuron-fbbt_00111240/). Full query output and retrieval provenance are pinned in `data/raw/larval_l1em/catmaid_route_audit.json`.

## Candidate decisions

- **L1: FAIL.** The proposed larval γ1pedc / DAN-c1 / MBON-m1 tuple confuses distinct larval identities and transfers adult teaching logic. The prior record remains in [`LARVAL_MVP_PHASE0_AUDIT.md`](LARVAL_MVP_PHASE0_AUDIT.md).
- **L2 (DAN-d1 / MBON-d1): anatomy gate PASS for model design only.** S1/CATMAID confirms KC→MBON-d1, DAN-d1→MBON-d1, and a two-hop MBON-d1→Ipsigoro→Goro route. Larval studies support DAN-d1 aversive teaching and MBON-d1 approach-promoting behavior. The precise KC→MBON-d1 synaptic depression locus remains **INFERRED**, not directly measured for this candidate. The 127-node / 131-edge anatomy manifest is built and integrity-checked. An electrical-reference config is now frozen before any outcome-based work; it uses an explicitly artificial positive-sign scenario for chemical edges, excludes DAN-d1 as an ordinary electrical synapse, and freezes explicit sensory/action overlays. The resulting v1 fails pre-training controllability: the declared KC→MBON-d1 multiplier sweep never activates Ipsigoro/Goro or the action interface. See [`LARVAL_L2_CONTROLLABILITY_PROBE.md`](LARVAL_L2_CONTROLLABILITY_PROBE.md). This rejects that electrical reference for learning, not the biological candidate.

## Interpretation

This audit advances the replacement pathway beyond a prose-only proposal and establishes an anatomical route to a behaviorally relevant action node. It licenses the minimal L2 anatomy manifest and evidence-labelled model design. No learning experiment may use electrical model v1 after its controllability failure. Any follow-up requires primary evidence that independently constrains electrical effects and the plasticity mechanism, then a separately versioned and frozen model. Do not extend the failed weight sweep or tune on task performance.
