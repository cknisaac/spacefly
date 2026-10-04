# EA-MVP iteration-one receipts

These six archives publish the saved iteration-one run receipts and small working diagnostics. They contain **103 files from `runs/`** and **45 top-level `work/` files**. No experiment was rerun to assemble them. Each archive retains repository-relative paths; extract from the repository root to restore the paths cited in the stage reports.

```text
tar -xzf results/ea-mvp-iteration-1/ea-core.tar.gz
tar -xzf results/ea-mvp-iteration-1/ea-confirmation-v2.tar.gz
tar -xzf results/ea-mvp-iteration-1/ea-confirmation-fixed.tar.gz
tar -xzf results/ea-mvp-iteration-1/freedom-dive.tar.gz
tar -xzf results/ea-mvp-iteration-1/lazer-mvp.tar.gz
tar -xzf results/ea-mvp-iteration-1/work-evidence.tar.gz
```

[manifest.json](manifest.json) records SHA-256 and byte size for every contained file and each archive. The [training viewer](../../visualization/ea-mvp-training-playback.html) and [silent replay MP4](../../visualization/freedom-dive-fly-replay-silent.mp4) can be opened without extraction. The MP4 is a saved FD-4 playback, not live neural activity.

The original MP4 with imported *Freedom Dive* audio, imported `.osz`/`.osu` media, raw connectome tables, copied osu!lazer source checkout, caches, and machine-specific application data are excluded. The source checkout is available separately from osu!lazer upstream. These bundles do not revise any frozen protocol or strict-biology result.
