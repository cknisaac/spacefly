# Implemented system at a glance

The repository contains several related systems. The later [EA-MVP engineering implementation](https://github.com/cknisaac/spacefly/tree/ea-mvp-engineering-assumption-fly-learner/src/project_b/ea_mvp) connects a reduced timing circuit to a headless game through explicit engineered interfaces; see its [training explainer](https://github.com/cknisaac/spacefly/blob/ea-mvp-engineering-assumption-fly-learner/docs/EA_MVP_FLY_TRAINING_EXPLAINER.md).

This page describes the earlier frozen MaleCNS Level 4D experiment retained on `main`. It uses a **reduced circuit**, not the complete connectome or the headless game loop:

```text
current note position → fixed Gaussian KC encoder → 32 modeled KC cells
                                                     ↓
                                   audited KC→MBON05 contact/weight slots
                                                     ↓
                                            modeled MBON05 voltage
                                                     ↓
                                fixed bin readout → action event

external teaching pulse → modeled PAM08 DANs → local eligibility × anatomical gate
                                                  ↓
                                      KC→MBON05 weight update
```

The anatomy-selected DAN IDs are 87177, 107285, and 55210. The moving note takes 500 ms. Only the KC→MBON05 slots selected by the frozen mask can change. The output is a modeled action event; this level has no physical keyboard key, trained decoder, game score, or biological motor neuron.

| Code area | Role |
| --- | --- |
| [`src/project_b/connectome/`](../src/project_b/connectome/) | Import and validate MaleCNS source anatomy |
| [`src/project_b/neurons/`](../src/project_b/neurons/) and [`simulation/`](../src/project_b/simulation/) | Explicit neural state and event timing |
| [`src/project_b/plasticity/`](../src/project_b/plasticity/) | Local learning primitives and weight limits |
| [`src/project_b/malecns_continuous_position_learning/`](../src/project_b/malecns_continuous_position_learning/) | The frozen position and moving-note experiments |
| [`src/project_b/osu/`](../src/project_b/osu/) | Separate headless game mechanics fixture |
| [`src/project_b/mvp_c1/`](../src/project_b/mvp_c1/) | Earlier candidate work retained for diagnosis |

Other studies test the game, a synthetic learning network, full-source import, electrical transfer, and larval candidates. Their roles and outcomes are in the [track guide](index.md). For detailed model definitions and biological caveats, see [MODEL.md](MODEL.md), [BIOLOGY.md](BIOLOGY.md), and the [assumptions register](../ASSUMPTIONS.md). [ARCHITECTURE.md](../ARCHITECTURE.md) preserves the earlier broader system plan and historical implementation notes.
