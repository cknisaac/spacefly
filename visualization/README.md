# Level 4D recorded playback

Open [malecns-level4d-playback.html](malecns-level4d-playback.html) in a local browser. It is a self-contained playback of selected data from the frozen Level 4D receipt; it does not simulate another trial or download data.

Choose a condition and either **Frozen evaluation** or **Teaching presentation**. In frozen evaluation, a fresh 500 ms note uses retained weights with DAN and plasticity off. Its recorded KC spikes, MBON05 voltage, and action event are shown. In teaching mode, select a block to inspect its first DAN-activated presentation. That presentation has recorded KC and DAN spikes and before/after weights; the weights change at the DAN gate. A full MBON voltage trace for that particular teaching presentation was not stored, so the playback leaves that lane unavailable. The Level 4D receipt records an action event, not a physical key code.

[malecns-level4d-source.html](malecns-level4d-source.html) is the editable Codex visualization fragment from which the standalone file was rendered. Both files embed a compact selection of saved logs. The [published result bundle](../results/malecns-level4d/summary.md) contains the complete 21-position maps and source artifact hashes. The large full receipt remains in local `runs/` and is not committed.

## EA-MVP iteration-one recorded training

Open [ea-mvp-training-playback.html](ea-mvp-training-playback.html) locally. It embeds all 500 saved seed-907 single-note training trials and three later frozen-weight pattern evaluations. Use the trial slider or **First press** button, select 1×/5×/20× simulated-time playback, and compare learned, shuffled-teaching, and initial-weight arms in the frozen tests. Only the repeated lane-0 note was trained; lane switches, chords, holds, and the full *Freedom Dive* chart were not training material. The HTML does **not** include the entire song or per-millisecond neural voltage traces.

The [fly-training explainer](../docs/EA_MVP_FLY_TRAINING_EXPLAINER.md) documents the biological versus engineered pipeline and the dense `11`/`121` limitation. The HTML is a self-contained record, not a live neural run. Given the local raw receipts under `runs/ea_mvp/`, rebuild it with `python scripts/build_ea_mvp_training_viewer.py` and check controls with `node scripts/check_ea_mvp_training_viewer.js`. The editable [viewer template](ea-mvp-training-playback.template.html) is included; the raw receipts and imported music are not committed.
