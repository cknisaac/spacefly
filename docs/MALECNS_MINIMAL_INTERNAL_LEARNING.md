# MaleCNS minimal internal-learning experiment

**2026-10-02 · MALECNS-MINIMAL-INTERNAL-LEARNING-v1 · PASS for the reduced engineering fixture.** This is a new isolated experiment. It does not replace, revise, or reinterpret the historical adult Branch A/B results.

## Claim and limits

The result supports this narrow statement: **a deterministic connectome-constrained adult Drosophila simulation fixture stored a two-state association in selected KC→MBON05 weight variables under an artificial encoder, voltage normalization, teacher-gated LTD rule, and fixed threshold readout.** It is an internal-learning infrastructure proof. It does not establish adult fly physiology, biological dopamine, visual processing, motor execution, or fly behavior.

The exact traced MaleCNS v1.0 source and KC→MBON contact mask are **MEASURED** anatomy. The state-to-KC encoder, contact-ratio voltage normalization, LIF constants/effects, local LTD equation, artificial teacher, MBON voltage readout, and action threshold are **ENGINEERING ASSUMPTIONS**. Sharing a compartment and having a PAM overlap in the historical B2 mask do not establish functional plasticity at these terminals. No PAM or other DAN neuron is simulated here.

## Reused infrastructure and frozen circuit

The experiment is under `src/project_b/malecns_minimal_internal_learning/`. It reuses the existing MaleCNS/B2.1 source loader (`load_mvp_circuit`), source graph and contact audit, sparse `SparseGraph`, deterministic CPU `SpikingSimulator`, LIF implementation, simulator checkpoint/restore, and unittest suite. The audit checksum and every selected contact-row ID are pinned in [the experiment config](../configs/malecns_minimal_internal_learning.json). The loader verifies that all selected KC→MBON pairs occur in its MaleCNS v1.0 traced runtime graph. No random draws were used; seed 31001 is recorded as the run identifier.

The reduced topology is 8 real KC source IDs and MBON05 source ID **10495**. Eight aggregate KC→MBON edges represent **164 audited plastic contact rows** (10, 19, 22, 25, 22, 16, 25, 25). Each aggregate edge represents only its pinned plastic contact rows; other contacts are omitted from this reduced overlay. The first four audited KC IDs form fixed STATE_A (target); the next four form fixed STATE_B (control). This source-order selection was frozen before simulation outcomes were examined.

| State | KC source IDs | Audited plastic contacts |
|---|---|---:|
| A | 19083, 33808, 37916, 38113 | 76 |
| B | 38549, 38962, 39531, 41131 | 88 |

The encoder supplies a fixed 1.2 mV-equivalent external drive to each KC in the presented state for a 100 ms observation window. Within each state, edge weight is the KC's share of that state's audited plastic contact rows, so each state has the same total normalized input strength at multiplier 1.0. No downstream cell, visual path, timing system, optimizer, trainable decoder, or task information is used.

## Pretraining controllability gate

Plasticity was off. The declared STATE_A edge multipliers produced strictly monotonic MBON maximum membrane voltage:

| Multiplier | MBON activity (mV-equivalent) | Fixed action |
|---:|---:|---|
| 1.00 | 0.189527 | No |
| 0.80 | 0.151622 | No |
| 0.60 | 0.113716 | Yes |
| 0.40 | 0.075811 | Yes |
| 0.20 | 0.037905 | Yes |

The action rule and threshold were frozen before training: action when maximum recorded MBON voltage is at or below **0.13266897755112178 mV-equivalent**, the midpoint of the 0.8 and 0.6 probe responses. Both STATE_A and STATE_B produce 0.189527 mV-equivalent and no action before training. MBON spiking remains zero; the readout is its declared subthreshold voltage proxy, not a biological action neuron.

The existing simulator's committed-tick state was checkpointed at 50 ms and restored into a matching simulator. Continuation to 100 ms matched exactly for all probe conditions. Repeated initial-state runs also matched exactly. The complete probe is [saved here](../runs/malecns_minimal_internal_learning/controllability.json).

## Frozen local LTD and training

For each selected KC edge, eligibility follows `e_i(t) = decayed_e_i + 1` at a KC spike and decays exponentially with τ = **1,000,000 µs**. One artificial teacher pulse follows each STATE_A presentation by 1,000 µs. On teacher, only eligible selected edges update as `w_i = max(0.2 w_i_initial, w_i − 0.03 e_i)`. Training used exactly **3 STATE_A repetitions**. STATE_B was never taught in the primary arm. The rule has no potentiation, recovery, RPE, optimizer, or postsynaptic-spike requirement. The teacher, trace constants, learning rate, and lower bound are **ENGINEERING ASSUMPTIONS**.

All four STATE_A edges reached their predeclared 20% floor. All four STATE_B edges remained bitwise unchanged.

| KC source ID | Initial weight | Final weight | State |
|---:|---:|---:|:---:|
| 19083 | 0.131579 | 0.026316 | A |
| 33808 | 0.250000 | 0.050000 | A |
| 37916 | 0.289474 | 0.057895 | A |
| 38113 | 0.328947 | 0.065789 | A |
| 38549 | 0.250000 | 0.250000 | B |
| 38962 | 0.181818 | 0.181818 | B |
| 39531 | 0.284091 | 0.284091 | B |
| 41131 | 0.284091 | 0.284091 | B |

Every KC spike, eligibility at each teacher, teacher flag, and weight change is retained in [the run result](../runs/malecns_minimal_internal_learning/result.json).

## Frozen test and controls

Weights were retained for test; plasticity and teacher were off. Encoder and threshold were unchanged.

| Arm | STATE_A MBON activity / action | STATE_B MBON activity / action |
|---|---|---|
| Before training | 0.189527 / No | 0.189527 / No |
| STATE_A teacher training | 0.037905 / Yes | 0.189527 / No |
| Plasticity-off training control | 0.189527 / No | 0.189527 / No |
| Wrong-state teacher control (teacher on B) | 0.189527 / No | 0.037905 / Yes |

All seven experiment criteria passed: only selected internal KC→MBON edge variables changed; updates followed the taught state; frozen STATE_A acquired action while STATE_B did not; plasticity-off training acquired no action; and the wrong-state teacher moved the action to STATE_B. No threshold or decoder training occurred.

## Verification and disposition

The dedicated experiment tests cover active KC plus teacher, inactive KC plus teacher, KC without teacher, plasticity off, and nonplastic-edge immutability, as well as the complete probe, replay, learning, and controls. The complete existing unittest suite passed: **161 tests in 64.3 seconds**. The environment's system Python lacked `pyarrow`; tests were run with the repository's `.venv`, which supplies NumPy and PyArrow.

Machine-readable configuration and outputs:

- [Frozen experiment configuration](../configs/malecns_minimal_internal_learning.json)
- [Controllability probe](../runs/malecns_minimal_internal_learning/controllability.json)
- [Training and control results](../runs/malecns_minimal_internal_learning/result.json)

The requested outcome-blind replication is now complete; see the separate [replication report](MALECNS_MINIMAL_INTERNAL_LEARNING_REPLICATION.md). The original result and its config and outputs remain unchanged. No DAN pathway, visual input, osu timing, or biological motor circuit is admitted by either result. The replication does not justify tuning the successful fixture or expanding its biological claim.
