# Spiking reference and local plasticity primitive

**2026-10-01 Candidate 1 B2.1 design:** The [resolved addendum](B2_1_CANDIDATE1_EXECUTABLE_DYNAMICS.md) explicitly sets a 5-ms signed exponential chemical-current state after 2-ms arrivals, three independent inverse-CDF exponential boundary-flip streams (100-ms mean), and a 20-ms graded APL state with exact LIF convolution. These are versioned engineering assumptions for the proposed 718-cell runner; that runner and its coupled checkpoint/replay remain unimplemented. Existing M1 and historical Electrical V1 models below retain their own separate contracts.

**2026-09-30 MaleCNS update:** [Electrical Model V1](ELECTRICAL_MODEL_V1.md) is a separate frozen, neutral-only implementation of the approved **115-body** circuit. It uses physical pA/pF/nS units, class-specific spiking parameters, local graded APL, a separate inactive DAN state, named effect hypotheses, and an autonomous DN boundary. Its 9,505 UNKNOWN source pairs remain electrically inactive; plasticity is off. The numerical values and evidence labels are documented there and in [the frozen config](../configs/electrical_model_v1.json). Its [24-run neutral operating-state gate](ELECTRICAL_V1_NEUTRAL_GATE_RESULT.md) **passed as an engineering activity/safety test**. The sensory–KC–MBON32 route was silent, so the gate does not establish motor-route transmission or learning. The historical synthetic/reference model below and its mV-equivalent units are unchanged.

**Circuit V1 note:** the LIF defaults and synthetic signed effects below are reference-fixture values. The selected MaleCNS [effect policy](CIRCUIT_V1_EFFECT_POLICY.md) does not transfer them to every body or edge. It has class-specific model families, 10,960 explicitly UNKNOWN effects, and no assigned numeric weights, delays or intrinsic constants; the runtime-readiness check fails closed. The Session 7 all-positive overlay remains a failed historical stress scenario.

**Scope:** A deterministic, current-based leaky integrate-and-fire (LIF) simulator with an optional local eligibility primitive. This is an engineering reference model, not a claim that every Drosophila neuron spikes or shares these parameters. The simulator module itself is independent of the M0 osu environment. An external [synthetic runner](CLOSED_LOOP.md) now couples the modules for a lane-one task; the neuron model has no DAN biology or connectome ingestion.

## Equations and units

For neuron $i$, between synaptic arrivals:

\[
\tau_{m,i}\frac{dV_i}{dt}=-(V_i-V_{rest,i})+I_{ext,i}+I_{syn,i},
\qquad
\tau_{syn,i}\frac{dI_{syn,i}}{dt}=-I_{syn,i}.
\]

`V`, `V_rest`, `V_reset`, `V_threshold`, external drive and synaptic drive are in **mV-equivalent model units**. This does not claim a measured physical conductance or current. All stored times and delays are integer **microseconds**; time constants are named `tau_m_us` and `tau_syn_us`.

An edge of signed weight `weight_mv` produces $I_{syn,post}\leftarrow I_{syn,post}+weight$ at the exact scheduled arrival time $t_{spike}+delay_{us}$. Positive is excitatory in this model and negative inhibitory. These synthetic signs are configured, not inferred from fly transmitter labels. Delays must be strictly positive.

Subthreshold state is integrated analytically over each interval of length $h$ between events. Write $a=e^{-h/\tau_m}$ and $b=e^{-h/\tau_{syn}}$. Then

\[
I_{syn}(t+h)=I_{syn}(t)b,
\]
\[
V(t+h)=V_{rest}+(V(t)-V_{rest})a+I_{ext}(1-a)
+I_{syn}(t)\frac{\tau_{syn}}{\tau_{syn}-\tau_m}(b-a).
\]

When the two time constants are equal, the last term is $I_{syn}(t)(h/\tau_m)a$. The implementation uses this limit to avoid division by zero. With no synaptic input and $V(0)=V_{rest}$, constant drive gives $V(t)=V_{rest}+I_{ext}(1-e^{-t/\tau_m})$ until the first spike; the unit test compares each pre-spike sample to this expression.

## Spike and event semantics

1. The simulator starts at 0 µs. Configurable threshold-check ticks occur at positive multiples of `dt_us`, initially 1000 µs; 500 and 250 µs are also tested.
2. At each tick, queued arrivals up to that tick are popped in deterministic `(arrival_us, post, pre, canonical_edge_slot, sequence)` order. Each target neuron integrates only across its own arrival times, preserving off-grid arrival timestamps. A synaptic arrival exactly at a tick changes drive at that instant and affects voltage in the next interval; it does not jump membrane voltage instantaneously. The effective edge weight is captured when the presynaptic spike schedules the arrival, so later dopamine cannot retroactively alter that pending event.
3. Once all neurons reach the tick, a neuron with $V\geq V_{threshold}$ and no active refractory clamp emits **one** spike timestamped at that tick. Its pre-reset voltage is recorded; voltage is then set to `V_reset`. Its `refractory_until_us` is spike time plus `refractory_us`.
4. During refractory time, voltage remains at `V_reset`, while synaptic drive continues to decay and may receive new arrivals. A refractory end inside a tick interval splits integration: voltage resumes evolving immediately after that exact microsecond. The next spike can occur only at a threshold-check tick.
5. Spikes from one tick schedule strictly future arrivals. Neurons are checked in ascending runtime index; CSR edges have canonical ordering. There is no random source. Repeating the same inputs, including chunked `run_until` calls, produces identical CPU timestamps and traces.
6. If plasticity is attached, the simulator sends the complete tick's spike batch to it after spike detection and scheduling. A caller can then deliver an external scalar `D` with `simulator.apply_dopamine(D)` after `run_until(t)`; the event is timestamped at the current tick. The synthetic lane-one runner now performs that game-neural-reward ordering; a full fly-system scheduler remains future work.

Threshold crossing time is **tick-quantized**. It is not an interpolated continuous crossing time. A smaller `dt_us` may change spike timestamps, and this is a declared numerical-model sensitivity, not an unnoticed change to game time. No connection is evaluated via an N×N matrix.

## Storage and scale boundary

The immutable `SparseGraph` compiles presynaptic outgoing adjacency into `offsets[N+1]` and edge-length arrays for pre, post, signed weight and delay. On a spike, only outgoing slots are scheduled. Simulator state is one-dimensional per-neuron voltage, synaptic drive, refractory deadline, spike flag and spike count. The priority queue contains only pending events. Trace and arrival recording are opt-in, with a selected neuron set. Storage therefore scales as $O(N+E+Q+R)$, where $Q$ is pending arrivals and $R$ is requested recording. Each integration tick visits neurons plus the arrivals due at that tick; there is no pairwise $N^2$ allocation. A 100,000-neuron/three-edge CSR construction is included in the tests.

This CPU reference favors clarity. Sparse topology and the event/state contracts can be retained if later profiling justifies a faster kernel. No performance or biological accuracy claim about a full fly connectome follows from these tiny tests.

## Eligibility and dopamine rule

The caller selects canonical CSR edge slots as the plastic mask. The immutable graph retains its original weights; a separate overlay holds current effective weights only for masked slots. An incoming lookup is built only for those slots. Storage adds $O(P+U)$, where $P$ is the number of plastic edges and $U$ is the number of distinct plastic presynaptic neurons, with no dense neuron-pair matrix.

For a masked edge $i\to j$, a presynaptic spike at $t_i$ adds 1 to an exponentially decaying pre-trace $x_i$. At a **later** postsynaptic spike $t_j$, eligibility increments by the current trace: $e_{ij}(t_j^+) = e_{ij}(t_j^-) + x_i(t_j)$. Between events, $dx_i/dt=-x_i/\tau_{pre}$ and $de_{ij}/dt=-e_{ij}/\tau_e$. The full simultaneous spike batch is handled as one event: current postsynaptic spikes read earlier pre-traces before current presynaptic spikes are added, so same-tick pre/post spikes create no pair. A reversed post-then-pre sequence also creates no eligibility until a later post spike.

An externally supplied, finite signed dopamine scalar $D$ applies the requested rule at the event time:

\[
w_{ij}^{new}=\operatorname{clip}(w_{ij}^{old}+\eta e_{ij}(t)D,\ w_{min},w_{max}).
\]

Zero dopamine or zero eligibility leaves weights unchanged. Positive or negative $D$ raises or lowers a positive-eligibility weight subject to bounds. Eligibility and $D$ are dimensionless in this fixture; $\eta$ has mV-equivalent units. Dopamine does not clear eligibility, so a later dopamine event can update the same eligible edge again while the trace persists. This is a declared rule choice. The test fixture uses `eta=0.1`, `tau_pre_us=10000`, `tau_eligibility_us=20000`, weight bounds 0–12 mV-equivalent, and an externally supplied `D=1`. These values and the scalar dopamine interpretation are **not measured fly parameters**; compartmental DAN dynamics and biologically appropriate timing remain unresolved.

The four-case automated gate is `tests/test_plasticity.py`. In its A→B circuit, A spikes at 1 ms, B at 5 ms, and dopamine at 6 ms. The expected eligibility is $e(6\,ms)=e^{-4/10}e^{-1/20}$ and the update is $0.1e(6\,ms)$ mV-equivalent. No dopamine and dopamine without a pair give exactly zero update. Waiting to 206 ms before dopamine reduces the update by $e^{-200/20}$, far below one thousandth of the recent update. Tests also cover masking, negative modulation, clipping, simultaneous spikes, and old queued arrivals retaining their emission-time weight.

## Reproducible demonstrations

Run from the project root after setting `PYTHONPATH=src`:

```powershell
python scripts/demo_m1.py --config configs/m1_demos.yaml
python -m unittest discover -s tests -v
```

The demo writes [a voltage plot](figures/m1_lif_trace.png), [a vector version](figures/m1_lif_trace.svg), and [machine-readable spike/arrival/trace evidence](figures/m1_circuit_results.json). The values below are from the checked-in configuration, not fitted to fly recordings.

| Demonstration | Observed deterministic evidence |
| --- | --- |
| Constant drive 2.0 mV-equivalent, `tau_m=10 ms`, threshold 1.0 mV, reset 0, refractory 3 ms | The closed-form voltage rises through 0.190, 0.363, …, 0.902 mV at 1–6 ms. At 7 ms its pre-reset value is 1.006829 mV, so a spike is emitted and post-reset voltage is 0. Spikes repeat at 17 and 27 ms; voltage is clamped at 0 during each 3 ms refractory period. |
| A → B, weight +8, delay 2 ms | A spikes at 1 ms, arrival at B is 3 ms, B spikes at 5 ms. B has no external drive. |
| A ─| B, weight −6, delay 2 ms | With B's own constant drive, B first spikes at 7 ms without inhibition. A's spike at 1 ms arrives at 3 ms and delays B's first spike to 22 ms. |
| A → B → C, each weight +8 and delay 2 ms | Spikes are A 1 ms, B 5 ms, C 9 ms. Arrivals are at 3 and 7 ms. |
| Off-grid delay 1.25 ms | A spikes at 1 ms; B receives the effect at **2.25 ms**, which is recorded exactly, then spikes at the 4 ms tick. |

The test suite checks analytical rise, threshold/reset, refractory clamp including an off-grid refractory end, excitation, inhibition, propagation order, exact synaptic delay, configurable tick size, deterministic replay/chunking, validation failures, and sparse storage. These demonstrations are an engineering gate for a later fly circuit, not biological validation.
# MaleCNS minimal internal-learning fixture — 2026-10-02

The isolated experiment uses eight selected KC LIF cells, one MBON05 LIF cell, and eight aggregate edges from the pinned plastic contact mask. Each fixed four-KC state ensemble is contact-ratio normalized to total edge strength 1.0 mV-equivalent. Neuron constants and 2 ms delay reuse declared project LIF values. MBON maximum subthreshold voltage in a 100 ms window drives a fixed inverse threshold at 0.13266897755112178 mV-equivalent. Three STATE_A teacher presentations apply `w_i=max(0.2w_i_initial, w_i−0.03e_i)` with 1 s eligibility decay. These are experimental engineering settings, not calibrated adult physiology. See [the full model report](MALECNS_MINIMAL_INTERNAL_LEARNING.md).
