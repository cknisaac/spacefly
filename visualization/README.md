# Level 4D recorded playback

## Iteration-one videos and training viewer

The later saved playbacks are on the engineering branch:

- [EA-MVP training showcase MP4](https://github.com/cknisaac/spacefly/blob/ea-mvp-engineering-assumption-fly-learner/visualization/ea-mvp-training-showcase.mp4)
- [Freedom Dive replay MP4, silent](https://github.com/cknisaac/spacefly/blob/ea-mvp-engineering-assumption-fly-learner/visualization/freedom-dive-fly-replay-silent.mp4)
- [Interactive training HTML](https://github.com/cknisaac/spacefly/blob/ea-mvp-engineering-assumption-fly-learner/visualization/ea-mvp-training-playback.html): download and open locally to use the playback controls.

The videos also appear in the root [README](../README.md). These are saved-event playbacks. The [training explainer](https://github.com/cknisaac/spacefly/blob/ea-mvp-engineering-assumption-fly-learner/docs/EA_MVP_FLY_TRAINING_EXPLAINER.md) describes the training, frozen tests, and claim boundaries.

## Earlier Level 4D viewer

Open [malecns-level4d-playback.html](malecns-level4d-playback.html) in a local browser. It is a self-contained playback of selected data from the frozen Level 4D receipt; it does not simulate another trial or download data.

Choose a condition and either **Frozen evaluation** or **Teaching presentation**. In frozen evaluation, a fresh 500 ms note uses retained weights with DAN and plasticity off. Its recorded KC spikes, MBON05 voltage, and action event are shown. In teaching mode, select a block to inspect its first DAN-activated presentation. That presentation has recorded KC and DAN spikes and before/after weights; the weights change at the DAN gate. A full MBON voltage trace for that particular teaching presentation was not stored, so the playback leaves that lane unavailable. The Level 4D receipt records an action event, not a physical key code.

[malecns-level4d-source.html](malecns-level4d-source.html) is the editable Codex visualization fragment from which the standalone file was rendered. Both files embed a compact selection of saved logs. The [published result bundle](../results/malecns-level4d/summary.md) contains the complete 21-position maps and source artifact hashes. The large full receipt remains in local `runs/` and is not committed.
