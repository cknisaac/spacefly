# Learning in a fly connectome: a research prototype

This project asks whether a small circuit chosen from a fruit-fly wiring diagram can change its response after a teaching signal. It combines a real **MaleCNS v1.0** map of which cells contact which, a computer model of electrical activity, and explicitly designed rules for input, teaching, learning, and output.

**Current result:** the final moving-note experiment, Level 4D, is frozen. Teaching at the wrong region produced a first action at position **x=0.20** that persisted when teaching and learning were switched off. Teaching at the intended target near **x=0.70** produced no action. The naive model and a matched teaching-on/learning-off control produced no action. The declared behavioral test therefore **failed**, while the intended anatomy-dependent learning mechanism operated. We record the branch as **“Mechanistic success / behavioral robustness incomplete.”** See the [full claim and limits](../../docs/MALECNS_MOVING_LEARNING_BRANCH_FREEZE.md).

## What the model does, in ordinary terms

A *connectome* is a map of connections between nerve cells. Here, 32 selected Kenyon cells (KCs) feed a mushroom-body output cell called MBON05. A simulated note travels across a one-dimensional position from 1 to 0. A fixed input rule makes different KCs respond at different positions. During training, an external event stimulates three anatomy-selected dopamine neurons (DANs). If an active KC has a mapped route to an active DAN, the model can weaken that KC's connection to MBON05. A fixed rule turns MBON05 activity into an action event.

```text
moving note → fixed position encoder → KC spikes → KC→MBON05 connections
                                               ↑            ↓
external teaching event → selected DAN spikes → local learning gate
                                                            ↓
                                               MBON05 response → fixed action event
```

The cell IDs and contact relationships come from the connectome. The position encoder, simulated voltage scale, dopamine stimulation, plasticity formula, and action rule are **engineering assumptions**. This experiment does not simulate a whole fly or establish that a fly would perform the task. Level 4D does not send a physical keyboard press or receive an osu! judgment.

## Explore the work

- [Current status](../../docs/project-status.md): what passed, what failed, and what is frozen.
- [Experiment results](../../results/index.md): each major stage's declared result and interpretation.
- [Level 4D playback](../../visualization/malecns-level4d-playback.html): download or open the HTML locally to scrub a saved moving note, neural events, weights, voltage, and output. The training and frozen-evaluation traces are separate recorded phases.
- [Documentation guide](../../docs/index.md): the infrastructure, synthetic, pathway, larval, and internal-learning tracks.
- [Research guide](../../research/index.md): source evidence, candidate notes, and unresolved questions.
- [Source data](../../data/README.md): official downloads, checksums, and the local-only data boundary.

The append-only [development log](../../CURRENT.md) and original stage reports preserve the chronology. Older Branch A/B and milestone labels are historical names; the [decision timeline](../../docs/history/timeline.md) explains the changes.

## Get started

Use Python **3.11 or newer**. From the repository root, create and activate a virtual environment, then install the package:

```text
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[connectome]"
python -m unittest discover -s tests
```

The import and some experiment tests require the source files described in the [data guide](../../data/README.md). The saved [compact Level 4D result](../../results/malecns-level4d/summary.md) and playback can be inspected without rerunning training. See [reproducibility](../../docs/reproducibility.md) for exact boundaries and commands.

## Repository map

| Path | Contents |
| --- | --- |
| `src/project_b/` | Simulator, connectome import, game fixture, and experiments |
| `configs/` | Frozen protocols and source selection |
| `tests/` | Deterministic checks |
| `docs/` | Scientific reports, plans, and guided indexes |
| `research/` | Guide to evidence and exploratory work |
| `results/` | Small published result bundles and artifact checksums |
| `visualization/` | Offline playback of recorded traces |
| `data/` and `runs/` | Local source data and full generated runs, excluded from normal Git history |

The Python package is still named `project_b` so existing scripts and frozen configurations keep working. A public software license and author citation will be added once their terms are chosen. The MaleCNS and larval connectome sources have their own provenance in the [data manifests](../../data/manifests/).
