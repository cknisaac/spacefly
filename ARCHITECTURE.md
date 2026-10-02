# Project B architecture

> **Historical broader architecture plan.** For the implemented reduced MaleCNS experiment and current branch status, start with [the architecture guide](docs/architecture.md) and [current status](docs/project-status.md).


## Purpose and scope

The primary experiment asks whether a connectome-constrained, temporally explicit fly circuit with localized reinforcement plasticity can learn lane selection and precise timing in headless osu!mania 4K, and whether actual fly topology changes that learning relative to matched controls. Success or failure must be observable under identical interfaces and evaluation rules. The full biological system remains proposed; M0 game mechanics, the M1 spiking reference, local plasticity and reward primitives, a 128-neuron synthetic lane-one closed loop, and a validated **MaleCNS v1.0** importer are implemented. A separate non-learning scale study now simulates sampled MaleCNS topology with declared artificial electrical effects. No fly task behavior or training has run.

The first supported game profile is native stable mania, OD8, four lanes, ordinary notes. M0 implements this headless game module and a separate stable-convert window profile. Ruleset, OD, and event times remain parameterized. Long notes are represented in the domain model but rejected until their judgement mechanics are implemented and verified. M1 implements deterministic LIF, signed delayed synapses and sparse event propagation. Later work adds selected-edge eligibility, independent reward/RPE, and the explicitly artificial [lane-one closed loop](docs/CLOSED_LOOP.md). It demonstrates a simple synthetic task, not fly circuitry or the full M2 learning gate.

## System boundary and flow

```text
Beatmap/generated task -> headless osu environment -> sensory observation
                                                    -> artificial or visual encoder
                                                    -> timestamped input events
                            immutable connectome + explicit interface overlays
                                                    -> sparse neural runtime
                                                    -> fixed motor readout
                                                    -> key-down/key-up events
                                                    -> osu judgement
                                                    -> utility and RPE
                                                    -> artificial reinforcement route
                                                    -> DAN/modulatory activity
                                                    -> eligibility-gated edge updates

One integer-microsecond scheduler orders every event. Experiment orchestration
configures runs; recording and analysis consume events without controlling them.
```

The game emits judgements, never synaptic updates. The neural runtime emits population activity, never a game score. Adapters translate between these domains and log the translation. An artificial injection or route is a named overlay, not an internal connectome edge.

## Data contracts and time

| Contract | Proposed boundary |
| --- | --- |
| `time_us` | Signed 64-bit integer microseconds for game objects, key transitions, spikes, synaptic arrivals, judgements, and modulatory events. Conversions from `.osu` millisecond timestamps are exact and centralized. |
| Neural integration | Configurable step, initially 1000 µs, with 500 and 250 µs convergence profiles. State sampling and off-grid event effects must have explicit semantics; quantization error is measured. |
| Event order | M0 orders expiry before input at the same µs. The neural runtime orders synaptic arrivals by `(arrival_us, post, pre, edge_slot, sequence)`, then threshold checks by neuron index at ticks; strictly positive delays prevent zero-time feedback. Plasticity consumes the complete spike batch after the tick, so same-tick pre/post spikes do not pair. The synthetic runner samples sensory drive at each interval start, advances neurons to the next tick, processes game expiry before motor key events, then processes judgement/RPE and applies synthetic dopamine at that tick. An off-grid expiry's modulation is delivered at the next tick; full fly-system scheduler policy remains open. |
| `NeuronRecord` | Stable dataset-qualified source ID, runtime index, optional cell type, transmitter annotation and confidence, region, source/version, and raw metadata. Unknown is an explicit value. |
| `EdgeRecord` | Stable edge ID, pre/post runtime indices and source IDs, synapse count, source/confidence, transmitter/effect evidence, delay in µs, and overlay flag. A source edge is never silently merged with an engineered attachment. |
| Runtime state | Per-neuron membrane/refractory/synaptic state; per-edge effective weight and delay; eligibility only for masked plastic edges; independent scheduler and reward-baseline state. |
| Game events | Lane, object ID, note/hold kind, time(s), key state transition, and resulting `ManiaJudgement`. `NULL_PRESS` is an action event, not a judgement. |
| Reinforcement events | Currently: original `JudgementRecord`, `JudgementUtility`, `RewardPrediction` with expectation before/after and RPE, and timestamped synthetic `ModulatorySignal`. Future: optional explicitly labelled shaping/action cost, artificial route, target DAN population, feedback latency and arrival time. |

Store units in names (`delay_us`, `tau_ms`, `weight_nS` if conductance is chosen). Do not infer a physical unit for synapse-count-derived weight unless calibrated. Checkpoint and replay formats must include the scheduler queue, random generator states, neuron/edge/plasticity states, environment state, config, and source checksums when exact resumption is promised.

## Sparse scale path

1. The selected MaleCNS v1.0 importer validates pinned full and traced-only source objects, reconciles every traced pair with the full segment graph, and assigns a contiguous runtime index in signed body-ID order to `status == Traced` annotation rows. It outputs immutable columnar neuron/edge tables plus manifest, validation report, and checksums. Each directed `connections.parquet` row preserves its zero-based traced-source row and synapse count. The `region` field contains only a source `somaNeuromere` with its basis recorded; missing locations stay unknown. The staged scale study extracts nested induced samples and records both directions of boundary cuts without changing the source graph. Its 20,000-neuron MB-enriched subset is not a validated task subcircuit. See [the active dataset report](docs/MALECNS_V1_DATASET_REPORT.md) and [the scale study](docs/MALECNS_V1_SCALE_PROFILE.md).
2. Compile directed edges into presynaptic outgoing compressed sparse row adjacency: `offsets[N+1]` and aligned arrays for target index, edge ID, effective weight reference, delay, and effect class. Optional incoming indexes support analysis or plasticity without replacing the outgoing representation. No dense N×N weights or state.
3. On a spike, visit only outgoing edges and schedule timestamped arrival events. Keep eligibility storage restricted to plastic edge IDs. Neuron state is stored in typed arrays, separate from topology, so kernels can change without changing model contracts.
4. Initially use a deterministic CPU reference backend with Python orchestration and NumPy/SciPy sparse data where suitable. The scheduler and propagation API permit an event-driven or hybrid backend later. An event-driven design does not guarantee better performance at every activity level; M14 chooses it or an alternative based on profiling and parity tests.
5. Bound recording to summaries and selected populations. Stream raw judgement/action/reward events, and sample diagnostic spikes selectively. Benchmarks report memory per neuron/edge, queue peak, active-edge visits, simulated seconds per wall second, and parity against the reference backend.

This layout scales storage and propagation with neurons, edges, and triggered events rather than all possible neuron pairs. Delayed arrivals may still dominate memory or runtime during high activity; queue limits and profiling are required. Synapse count is an anatomical observation, not a measured conductance.

## Module boundaries

The master specification's proposed `src/` names are retained as module boundaries. M0 implements `src/project_b/osu/`. M1 adds `neurons/`, `synapses/`, `simulation/` and a shared integer-time helper in `utils/`. Later requests add `plasticity/` and `neuromodulation/` primitives, the artificial `sensory/` time-to-contact encoder, the fixed `motor/` readout, and `experiments/tiny_brain.py` as the only domain-coupling orchestration. **After the 2026-10-01 pivot, this exact-timestamp time-to-contact encoder is a historical synthetic fixture, not the MVP sensory contract; the MVP requires a fixed current-position population encoder.** `connectome/` owns MaleCNS source validation, a versioned sparse columnar schema, and a compact NumPy CSR adapter. `scripts/profile_malecns_scale.py` alone composes source subsets with explicit non-learning electrical overlays and the CPU reference simulator. The importer never imports simulation, plasticity, or training code. An earlier BANC importer is retained only as superseded provenance. DAN population dynamics, full four-lane interfaces and primary training remain proposed.

| Future module | Owns | Must not own |
| --- | --- | --- |
| `connectome/` | Pinned MaleCNS v1.0 full/traced source validation, source metadata, typed neuron/connection tables; later subgraph extraction and overlay manifests | Runtime learning, game rules |
| `neurons/` | Neuron model classes and state transitions, parameter sets by cell class | Beatmap state, rewards |
| `synapses/` | Event propagation, edge effects, delays, weight representation, unknown-effect policy | Reward calculation |
| `plasticity/` | Plastic-edge masks, local traces, bounds, homeostasis as optional separate mechanism | Direct game judgement access |
| `neuromodulation/` | Centered hit utility, expected utility/RPE, synthetic modulatory event; later artificial reinforcement and DAN route | Direct arbitrary edge mutation, official game scoring |
| `sensory/` | Artificial lane-one time-to-contact population; later four-lane/visual encoding and labelled injection overlay | Target key or ideal press-time leakage |
| `motor/` | Fixed causal spike-window readout, threshold/hysteresis and lane-one key state; later selected descending populations/four channels | Trainable primary decoder, judgement rules |
| `osu/` | `.osu` parsing, ruleset profiles, key mechanics, judgement, score/accuracy as separate outputs | Biological reward or synaptic plasticity |
| `simulation/` | Canonical scheduler, deterministic tie order, neural step/event coupling, backend protocol, checkpoints/replay | Experiment hypothesis selection |
| `training/` | Curriculum scheduling, frozen evaluation, seed/split policy | Hidden changes to model rules |
| `experiments/` | Synthetic 100–500-neuron graph fixture, lane-one closed-loop scheduler, configured controls, provenance and run manifests | Core neuron/game mechanics |
| `analysis/` | Metrics, error histograms, learning curves, controls and uncertainty | Mutation of a running model |
| `utils/` | Narrow generic parsing, hashing, units, serialization helpers | Biological assumptions |

Configuration is resolved before construction; dependency direction is from orchestration to domain interfaces, not from `osu/` into neural internals. Versioned ruleset and connectome adapters are replaceable without modifying plasticity code. A backend implements the same step/event and checkpoint contracts as the CPU reference.

## Experimental boundary

The **synthetic validation track** uses an engineered 100–1000-neuron network to establish correct propagation, local learning, and a first single-lane learning gate. It does not establish fly biological plausibility. The **primary track** imports one identified fly subcircuit, keeps its measured topology distinct from artificial entry/exit/reward overlays, and restricts plasticity to justified edges. The **comparison track** changes topology, reward timing, DAN route, plasticity mask, or motor mapping through explicit manifests while holding the rest of the protocol constant.

Generated training, validation, and held-out test patterns are disjoint. Final evaluation freezes plasticity. All major results include predeclared seeds, baseline and ablation comparisons, categorical judgements, signed and absolute timing error, neural activity, plasticity, and compute metrics. No result is attributed to fly topology unless appropriate degree-preserving shuffle and matched random controls support that inference.

## Decisions held open

- M0's stable-native game contract is specified in [docs/OSU_ENVIRONMENT.md](docs/OSU_ENVIRONMENT.md) against the [official mania judgement reference](https://osu.ppy.sh/wiki/en/Gameplay/Judgement/osu%21mania). The reference states late MEH hits are impossible and that an unhit note misses after the OK window; a symmetric ±127 ms rule alone is insufficient. Exact half-millisecond ties and rare same-lane overlap cases remain documented client-parity assumptions.
- M1's exact subthreshold equation, tick-based threshold/reset, refractory clamp, signed synthetic effects, sparse CSR storage and deterministic arrival ordering are specified in [docs/MODEL.md](docs/MODEL.md). These are engineering model choices and tiny-network validation, not biological evidence.
- The isolated plasticity primitive uses exponentially decaying pre-spike and eligibility traces on explicitly selected edge slots. Dopamine is an external scalar event; no DAN population or compartmental route exists yet. [docs/MODEL.md](docs/MODEL.md) specifies its update and event ordering. The trace time constants, pairing rule and bound values are engineering fixtures.
- The independent [reward contract](docs/REWARD.md) maps all six osu judgements to centered utility, maintains one exponential expected-utility baseline, computes RPE, and emits a timestamped synthetic dopamine-like scalar. The module itself does not touch simulator state; the synthetic runner explicitly delivers its output. Prediction context, biological feedback latency, DAN routing and calibration remain open.
- The [synthetic lane-one runner](docs/CLOSED_LOOP.md) wires that scalar to the simulator's masked plasticity after a real game judgement. Its `D` before judgement is the fixed motor key decision; dopamine-like modulation follows RPE. It is a reproducible artificial circuit with explicit exploration, a plasticity-off control, frozen evaluation, and trusted same-version checkpoint replay. Seed-dependent timing and generalization remain open.
- The selected import pins [MaleCNS v1.0](https://male-cns.janelia.org/download/) for one adult male brain and ventral nerve cord. Its full segment graph and traced-neuron graph remain distinct from the synthetic learner and from the superseded BANC files. A non-learning electrical stress test samples this topology, but biological circuit route, task boundary policy, region coverage, and scientifically grounded effects remain open. Do not splice in edges from other specimens.
- Determine selected circuit, boundary treatment, sign/effect evidence, synapse-count scaling, neuron-class dynamics, delays, plasticity rule and DAN targeting before claiming biological meaning. `ASSUMPTIONS.md` is the decision register.
- The later visual pathway and long-note mechanics require new validation gates. They are not implied by success with artificial lane channels and ordinary notes.

## Circuit V1 design reference

[CIRCUIT_V1.md](CIRCUIT_V1.md) defines the proposed 140-body MaleCNS visual KC/MBON/DAN/descending selection, complete source IDs, measured paths, cut boundaries and mechanism evidence classes. The [Circuit V1 data product](docs/CIRCUIT_V1_SUBSET.md) now materializes exactly those source neurons, every induced source edge, a candidate-only plastic mask and boundary manifests with hashes. It is not an implemented electrical runtime graph or a passed M3/M4 physiology gate. Unresolved functional effects remain explicit.

The existing module boundaries remain applicable: immutable sparse topology, separate effects/plasticity/modulatory state, and named sensory/reinforcement/motor interfaces. This candidate additionally requires an explicitly justified local graded APL representation and compartment-specific dopamine/plasticity semantics before electrical runtime implementation. Uniform LIF dynamics, positive count-derived weights and a global scalar dopamine event do not satisfy those biological requirements. Task execution has not begun.

## Circuit V1 policy boundary

The [Circuit V1 effect policy](docs/CIRCUIT_V1_EFFECT_POLICY.md) now resolves all selected source pairs and neurons into explicit effect/model/delay/boundary records. `ConnectionEffectPolicy` applies only named, target-specific class rules; unmatched edges remain literal `UNKNOWN` with no weight. `NeuronParameterPolicy` distinguishes external visual sources, spiking KC/MBON/DN proxies, local graded non-spiking APL and separate dopaminergic state. `DelayPolicy` preserves unknown biological timing. `BoundaryInputPolicy` records cut drive and pending artificial interfaces without filling it in. Every future numeric model value must carry literature, inference or engineering provenance. `require_runtime_ready()` refuses to convert this unresolved policy to the current spiking runtime. The old scale profiler is a historical failed stress protocol, not the Circuit V1 electrical model.
