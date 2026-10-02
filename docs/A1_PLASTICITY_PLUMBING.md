# A1 — plasticity and learning plumbing

**Scope:** generic simulator infrastructure under the new Branch A roadmap. The historical `ThreeFactorPlasticity` rule is an engineering fixture. A1 does not establish that this rule is the selected fly rule or that the synthetic learner passes M2. The A0 freeze manifest remains a historical snapshot; it is not regenerated as implementation work proceeds.

## A1.1 — inventory and readiness review

**Question:** Which local-learning mechanisms already exist, and what must be checked before a candidate fly rule can use them?

| Requirement | Existing implementation/evidence | Gap or decision |
| --- | --- | --- |
| Selected plastic locus | `ThreeFactorPlasticity` stores a sorted unique CSR-slot mask and effective weights separately from `SparseGraph`; the simulator reads effective weight only at spike emission. | Check multiple selected and unselected edges together, including all nonweight state. The actual γ4 mask is a B2 decision. |
| Local eligibility | Presynaptic trace, later postsynaptic pairing and exponential eligibility decay are in `plasticity/eligibility.py`. Simultaneous spikes do not pair. `tests/test_plasticity.py` covers order, coincidence, decay and four causal cases. | Test deterministic arithmetic across equivalent spike-batch orderings and independent edge histories. This pre/post rule is **not** the B1-selected γ4 KC/DAN temporal-order rule. |
| Delayed teaching | The orchestrator computes judgement → utility → expected utility/RPE → synthetic modulation, then calls `SpikingSimulator.apply_dopamine` at a neural tick. Calling at a later tick applies decayed eligibility. | Verify exact delayed arithmetic. There is no internal queued DAN event or candidate-specific PAM state; those require the B2 timing/teaching design and A2 checkpoint contract. |
| Bounds and clipping | Selected effective weights clip to declared finite bounds; proposed non-finite updates raise. Existing tests cover positive upper clipping and one negative modulation. | Add a lower-bound and rejected-update atomicity check. Numeric bounds for a fly candidate remain B2 assumptions. |
| Determinism and isolation | Selected slots are sorted; graph topology/base weights are stored separately. Simulator spike order is neuron order, and queued arrivals capture weight at emission. Existing tests cover queued-arrival causality and same-seed replay. | Check byte-exact repeated local arithmetic and that dopamine delivery leaves neural, queue, graph and unselected-edge state untouched. |
| DAN/rule semantics | B1 selected a KCg-m→MBON05 γ4 candidate and a **KC/DAN temporal-order** rule family with PAM08 modulation; [B1 report](B1_MVP_PATHWAY_RULE_SELECTION.md). | B2 has not locked equations, coincidence policy, PAM drive, exact compartment mask or weight bounds. Do not substitute the current signed-RPE × pre/post trace rule. |

**A1.1 result: PASS as an inventory.** The generic rule and delivery seam exist. The next step is A1.2, with three small checks below. No separate discovery step is needed before these checks; A1.3 candidate integration remains conditional on B2.

## A1.2 — locked generic invariant checks

**Question:** For a declared spike and teaching sequence, do only selected weights change by the expected deterministic bounded amount?

**Intervention:** Use tiny synthetic graphs with fixed edge slots and timestamps. Add regression checks for (a) equivalent spike-batch ordering with delayed teaching, (b) positive and negative clipping plus atomic rejection of non-finite proposed updates, and (c) simulator-level isolation of neural, event-queue, graph, parameter and unselected-edge state during a weight update. Assert exact arithmetic where operations are identical and tight numerical agreement against the closed-form decay where exponentials are evaluated. Existing four-case tests remain the controls.

**Possible outcomes:** PASS if all declared invariants hold; FAIL if an unintended value changes, an update is order-dependent, bounds fail or rejection partially applies; INCONCLUSIVE only if a fixture cannot observe the relevant state. Preserve any failure and fix a demonstrated plumbing defect before advancing.

**Frozen controls:** existing implementation equations, edge ordering, time units and all historical configs/results. No parameter search, training run, biological rule claim or task performance criterion. Output is source-local regression evidence plus a short result and readiness review here.

**A1.2 mini-step sequence:** A1.2a delayed/order/mask arithmetic → review; A1.2b bounds and atomic rejection → review; A1.2c simulator state isolation → review. The first two can use the existing generic rule; the third uses the existing simulator with no game coupling.

### A1.2 result and step reviews — 2026-10-01

The new [generic invariant checks](../tests/test_a1_plumbing.py) all passed. The relevant existing plasticity, neuromodulation and closed-loop tests also passed: **31/31** with the repository `.venv` and `PYTHONPATH=src;tests`. This is a plumbing regression run, not a new scientific experiment or synthetic performance gate.

| Mini-step | Observed result | Readiness decision |
| --- | --- | --- |
| **A1.2a — delayed/order/mask** | Equivalent presynaptic and postsynaptic spike batches in opposite enumeration orders gave identical update records. Two selected edges matched closed-form decay after a delayed nonzero teaching event; the unselected edge and source graph weights stayed fixed. | **PASS; ready for A1.2b.** No repair mini-step needed. |
| **A1.2b — bounds/atomicity** | Positive and negative modulation clipped at both declared bounds. A two-edge update that overflowed on the second proposal raised before committing the first proposed change; weights and eligibilities stayed at their prior values. | **PASS; ready for A1.2c.** No repair mini-step needed. |
| **A1.2c — simulator isolation** | Delivery changed the selected effective weight while immutable graph weights, unselected effective weight, neural snapshot, event queue, diagnostics, parameters and external drive stayed equal to pre-delivery state. | **PASS; ready for A1.3 interface review.** No repair mini-step needed. |

**A1.2 result: PASS for the declared generic fixture.** Existing `ThreeFactorPlasticity`, simulator and historical configurations were not changed. The test count is limited to relevant modules; it does not validate a γ4 learning rule.

## A1.3 — candidate integration contract and readiness review

**Question:** What is the smallest simulator boundary that can carry the B1-selected γ4 KC/DAN rule without treating the historical signed scalar rule as fly physiology?

The B1 package has **689 KCg-m_L→MBON05 10495 anatomical pairs** and **25 PAM08_L candidates**. These are candidate populations, not a finalized plastic mask or an executable learning rule. The implementation boundary must have:

1. **A source-derived mask:** selected MaleCNS edge/pair IDs, compartment policy and a checksum. It may update only those effective weights. The immutable connectome topology, other source edges, neural parameters and fixed sensory/motor interfaces remain unchanged by learning.
2. **Causal local activity inputs:** timestamped KC activity and nonnegative compartment-local PAM/DAN activity, with an explicit same-time order. Both event types must be able to produce an update because KC-before-DAN and DAN-before-KC have opposite effects. A method limited to `apply_dopamine(signed_scalar)` after pre/post spike pairing is insufficient.
3. **Separated feedback stages:** resolved first-action disposition → utility/prediction error → artificial reinforcement interface → PAM activity → local rule. The game and reward predictor cannot write weights. Negative RPE is not silently represented as negative dopamine concentration.
4. **Audit records:** each event's source, time, compartment, selected mask identity, local trace state used, old/proposed/applied weight, clipping and all unchanged-edge checks. Deterministic event order and exact continuation are later A2 requirements.
5. **Failure behavior:** reject wrong compartments, non-finite activity, unknown source IDs and unselected-edge proposals before any partial commit; record zero-update events as well as changes.

**Unresolved B2 inputs:** exact γ4 contact/pair mask, trace equations and reset policy, coincidence rule, PAM drive and feedback semantics for early/late/no-DOWN, delay policy, numerical time constants/gains/bounds, and which downstream assumptions are fixed. B1 supports the temporal polarity, not these numbers.

**A1.3 decision:** the interface contract is **specified**, but candidate implementation is **PENDING B2**. Implementing a generic protocol now would force premature assumptions about when an update is returned and how KC/DAN state is represented. The next safe Branch A work is A2.1's state schema; once B2 is locked, resume candidate integration at this boundary and repeat the A1.2 isolation checks with the chosen rule.

## A1 stage decision

**Generic A1 plumbing: PASS. Candidate-specific A1 integration: PENDING B2.** A1.1, A1.2a–c and the A1.3 boundary review each support progression without a repair mini-step. The active Branch A roadmap may proceed to A2.1, while the exact fly rule remains a Branch B design task. No synthetic learning-performance condition was used.

## A1.3 resumed after B2 — 2026-10-01

B2 has now locked `MVP-C1`. The earlier **PENDING B2** statement above records the state before that design; this section supersedes its status. The implementation is limited to the selected contact mask, local KC/PAM rule and simulator weight seam. It does not execute B3, task feedback, PAM current injection or training.

| Mini-step | Result and evidence | Readiness review |
| --- | --- | --- |
| **A1.3a — source contact binding** | [Mask builder](../scripts/build_b2_gamma4_runtime_mask.py) verified the 2,965,367,002-byte MaleCNS partner file against its pinned SHA-256, resolved every B2 source partner row to a KC, and combined those rows with the B1 source pair contact counts. The [runtime mask](../configs/b2_candidate1_runtime_mask.json) holds 13,957 contact IDs on 688 selected pairs plus the fixed-only KC 51583, all 689 pair totals (16,398 contacts), B1/B2 checksums and `g4(L)` identity. An initial attempt using the older Circuit V1 subset failed because MBON05 10495 is absent from that distinct cohort; the builder was corrected to use B1's pinned 689-pair anatomy. | **PASS after source-cohort correction; ready for A1.3b.** No additional mask discovery is needed. |
| **A1.3b — local γ4 rule** | [Candidate rule](../src/project_b/plasticity/gamma4.py) splits each active pair's initial positive coupling by selected/total contact count, keeps the fixed contribution unchanged, and applies B2's 1-s KC trace, 1.2-s PAM trace, nonnegative actual-spike fraction, 0.001 initial-weight update, 0.5–1.5× plastic bounds and depression on coincidence. It returns pre-trace, proposed/applied, clipping, KC source, compartment and mask-checksum records, including zero-effect events. All proposals are checked before commit; invalid source indices, duplicate batches and wrong compartment reject without partial changes. | **PASS; ready for A1.3c.** The rule accepts actual PAM spikes only; task RPE cannot be passed as signed dopamine. |
| **A1.3c — simulator seam and regression** | `SpikingSimulator` accepts the candidate rule, captures the local batch record, uses effective weights only at emission and retains already queued arrivals. Its legacy signed-scalar `apply_dopamine` rejects the γ4 rule. The B2 factory checks the pinned design/audit hashes and exact KC→MBON05 class-gain transform; a deliberately changed graph coupling is rejected. A full B2 mask fixture bound all 688 selected pairs; one KC followed by one PAM spike altered exactly one selected contribution and left graph/base and fixed-only state unchanged. Pairing order, coincidence, zero events, bounds, rejected batches, mask checks and simulator capture passed. The entire repository suite passed **124/124** tests, then the six γ4 tests passed again after the final hash/transform guards. | **PASS for A1.3; no repair mini-step needed. Ready for A2.1 state/checkpoint schema.** |

**Limit:** This is a local-rule and simulator-boundary result. The B2 normalized full electrical network, 25-cell PAM pulse drive, first-action feedback timing and separated game/utility/request/PAM ledgers are not yet an executable coupled run. Those dependencies belong to A2–A4 integration before B3. The current simulator uses its historical mV-equivalent LIF quantities; these tests do not establish B2 electrical controllability or biological learning. The `last_plasticity_record` is a one-batch handoff for later orchestration, not a persistent run ledger or checkpoint. The next step is **A2.1**, which must enumerate the new KC/PAM traces, split weights and batch/feedback state explicitly before exact replay work. Stop before A2.1 execution under this request.
