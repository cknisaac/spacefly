"""Translate trial-relative fly events onto the headless game's absolute clock."""

from __future__ import annotations

from project_b.simulation import SpikeEvent


def absolute_kc_spikes(spikes: tuple[SpikeEvent, ...], *,
                       trial_start_us: int) -> tuple[SpikeEvent, ...]:
    """Move recorded fly spikes to game time without changing source indices.

    ENGINEERING ASSUMPTION boundary: the fly's local zero is the first visible
    frame. The game and DAN adapter use absolute integer microseconds.
    """
    if type(trial_start_us) is not int or trial_start_us < 0:
        raise ValueError("trial_start_us must be a nonnegative integer")
    return tuple(SpikeEvent(spike.time_us + trial_start_us,
                            spike.neuron_index, spike.voltage_before_reset_mv)
                 for spike in spikes)
