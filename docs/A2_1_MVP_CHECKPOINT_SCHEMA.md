# A2.1 — MVP-C1 coupled-state checkpoint schema

**2026-10-01 · PASS as a state and compatibility contract.** The machine-readable [contract](../configs/a2_1_mvp_checkpoint_contract.json) is `MVP-C1-checkpoint-v1`. This stage inventories the state needed for exact continuation and defines what a future writer/restore must accept. It does **not** implement or validate coupled replay, frozen evaluation, or a B3 run.

## Question and evidence boundary

**Question:** Is every value that could affect the next neural event, selected weight, first action, judgement or audit record identified before building a coupled checkpoint?

A1.3 supplies a candidate-specific γ4 rule with mutable selected weights, KC/PAM traces and a one-batch record. The existing synthetic `TinyLaneSession` pickles its full Python object for same-version trusted replay. Electrical V1 has a narrower explicit checkpoint covering its neural arrays, queue, APL state and autonomous boundary. Neither is an MVP-C1 coupled checkpoint; B2's renderer, delayed sensory current, feedback pulses, game and first-action bookkeeping are not yet implemented as one runner. The schema below names their required state so A2.2 can implement and test it without silently discarding an in-flight cause.

## Checkpoint cut and event order

Only save at **`COMMITTED_TICK_AFTER_FEEDBACK_AND_LEDGER_FLUSH`**: all events with timestamp `time_us` have passed the B2 order (expiry; current observation; boundary flip/request; due arrivals; neural integration and one simultaneous spike batch; local plastic update; motor action; judgement and feedback request), and every resulting audit record is durably appended. The next operation is the first phase of the next 1-ms tick. A partially processed spike batch, game action or ledger write is not checkpointable. Future arrivals, delayed cue drive, PAM pulses and teaching primes may remain queued at this cut; they must be saved with stable sequence numbers and origin IDs. `next_tick_us`, current phase and event-order version are explicit so a restore cannot replay the last phase twice.

The timeline uses signed 64-bit integer microseconds. Preserve the exact relative order of equal-time events and the simulator's queued-arrival payload weight, which was captured at spike emission. Restore heaps from their ordered records without recomputing a queued weight from a newer synapse. Each source stream has its own monotonic sequence or a shared global event sequence. A cancelled cue retains a generation/tombstone sufficient to reject stale delayed arrivals after restore.

## Immutable identity and compatibility envelope

The checkpoint references, and restore verifies, the following immutable inputs before touching live state:

| Identity | Why it is required |
| --- | --- |
| Schema/candidate `MVP-C1-checkpoint-v1`; code revision or source-tree digest; runtime backend, Python/numeric-library versions and float policy | Same state must use the same update and serialization semantics. Unknown versions are rejected; v1 has no implicit migration. |
| MaleCNS v1.0 traced scope, neuron/connection and partner-source SHA-256; B1 anatomy digest; ordered source IDs and source-ID→runtime-index map digest | Prevents loading 688 learned values onto a different graph or KC ordering. |
| B2 resolved design, γ4 contact audit, runtime mask and ordered CSR graph digests | Fixes the selected 13,957 contact rows, 688 selected pairs, fixed/plastic split, source topology, edge order, effect signs, delays and engineering gains. |
| Effect, APL, sensory, PAM, autonomous boundary and motor overlay/config digests; initial seed map | These engineering choices determine future dynamics but are not measured source synapses. All active control switches are named and hashed. |
| Renderer and full note-schedule digest, OD8 ruleset/window identity, first-action metric version | A resumed game must see the same future scheduled cues and score them under the same rules. The neural encoder itself still receives only current rendered position. |

The checkpoint stores no second mutable copy of the source graph, fixed contact weights or constants. On restore, derive them from the pinned inputs and verify the ordered graph/mask hashes. This avoids a saved state silently overriding source anatomy. A run manifest records all digests, candidate version, control condition, seed, training/frozen mode and checkpoint payload hash. A mismatch is an error, never a warning or automatic reset.

## Required dynamic state by owner

| Owner | Values that must continue exactly |
| --- | --- |
| **Clock and scheduler** | Committed `time_us`, `next_tick_us`, phase, event-order version, global/stream sequence counters, every future event as `(due_us, priority, sequence, source/origin ID, payload)`, cancellation generations and queue safety counters. Save the chemical-arrival queue with captured signed weight, edge slot and source IDs. |
| **Neural and graded APL** | Per-neuron membrane and synaptic-drive values, refractory end, spike count, current external drive, last integration time if distinct from global clock; APL graded state and last update time; delivered/scheduled/peak queue counters and any diagnostic state that contributes to future ledgers. PAM08 cells use the same per-neuron state. Spike/voltage history already flushed to a ledger needs a cursor and hash, not a duplicate unbounded buffer. |
| **γ4 plasticity** | For all 688 selected KC pairs: mutable positive plastic contribution keyed by **KC source ID**; KC trace value and last update time; compartment PAM trace value/last update time; last event and simultaneous batch timestamps; enabled/frozen flag; mask digest. The fixed contribution and `w0` come from B2 graph plus selected/total contact counts. Validate each saved plastic value against 0.5–1.5× its own `w0`. Save no signed RPE as dopamine state. |
| **Renderer and sensory latency** | Renderer clock/current visible note IDs and consumed/expired flags; observation sampling cursor; currently presented position and emitted-current ledger cursor; all queued 25-ms KC drive records with due time, source cue ID, sample ID, target KC, amplitude and insertion order; cancellation generations so a consumed cue cannot leak old drive. Future note timestamps belong to renderer state, never the encoder input. |
| **Boundary and PAM current** | For each of MBON05, MBON20 and DNp42: autonomous telegraph sign, next flip time, independent RNG state and boundary clock; the fixed mean/level is identity. Every active artificial PAM pulse has origin outcome, request amplitude, start/end time and delivered-current cursor; pending requests and spontaneous PAM RNG state, if enabled, are distinct. Only actual PAM spikes update the γ4 rule. |
| **Motor and game** | DNp42 spike-time deque within the 20-ms window, key-down flag, last DOWN/observation time, minimum/maximum hold and cooldown state; emitted key-action cursor. Game clock, four lane key states, per-lane unresolved-note cursor, resolved note IDs, expiry heap with tie order, raw action/judgement cursors. Key state in motor and game must agree at the cut. |
| **First-action and feedback** | For each active or resolved note, causal first-DOWN assignment, disposition/signed error or missing status, extra DOWN count, and A3 ledger cursor. Expected utility **before** the next outcome, pending late/no-DOWN prime with origin note/category/amplitude, pending early flush after cue consumption, active pulse schedule, feedback decision cursor and any deferred end-of-sequence discard. A resolved outcome must preserve separate judgement → utility → prior prediction/RPE → nonnegative request → actual PAM spike → selected update record IDs. |
| **Training and audit** | Current map/note and training-run indices, mode (training/control/frozen), exploration state/RNG if enabled, all other RNG algorithm states and stream names, resolved config identity, ledger byte offsets/hash-chain heads and last committed event/plasticity batch IDs. At the save cut, no unflushed `last_plasticity_record` or uncommitted game/feedback event is allowed. |

**Not causal after the cut:** historical plot arrays and summaries can be regenerated from immutable ledgers. If an in-memory accumulator is used to emit a future summary, save its exact value or derive it from a verified ledger prefix before resuming. Do not drop it merely because it is called a diagnostic.

## Format and restore checks

Version 1 specifies canonical UTF-8 JSON with sorted keys and SHA-256 checksums for a manifest and state payload. Every finite binary64 dynamic float is encoded with `float.hex()` and restored exactly; integers are checked as signed 64-bit values, with no NaN/Infinity and no lossy rounding. Large arrays or queues may move to separately hashed, little-endian typed payloads in an explicitly versioned revision; a writer may not silently change encoding. JSON/payload output is written to a temporary file, flushed and atomically renamed before the manifest points to it. Loading executable pickle is outside this primary checkpoint contract.

Restore is **validate-then-commit**. It checks schema and required/unknown fields, all referenced hashes, source/graph dimensions and IDs, queue order/positive chemical delays, finite drives/weights/traces, weight bounds, RNG state shapes, nonnegative PAM requests, synchronized clocks, key-state agreement, event/ledger offsets and payload digest. A failure leaves the live run unchanged. The writer must reject a noncommitted phase or an unflushed ledger. No v1 migration, best-effort repair, remapping by array position, reseeding, queue regeneration or reset of a missing component is allowed.

## A2.1 mini-step review and next gate

| Mini-step | Result | Readiness |
| --- | --- | --- |
| **A2.1a — inventory** | Inspected A1.3, synthetic and Electrical V1 checkpoint paths, boundary RNG, simulator queue, motor deque and game state. Identified the missing MVP-only cue cancellation, PAM request, first-action and ledger cursors. | **PASS; ready for A2.1b.** |
| **A2.1b — contract** | Fixed the committed tick cut, identity hashes, owner-by-owner state, exact float encoding, rejection and atomic-write rules in this report and the JSON contract. | **PASS; ready for A2.1c review.** |
| **A2.1c — completeness review** | Every B2 event-order phase has a saved continuation owner; pending chemical, sensory, boundary and feedback events have origin IDs and ordering; the γ4 fixed/plastic split and traces are explicit. Existing implementations are partial and cannot claim this checkpoint. | **PASS for A2.1 schema. No repair mini-step needed before implementing A2.2.** |

**Sole proposed next stage — A2.2 exact continuation (GPT-6.1 Sol / High).** Implement the coupled writer/restore against this contract, then compare uninterrupted and resumed raw spike/arrival, γ4 update, PAM, key-action, first-action and judgement ledgers bit for bit at several committed cuts, including queued arrivals, delayed cue drive, an early flush and a pending late prime. Fail on any mismatch or missing field; report **INCONCLUSIVE** if the full MVP runner or A3 feedback owner is not yet present. Do not run B3, training, tuning or A2.3 frozen evaluation under A2.1 authorization. Stop here.
