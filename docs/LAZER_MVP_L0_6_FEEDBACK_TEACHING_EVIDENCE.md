# One-lane lazer MVP L0.6 — feedback and teaching-rule evidence audit

**Stage:** L0.6 — evidence for an outcome- and timing-specific teaching rule  
**Status:** **INCONCLUSIVE; NO-GO for biological training under the frozen task contract**  
**Scope:** Read-only primary-literature audit; no simulation, rule implementation, weight change, or training

## Question and frozen model boundary

Does primary research justify converting the one-lane task's game outcomes into
teaching events for the frozen MaleCNS γ4 KC→MBON05 model, with timing and
polarity sufficient to learn the first key-down?

The tested route supplies only current visibility, lane, and position to the
policy. The game-side `GameFeedbackEvent` contains a judgement label and the
time that label becomes available; the evaluator separately retains the note
identity, scheduled time, first action, and signed timing error. No visual or
other sensory representation of the game judgement is connected to the fly
model. L0.4 established direct-intervention controllability only. L0.5
established event timing and field separation only. This audit does not reopen
the retired Branch B Candidate 1 decision or start the separately proposed
Branch B B6.2 work.

## Primary-study findings

| Primary study | Direct result relevant here | Transfer limit for this task |
|---|---|---|
| [Handler et al. (2019), *Cell*](https://pmc.ncbi.nlm.nih.gov/articles/PMC9012144/) | In an olfactory-learning task and γ4 preparation, temporal order between KC and broad γ4–5 PAM-DAN activation changed KC-evoked γ4 MBON responses in opposite directions. The tested significant ISIs included DAN-before-KC (−1.2 s), coincidence (0 s), and KC-before-DAN (+0.5 s). DopR1- and DopR2-associated pathways contributed oppositely. | Supports a temporal-order plasticity family in a related compartment. It does not test this 32-KC MaleCNS subset, the exact 25 PAM08_L bodies as a sufficient teacher, action-outcome learning, game judgements, or a ±73.5-ms task window. The experimental manipulation is a broad γ4–5 driver; the synaptic readout is a calcium response. |
| [Vogt et al. (2014), *eLife*](https://elifesciences.org/articles/02395) | Flies learned appetitive and aversive color associations; dopamine neurons and KC output were required in the reported visual-conditioning designs. | Supports visual associative learning in some tasks. The study used color paired with sucrose or electric shock, and noted that the visual input route to KCs was not identified. It does not show that flies perceive osu! judgement text, score sounds, or a moving-note coordinate through this model's direct KC injection. |
| [Wiggin et al. (2021), *Frontiers in Behavioral Neuroscience*](https://doi.org/10.3389/fnbeh.2021.681593) | A Y-track study reports turn-contingent sucrose operant learning under particular rest and task conditions. | Demonstrates that action-contingent learning can be studied in flies, but does not establish the γ4 KC→MBON05/PAM08 circuit as the locus or provide feedback rules for first-action timing. The paper discusses other potential navigation/action-plasticity loci, including central-complex circuits. |
| [Dylla et al. (2017), *Frontiers in Neural Circuits*](https://pmc.ncbi.nlm.nih.gov/articles/PMC5476701/) | In olfactory trace conditioning, DAN responses changed with learning, but the authors found no evidence for DAN reward-prediction-error coding in that experiment. | Does not rule out prediction-error-like signals in every fly circuit or task. It does show that a generic global RPE rule cannot be inferred from the mere involvement of dopamine in fly learning. |
| [Senapati et al. (2021), *Nature Communications*](https://pmc.ncbi.nlm.nih.gov/articles/PMC7893153/) | Unexpected omission of a previously learned electric-shock punishment during an odor cue activated PAM-β′2a reward signaling in a circuit involving PPL1-γ2α′1, MBON-γ2α′1, and MBON-γ5β′2a. | Supports a specific learned-punishment-omission mechanism. It is not an unconditioned response to no key-down, uses different compartments and a multi-neuron relay, and does not establish that PAM08/γ4 treats an unobserved game miss as reward or punishment. |
| [Hattori et al. (2023), *Nature*](https://www.nature.com/articles/s41586-023-06671-8) | Artificial activation of a broad β′2-and-γ4 PAM population supported reward-seeking in the authors' olfactory assay. In that assay, the available γ4-only split driver did not produce the same detectable shock-resistant reward-seeking memory. | Makes a broad appetitive role for γ4 PAM activity plausible, while warning that γ4 alone may not carry the whole behavioral effect in that assay. It does not establish the selected MaleCNS PAM08 subset's sufficiency, or map a osu! grade to that activity. |

Together, these studies support general visual and olfactory associative learning,
temporal-order plasticity in γ4-related preparations, and several
reinforcement-dependent dopamine roles. They do not supply the missing
task-specific bridge from a game event to activity of the selected teacher
population and then to an update that improves the first action.

## Outcome-specific evidence matrix

| Frozen task outcome | What the headless game/model exposes | Research support for the required teaching interpretation | Audit result |
|---|---|---|---|
| First down in the Good-or-better window | Evaluator compares first-down time with hidden note time; game emits a judgement label. The policy sensory input has no score cue. | No reviewed primary study maps an osu!-like success grade to PAM08 activity or a positive event at this exact circuit. | **Unsupported task mapping.** Treating a score grade as biological reward would be an engineering assumption. |
| Early or late judged press, including a judged MISS | A judgement label and availability timestamp; signed error and scheduled note time remain evaluator-only. | Handler supports order-sensitive KC/DAN plasticity, not an early/late classification against an external beatmap clock or a learned target action time. | **Insufficient for polarity or credit.** A temporal-order mechanism alone does not identify which game outcomes should produce which event. |
| Too-early null press | No judgement event at the null press. The first action is retained only in the evaluator audit. | No direct evidence that the selected circuit receives a motor copy of this key command or a sensory signal that it was too early. | **No immediate teaching signal is justified.** |
| No down followed by automatic expiry | The headless engine emits MISS at expiry. The same feedback record is produced by no press and by a too-early null followed by expiry. | Senapati et al. support omission of an expected punishment after prior cue learning in a different circuit. They do not support interpreting no key action as a learned positive or negative outcome here. | **Unresolved observability and valence.** The evaluator distinguishes histories; the feedback event and fly policy do not. |
| Retry after a null or judged first press | The game can later emit a judgement for a retry; the evaluator preserves first-action failure. The event has no note ID or action-history field. | No reviewed study establishes first-action-specific motor credit or a biological representation matching the evaluator's “first down” metric. | **First-action credit remains an engineering objective.** The final game judgement can fail to describe the first action. |
| ±73.5 ms Good boundary | Hidden evaluation threshold derived from the pinned OD8 game profile. | Handler's sampled significant intervals include hundreds of milliseconds to 1.2 seconds; they do not measure a 73.5-ms eligibility kernel. | **Not a biological timing constant.** The game threshold must remain a task metric, not a claimed fly plasticity window. |

## Missing links and interpretation

The current path lacks evidence for all four elements needed before training:

1. **Observable outcome:** the fly sensory input contains no judgement display,
   sound, or other encoded game result. L0.5's feedback cursor is an
   engineering interface; the evaluator's hidden timing record must not be
   used as a biological input.
2. **Outcome meaning:** `PERFECT`, `OK`, and `MISS` are software labels, not
   measured reinforcers for this circuit. In particular, a missing action is
   not itself evidence of an aversive event, and an automatic MISS cannot be
   presumed equivalent to a consequence the fly sensed.
3. **Cell- and compartment-specific teaching:** Handler et al. used broader
   γ4–5 PAM populations. Transfer to the chosen MaleCNS PAM08 cells is
   **INFERRED**; the exact subset's response to game-like success, error, or
   omission is unmeasured. Hattori et al. further show that reward effects can
   depend on activating a broader β′2+γ4 ensemble in their task.
4. **Action-specific credit and timing:** none of the audited studies supplies
   a rule that assigns credit to the first of several key-downs or converts the
   game's ±73.5-ms objective into KC eligibility, dopamine timing, and a
   justified synaptic direction at this MaleCNS mask. The proposed traces and
   global reward-prediction code therefore remain model assumptions, not a
   literature-derived teaching rule.

By the L0.6 predeclared criterion, PASS requires primary evidence for each
rule component needed by this task and a falsifiable outcome mapping. That
criterion is not met. **L0.6 is INCONCLUSIVE and the biological training route
is NO-GO under the frozen task contract.** This does not show that flies cannot
learn action timing; it shows that the available evidence does not justify
this model's particular feedback-to-teacher rule. Do not implement a teacher
or train by assigning convenient reward signs to the software labels.

## Stop and next proposal

No teacher, DAN events, weight updates, simulation, or training followed this
audit. L0.7 and L0.8 remain held. The separate Branch B B6/B6.1 decisions are
unchanged; this report neither starts B6.2 nor admits a new learning
candidate.

**Sole next proposed stage: L0.9a — pinned osu!lazer runtime parity corpus.**
This is an independent software track toward the user's headless-game goal and
does not clear the biological learning no-go. Compare the source-derived
Python tap-note event stream against a small executable harness pinned to
`2026.1001.0-tachyon` / `da27300fcbfa246f87c3ba1a14cbd00b68c7e9a9`. Freeze
OD8 timing boundaries, early-MISS versus null, late expiry ordering, same-time
actions, same-lane note priority, and independent-lane chords. Primary gate:
zero judgement or event-order mismatches across the frozen corpus. Do not add
holds, mods, total-score rules, or train a fly policy in that stage. The local
environment currently has no `dotnet` executable, so the reference-runner
approach and any SDK setup must be resolved before executing L0.9a.
