"""Current-position-only adapter from a moving note to the fixed KC→MBON MVP."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from project_b.malecns_continuous_position_learning.encoder import population_drive
from project_b.malecns_continuous_position_learning.online_readout import (
    OnlinePositionReadout,
)
from project_b.malecns_continuous_position_learning.probe import _lif
from project_b.neurons import LIFParameters
from project_b.osu.adapter import PolicyKeyTransition, PositionObservation
from project_b.osu.types import require_lane
from project_b.simulation import SpikingSimulator
from project_b.synapses import SparseGraph, Synapse


def load_position_config(root: Path, config_path: str) -> dict:
    """Read and minimally validate the frozen 32-KC→MBON05 source config."""
    path = Path(root) / config_path
    config = json.loads(path.read_text(encoding="utf-8"))
    cells = config["circuit"]["selected_kcs"]
    if len(cells) != 32 or config["circuit"]["mbon_source_id"] != 10495:
        raise ValueError("online position MVP requires the frozen 32-KC→MBON05 cohort")
    preferred = [cell["preferred_position"] for cell in cells]
    if (preferred != sorted(preferred) or len(set(preferred)) != len(preferred)
            or any(not 0.0 <= value <= 1.0 for value in preferred)):
        raise ValueError("KC preferred positions must be unique, ordered, and normalized")
    if sum(cell["plastic_contact_rows"] for cell in cells) <= 0:
        raise ValueError("KC→MBON05 contacts must have positive total weight")
    return config


class OnlineFlyPolicy:
    """Run the fixed fly-inspired position encoder one observation at a time.

    Game timing remains outside this class. Each observation is the current
    visible state only. The current observation sets drive for the *next*
    neural interval, while the MBON sample at this timestamp closes the
    interval driven by the previous observation.
    """

    def __init__(self, config: dict, *, lane: int = 0,
                 weights: list[float] | None = None,
                 position_bin_width: float = 0.05,
                 key_hold_us: int = 10_000) -> None:
        self.config = config
        self.cells = config["circuit"]["selected_kcs"]
        self.n_kc = len(self.cells)
        self.lane = require_lane(lane)
        total_contacts = sum(cell["plastic_contact_rows"] for cell in self.cells)
        initial = [cell["plastic_contact_rows"] / total_contacts
                   for cell in self.cells]
        self.weights = list(initial if weights is None else weights)
        if (len(self.weights) != self.n_kc
                or any(type(w) not in (int, float) or not math.isfinite(w) or w <= 0
                       for w in self.weights)):
            raise ValueError("weights must contain one positive finite value per selected KC")
        lif_config = config["overlay"]["lif"]
        self.dt_us = lif_config["dt_us"]
        if type(self.dt_us) is not int or self.dt_us <= 0:
            raise ValueError("overlay integration step must be a positive integer")
        self.sigma = config["encoder"]["sigma"]
        self.peak_drive_mv = config["encoder"]["peak_drive_mv"]
        self.threshold_mv = config["continuation"]["frozen_action_threshold_mv"]
        self.position_grid = list(config["evaluation"]["position_grid"])
        self.position_bin_width = position_bin_width
        self.key_hold_us = key_hold_us
        self._graph = SparseGraph(self.n_kc + 1, [
            Synapse(i, self.n_kc, self.weights[i],
                    config["overlay"]["synaptic_delay_us"])
            for i in range(self.n_kc)
        ])
        self._lif: LIFParameters = _lif(config)
        self._sim: SpikingSimulator | None = None
        self._readout: OnlinePositionReadout | None = None
        self._started = False
        self._finished = False
        self._time_us = 0

    def begin(self, observation: PositionObservation) -> None:
        """Start one note at simulation time zero with its first visible frame."""
        if self._started:
            raise RuntimeError("policy has already begun")
        if type(observation) is not PositionObservation or not observation.visible:
            raise ValueError("begin requires a visible PositionObservation")
        if observation.lane != self.lane:
            raise ValueError("observation lane differs from the configured output lane")
        assert observation.position is not None
        drive = list(population_drive(
            observation.position, self.cells, sigma=self.sigma,
            peak_drive_mv=self.peak_drive_mv)) + [0.0]
        self._sim = SpikingSimulator(
            [self._lif] * (self.n_kc + 1), self._graph, drive,
            dt_us=self.dt_us, record_neurons=[self.n_kc], record_spikes=True,
        )
        self._readout = OnlinePositionReadout(
            position_grid=self.position_grid,
            bin_width=self.position_bin_width,
            threshold_mv=self.threshold_mv,
            dt_us=self.dt_us,
            lane=self.lane,
            key_hold_us=self.key_hold_us,
            direction=-1,
        )
        self._readout.begin(self._time_us, observation.position)
        self._started = True

    def step(self, observation: PositionObservation) -> tuple[PolicyKeyTransition, ...]:
        """Consume the next frame and return newly available key transitions."""
        if not self._started or self._finished or self._sim is None or self._readout is None:
            raise RuntimeError("begin() must be called before step(), and finish() only once")
        if type(observation) is not PositionObservation:
            raise TypeError("observation must be a PositionObservation")
        if observation.lane != self.lane:
            raise ValueError("observation lane differs from the configured output lane")
        self._time_us += self.dt_us
        time_us = self._time_us

        snapshot = self._sim.run_until(time_us)
        voltage = snapshot.voltage_trace[-1].voltage_before_reset_mv
        actions = self._readout.step(
            time_us, observation.position if observation.visible else None, voltage)
        if observation.visible:
            assert observation.position is not None
            drive = list(population_drive(
                observation.position, self.cells, sigma=self.sigma,
                peak_drive_mv=self.peak_drive_mv)) + [0.0]
        else:
            drive = [0.0] * (self.n_kc + 1)
        self._sim.set_external_drive_mv(drive)
        return tuple(PolicyKeyTransition(action.time_us, action.lane, action.kind)
                     for action in actions)

    def finish(self) -> tuple[PolicyKeyTransition, ...]:
        """Close the final position bin and return any scheduled key release."""
        if not self._started or self._finished or self._sim is None or self._readout is None:
            raise RuntimeError("begin() must be called before finish(), exactly once")
        self._finished = True
        actions = self._readout.finish(self._sim.current_time_us)
        return tuple(PolicyKeyTransition(action.time_us, action.lane, action.kind)
                     for action in actions)

    def reproducibility_metadata(self) -> dict[str, object]:
        """Stable model, parameter, and weight identifiers for replay logs."""
        config_bytes = json.dumps(
            self.config, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
        weight_bytes = json.dumps(
            self.weights, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
        return {
            "policy_class": type(self).__qualname__,
            "config_sha256": hashlib.sha256(config_bytes).hexdigest(),
            "weight_vector_sha256": hashlib.sha256(weight_bytes).hexdigest(),
            "source_ids": [int(cell["source_id"]) for cell in self.cells],
            "lane": self.lane,
            "dt_us": self.dt_us,
            "position_bin_width": self.position_bin_width,
            "key_hold_us": self.key_hold_us,
        }

    @property
    def decisions(self):
        """Causal bin-decision ledger for test and run evidence."""
        if self._readout is None:
            return ()
        return self._readout.decisions

    @property
    def first_valid_time_us(self) -> int | None:
        return None if self._readout is None else self._readout.first_valid_time_us

    @property
    def simulator_state(self) -> dict | None:
        """Return a detached simulator checkpoint for reproducible run logs."""
        return None if self._sim is None else self._sim.state()

    @property
    def mbon_voltage_trace(self) -> tuple[tuple[int, float], ...]:
        """Recorded MBON pre-reset samples, including their simulator times."""
        if self._sim is None:
            return ()
        return tuple(
            (sample.time_us, sample.voltage_before_reset_mv)
            for sample in self._sim.snapshot().voltage_trace
            if sample.neuron_index == self.n_kc
        )
