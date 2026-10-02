# Reproducibility and publication boundary

## Inspect the published result

The [Level 4D result bundle](../results/malecns-level4d/summary.md) contains a compact machine-readable metric file, every frozen position-map row, artifact hashes, and a portable playback. It was extracted from the existing full receipt without running another learning experiment.

## Run the software checks

Install Python 3.11+ in a virtual environment and run, from the repository root:

```text
python -m pip install -e ".[connectome]"
python -m unittest discover -s tests
```

The suite includes checks that need locally available connectome artifacts. The [data guide](../data/README.md) and [MaleCNS import report](MALECNS_V1_DATASET_REPORT.md) explain how the original source files and derived tables are obtained. The public manifests record filenames, official URLs, sizes, and SHA-256 hashes.

## Full historical runs

The `runs/` tree contains large raw results and is ignored by Git. Many old reports link to local `runs/` files or heavy `docs/figures/` traces. Those links describe original evidence paths; a fresh GitHub checkout will have the compact published bundle but not every historical raw event stream. [Artifact hashes](../results/malecns-level4d/artifacts.json) and the [local diagnostic manifest](../results/local-artifact-manifest.csv) let an independently obtained full receipt be checked against this record.

The Level 4D runner is [`experiment_level4d_final_moving_note_repair.py`](../src/project_b/malecns_continuous_position_learning/experiment_level4d_final_moving_note_repair.py), with a [frozen configuration](../configs/malecns_level4d_final_moving_note_repair.json). Its parent-stage receipts and source-derived anatomy files are required for exact replay. The repository does not currently provide a one-command, data-free reproduction of the entire experimental history. Read the [protocol](MALECNS_LEVEL4D_FINAL_REPAIR_PROTOCOL.md) before interpreting or rerunning it.

The documentation reorganization has not altered historical configurations, results, thresholds, or learning code. [CURRENT.md](../CURRENT.md) is the append-only record of stage decisions and verification.

## Check the public tree before publishing

Run `python scripts/build_docs_catalog.py --check` to confirm the document index is current, then `python scripts/check_publication.py` to check curated links, the compact Level 4D result, artifact hashes when locally available, and the candidate Git file sizes. With the full local `docs/figures/` cache present, `python scripts/build_local_artifact_manifest.py --check` verifies the excluded-file hash list. Regenerate that list with the same command without `--check` after changing which local diagnostic files are excluded.

The project currently has no chosen public author citation or software license. Those fields are intentionally unset.
