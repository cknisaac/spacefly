# L0.9a.1 — dual-time and action-trace result

**Status: PASS for normalized logical-event and key-transition parity on the
frozen tap corpus.** Raw Lazer update timestamps remain frame-dependent and are
retained as a separate observation.

## Question and scope

Can the headless game preserve an exact logical event time while the pinned
osu!lazer replay host records the time it observed that event, and can the
runtime probe capture every replayed DOWN/UP transition?

The probe used pinned osu! commit
`da27300fcbfa246f87c3ba1a14cbd00b68c7e9a9`, OD8, no mods, rate 1.0, the frozen
eight-scenario corpus, and the 24 judgement-window vectors. It ran the C#
ReplayPlayer tests twice from the same initial conditions.

## Contract change

- `JudgementRecord.logical_event_time_us` is now the canonical deterministic
  time. `event_time_us` remains as a compatibility property that returns this
  logical time.
- `JudgementRecord.observed_game_time_us` optionally stores the timestamp
  observed by the runtime. Python-generated records leave it `None`.
- Checkpoints write the new names and restore both the new schema and older
  records that used `event_time_us`.
- Feedback and reward scheduling read logical time only. The policy-facing
  `GameFeedbackEvent` does not expose observed frame time.
- The frozen corpus is now schema version 2 and identifies logical time
  explicitly.

The pinned C# probe records the actual key-binding DOWN/UP callbacks and reads
their timestamps from the active replay frame. For judgements, it preserves
`JudgementResult.TimeAbsolute` as the raw observed time. The normalizer assigns
an automatic MISS its first invalid logical microsecond (`note_time_us +
127501` at OD8), and assigns a force-MISS the later successful hit's logical
time. It keeps the raw observed timestamp alongside that logical time.

## Results

- Both pinned C# runs passed all three discovered NUnit tests: the test host
  constructor, eight frozen replay scenarios, and 24 playable timing-boundary
  cases. The two runs had identical normalized judgements and action order.
- All replayed DOWN/UP transition records, lanes, and replay-frame times
  matched the frozen inputs. All eight normalized scenario traces matched the
  headless corpus with zero logical-time, event-order, judgement, direct-hit
  offset, or action-disposition differences.
- The linked C# timing methods still match all 24 classifier vectors. The
  playable test confirms that late presses at and beyond +127.501 ms do not
  become direct judgements because the note has already expired.
- Automatic-MISS observations vary across runs, as expected from update
  scheduling. In the latest pair, the no-press MISS was observed at +138.313
  and +143.991 ms relative to note time; the too-early/null case was observed
  at +143.429 and +143.674 ms. The normalized logical time was +127.501 ms in
  each case. Raw values remain in the two probe JSONL files.
- Focused Python regression checks passed **58 tests** across the game
  environment, parity corpus, feedback, CLI, neuromodulation, and six available
  first-action-audit tests. The seventh first-action audit test could not run
  because its historical ignored input
  `docs/figures/a2_mvp_coupled/uninterrupted_ledger.json` is absent.

Raw and normalized run artifacts are ignored under `work/`:

- `work/lazer_runtime_reference_probe.jsonl` — SHA-256
  `C201D83F2786F76B3A01186270713A166425A1BE3DB1652B72D59CFF7C876050`
- `work/lazer_runtime_reference_probe_repeat.jsonl` — SHA-256
  `4B225CC2B0CC550AF39D901AC396E17D826190E130DB64B725E00EE53C7A6C49`
- `work/lazer_runtime_normalized_trace.json` — SHA-256
  `CB5A6383BD9D9E0E5208B30E9FF88C29D8118FE411BD33D794B4F6F7849672D7`

Re-run with `python scripts/run_lazer_runtime_probe.py`. It checks the pinned
revision, captures two raw runs, compares normalized traces to the frozen
corpus, and leaves the raw observations available for inspection.

## Limits and next stage

This passes the **logical event and action-transition contract**. It does not
make frame-dependent `TimeAbsolute` values identical, validate cumulative
score/accuracy/combo totals, implement an in-process game adapter, or support
holds, mods, or arbitrary `.osu` maps. L0.6 remains **INCONCLUSIVE / NO-GO** for
a biological teacher and fly training; this stage changed no learning rule,
weights, or training behavior.

Sole next proposed stage: **L0.9b — one-lane headless vertical slice and
adapter conformance.** Freeze the shared observation/action/result interface,
replay one causal policy trace through the game seam, verify first-action
audit and deterministic replay, and reject future-time, score, judgement, or
target-key fields from policy input. Stop after that stage before score-total
parity or any learning work.
