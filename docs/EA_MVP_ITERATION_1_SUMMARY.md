# Spacefly iteration 1 — engineering-assumption fly learner

**Closed 2026-10-04.** This is a handoff and navigation page, not a new experiment or a revision to a frozen result. The [EA-MVP specification](EA_MVP_SPEC.md) records the assumption registry and claim boundary; the [EA roadmap](EA_MVP_ROADMAP.md) and [Freedom Dive roadmap](EA_MVP_FREEDOM_DIVE_REPLAY_ROADMAP.md) retain the stage-by-stage decisions. The [fly training explainer](EA_MVP_FLY_TRAINING_EXPLAINER.md) gives a biological-versus-engineered account in ordinary language.

## What was built

- A headless osu!mania game and a separate playable 4K recreation, with a pinned *Freedom Dive* 4K Normal chart comparison. The playable recreation was kept separate from fly-policy changes. See the [recreation report](OSU_MANIA_RECREATION_RESULT.md) and [map comparison](OSU_MANIA_FREEDOM_DIVE_NORMAL_RESULT.md).
- A reduced MaleCNS v1.0-derived 32-KC→MBON05 timing circuit, with selected KC→MBON05 synapses as its only adaptive policy state. A fixed present-position encoder, electrical model, key readout, judgement→PAM08 teacher, eligibility rule, lane/chord router, and hold-release rule are all **ENGINEERING ASSUMPTIONS**. The source anatomy and strict biology results remain distinct.
- A saved fixed-speed training run. In seed 907, 500 repetitions of one lane-0 note led to the first press at trial 359; trials 1–358 were MISS and trials 359–500 were PERFECT. Seven selected synaptic weights changed. This is repeated single-note training, not training on four-lane songs or varied patterns.
- Frozen-weight tests: sequential lanes, equal-time chords, sequential holds, three EA-13 pattern families, and a full headless *Freedom Dive* run. The song replay used one continuing neural simulator, judged 1,310 chart objects, and kept fly weights fixed. The separate replay companion shows the saved run in the recreation. See [EA-13](EA_MVP_EA13_BROAD_EVALUATION_RESULT.md) and [FD-6](EA_MVP_FD6_REPLAY_COMPANION_RESULT.md).
- A [self-contained HTML playback](../visualization/ea-mvp-training-playback.html) for the 500 recorded training trials and three later frozen pattern tests. This is saved-event playback, not a live neural run. The [viewer guide](../visualization/README.md) explains its controls and data boundary.

## Decision ledger

| Question | Iteration-one result | Practical meaning |
| --- | --- | --- |
| Strict MaleCNS moving-note target learning | **FAIL** at Level 4D | The wrong-region action persisted; intended target action did not appear. This separate historical result is unchanged. [Frozen summary](MALECNS_MOVING_LEARNING_BRANCH_FREEZE.md) |
| EA-MVP local learning on repeated fixed-speed note | **Narrow PASS** in development; seed-907 training recorded | Under disclosed artificial interfaces, changed selected synapses acquired a fixed-speed timing press. [EA-5 v2](EA_MVP_EA5_V2_RESULT.md) |
| Generalization to unfamiliar note speeds | **FAIL 0/8** | Keep the tested policy to a fixed speed per map. [EA-6 v2](EA_MVP_EA6_V2_CONFIRMATION_RESULT.md) |
| Fixed-speed confirmation | **3/3 completed; formal 6/8 gate not reached** | The user capped the check at three seeds. Shuffled teaching matched learning-on. [EA roadmap](EA_MVP_ROADMAP.md) |
| Fresh lane/chord/hold patterns | **PASS within the EA-13 frozen scope** | Fixed routing plus retained timing weights worked on those small patterns; shuffled-teaching actions remained identical. [EA-13](EA_MVP_EA13_BROAD_EVALUATION_RESULT.md) |
| Full *Freedom Dive* headless playback | **FD-4 PASS for technical replay; quality limited** | The trace is deterministic and complete under its declared checks, not evidence of learning the chart. [FD roadmap](EA_MVP_FREEDOM_DIVE_REPLAY_ROADMAP.md) |
| osu!lazer comparison | **FD-5 PARTIAL** | Per-object judgements and non-miss offsets matched pinned in-process lazer across segments; uninterrupted full-map score parity was not verified. [FD-5 result](EA_MVP_FD5_LAZER_PARITY_RESULT.md) |
| Saved replay companion | **FD-6 PASS** | A separate Pygame viewer reproduces the saved headless trace; it is not live neural activity or desktop-client play. [FD-6 result](EA_MVP_FD6_REPLAY_COMPANION_RESULT.md) |

## Important limitation: dense same-lane repeats

The *Freedom Dive* trace is weaker on `11`-like direct repeats than on `121`-like returns. For same-lane tap gaps of 250–300 ms, 53/158 direct repeats missed versus 0/27 returns after an intervening other-lane note. One direct repeat pressed its second note 166 ms early; only one entire-chart DOWN attempt was suppressed because a key was already held. The likely issue is the engineered visible-cue selection, per-lane motion history, and readout rearm boundary, but the exact cause is not established without per-tick traces and a matched `11`/`121` diagnostic. The tally is reproducible from local chart/action receipts with [`analyze_ea_mvp_fd4_lane_repeats.py`](../scripts/analyze_ea_mvp_fd4_lane_repeats.py). See the [explainer](EA_MVP_FLY_TRAINING_EXPLAINER.md) for details.

## Claims and artifact boundary

**Supported:** a connectome-constrained *engineering model* stored a fixed-speed response through local changes in selected fly synapses, and the retained weights supported the stated frozen tests and headless chart playback under fixed external interfaces.

**Not supported:** that a living fly can play osu!; that this is a complete fly-brain simulation; that natural visual, motor, or game-feedback pathways were established; that correct judgement pairing caused the weight state (shuffled teaching performed identically); that dense same-lane repeats, mid-map speed changes, or mixed overlaps are solved; or that the full score was reproduced in the desktop osu!lazer client.

Source, configuration, protocols, reports, scripts, tests, the standalone HTML playback, a [silent replay video](../visualization/freedom-dive-fly-replay-silent.mp4), and [compressed iteration-one receipts](../results/ea-mvp-iteration-1/README.md) are in Git. The bundles restore the original `runs/ea_mvp/` paths and selected `work/` diagnostics; the published HTML embeds a compact selection of recorded events so it opens without extraction. The imported `.osz`, song audio, raw connectome tables, and copied osu!lazer source stay local. The original Python package name `project_b` is retained for compatibility.

## Release verification

The EA-MVP, lazer, playable-game, online-readout, environment, timing-window, and CLI focused suites passed **97 tests** in total using `PYTHONPATH=src`. The HTML builder checked the 500-trial and later-pattern data, its offline interaction harness passed, the direct-repeat tally reproduced 53/158 versus 0/27, and the generated documentation catalog passed `--check`. The full historical suite was not certified for this release: the initial system-Python invocation lacked `src` on the import path, and a corrected broad run was stopped after it entered intensive older simulations. A separate legacy first-action test has one error because its local `docs/figures/a2_mvp_coupled/uninterrupted_ledger.json` is absent; six tests in that file pass. These are verification boundaries, not changes to scientific result gates.
