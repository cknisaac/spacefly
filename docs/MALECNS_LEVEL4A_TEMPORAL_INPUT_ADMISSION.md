# MaleCNS Level 4A — task-free temporal-input admission

**Stage:** Level 4A  
**Protocol:** frozen before duration evaluation  
**Learning:** OFF  
**DAN teaching:** OFF

## Question

What is the shortest predeclared linear moving-note duration, under the frozen
Level 4 encoder, LIF/contact model, threshold, and readout, that produces KC
spiking and a usable non-action-everywhere MBON response?

## Fixed model and intervention

The only varied model input is the duration of the same single note moving
linearly from normalized `x=1.0` to `x=0.0`. Test exactly **100, 250, 500,
750, and 1,000 ms**. Each duration is an integer multiple of the inherited
1-ms LIF integration step.

Keep fixed the same 32 KCs, MBON05, Gaussian encoder (`σ=0.08`, peak
`1.2 mV-equivalent`), LIF/contact model, original weights, 21-position grid,
fixed action threshold, readout, and recorded Level 3B DAN identities. No DAN
is stimulated. Plasticity is disabled; no weights change. The note path and
input rule remain `x(t)=1-t/duration`, with the encoder receiving current
position only at each inherited integration tick.

For each duration, run the identical task-free presentation twice from fresh
resting state. Record per-tick MBON05 voltage with current position, the full
position-binned map, all KC spike times/IDs/counts, and action bins. Require
exact deterministic replay across those outputs.

## Frozen admission gates

A duration is admitted only if all four conditions pass:

1. At least one KC spike occurs.
2. A meaningful MBON response occurs: MBON05 maximum voltage exceeds the
   fixed action threshold in at least **three adjacent 0.05-wide position
   bins** (at least 0.10 normalized position span), with nonzero activity.
3. The naive baseline is not action everywhere: at least one position bin's
   MBON05 maximum voltage exceeds the fixed action threshold.
4. The repeated run exactly matches its first run for KC spike events/counts,
   per-tick position/MBON trace, position map, and action positions.

Select the shortest duration that passes all four gates. If none passes,
record FAIL and identify temporal drive/integration as the blocker. Do not
adjust the amplitude, threshold, LIF parameters, learning rate, encoder,
readout, path, or duration candidate list. Do not run learning or teaching.
After selecting a speed or reporting failure, stop.

## Frozen artifacts

- [Level 4A config](../configs/malecns_level4a_temporal_input_admission.json)
- [Level 4A runner](../src/project_b/malecns_continuous_position_learning/experiment_level4a_temporal_input_admission.py)
- Parent [Level 4 protocol](MALECNS_LEVEL4_MOVING_NOTE_PROTOCOL.md) and
  [Level 4 result](MALECNS_LEVEL4_MOVING_NOTE_RESULT.md)

## Recorded outcome

The five predeclared durations were tested twice each. **500 ms** was the
shortest duration to pass all gates: 30 KC spikes from 30 KCs, an MBON
response above threshold in 19 contiguous position bins, a baseline that was
not action everywhere, and exact replay. The 100- and 250-ms durations had no
KC spikes and action at every bin. The 750- and 1,000-ms durations also passed,
but were longer than necessary. The selected speed is frozen at **500 ms** in
[the admitted Level 4 config](../configs/malecns_level4_moving_note_admitted_500ms.json).
The full timecourses are in the [Level 4A result](MALECNS_LEVEL4A_TEMPORAL_INPUT_ADMISSION_RESULT.md)
and raw receipt. No learning or teaching was run; stop here.
