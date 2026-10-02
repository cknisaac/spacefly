# Electrical Model V1: frozen 115-body neutral implementation

**2026-09-30. Status:** electrically runnable implementation for the approved 115-body MaleCNS Circuit V1, with fixed engineering hypotheses. At implementation freeze it had not been through the full neutral gate; the subsequent [24-run gate passed](ELECTRICAL_V1_NEUTRAL_GATE_RESULT.md) as an engineering activity/safety check. The sensory–KC–MBON32 route was silent in that neutral condition, so no motor transmission, fly biological validity or learning is established. There is no task interface. The source/evidence decisions are in [route closure](CIRCUIT_V1_ROUTE_CLOSURE.md), [sign audit](CIRCUIT_V1_SIGN_AUDIT.md), [Circuit V1](../CIRCUIT_V1.md), and the [DN boundary contract](DN_BOUNDARY_OPERATING_STATE_CONTRACT.md). The exact frozen numerical policy is [electrical_model_v1.json](../configs/electrical_model_v1.json).

## Anatomy, identity and effect policy

The model selects the three visual candidates **13285/13707/13874**, all **107** right `KCg-d` cells, **APL 10540**, **PPL103 14182**, **MBON32 519131**, **DNa03 519624**, and **DNa02 523769**. `build_circuit()` checks the parent neuron/connection hashes, candidate-contact file hash and selected-ID hash before assigning any effect. The built local [manifest](../data/processed/malecns_v1_electrical_v1/manifest.json) identifies **115 bodies, 10,009 directed source pairs and 45,010 source contacts**. Source row IDs, counts and transmitter annotations remain attached to the separate overlay; no parent parquet or earlier 140-body policy is changed.

| State | Pairs / contacts | Implemented consequence | Evidence for direction |
| --- | ---: | --- | --- |
| `ACTIVE_FAST` | 184 / 2,904 | Named current injection on source spike after fixed delay | KC→MBON32 class excitation `LITERATURE-CONSTRAINED`; sensory→KC, MBON32→both DNs, DNa03→DNa02 `INFERRED` |
| `GRADED_INPUT` | 106 / 5,521 | KC spike raises its APL local state | `INFERRED` mapping of KC→APL source contacts |
| `GRADED_OUTPUT` | 106 / 5,455 | APL local state injects inhibitory current into the corresponding KC | Local inhibitory APL→KC `LITERATURE-CONSTRAINED`; one-domain-per-KC geometry `ENGINEERING ASSUMPTION` |
| `MODULATORY` | 108 / 962 | PPL103→KC/MBON contacts retained, with no fast current or neutral teaching | DA identity `MEASURED`; spatial functional access `INFERRED`; release/rule `UNKNOWN` |
| `UNKNOWN` | 9,505 / 30,168 | Anatomy retained, electrical effect **inactive** | `UNKNOWN` |

`UnknownEdgePolicy.RETAIN_ANATOMY_INACTIVE` fails closed: an UNKNOWN edge cannot carry a numerical weight. Inactivity is a model omission, **not** a claim that the anatomical synapse has zero physiological effect. In particular, KC recurrence and the reverse DNa02→DNa03 pair remain present but inactive. The old all-positive electrical overlay is not reused. Numeric pA amplitudes below are **ENGINEERING ASSUMPTIONS** for the named hypotheses only; their signs are not promoted to `MEASURED` exact-target effects.

| Named fast hypothesis | Frozen current step per source contact |
| --- | ---: |
| sensory→KC | +0.03 pA |
| KC→MBON32 | +0.01 pA |
| MBON32→DNa03 | −0.10 pA |
| MBON32→DNa02 | −0.10 pA |
| DNa03→DNa02 | +0.04 pA |

`MEASURED`: KC→MBON32 has 1,129 anatomical contacts on 105 pairs. The separately retained, anatomy-only candidate mask holds **796 contacts on 100 KC pairs**, screened for γ2 endpoints and same-KC PPL103 contact as described in route closure. The other **333** contacts are retained as fixed anatomy; for mixed pairs the overlay records candidate and remainder counts separately. All 1,129 contacts currently contribute to the frozen fast class hypothesis. `ENGINEERING ASSUMPTION`: **plasticity is disabled**, and no eligibility, dopamine update, reward or learning rule is invoked. Terminal dopamine access and the exact KC→MBON32 rule remain `UNKNOWN`.

## Cell dynamics and numerical units

There are **113** point spiking surrogates (3 visual, 107 KCs, MBON32 and two DNs). Each uses passive current-based LIF subthreshold dynamics. This is an **ENGINEERING ASSUMPTION** for electrical testing, with literature constraining only the broad cell roles; no exact-body MaleCNS membrane parameter is claimed measured.

```text
C_i dV_i/dt = -g_i(V_i - V_rest,i)
              + I_fast,i + I_APL,i + I_boundary,i + I_neutral_sensory,i
dI_fast,i/dt = -I_fast,i / tau_fast
I_fast,post(t_arrival+) = I_fast,post(t_arrival-) + contacts × current_per_contact
```

`V` is mV, `C` pF, `g` nS, currents pA and time ms (stored event time is integer µs); **1 pA / 1 nS = 1 mV**. `I_neutral_sensory=0 pA` for the fixed neutral condition. There is no osu engine, cue/note clock, exploration, reward, ideal key, one-key readout or motor feedback in this runtime. The boundary current is separately injected and logged. Subthreshold passive+exponential-current segments are integrated analytically between discrete events; threshold evaluation remains on a fixed grid.

Every number in this table is **ENGINEERING ASSUMPTION**, individually labelled in the config. The cell-class and behavioral literature summarized in [Circuit V1](../CIRCUIT_V1.md) constrains model-family choice, not these exact values. They were frozen before the neutral gate and before any task output.

| Class | C (pF) | g (nS) | rest / onset / reset (mV) | refractory (µs) | passive τ (ms) |
| --- | ---: | ---: | --- | ---: | ---: |
| selected sensory | 10 | 1 | −60 / −45 / −61 | 1,500 | 10 |
| right KCg-d | 5 | 0.5 | −62 / −48 / −63 | 2,000 | 10 |
| MBON32 | 20 | 1 | −58 / −43 / −59 | 2,000 | 20 |
| DNa03 | 30 | 1.5 | −60 / −45 / −61 | 2,500 | 20 |
| DNa02 | 40 | 2 | −60 / −45 / −61 | 2,500 | 20 |

At threshold, record one spike, reset voltage, and hold reset through refractory time. No conductance reversal, adaptation, dendritic compartment, spike waveform or stochastic intrinsic noise is modelled; those exact dynamics are `UNKNOWN`. Different C/g give distinct class timescales or scales despite some coincident ratios. The sensory cells are silent under the fixed neutral input; this is not evidence that they are naturally silent.

### APL and DAN

`LITERATURE-CONSTRAINED`: APL is local, graded and inhibitory rather than a generic spiking cell. `ENGINEERING ASSUMPTION`: the implementation gives each retained KC one independent γ2-like local APL variable `a_k`; a KC→APL source event adds `0.002 × source contacts`, `da_k/dt=−a_k/50 ms`, and source APL→that-KC contacts inject `−0.02 pA × contacts × a_k`. The source local-contact counts are `MEASURED`, but pair counts do **not** identify APL subbranches; the one-domain-per-KC correspondence, coefficients and 50-ms decay are model geometry, not a traced microcircuit. A separate 20-ms calyx variable is currently quiescent. There is no global APL spike or all-KC pooling. Cross-KC lateral inhibition, spatial release fields and other missing APL inputs remain `UNKNOWN`.

PPL103 is **not** forced into a LIF spike class. It has a separate dopamine state with **200-ms** passive decay (`ENGINEERING ASSUMPTION`), initially and permanently zero under neutral mode. Its 108 modelled modulatory source pairs schedule no fast current. There is no reward-derived teaching pulse or KC→MBON32 update. The natural PPL103 spike/release dynamics and exact plasticity rule are `UNKNOWN`.

## DN normalization and `dn-boundary-v1`

For each passive DN, define `R_in = 1/g_leak` and `ΔV = V_onset − V_rest = 15 mV`; then `I_ref = ΔV/R_in = g_leak ΔV`. The independently declared parameters give **22.5 pA** at DNa03 and **30 pA** at DNa02. These are positive finite passive *model* reference currents, not measured rheobase or chosen from firing outcomes. If they cannot be computed, construction stops.

The [contract](DN_BOUNDARY_OPERATING_STATE_CONTRACT.md) is implemented directly:

```text
I_boundary,i(t) = I_ref,i × s × [1 + 0.20 X_common(t) + 0.20 X_i(t)]
s ∈ {low:0.5, nominal:1.0, high:1.5}
```

Each `X` is a stationary fair ±1 telegraph stream with exponential flip intervals of mean **100,000 µs**. Continuous-time target autocorrelation is `exp(−|lag|/50 ms)`. The normalized mean is `s`, variance `0.08s²`, support `[0.6s,1.4s]`, and zero-lag correlation of the two **boundary fluctuations** is 0.5. `ENGINEERING ASSUMPTION`: Python MT19937 (`random.Random`) uses named independent streams derived by SHA-256 of `dn-boundary-v1|master_seed|stream_name`, for seeds **31001/31002/31003**. Initial sign uses one fair draw; intervals use inverse-CDF `−100000 log(1−u)` rounded half-even to integer µs, minimum 1 µs. This discretizes, rather than changes, the contract's 50-ms continuous target. All five streams (common, two private, two replacement) advance on an autonomous clock even when a control does not inject them. The checkpoint saves every RNG state, sign and next flip. No boundary API accepts task or neural data.

Condition D replaces the one common stream with two independent replacement streams, keeping each DN's **marginal** level, variance, support and temporal law; boundary cross-correlation becomes zero. Correlation of resulting spikes is not specified. Condition B injects exactly zero while still advancing the autonomous streams. Proxy drive never creates fictitious anatomical synaptic events.

## Event ordering, controls and neutral logging

**ENGINEERING ASSUMPTION** timing policy: fixed threshold grid **500 µs**, fast-current decay **5,000 µs**, and every named chemical event has a strictly causal **1,000 µs** delay. The old overlay's 2-ms delay is not reused. Between ticks, integrate exactly over boundary flips and queued arrivals. Interior ties process boundary flips then arrivals. At a tick: integrate to the tick using old drives; detect spikes in ascending source-ID order; reset/set refractory and schedule their future events; process boundary flips; deliver due chemical events ordered by `(arrival, postsynaptic index, presynaptic index, source row, insertion sequence)`. Arriving current changes state for the *next* interval and cannot cause a same-tick spike. A natural spike/reset/refractory operation is not a safety clip. Queue overflow (100,000) and nonfinite state stop execution. Clock and delay are integer µs; analytical exponentials use floating-point arithmetic. Exact-bit reproducibility is expected on the same Python/NumPy platform, not asserted across math-library versions.

| Condition | Boundary | MBON32→DN function |
| --- | --- | --- |
| A | shared proxy at low/nominal/high | both branches active under their named hypotheses |
| B | omitted proxy | both branches active |
| C | same shared proxy as A at low/nominal/high | both branches functionally disconnected; source rows retained |
| D | nominal independent-background proxy | both branches active |

The frozen [operating-state gate](DN_BOUNDARY_OPERATING_STATE_CONTRACT.md) predeclared **24** runs: three seeds × (A three levels, B one, C three, D one), each with 10-s settling and 60-s observation. This implementation document was frozen before those runs; the subsequent [result](ELECTRICAL_V1_NEUTRAL_GATE_RESULT.md) reports them separately. The neutral runtime supports condition and seed selection only from that fixed set; it cannot accept arbitrary levels.

The runtime exposes per-class and per-DN spike counts, exact spike times/IDs, separate `synaptic_drive_pa`, `apl_drive_pa`, `boundary_drive_pa` and leak-drive samples for requested cells, membrane voltage, refractory time and per-second DN refractory bins, voltage excursion counters, queue size/peak, scheduled/delivered counts, and a complete checkpoint. Samples are taken after tick events, so sampled current is the drive for the following interval. Caller-selected recording prevents dense all-cell traces by default; no note/task field is logged or accepted. A future gate runner must separate settling/observation metrics and preserve all 24 individual results.

## Evidence limits and readiness

The source bodies, contact counts, selected transmitter labels and screened candidate mask are `MEASURED` reconstruction/annotation facts. KC→MBON excitation and local APL inhibition are `LITERATURE-CONSTRAINED` class constraints. The other named signs and route effects are `INFERRED`, with exact receptors, chloride/reversal effects, efficacy and kinetics still `UNKNOWN`. All membrane/current/decay/delay/geometry numbers, DN proxy statistics, fixed neutral input and numerical rules are **ENGINEERING ASSUMPTIONS**. They are versioned and frozen, not tuned to pass a gate or maximize osu performance.

The main model limitation is biological: only **42/17,716** traced-parent contacts into DNa03 and **310/23,957** into DNa02 lie inside the reduced circuit; source contact fractions are not current fractions. The boundary is a declared net-current surrogate, not a reconstructed conductance, synapse inventory or proof of an active fly state. KC recurrence and most other within-subset effects are inactive UNKNOWN. Selected visual IDs are not validated game-feature detectors, APL branch geometry is unvalidated, PPL103 is inactive in neutral mode, and the artificial one-key readout is absent. Any later behavioral model must face those unknowns and test the named route effects independently.

Implementation checks cover source identity, effect dispatch, UNKNOWN inactivity, exact mask totals, boundary algebra/stream pairing/independent marginals, checkpoint replay, controls, event timing, disabled learning and a short 500- versus 250-µs numerical refinement. The later [70-s, 24-condition result](ELECTRICAL_V1_NEUTRAL_GATE_RESULT.md) passed the engineering gate and includes three full-horizon refinements. Its silent sensory–KC–MBON32 route prevents a motor-route or learning claim. The exact-body biology remains unresolved even though the declared numerical operating-state criteria passed.
