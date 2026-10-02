# BANC v888 source validation and data-only import

**Superseded source audit:** the user selected MaleCNS v1.0 after this import. BANC is no longer Project B's selected connectome; see [the active MaleCNS report](MALECNS_V1_DATASET_REPORT.md). These BANC files remain separate for provenance and are not mixed into the MaleCNS graph.

## Scope and provenance

This run imports one specimen/release: the BANC adult female brain and ventral nerve cord, materialization v888. The three upstream files are kept byte-for-byte under `data/raw/banc_v888/`. "Raw" here means **unmodified upstream data products**, not raw EM imagery or the per-synapse table. The topology input is the **compiled v2 simple neuron-to-neuron edgelist**, whose synapse detector used a size threshold of at least 5. No further edge-count threshold was imposed by this importer. It must not be read as a complete inventory of every biological synapse.

The [BANC project data index](https://github.com/htem/BANC-project/blob/main/manuscript/print/banc_data_locations.md) identifies these products and the v2 size threshold. The [BANC paper](https://www.nature.com/articles/s41586-026-10735-w) and [archived dataset DOI](https://doi.org/10.7910/DVN/7WTH1N) identify the source study. These copies came from the project's public GCS bucket with pinned object generations; the archive API returned HTTP 403 in this environment. Object MD5 values from GCS and local SHA-256 hashes were checked before import. Exact URLs, generations, sizes, and SHA-256 hashes are in `data/raw/banc_v888/source_manifest.json` and copied into `data/processed/banc_v888_v2/import_report.json`.

| Source file | Bytes | SHA-256 |
| --- | ---: | --- |
| `banc_888_meta.feather` | 57,503,026 | `86ccf5df0c67419f8c5f43e93a7ed38d23a080e9f7fde26737290252f3780098` |
| `banc_888_edgelist_simple_v2.feather` | 305,250,378 | `363fdef3813b72a5e45a42f17034cd5a544b654c838929cecf6e1ce5f60625cb` |
| `banc_888_neurotransmitter_prediction_v2.csv` | 21,107,592 | `bb0f4afa48a05d90008c6d801e053ff2667fb1ba68e29501c92f49514540da1d` |

## Source validation

The importer validates checksums and required columns, rejects duplicate metadata IDs, nonpositive edge counts, missing edge endpoints, duplicate directed edge pairs, edge counts exceeding provided neuron totals, inconsistent `norm`, conflicting transmitter calls for the same ID, and transmitter scores outside `[0,1]`. It creates the normalized tables only after the source preflight passes. A separate post-import validator compared **all** normalized source IDs, all 11,752,828 edge directions and counts, and every source-row index to the upstream files.

| Finding | Observed |
| --- | ---: |
| Metadata rows / unique IDs | 188,508 / 188,508 |
| Directed connection rows / unique pairs | 11,752,828 / 11,752,828 |
| Unique IDs used by edges | 172,433 |
| Edge endpoint IDs missing from metadata | 0 |
| Nonpositive edge counts / inconsistent edge totals or norms | 0 / 0 |
| Self-connection rows | 156,311 |
| Sum of synapse counts in this edge product | 35,733,096 |
| Transmitter CSV rows / unique IDs | 169,635 / 168,432 |
| Transmitter CSV IDs repeated with the **same** call and score | 551 IDs, 1,203 extra rows |
| Metadata IDs absent from transmitter CSV | 20,092 |
| Transmitter CSV IDs absent from metadata | 16 |
| Non-null metadata versus CSV transmitter-call disagreements | 593 |
| Missing/NaN metadata transmitter scores | 808 |

The current GCS objects differ from older online column documentation in row counts and in containing self-connections. The object generations and hashes above identify what was actually measured here. The 593 transmitter disagreements were preserved as separate metadata and v2 CSV fields; no preferred biological call was invented. Duplicate CSV IDs were collapsed only after confirming their call and score agreed. The source metadata includes labels beyond neurons, so the table retains every source ID and marks explicit `glia`, `trachea`, and `not_a_neuron` entries. This avoids silently discarding connected IDs.

## Statistics

| Quantity | Count |
| --- | ---: |
| Source nodes explicitly labeled non-neuronal | 13,107 |
| Source nodes with unknown `super_class` | 28,632 |
| Connections incident to explicitly non-neuronal nodes | 60,017 |
| Connections incident to unknown-class nodes | 1,043,667 |
| Nodes with no incoming / no outgoing row in this edge product | 16,898 / 19,148 |
| Largest incoming / outgoing partner count | 6,577 / 6,669 |
| Largest incoming / outgoing summed synapse count | 29,724 / 32,963 |
| Distinct nonmissing `cell_type` labels | 11,504 |
| Nodes with missing `cell_type` | 69,760 |

Neuron-level `region` labels: optic lobe 108,764; central brain 47,688; ventral nerve cord 31,688; unknown 368. The region label locates the **neuron in the metadata**, not each synapse or every part of a neuron spanning regions.

Predicted transmitter calls in metadata: acetylcholine 87,059; glutamate 25,099; GABA 21,686; dopamine 8,344; histamine 7,411; octopamine 2,303; serotonin 1,936; tyramine 215; unknown 34,455. These are **per-neuron predictions**, not measured synaptic effects. Verified transmitter fields are missing for 123,022 source nodes and can list multiple transmitters. No excitatory/inhibitory sign, release probability, receptor, time constant, or dopamine reward function was inferred.

Edge synapse-count buckets: 1 = 6,456,552 rows; 2 = 2,125,957; 3–5 = 1,911,441; 6–10 = 731,824; 11–50 = 489,507; >50 = 37,547. Minimum/maximum edge count: 1/1,103. These totals describe the selected compiled edgelist, not the full per-synapse table.

The complete field counts, including cell classes/types and both transmitter sources, are in `data/processed/banc_v888_v2/import_report.json`.

## Internal schema and boundaries

- `neurons.parquet`: one row for each metadata ID, sorted by unsigned `source_id` with contiguous `runtime_index:uint32`. Includes region, side, flow, class hierarchy, cell type, proofreading/status annotations, metadata transmitter prediction/score/verification, separate `nt_v2_*` prediction/score, and `explicit_non_neuron:bool`. The filename follows the project interface; **a row is a source graph node, not necessarily a verified neuron**.
- `connections.parquet`: one row per source directed pair, preserving source order: `source_row:uint32`, `pre_index:uint32`, `post_index:uint32`, `synapse_count:int32`. `source_row` is the zero-based row in the immutable v2 edgelist; the indices join to `neurons.runtime_index` and recover original source IDs. Self-connections remain present.
- `import_report.json`: source manifest, validation findings, statistics, and schema meaning. `validation_receipt.json`: full round-trip comparison counts and derived-table checksums.

The internal tables are columnar and use O(N+E) storage. They do not materialize a dense N×N matrix. A later graph compiler may build outgoing CSR from these IDs without changing the source schema. No simulation, training, plasticity assignment, subgraph extraction, or sensory/motor mapping was performed.

## Open decisions before circuit use

1. Decide and document whether to exclude explicit non-neuronal nodes and how to handle the unknown-class nodes; record boundary edges in any resulting subgraph.
2. Audit the 593 metadata/CSV transmitter disagreements and choose a documented annotation precedence if a later circuit needs one. Keep missing calls unknown.
3. Select and audit the anatomical subcircuit and its source IDs, then define region and boundary policy. Neuron-level `region` cannot substitute for synapse neuropil location.
4. Treat edge counts as anatomy only. Synaptic sign, delay, efficacy, receptors, and plastic sites require separate evidence and sensitivity analyses.
5. If per-synapse spatial or transmitter evidence becomes necessary, import the pinned v2 per-synapse product separately; do not pretend this pair-level table contains it.

M2 synthetic learning remains below its declared reliability gate. This data-only import does not advance any training or biological-learning claim.

## Reproduction

With Python 3.11+ and `pyarrow` plus `numpy` installed, from the project root:

```powershell
python scripts/download_banc_v888.py
$env:PYTHONPATH='src'
python scripts/import_banc_v888.py
python scripts/validate_banc_import.py
python -m unittest tests.test_connectome_importer -v
```

The raw and processed directories are gitignored; do not commit the large source or generated graph files. `pyarrow` is an optional ingestion dependency and is not needed for the M0/M1 simulator tests.
