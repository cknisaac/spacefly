# Synthetic lane-one closed loop

This is a **fake-brain engineering fixture**, with no imported fly connectome. Its purpose is to exercise the full causal chain on a slow, generated osu!mania map:

```text
lane-one note → artificial time-to-contact sensory population
              → sparse 128-cell spiking network
              → fixed motor-population readout
              → D = key-down/key-up decision
              → real headless osu judgement
              → centered utility → expected utility/RPE
              → synthetic dopamine-like modulation
              → eligibility-gated selected-edge weight update
```

`D` in the pre-judgement part of this diagram means the **motor decision**, not dopamine. Lane one in human numbering is zero-based game lane `0`. The game alone assigns MAX/300/200/100/50/MISS. A null press produces no judgement and therefore no RPE event.

## Circuit and interfaces

The default 128-neuron circuit has 40 sensory neurons, 40 relay neurons, 32 motor neurons and 16 inhibitory neurons. Its immutable synthetic graph has 584 directed edges, including 480 explicitly masked plastic relay→motor edges. At 500 neurons the same builder uses sparse arrays for 3,023 edges; no neuron-pair matrix is allocated. All edge signs, weights and delays are **engineered fixture values**, not anatomical observations.

The artificial encoder gives four overlapping Gaussian-tuned sensory cells for each preferred time-to-contact of 500, 400, 300, 200, 150, 100, 75, 50, 25 and 0 ms. It sees only the next unresolved lane-one note while that note is visible (500 ms before to 100 ms after its timestamp). The drive changes smoothly with time; it contains no binary “press now” channel, target key answer or future judgement. The sensory cells spike, fixed sensory→relay edges propagate those spikes, and only relay→motor edges learn. Motor→inhibitory→motor edges supply fixed feedback suppression.

The fixed motor readout counts motor-population spikes over the preceding 20 ms and presses lane one at six or more spikes. It releases after activity falls or 30 ms elapses and enforces a 200 ms cooldown. This mapping has no trainable weights. During training only, a seeded, broad cue-gated exploratory pulse can stimulate the motor population; its chance is drawn on every global tick for matched-seed controls, and it is not scheduled at the note's desired press time. The pulse is an explicit artificial exploration overlay. It is off during frozen evaluation.

## Event order and feedback

At each 1 ms neural tick, the encoder sets the drive for the next interval, the spiking simulator advances, and the fixed readout inspects the current motor spike batch. The game processes any note expiry before a same-tick key action. A new game judgement then enters the independent utility/RPE pipeline; its synthetic dopamine-like amplitude is delivered to `ThreeFactorPlasticity` after that tick's spikes. An automatic MISS may have an off-grid game timestamp; its actual modulation delivery is at the next neural tick, less than 1 ms later. Both timestamps and every selected-edge weight change are logged. Pending synaptic arrivals retain the weight captured when their presynaptic spike was emitted.

Training uses `Δw = η e D` only on the plastic mask. The declared demo has 16 notes at 1 s intervals, with the first at 800 ms. The first eight permit exploration and weight updates. The last eight have neither exploration nor updates, so their keypresses must come from current network state and learned weights. The no-plasticity control uses the same seed, map and tickwise random stream. `TinyLaneSession` can round-trip its complete state midway through a map using **trusted, same-version, in-process** checkpoint bytes; untrusted checkpoint loading and a durable cross-version format are outside this fixture.

Run from the project root:

```powershell
$env:PYTHONPATH = (Resolve-Path 'src').Path
python scripts/demo_m2.py --config configs/m2_tiny.yaml
python -m unittest discover -s tests -q
```

The script writes [the event and weight ledger](figures/m2_tiny_run.json), including config, seed, population counts, key decisions, judgements, utility, expected utility, RPE, modulation generation/delivery times and per-edge changes. In the declared seed-1 example, training produces 5/8 judged hits. Frozen evaluation produces 8/8 **OK** hits, each 76 ms early, versus 0/8 frozen hits in the plasticity-off control. This shows a functioning closed loop and retained response, **not precise timing or robust learning**: a checked seed-5 run produces 0/8 frozen hits. A later [16-seed on/off/shuffled-reward checkpoint](CHECKPOINT_CONTROLS.md) found a mean benefit but failed its declared across-seed reliability gate; timing remained early and randomized-map transfer is untested. No result here is evidence about a fly circuit.
