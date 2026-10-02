# Project B — progress by work session

**Updated 2026-09-30.** Sessions below group related work for reporting; they are not milestone numbers. Earlier reports retain their own historical session names.

**Current position:** the game and neural foundations work, and MaleCNS anatomy is validated. Synthetic learning has not passed its reliability gate. Circuit V1 has source-backed anatomy and an explicit uncertainty policy, but no validated electrical baseline or fly-task training result.

## Session 1 — Specification, architecture and scientific rules

**Completed.** Read the attached master specification and created the five standing documents: AGENTS, ARCHITECTURE, MILESTONES, ASSUMPTIONS and CURRENT. Separated game judgement, neural simulation, sensory/motor interfaces, plasticity, neuromodulation, connectome import and experiment analysis. Chose stable source IDs, sparse outgoing adjacency and a shared integer-microsecond timeline so larger graphs can use the same contracts.

**Still open.** Sparse architecture does not guarantee practical whole-connectome runtime. Biological effects, experiment thresholds, boundary treatment and model approximations need explicit evidence and acceptance tests at each stage. A reconstructed connection cannot be treated as a known excitatory synapse.

## Session 2 — Game engine and spiking simulator

**Completed: M0 and M1.** The headless osu!mania environment supports generated four-key tap notes, key transitions, judgement windows, expiry, overlapping-note priority, simultaneous lanes and deterministic replay. The neural reference supports LIF temporal state, signed synaptic effects, nonzero delays, refractory periods and sparse event propagation. Their respective completion suites reached 29 and 48 cumulative tests.

**Still open.** Native `.osu` parsing and long-note scoring are not implemented. Some unusual client timing cases need direct parity fixtures. Neural threshold detection is discretized, and the LIF defaults are synthetic reference values, not shared fly electrophysiology. Large event queues remain a performance constraint.

Sources: [game environment](OSU_ENVIRONMENT.md), [neural model](MODEL.md).

## Session 3 — Eligibility, dopamine gate and reward prediction

**Completed.** Selected synapses acquire decaying eligibility after pre/post activity. A separate modulation event applies the requested three-factor update. Automated tests verify recent activity plus dopamine changes weight, either factor alone does not, and a long delay greatly reduces the update. The reward chain separately converts real game judgements into utility, expected utility, prediction error and a synthetic dopamine-like signal.

**Still open.** These tests prove the implemented rule's behavior, not that it learns a useful policy or reproduces mushroom-body plasticity. Eligibility timing, mandatory postsynaptic activity, weight bounds, global reward prediction and scalar modulation are engineering assumptions. Actual DAN compartment targeting and release dynamics are not implemented.

Sources: [reward](REWARD.md), [model](MODEL.md).

## Session 4 — Synthetic closed loop and reliability tests

**Completed.** Built a 128-neuron default one-lane circuit with causal cue encoding, a fixed motor readout, exploration, real game feedback and selected-edge learning. Full-state same-version checkpoints replay deterministically. Some runs retain useful responses; the first successful demo produced eight early OK hits.

The 16-seed control checkpoint failed its consistency gate. The later approved study completed **192 trials in 30.87 minutes**, within its six-hour cap. On 32 held-out seeds, frozen GOOD+ averaged **46.1% plasticity on, 0% off, 11.5% shuffled reward**. On won strictly against off in 16/32 seeds and shuffle in 15/32, below the required 24/32. Mean absolute hit error was **60.6 ms**, above the 40 ms limit.

**Still open.** M2 is incomplete: average benefit did not become reliable, precise learning across seeds. Dense maps, multiple lanes and 300–400 BPM play were not tested. The seeds vary maps/cue gains and exploration; the synthetic topology and initial weights are shared, so seeds are not different fly brains.

Sources: [closed loop](CLOSED_LOOP.md), [control checkpoint](CHECKPOINT_CONTROLS.md), [overnight results](OVERNIGHT_RESULT.md).

## Session 5 — Mechanistic learning diagnosis

**Completed.** Matched-checkpoint probes compared no update, one predefined small displacement and the actual full update. Full updates helped one selected seed and harmed another; small probes changed no judgement tier, leaving local direction versus update size unresolved. Fixed-weight repeats found a stale reward baseline could dominate the proposed update; a fresh pooled estimate removed most measured drift, without establishing better behavior.

Eight networks, seeds **2000–2007**, retained weights through 384 outcomes. Mean frozen plasticity-on GOOD+ was **62.50% → 64.06% → 9.77%** at 24/96/384 outcomes. More exposure alone did not fix this configuration. A later frozen exploration/map diagnostic stopped after five seeds; exploration partly helped weak late states, while the tested map change had a smaller effect.

**Still open.** Competing explanations include damaging late weights, excessive/clipped updates, weak credit assignment, reward-baseline lag and motor timing/cooldown. No single root cause has been established. A weight-transplant test is prepared but **never run**. Longitudinal seeds 2008–2031 were untested; exploration/map seeds 2005–2007 were untested in that separate experiment.

Diagnosis remains paused. On resuming, first read **[FUTURE_DIAGNOSTICS.md](FUTURE_DIAGNOSTICS.md)**; it records the smallest discriminating tests and the incomplete protocols. No arbitrary learning-rate search is proposed.

## Session 6 — MaleCNS ingestion and scale profiling

**Completed.** Corrected the selected source from BANC to **MaleCNS v1.0**, preserved source provenance and independently validated the import. The traced graph contains **165,122 neurons, 25,563,197 directed pairs and 124,025,046 contacts**. Source IDs, counts, annotations and original row references survive normalization.

Non-learning profiles used source-derived samples from 100 to 50,000 neurons. The declared all-positive, uniform-LIF overlay failed: the smallest lacked propagated activity, 1,000 neurons became overactive, and larger samples hit event/queue limits.

**Still open.** This is a failed electrical overlay, not evidence that the fly brain itself is unstable. It must not be tuned into a passing regime. Source annotation coverage is incomplete, and a truncated graph needs a defensible account of excluded inputs. Backend efficiency will need work once an explicit model exists.

Sources: [dataset report](MALECNS_V1_DATASET_REPORT.md), [historical scale profile](MALECNS_V1_SCALE_PROFILE.md).

## Session 7 — Circuit V1 extraction and evidence policies

**Completed.** Designed and extracted a reproducible **140-neuron** candidate containing visual inputs, KCs, APL, MBONs, DANs and descending cells. It retains all **12,153 internal pairs / 57,771 contacts**, plus boundary statistics. The **214 plastic candidate pairs** are anatomical candidates, not established active plastic synapses.

Implemented separate connection-effect, neuron-parameter, delay and boundary policies. Unsupported effects remain UNKNOWN and runtime conversion is blocked. The audit found no relevant metadata propagation loss. **45,115 contacts (78.09%)**, or **10,960 pairs (90.18%)**, remain UNKNOWN in this unchanged policy; recurrent KC contacts dominate the total. The latest completed suite before the critical-route work had **96 passing tests**.

**Still open.** The currently classified effects do not connect sensory input to descending output. Numerical dynamics, per-contact plasticity localization, local APL treatment, missing boundary drive and the artificial task interfaces are unresolved. The 78% figure measures unknown functional effects, not missing anatomical connections or simply missing transmitter names.

Sources: [subset](CIRCUIT_V1_SUBSET.md), [effect policy](CIRCUIT_V1_EFFECT_POLICY.md), [sign audit](CIRCUIT_V1_SIGN_AUDIT.md).

## Current follow-up — Critical-route evidence gate

The [evidence report](CIRCUIT_V1_CRITICAL_ROUTE_EVIDENCE.md) reconciles KC consensus semantics and corrects the source receptor-field interpretation. It audits a smaller **115-body proposal** using the original input trio and complete KC class, MBON32_R **519131**, PPL103_R **14182**, APL_R **10540**, DNa03_L **519624** and DNa02_L **523769**.

This route removes the mandatory unresolved MBON01 glutamate relay. However, exact KC→MBON32 plasticity is still inferred, downstream target effects remain unproven, and boundary losses are severe. The proposal has not replaced the implemented 140-body artifacts. **Electrical readiness remains NO.**

## Work still needed to complete the project

1. **Finish the model contract:** localize the proposed plastic compartment; declare exact-target effect inferences, graded APL treatment, class dynamics, delays and boundary inputs with provenance. Keep unsupported effects UNKNOWN. No score-driven adjustment of the failed overlay.
2. **Establish a non-learning fly baseline:** implement the approved model, test activity and queue bounds, verify causal cue-to-action behavior and validate fixed sensory/motor interfaces. Report failures before adding learning.
3. **Resolve synthetic learning causally:** resume the prepared diagnostics and demonstrate stable frozen improvement above paired off/shuffled controls under a fresh declared protocol. Fly anatomy alone does not fix the failed synthetic rule.
4. **Localize and test fly plasticity/reinforcement:** implement the approved KC/MBON/DAN mechanism; prove targeting and timing; then test one-lane learning and retained performance above controls.
5. **Expand the task only after that gate:** two/four lanes, precision and density progression, chords and native tap-note maps. Long-note behavior and richer visual input need separate validated work.
6. **Complete controls and scaling:** compare actual versus matched shuffled/random topology, run the planned mechanism ablations, add durable versioned checkpoints, and optimize sparse execution with parity checks. Benchmark the intended 300–400 BPM / roughly 2,000-note-per-minute workload directly.

Most immediate work concerns causal diagnosis and missing model evidence. Fine tuning becomes meaningful only after those contracts and tests are established. See [MILESTONES.md](../MILESTONES.md) for the full acceptance sequence.
