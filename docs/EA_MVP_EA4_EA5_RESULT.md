# EA-MVP teacher check and first development result

**2026-10-03.** This is the separate **ENGINEERING ASSUMPTION** branch. The strict biology reports and saved osu! recreation were not changed. EA-05 (game label to DAN) and EA-06 (eligibility and local LTD) were frozen in `configs/ea_mvp_teacher_local_protocol.json` before the EA-4 fixture. The EA-5 development count and checkpoints were frozen in `configs/ea_mvp_development_v1.json` before development.

## EA-4: PASS for the one-pulse mechanism

The real headless game's label-only MISS was delivered after it became available. The fixed adapter drove the three predeclared PAM08 DANs. One recently active, connected KC→MBON05 synapse changed. DAN-off, plasticity-off, eligibility-off, late unpaired MISS, GOOD, and no-result controls kept all weights unchanged. Two exact replays and the original-weight floor check passed. The receipt is `runs/ea_mvp/teacher_local_result.json`. This validates the engineered local update contract, not useful task learning or a physiological game-to-DAN mapping.

## EA-5 v1: FAIL for behavior

The frozen development run completed 500 repeated isolated lane-0 notes in each of learning-on, DAN-off, and plasticity-off arms. All 500 learning-on episodes received MISS and had no key DOWN, so the predeclared Good-or-better first-DOWN count was **0/500**. The two controls also had 0/500. Learning-on made one local synaptic update per episode; both controls made zero. The only changed edge was KC source **45199**, selected slot 0, whose weight fell from **0.03649635** to **0.01480582**. Full receipt: `runs/ea_mvp/development_v1.json`, SHA-256 `c7e8339cdeda60efd839ef0f823d70ff619cbaa7d3bee582cf23b0e66c96b36c`.

The game resolves a no-action MISS at approximately 627.5 ms; the first artificial DAN spike occurs at 642 ms. The frozen 150-ms eligibility window starts at 492 ms and contains only the terminal KC spike at 500 ms. Earlier KCs did spike along the path, but their spikes are outside this window, so their synapses cannot change. The fixed readout closes the x=0 bin at 501 ms, inside the Good window, but its decision uses the **maximum** voltage recorded across that bin. Its baseline maximum was 0.01041946 mV at 489 ms, before the sole eligible KC45199 spike, and exceeds the 0.00557234 mV threshold. Depressing that last synapse cannot lower an already recorded maximum; all earlier bins also close before that spike. In a separate task-free boundary diagnostic, forcing this one eligible weight to its allowed 20% floor still produced no DOWN. This is a structural timing/credit-assignment failure, not evidence that more episodes or a larger learning rate would help.

The source config's present LF bytes differ from a historical pin only by line endings; deterministic LF→CRLF conversion reproduces the legacy checksum. The EA-specific loader checks both representations and the audited 32-KC/DAN coverage. It leaves all strict source files and strict hash checks unchanged.

## Decision and next experiment

**EA-5 v1 FAIL. EA-6 confirmation is not run.** The strongest supported statement is that this engineered game-feedback loop modifies a source-identified fly synapse locally, but did not learn a timely key action under the frozen v1 assumptions.

Next, predeclare an EA-01/03 task-independent sensory recruitment and controllability probe. It should determine whether cue positions before contact can activate multiple audited KCs and whether a declared local weight intervention can affect the fixed readout there, while preserving the source anatomy. If it fails, retain the FAIL and version any revised engineering assumption before further development. Do not choose a sensory scale or eligibility window by maximizing game score. A fresh confirmation is allowed only after a separately frozen development candidate passes its mechanism and retention gates.
