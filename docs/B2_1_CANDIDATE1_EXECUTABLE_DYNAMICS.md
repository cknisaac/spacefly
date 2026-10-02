# MVP-B2.1 — Candidate 1 executable-dynamics addendum

**2026-10-01 · PASS for a versioned engineering design only.** The [B2 design](B2_CANDIDATE1_DESIGN.md) selected the pathway, γ4 mask, rule, interfaces and major numerical assumptions. The [A2.2/A2.3 review](A2_2_A2_3_CHECKPOINT_PROGRESS.md) identified three remaining timing laws required to construct one unambiguous coupled runner. This addendum fixes those laws and maps every source pair to an active, modulatory or explicitly quarantined class. It does not implement or run the 718-cell circuit, replay gate, B3 panel or learning. All new values are **ENGINEERING ASSUMPTIONS**, not measured MaleCNS kinetics.

The authoritative inputs are the immutable [original B2 JSON](../configs/b2_candidate1_design.json), [B2.1 addendum](../configs/b2_1_candidate1_dynamics_addendum.json), [resolved config](../configs/b2_1_candidate1_resolved.json), [source coverage](figures/b2_1_candidate1_dynamics/source_coverage.json) and [validation receipt](figures/b2_1_candidate1_dynamics/validation_receipt.json). The [resolver](../scripts/resolve_b2_1_candidate1.py) checks source and config consistency. It embeds the original B2 fields rather than rewriting that design or its historical receipt.

## 1. Chemical current after a measured active connection

At a presynaptic spike, capture that pair's current signed effective weight and schedule an arrival exactly **2,000 µs** later. At arrival time, add the captured weight to the target's signed voltage-equivalent synaptic-current state `S`; voltage does not jump. Between events, `S` decays exponentially with **τsyn = 5,000 µs**. This is the existing reference LIF current form with a newly explicit Candidate 1 constant. A contact count determines the declared B2 weight transform; it is not a measured conductance. A later γ4 weight update cannot change an already queued arrival.

For a positive interval `Δ` from a fully processed event time, the exact subthreshold rule is

```text
S(t+Δ) = S(t) exp(-Δ/τsyn)
V(t+Δ) = Vrest + [V(t)-Vrest] exp(-Δ/τm)
         + Iconstant [1-exp(-Δ/τm)]
         + S(t) Φ(Δ;τm,τsyn) + IAPL(t) Φ(Δ;τm,τAPL)
Φ(Δ;τm,τx) = τx/(τx-τm) [exp(-Δ/τx)-exp(-Δ/τm)]
Φ(Δ;τm,τm) = (Δ/τm) exp(-Δ/τm)
```

`τm=20,000 µs`, `τAPL=20,000 µs`, and every current is in B2's **normalized threshold-margin** units. `Iconstant` is the sum of currently held external sensory/PAM and autonomous-boundary currents for the target, held piecewise constant over that interval. The formula defines a signed current state, so inhibitory arrivals use negative values; unknown source pairs inject no current. During an absolute refractory interval, clamp voltage at reset while decaying `S` and APL state normally; resume the exact formula when refractory ends. Threshold checks occur on the 1,000-µs grid. The general τx=τm limit is required so the APL term is finite, not a numerical special case chosen after a run.

Before processing events at microsecond `t`, integrate the open interval since the preceding event using the state that was already in force. At `t`, sort chemical arrivals by `(due_us, post_source_id, pre_source_id, source_row, insertion_sequence)`, add all finite signed contributions, then let them affect only following positive intervals. This also defines ties with boundary flips and APL arrivals; no same-instant voltage jump or zero-delay loop is permitted.

## 2. Autonomous omitted-input boundary

Use one independent two-state telegraph stream for each of MBON05 **10495**, MBON20 **11145** and DNp42 **10713**. Their nominal mean currents remain **0.5, 2.0 and 2.0 threshold units** from B2. Low/nominal/high multiply those means by **0.5/1/1.5**. A stream's sign is ±1 and the held current is `level × mean_i × (1 + 0.2 sign_i)`. It reads only the resolved config, dedicated RNG state and elapsed time; it never reads cue, note schedule, feedback, spikes or score. It continues across note boundaries.

**Waiting law:** independent exponential intervals with continuous mean **100,000 µs**, mapped to a positive integer as `max(1, round(-100000 log1p(-u)))`, where `u` is the next Python `random.Random.random()` draw and `round` uses ties-to-even. Python's MT19937 state and runtime version are checkpoint identity. For master seed `s` and source ID `i`, initialize a separate stream with integer SHA-256 of UTF-8 `mvp-c1-boundary-v1|s|i`; its first draw selects sign +1 if `<0.5`, and the next draw gives the first flip after time zero. Every flip toggles that target's sign and schedules another strictly positive wait from the same stream. At tied flips, process targets by ascending source ID. Exact microsecond flips split integration intervals; they are never rounded to a neural tick. Save all three signs, next-flip times, full RNG states and boundary clock in a coupled checkpoint.

This choice follows the *method* used by the historical [DN boundary runtime](../src/project_b/electrical_v1/boundary.py), with new independent Candidate 1 streams. It does not import historical circuit currents or claim that contact counts measure missing drive. The RNG law is locked before any Candidate 1 electrical or game result.

## 3. Graded APL application

APL **10977** is one nonspiking graded state `L∈[0,1]`, initialized at zero. It decays as `L(t+Δ)=L(t)exp(-Δ/20000)` between events. Each **measured KC→APL** pair schedules a graded increment at the KC spike plus **2,000 µs**. The increment equals its source contact count divided by the **37,593 KC→APL contacts** among the selected 689 KCs. At a due time, decay `L` to that time, apply all same-time increments in source-row/insertion order, and clip once to `[0,1]`. The source graph has 689 such pairs. This is an explicit input normalization, not a claim that every contact has identical physiological release.

For each **measured APL→target** pair within the roster, apply continuous inhibitory current `IAPL,target(t) = -0.2 L(t)` over the following interval through the exact `Φ(Δ;τm,τAPL)` term above. There are **702 APL target pairs / 40,739 contacts**. Each target has one APL source pair, so B2's *per-target APL effect-class* contact-share denominator equals that pair's own contact count; every connected target gets the same declared coefficient. Unconnected targets receive zero APL current. An APL arrival does not jump any target voltage. APL emits no spike and never enters the ordinary chemical queue as a presynaptic LIF cell. Save `L`, last update time and pending KC→APL arrivals for exact replay.

This one-global-state reduction is an **ENGINEERING ASSUMPTION**. It may miss spatially local APL effects; B3 can only test this declared model. The γ4 contact mask and actual PAM08-spike update rule remain those of B2/A1.3.

## 4. Source graph and runner interface

The [coverage audit](figures/b2_1_candidate1_dynamics/source_coverage.json) independently rereads the pinned normalized MaleCNS files and accounts for **all 153,854 induced pairs / 333,380 contacts** in the 718-cell roster:

| Role in the proposed runner | Pairs | Contacts |
| --- | ---: | ---: |
| Active electrical or graded hypotheses | **138,982** | **308,475** |
| PAM08 anatomical/modulatory only | **7,079** | **11,783** |
| Unknown, source-retained but no numerical current | **7,793** | **13,122** |

The active total includes 136,314 KC→KC pairs, 689 KC→MBON05, 586 KC→MBON20, 689 KC→APL inputs, 702 APL outputs and the two output-route pairs. This exhausts the roster without making a default positive edge. Among the 718 source IDs, **717 have explicit spiking state and APL has graded state**. PAM08 source edges are retained as modulatory anatomy; only actual PAM08 spikes drive the γ4 local trace. The 13,957 γ4 contact candidates, 688 selected pairs, fixed/plastic split, class gains and exact downstream pair hypotheses are unchanged.

The future runner must assemble source graph/effect overlay, LIF and captured-weight chemical queue, graded APL, autonomous boundary, delayed current-position encoder, PAM08 current and γ4 rule, fixed DNp42 readout, game/first-action feedback, and durable audit ledger under one clock. The addendum's `future_event_owners` map assigns chemical/APL arrivals, boundary flips, delayed sensory changes, PAM pulse transitions, early flush, late prime, expiry, motor action, judgement, plastic update and ledger commit to continuation owners. It must implement the A2.1 committed-tick checkpoint cut and validate all owner states before restore. A2.1's historical `B2_design_sha256` remains the original B2 digest; the addendum is a separate effect/boundary identity and the resolved-config SHA belongs in `resolved_config_sha256`. No checkpoint may silently substitute the 5-ms historical default without this resolved digest.

At an exact timestamp, first finish integration of the preceding open interval. Then process B2's expiry/observation order, ascending-ID boundary flips, PAM and delayed-sensory current changes, source-ordered chemical/APL arrivals, the tick's simultaneous threshold/spike batch, γ4 update, fixed readout/key transition, game outcome/feedback, and ledger flush. A change at time `t` affects following positive time, not the interval that ended at `t`. A committed checkpoint is allowed only after all ledger entries for that tick are durable; every future queue record retains origin and stable sequence. The 1-ms tick quantizes spike *detection*, while source arrivals and boundary flips retain exact integer-microsecond time. A2.2 must measure/report that quantization before any biological timing claim.

## Stage result, verification and limits

**PASS under the proposed B2.1 criterion:** one versioned resolved config fixes all three missing laws; the source audit accounts for every induced pair; the static validation confirms B2 roster/mask/means/delays/tick compatibility and maps twelve future event kinds to checkpoint owners. The resolver checks pinned normalized source SHA-256, B1/B2 audit and runtime-mask digests. The receipt records the resolved config and addendum hashes. No neural or task outcome was used to select the new 5-ms current decay or waiting-law implementation.

This design pass does **not** upgrade A2.2/A2.3 from INCONCLUSIVE. The coupled runner, exact whole-run replay, frozen fresh-note replay, A3 independent first-action audit, A4 paired-control audit, B3 controllability and task learning remain untested. Original B2 evidence and its receipt are preserved.

## Sole next stage — resume A2.2 full coupled continuation

**Question:** Can a source-derived `MVP-C1` runner using this resolved config checkpoint and resume with bit-for-bit identical future neural, APL, PAM, first-action, judgement and audit ledgers? B2.1 makes one runner identifiable; exact continuation is now the most discriminating infrastructure test. **Intervention:** implement the full owner/queue integration, checkpoint at several committed cuts with pending chemical/APL arrival, sensory drive, early flush, late prime and boundary flip, then compare uninterrupted versus restored ledgers. **Controls:** same source/resolved hashes, observations, note schedule, seeds, fixed interfaces and state; a tampered identity must reject without mutation. **Primary endpoint:** every declared cut replays future ledger bytes and selected weights identically. **Secondary:** event-owner coverage, queue peaks, numerical finiteness and APL/boundary state hashes. **PASS** only if all cuts match; **FAIL** for a verified mismatch; **INCONCLUSIVE** if the full runner is still absent. Do not run B3, train, tune gains, change masks or treat a component fixture as a coupled pass. Save raw comparisons, report and status update, then stop. The active Branch A roadmap assigns **GPT-6.1 Sol / High** to A2.2; the user's lower-usage preference can be applied to a bounded implementation substep without changing its gate.

## Active-time accounting

B2.1 charged **9.5 minutes** of active stage time. [Ledger](figures/b2_1_candidate1_dynamics/budget_ledger.json). The B1/B2/B2.1 recorded subtotal is **37.2 minutes**. Candidate-specific A1.3 and A2 elapsed work has no comparable ledger, so the true remainder of the eight-hour Candidate 1 cap is **unknown** until that time is reconciled.
