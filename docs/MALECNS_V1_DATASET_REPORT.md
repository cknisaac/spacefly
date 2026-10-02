# MaleCNS v1.0 source validation and data-only import

## Selected source and scope

**MaleCNS v1.0 is the selected Project B connectome.** It is one adult male brain and ventral nerve cord reconstruction. The [official release page](https://male-cns.janelia.org/release/) identifies v1.0, and the [official download page](https://male-cns.janelia.org/download/) supplies the five files used here. The unmodified upstream objects are retained under `data/raw/malecns_v1/`, pinned to exact GCS generations and verified against the published object MD5 plus local SHA-256. Their URLs, generations, sizes and hashes are in `source_manifest.json` and copied into the import report.

The release supplies two connection scopes. The **full** file contains all segment-to-segment pairs, including fragments that are not curated neurons. The internal neuron graph uses the release's own **traced-only** file and annotation rows with `status == Traced`. Every traced-only pair and count was checked against the full file restricted to those traced IDs. This is a documented source-product boundary, not a learned or task-selected subcircuit. The files are released at minimum synapse confidence 0.5; this importer adds no pair-count threshold.

| Unmodified upstream file | Bytes | SHA-256 |
| --- | ---: | --- |
| `body-annotations-male-cns-v1.0-minconf-0.5.feather` | 14,483,314 | `2177e246113e4cfbf1e7772ec37c6da1955ff22e8063d0b1f833101f99a9a3b2` |
| `body-neurotransmitters-male-cns-v1.0.feather` | 43,282,834 | `95c9289220663abeb3409f3ad9e5a7f8a53f8093f5139d15502cd08da8879621` |
| `body-stats-male-cns-v1.0-minconf-0.5.feather` | 778,062,826 | `ca5dc83a26382ae70c8d8f42fc09ce2dbc1af7c03f3a001a1936b5e142540647` |
| `connectome-weights-male-cns-v1.0-minconf-0.5.feather` | 1,051,241,946 | `e35da783d1c686b2b58b3b87cd6a403ae43bfcfba8bff28e08ef752c1a56afc1` |
| `connectome-weights-male-cns-v1.0-minconf-0.5-traced-only.feather` | 508,025,642 | `9b3beab17bad5f618be3f2c02d3139a8d07b822565919c013f1e5506d93e604b` |

The earlier BANC import is **superseded and not selected**. Its files remain separate for provenance; no BANC edges or annotations enter this MaleCNS graph.

## Validation results

| Check or quantity | Result |
| --- | ---: |
| Annotation rows / unique body IDs | 211,577 / 211,577 |
| Rows labeled `Traced` | 165,122 |
| Transmitter rows / unique body IDs | 1,835,518 / 1,835,518 |
| Body-stat rows | 88,384,522 |
| Full segment-graph directed pairs | 151,856,684 |
| Sum of counts in full graph | 311,833,243 |
| Traced-graph directed pairs | 25,563,197 |
| Sum of counts in traced graph | 124,025,046 |
| Unique traced neurons used as an endpoint | 164,587 |
| Traced graph endpoints missing a `Traced` annotation | 0 |
| Duplicate directed pairs in traced graph | 0 |
| Nonpositive edge counts in either source graph | 0 |
| Traced-only rows and counts matching full graph's traced-ID restriction | 25,563,197 / 25,563,197 |
| Body-stat `post` sum versus full-graph count sum | Equal: 311,833,243 |
| Self-connections, full / traced | 123 / 101 |
| Traced neurons without a transmitter row | 502 |

The body-stat `synweight` field is **`post + downstream`**, not a second independent synapse total. Its source-wide sum is 623,666,486, while both `post` and `downstream` sum to 311,833,243. The import checks this identity and compares the full graph's edge-count sum with `post`.

An independent post-import validator compared every one of the 165,122 normalized neuron IDs and every one of the 25,563,197 normalized directed pairs and counts with the corresponding immutable source row. It also verified contiguous runtime indices and wrote derived-table checksums to `data/processed/malecns_v1_traced/validation_receipt.json`.

## Neurons, classes, regions and transmitters

The traced graph has 535 annotated traced neurons with no pair in the traced-only edge product. Among all traced neurons, 659 have no incoming pair and 1,583 have no outgoing pair. The largest incoming and outgoing partner counts are 11,526 and 11,203. Pair-count buckets: one synapse 10,292,924 rows; 2–4 9,034,591; 5–9 3,486,275; 10–49 2,521,469; at least 50 227,938.

There are 11,751 distinct nonmissing cell-type labels; 2,605 traced neurons have no type. The `class` field is missing for 140,598 traced neurons, so `superclass`, `class`, and `type` remain separate source annotations. Selected superclass counts: optic-lobe intrinsic 89,390; central-brain intrinsic 32,160; VNC intrinsic 13,151; visual projection 9,201; VNC sensory 6,365; central-brain sensory 4,868; optic-lobe sensory 4,114; ascending 1,846; descending 1,314; VNC motor 708. These are source labels, not verified functional input/output mappings for osu.

**Region coverage is limited.** The flat annotation file provides usable `somaNeuromere` labels for 21,800 traced neurons; 143,322 have no usable label. Two literal `NA` source values are counted as unknown while the raw file stays unchanged. The internal `region` column copies only usable source values and gives its basis as `soma_neuromere`. A soma neuromere is not a per-synapse ROI or a complete brain/VNC assignment for neurons that span compartments. No coordinate threshold or superclass prefix was used to fabricate missing regions. The largest observed soma-neuromere labels are T2 5,073, T1 4,295, T3 3,968, CG 2,396 and LB 1,312.

Per-neuron predicted transmitter calls: acetylcholine 94,946; glutamate 28,055; GABA 20,218; dopamine 4,443; histamine 2,026; serotonin 465; octopamine 102; source `unclear` 14,365; missing transmitter row 502. The separate consensus and ground-truth fields are preserved and counted in the machine-readable report. **Transmitter identity does not determine synaptic sign** without receptor/effect evidence; a dopamine call does not identify a task reward route.

## Internal schema

- `neurons.parquet`: 165,122 traced annotation IDs sorted by signed `source_id:int64`, with stable contiguous `runtime_index:uint32`; source status, superclass/class/subclass/type/instance, `region` with `region_basis`, soma neuromere/side, receptor annotation, and separate transmitter prediction, confidence, consensus and ground-truth fields.
- `connections.parquet`: 25,563,197 source-order directed pairs as `source_row:uint32`, `pre_index:uint32`, `post_index:uint32`, `synapse_count:int64`. Indices join to `neurons.runtime_index`, recovering both original body IDs. Self-connections are retained.
- `import_report.json`: source manifest, validation and complete statistics. `validation_receipt.json`: independent full-row round trip and derived file hashes.

The tables use O(N+E) columnar storage and no dense N×N matrix. A later runtime may compile outgoing CSR without changing the source data contract. No synaptic weight, delay, sign, plasticity mask, subcircuit, sensory/motor interface, simulation, or training was created here.

## Open limits before circuit use

1. A neural subcircuit still needs explicit source IDs, its edge-cut boundary and a route audit. The official traced-only graph is a release scope, not a task circuit.
2. Most traced neurons lack a soma-neuromere label. Per-synapse neuropil/ROI analysis requires a separate spatial source product; do not infer it from this flat pair table.
3. Predicted transmitters include `unclear` and missing cases. Receptor-dependent effects, delays, efficacy, and plastic sites remain unresolved.
4. The full graph includes untraced fragments. Its 151.9 million pairs and 311.8 million counted contacts must not be called 151.9 million neuron-to-neuron edges.
5. Synthetic learning still fails its declared reliability gate; this data-only correction supplies no evidence of learning or fly dynamics.

## Reproduction

With Python 3.11+ and the project's optional `connectome` dependencies (`numpy` and `pyarrow`), from the project root:

```powershell
python scripts/download_malecns_v1.py
$env:PYTHONPATH='src'
python scripts/import_malecns_v1.py
python scripts/validate_malecns_import.py
python -m unittest tests.test_malecns_importer -v
```

The large raw and processed files are gitignored. Keep their source manifest and the generated validation receipt with any exported graph.
