# Level 4D recorded playback

Open [malecns-level4d-playback.html](malecns-level4d-playback.html) in a local browser. It is a self-contained playback of selected data from the frozen Level 4D receipt; it does not simulate another trial or download data.

Choose a condition and either **Frozen evaluation** or **Teaching presentation**. In frozen evaluation, a fresh 500 ms note uses retained weights with DAN and plasticity off. Its recorded KC spikes, MBON05 voltage, and action event are shown. In teaching mode, select a block to inspect its first DAN-activated presentation. That presentation has recorded KC and DAN spikes and before/after weights; the weights change at the DAN gate. A full MBON voltage trace for that particular teaching presentation was not stored, so the playback leaves that lane unavailable. The Level 4D receipt records an action event, not a physical key code.

[malecns-level4d-source.html](malecns-level4d-source.html) is the editable Codex visualization fragment from which the standalone file was rendered. Both files embed a compact selection of saved logs. The [published result bundle](../results/malecns-level4d/summary.md) contains the complete 21-position maps and source artifact hashes. The large full receipt remains in local `runs/` and is not committed.

## EA-MVP iteration-one recorded training

Open [ea-mvp-training-playback.html](ea-mvp-training-playback.html) locally. It embeds all 500 saved seed-907 single-note training trials and three later frozen-weight pattern evaluations. Use the trial slider or **First press** button, select 1×/5×/20× simulated-time playback, and compare learned, shuffled-teaching, and initial-weight arms in the frozen tests. Only the repeated lane-0 note was trained; lane switches, chords, holds, and the full *Freedom Dive* chart were not training material. The HTML does **not** include the entire song or per-millisecond neural voltage traces.

The [fly-training explainer](../docs/EA_MVP_FLY_TRAINING_EXPLAINER.md) documents the biological versus engineered pipeline and the dense `11`/`121` limitation. The HTML is a self-contained record, not a live neural run. Extract the [raw receipt bundles](../results/ea-mvp-iteration-1/README.md) to restore `runs/ea_mvp/`, then rebuild it with `python scripts/build_ea_mvp_training_viewer.py` and check controls with `node scripts/check_ea_mvp_training_viewer.js`. The editable [viewer template](ea-mvp-training-playback.template.html) is included.

The [silent Freedom Dive replay MP4](freedom-dive-fly-replay-silent.mp4) shows the saved FD-4 headless trace in the recreation. It is recorded playback with fixed fly weights, not a live neural run or desktop osu!lazer capture. The original export's imported song audio remains local.

The [training showcase MP4](ea-mvp-training-showcase.mp4) records the HTML viewer through all 500 training trials and all three later test patterns under learned, shuffled-teaching, and initial weights. It runs trials 1–350 at 20×, trials 351–358 at 5×, slows to 1× for the first press at trial 359, then returns to 20× for the remaining training trials. Every test arm plays at 1×. The video is silent and uses only saved events; no new simulation or learning was run. Rebuild with [`export_ea_mvp_training_showcase.js`](../scripts/export_ea_mvp_training_showcase.js) using Node.js, Playwright, Microsoft Edge, and FFmpeg.
