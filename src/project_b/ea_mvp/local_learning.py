"""EA-MVP artificial DAN stimulation and contact-local KC→MBON LTD."""

from __future__ import annotations

from dataclasses import dataclass

from project_b.ea_mvp.teacher import DanPulse
from project_b.malecns_minimal_internal_learning.ltd import LocalLTD
from project_b.neurons import LIFParameters
from project_b.simulation import SpikeEvent, SpikingSimulator
from project_b.synapses import SparseGraph


@dataclass(frozen=True, slots=True)
class LocalTeachingResult:
    weights_before: tuple[float, ...]
    weights_after: tuple[float, ...]
    dan_spikes: tuple[tuple[int, tuple[int, ...]], ...]
    credited_kc_spikes: tuple[tuple[int, int], ...]
    changes: tuple[dict, ...]
    gate_time_us: int | None


def stimulate_dans(pulse: DanPulse | None, lif: LIFParameters, *,
                   dt_us: int, enabled: bool = True) -> dict[int, tuple[int, ...]]:
    """Stimulate named DANs independently; the source graph is unchanged."""
    if pulse is None:
        return {}
    if pulse.onset_us % dt_us or pulse.duration_us % dt_us:
        raise ValueError("DAN pulse must align with the integration tick")
    results = {}
    for source_id in pulse.dan_source_ids:
        sim = SpikingSimulator([lif], SparseGraph(1, []), [0.0],
                               dt_us=dt_us, record_neurons=[0], record_spikes=True)
        sim.run_until(pulse.onset_us)
        if enabled:
            sim.set_external_drive_mv([pulse.amplitude_mv_equivalent])
        sim.run_until(pulse.onset_us + pulse.duration_us)
        results[source_id] = tuple(spike.time_us for spike in sim.snapshot().spikes)
    return results


def apply_local_teaching(*, weights: list[float], original_weights: list[float],
                         kc_source_ids: tuple[int, ...], spikes: tuple[SpikeEvent, ...],
                         dan_spikes: dict[int, tuple[int, ...]],
                         dan_coverage: dict[int, set[int]],
                         window_us: int, tau_us: int, eta: float,
                         minimum_fraction: float,
                         plasticity_on: bool = True,
                         eligibility_on: bool = True) -> LocalTeachingResult:
    """Change only KC slots with recent spikes and a connected active DAN."""
    if len(weights) != len(original_weights) or len(weights) != len(kc_source_ids):
        raise ValueError("weights, originals and KC IDs must align")
    if len(set(kc_source_ids)) != len(kc_source_ids) or window_us <= 0:
        raise ValueError("KC IDs must be unique and eligibility window positive")
    gate_time = min((times[0] for times in dan_spikes.values() if times), default=None)
    active_dans = {source_id for source_id, times in dan_spikes.items() if times}
    covered = set().union(*(dan_coverage[source_id] for source_id in active_dans)) \
        if active_dans else set()
    slots = tuple(i for i, source_id in enumerate(kc_source_ids)
                  if source_id in covered) if plasticity_on else ()
    rule = LocalLTD(list(weights), original_weights=original_weights,
                    plastic_slots=slots, tau_us=tau_us, eta=eta,
                    minimum_fraction=minimum_fraction)
    credited = []
    if gate_time is not None and eligibility_on:
        for spike in spikes:
            if (spike.neuron_index < len(kc_source_ids)
                    and gate_time - window_us <= spike.time_us <= gate_time):
                rule.observe_kc_spike(spike.neuron_index, spike.time_us)
                credited.append((spike.time_us, kc_source_ids[spike.neuron_index]))
    changes = rule.teacher_pulse(gate_time, teacher=bool(active_dans and plasticity_on)) \
        if gate_time is not None else ()
    enriched = tuple({**change, "kc_source_id": kc_source_ids[change["edge_index"]],
                      "connected_active_dans": tuple(sorted(
                          source_id for source_id in active_dans
                          if kc_source_ids[change["edge_index"]] in dan_coverage[source_id]))}
                     for change in changes)
    return LocalTeachingResult(tuple(weights), tuple(rule.weights),
                               tuple(sorted(dan_spikes.items())), tuple(credited),
                               enriched, gate_time)
