# EA-MVP EA-11 — hold notes

**Decision: PASS for three isolated sequential holds after a versioned task-free repair.**

## Engineering assumption

**ENGINEERING ASSUMPTION:** when a visible head reaches the strike position, the timing pathway starts a DOWN. A fixed head/tail state in the encoder/readout suppresses the ordinary tap UP while the hold body remains visible, then sends UP when the visible tail reaches position zero. This supplies a hold-duration and release rule that the connectome-constrained timing circuit does not provide.

## Preserved admission failure and repair

Frozen admission v1 failed: while the hold body stayed visible, its head also remained visible at position zero, so the fixed position-bin readout never closed the strike bin and emitted no DOWN. The failed result remains in `runs/ea_mvp/hold_admission_v1.json`.

The versioned v2 encoder kept the head visible for the strike sample only, then marked it absent while the body and tail continued. The task-free probe passed at 300 ms, 1 s, and 3.5 s durations on lanes 0, 1, and 3. It produced DOWN at 501 ms and UP exactly when the tail reached zero, with no game, feedback, or learning; weights stayed fixed and repeats were exact. See `configs/ea_mvp_hold_admission_v2.json` and `runs/ea_mvp/hold_admission_v2.json`.

## Headless map result

The frozen map contained three sequential holds on lanes 0, 1, and 3, lasting 300 ms, 1 s, and 3.5 s. The lane-0-trained retained weights triggered the heads; the fixed tail rule released each lane exactly at its tail time. All six head/tail judgements were PERFECT, with no body combo break. The matched initial-weight arm emitted no actions and missed all heads and tails. There was one neural initialization, three readout rearms, unchanged weights, and exact replay.

The frozen game config/result are `configs/ea_mvp_holds_v1.json` and `runs/ea_mvp/holds_v1.json`.

## Limits

This is sequential isolated-hold playback with a fixed engineered duration rule. It does not demonstrate a biological hold detector, learned release timing, overlapping holds, or tap/hold combinations. Strict biology results remain unchanged.
