# Source data and local artifacts

The repository includes **manifests and checksums**, not the multi-gigabyte connectome downloads or generated Parquet tables.

- [MaleCNS v1.0 source manifest](manifests/malecns_v1_sources.json) lists official release objects, versions, sizes, and SHA-256 hashes. The [dataset report](../docs/MALECNS_V1_DATASET_REPORT.md) explains the traced-only graph and validation.
- [Larval L1EM source manifest](manifests/larval_l1em_sources.json) records the cited supplement and the inspected public copy. The [larval audit](../docs/LARVAL_CONNECTOME_SOURCE_AUDIT.md) describes the scope.

The import scripts are [`download_malecns_v1.py`](../scripts/download_malecns_v1.py), [`import_malecns_v1.py`](../scripts/import_malecns_v1.py), and [`validate_malecns_import.py`](../scripts/validate_malecns_import.py). They work with locally available upstream files in `data/raw/` and write derived tables to `data/processed/`; both large directories are ignored by Git. Do not treat a checksum manifest as a substitute for the source data.

Full experiment receipts under `runs/` are likewise local. The [result registry](../results/index.md) lists the compact evidence included in the public tree and states which full receipts are absent.

Large historical checkpoint and trace files under `docs/figures/` are also local-only; their hashes are in the [diagnostic manifest](../results/local-artifact-manifest.csv).
