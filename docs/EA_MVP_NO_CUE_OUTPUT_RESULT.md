# EA-MVP EA-3.1 — no-cue and MBON-output attribution

**2026-10-03 · PASS for the frozen non-learning reduced-circuit gate.** No game score, teacher, DAN stimulation, synaptic update or training was run. Strict Branch B, Level 4D and larval results remain unchanged.

## Frozen question and intervention

The [EA-3.1 protocol](../configs/ea_mvp_no_cue_output_protocol.json) was saved before the probe. It fixes the same MaleCNS-derived 32-KC→MBON05 reduced circuit and source-config SHA-256 `528ac42f04bd7f3e254ee187b32f2279fa337ce47a370eb364411b59ae87f870`, the inherited artificial encoder/electrical/readout settings, and only one weight intervention: six KCs preferred within ±0.10 of position 0.5 receive 0.2× their initial aggregate weights. These non-anatomical values are **ENGINEERING ASSUMPTIONS** approved as a category by the user; they were not selected by game score. Each arm was repeated twice from a fresh state.

| Arm | Result |
| --- | --- |
| True no cue: zero external drive on the same sparse graph/LIF parameters | **0 spikes**, zero MBON peak voltage, no action source. |
| Initial weights, full present-position traversal | No DOWN; MBON 0.5-bin maximum **0.0120813377851571 mV-equivalent**. |
| Local-0.5 fixed-weight intervention, same traversal | MBON 0.5-bin maximum **0.00335687733958761 mV-equivalent**; first DOWN at **263,000 µs**, position **0.474**. |
| Same local intervention, but MBON voltage set to zero only at a paired readout | No DOWN at the output-off readout. The neural arm itself was preserved and logged. |

Every frozen primary check passed, including exact repeated records. The independent audit reconstructed first DOWN from saved key transitions and verified all spike/arrival source IDs against the frozen cohort. The [raw per-arm traces](../runs/ea_mvp/no_cue_output.json) include source-tagged spikes and arrivals, sampled MBON voltage, readout bins, actions, queued-arrival counts and repeat receipts. Raw result SHA-256: `84a742a6f3da618f41d79d8a278011e0f7745193ceb2b647b107c9c2d9f95288`.

The first run saved the frozen primary endpoints but omitted full raw trace serialization; it was repeated with **the same protocol and simulator logic**, adding source-tagged traces and action records. Both runs gave identical primary checks and numeric endpoints. The final raw artifact and independent audit above are the stage evidence. No parameter or intervention was changed.

## Decision and limits

**EA-3.1 PASS** for the declared reduced-circuit pretraining attribution gate. Together with EA-3's task-free 3/3 weight-intervention panel, this shows an engineered, fixed readout can convert a local change in selected MaleCNS-derived KC→MBON weights into a first key press, with no-cue and MBON-output-off silence. It does **not** show a fly learns the change, that game feedback has a valid biological meaning, that the full MBON→DN route works, or that the model plays osu! well. The output-off arm is an artificial readout lesion, not a measured biological lesion.

**Exactly one next proposed stage: EA-4 — teacher contract and local-rule sanity, without task training.** Freeze a label-only judgement→DAN table and event timing, then verify that already available labels trigger only declared DAN events and that a separate one-pulse local-rule fixture changes only eligible selected synapses; DAN-off and plasticity-off must change none. Keep the game-score audit outside the teacher. Stop after this gate. The user's prohibition on training remains in force; neither development learning nor confirmation may run under this result.
