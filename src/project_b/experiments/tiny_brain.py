"""Single-lane synthetic closed loop; no fly connectome or trainable decoder."""

from __future__ import annotations

import math
import pickle
import random
from dataclasses import dataclass

from project_b.motor import FixedMotorReadout, MotorDecision
from project_b.neuromodulation import (
    RPEModulator, ReinforcementEvent, ReinforcementPipeline,
)
from project_b.neurons import LIFParameters
from project_b.osu import GameEnvironment, JudgementRecord, TapNote
from project_b.plasticity import PlasticityParameters, ThreeFactorPlasticity, WeightChange
from project_b.sensory import TimeToContactEncoder
from project_b.simulation import SpikingSimulator
from project_b.synapses import SparseGraph, Synapse
from project_b.utils.time import require_time_us


@dataclass(frozen=True, slots=True)
class TinyBrainConfig:
    neuron_count: int = 128
    note_count: int = 8
    first_note_us: int = 800_000
    note_interval_us: int = 1_000_000
    explicit_note_times_us: tuple[int, ...] | None = None
    cue_gain_by_note: tuple[float, ...] | None = None
    dt_us: int = 1_000
    seed: int = 1
    exploration_probability: float = 0.002
    readout_on_threshold: int = 6
    readout_window_us: int = 20_000
    plasticity_enabled: bool = True
    modulation_gain: float = 1.0
    plasticity_eta: float = 0.2
    training_notes: int | None = None
    # Offline yoked control: one prerecorded utility per training judgement.
    reward_utility_schedule: tuple[float, ...] | None = None
    max_pending_arrivals: int = 100_000

    def __post_init__(self) -> None:
        if type(self.neuron_count) is not int or not 100 <= self.neuron_count <= 500:
            raise ValueError("neuron_count must be between 100 and 500")
        if type(self.note_count) is not int or self.note_count <= 0:
            raise ValueError("note_count must be positive")
        if (self.training_notes is not None
                and (type(self.training_notes) is not int
                     or not 0 <= self.training_notes <= self.note_count)):
            raise ValueError("training_notes must lie in 0..note_count")
        training_count = self.note_count if self.training_notes is None else self.training_notes
        if self.reward_utility_schedule is not None:
            if (type(self.reward_utility_schedule) is not tuple
                    or len(self.reward_utility_schedule) != training_count):
                raise ValueError("reward_utility_schedule must have one value per training note")
            if any(type(value) not in (int, float) or not math.isfinite(value)
                   or not -1 <= value <= 1
                   for value in self.reward_utility_schedule):
                raise ValueError("reward_utility_schedule values must be finite in [-1, 1]")
        for name in ("first_note_us", "note_interval_us", "dt_us"):
            if require_time_us(getattr(self, name), name) <= 0:
                raise ValueError(f"{name} must be positive")
        if self.first_note_us % self.dt_us or self.note_interval_us % self.dt_us:
            raise ValueError("note times must align with the neural tick")
        if self.note_interval_us < 700_000:
            raise ValueError("notes must be at least 700 ms apart in this slow fixture")
        if self.explicit_note_times_us is not None:
            times = self.explicit_note_times_us
            if type(times) is not tuple or len(times) != self.note_count:
                raise ValueError("explicit_note_times_us must match note_count")
            if any(require_time_us(t, "explicit_note_times_us") <= 0
                   or t % self.dt_us for t in times):
                raise ValueError("explicit note times must be positive neural ticks")
            if times[0] < 500_000 or any(b - a < 700_000
                                           for a, b in zip(times, times[1:])):
                raise ValueError("explicit notes must start after 500 ms and stay >=700 ms apart")
        if self.cue_gain_by_note is not None:
            if (type(self.cue_gain_by_note) is not tuple
                    or len(self.cue_gain_by_note) != self.note_count
                    or any(type(gain) not in (int, float) or not math.isfinite(gain)
                           or not 0.5 <= gain <= 1.5
                           for gain in self.cue_gain_by_note)):
                raise ValueError("cue_gain_by_note must have finite values in [0.5, 1.5]")
        if type(self.seed) is not int:
            raise ValueError("seed must be an integer")
        if type(self.max_pending_arrivals) is not int or self.max_pending_arrivals <= 0:
            raise ValueError("max_pending_arrivals must be positive")
        if (type(self.exploration_probability) not in (int, float)
                or not math.isfinite(self.exploration_probability)
                or not 0 <= self.exploration_probability <= 1):
            raise ValueError("exploration_probability must lie in [0, 1]")
        if type(self.readout_on_threshold) is not int or self.readout_on_threshold < 2:
            raise ValueError("readout_on_threshold must be an integer >=2")
        if require_time_us(self.readout_window_us, "readout_window_us") <= 0:
            raise ValueError("readout_window_us must be positive")
        if (type(self.modulation_gain) not in (int, float)
                or not math.isfinite(self.modulation_gain)
                or self.modulation_gain < 0):
            raise ValueError("modulation_gain must be finite and nonnegative")
        if (type(self.plasticity_eta) not in (int, float)
                or not math.isfinite(self.plasticity_eta)
                or self.plasticity_eta <= 0):
            raise ValueError("plasticity_eta must be finite and positive")


@dataclass(frozen=True, slots=True)
class TinyBrainLayout:
    graph: SparseGraph
    parameters: tuple[LIFParameters, ...]
    sensory: tuple[int, ...]
    relay: tuple[int, ...]
    motor: tuple[int, ...]
    inhibitory: tuple[int, ...]
    plastic_slots: tuple[int, ...]


def build_tiny_brain(config: TinyBrainConfig,
                     encoder: TimeToContactEncoder | None = None) -> TinyBrainLayout:
    """Build a deterministic sparse 100–500-cell synthetic circuit."""
    encoder = encoder if encoder is not None else TimeToContactEncoder()
    sensory_count = encoder.neuron_count
    if sensory_count != 40:
        raise ValueError("this fixture requires the 40-cell lane-one encoder")
    remaining = config.neuron_count - sensory_count
    relay_count = max(30, round(remaining * 0.45))
    motor_count = max(16, round(remaining * 0.36))
    inhibitory_count = remaining - relay_count - motor_count
    if inhibitory_count <= 0:
        raise ValueError("not enough neurons for the inhibitory population")
    sensory = tuple(range(sensory_count))
    relay = tuple(range(sensory_count, sensory_count + relay_count))
    motor = tuple(range(relay[-1] + 1, relay[-1] + 1 + motor_count))
    inhibitory = tuple(range(motor[-1] + 1, config.neuron_count))
    edges: list[Synapse] = []
    targets_per_bin = min(12, motor_count)
    for index, cell in enumerate(relay):
        sensory_index = min(sensory_count - 1, index * sensory_count // relay_count)
        edges.append(Synapse(sensory[sensory_index], cell, 8.0, 2_000))
        bin_index = sensory_index // encoder.replicas
        targets = (motor[(bin_index * 7 + offset) % motor_count]
                   for offset in range(targets_per_bin))
        for target in targets:
            edges.append(Synapse(cell, target, 0.04, 2_000))
    for index, cell in enumerate(motor):
        edges.append(Synapse(cell, inhibitory[index % inhibitory_count],
                             8.0, 2_000))
    for index, cell in enumerate(inhibitory):
        for motor_index in range(index, motor_count, inhibitory_count):
            edges.append(Synapse(cell, motor[motor_index], -2.0, 2_000))
    graph = SparseGraph(config.neuron_count, edges)
    relay_set, motor_set = set(relay), set(motor)
    plastic_slots = tuple(
        slot for slot in range(graph.edge_count)
        if graph.pre_indices[slot] in relay_set
        and graph.post_indices[slot] in motor_set)
    parameters = tuple(
        LIFParameters(refractory_us=(20_000 if i in motor_set else 10_000))
        for i in range(config.neuron_count))
    return TinyBrainLayout(graph, parameters, sensory, relay, motor,
                           inhibitory, plastic_slots)


@dataclass(frozen=True, slots=True)
class FeedbackDelivery:
    reinforcement: ReinforcementEvent
    delivered_time_us: int
    weight_changes: tuple[WeightChange, ...]


@dataclass(frozen=True, slots=True)
class ClosedLoopResult:
    config: TinyBrainConfig
    note_times_us: tuple[int, ...]
    graph_edge_count: int
    plastic_edge_count: int
    sensory_spikes: int
    relay_spikes: int
    motor_spikes: int
    inhibitory_spikes: int
    exploration_pulses: tuple[int, ...]
    decisions: tuple[MotorDecision, ...]
    judgements: tuple[JudgementRecord, ...]
    feedback: tuple[FeedbackDelivery, ...]
    final_plastic_weights_mv: tuple[float, ...]
    initial_plastic_weights_mv: tuple[float, ...]
    peak_queued_arrivals: int


class TinyLaneSession:
    """Deterministic coupled state, including a trusted in-process checkpoint."""

    def __init__(self, config: TinyBrainConfig = TinyBrainConfig()) -> None:
        self.config = config
        self.encoder = TimeToContactEncoder()
        self.layout = build_tiny_brain(config, self.encoder)
        self.plasticity = ThreeFactorPlasticity(
            self.layout.graph, self.layout.plastic_slots,
            PlasticityParameters(config.plasticity_eta, 80_000, 150_000, 0.0, 2.0))
        self.simulator = SpikingSimulator(
            self.layout.parameters, self.layout.graph, [0.0] * config.neuron_count,
            dt_us=config.dt_us, plasticity=self.plasticity)
        self.readout = FixedMotorReadout(
            self.layout.motor, window_us=config.readout_window_us,
            on_threshold=config.readout_on_threshold)
        self.reward = ReinforcementPipeline(
            modulator=RPEModulator(gain=config.modulation_gain))
        self.note_times_us = (config.explicit_note_times_us
                              if config.explicit_note_times_us is not None
                              else tuple(config.first_note_us + n * config.note_interval_us
                                         for n in range(config.note_count)))
        self.notes = tuple(TapNote(f"lane1-{n}", 0, time_us)
                           for n, time_us in enumerate(self.note_times_us))
        self.game = GameEnvironment(self.notes)
        self.rng = random.Random(config.seed)
        self.training_notes = (config.note_count if config.training_notes is None
                               else config.training_notes)
        self.initial_weights = tuple(
            self.plasticity.effective_weight(slot)
            for slot in self.layout.plastic_slots)
        self.decisions: list[MotorDecision] = []
        self.feedback: list[FeedbackDelivery] = []
        self.exploration_pulses: list[int] = []
        self.resolved_count = 0
        self.next_note = 0
        self.spike_counts = [0, 0, 0, 0]
        self.population_sets = tuple(map(set, (
            self.layout.sensory, self.layout.relay,
            self.layout.motor, self.layout.inhibitory)))
        self.peak_queue = 0
        last_expiry_us = self.note_times_us[-1] + self.game.windows.expiry_offset_us
        self.end_us = ((last_expiry_us + config.dt_us - 1)
                       // config.dt_us) * config.dt_us

    def step(self) -> None:
        """Run one tick; expiry precedes actions, feedback follows judgement."""
        if self.simulator.current_time_us >= self.end_us:
            raise ValueError("the map has already finished")
        start_us = self.simulator.current_time_us
        while self.next_note < len(self.notes) and self.next_note < self.resolved_count:
            self.next_note += 1
        next_time = (self.notes[self.next_note].time_us
                     if self.next_note < len(self.notes) else None)
        sensory_drive = self.encoder.encode(start_us, next_time)
        if next_time is not None and self.config.cue_gain_by_note is not None:
            sensory_drive = tuple(value * self.config.cue_gain_by_note[self.next_note]
                                  for value in sensory_drive)
        drive = [0.0] * self.config.neuron_count
        drive[:self.encoder.neuron_count] = sensory_drive
        visible = any(value > 0.1 for value in sensory_drive)
        # Draw on every global tick so matched seeds stay aligned even when
        # learned behavior resolves a note earlier in one run.
        in_training = self.resolved_count < self.training_notes
        if (self.rng.random() < self.config.exploration_probability
                and visible and in_training):
            self.exploration_pulses.append(start_us)
            for cell in self.layout.motor:
                drive[cell] = 20.0
        self.simulator.set_external_drive_mv(drive)
        tick_us = start_us + self.config.dt_us
        self.simulator.run_until(tick_us)
        queued = self.simulator.snapshot().queued_arrivals
        self.peak_queue = max(self.peak_queue, queued)
        if queued > self.config.max_pending_arrivals:
            raise ArithmeticError("synaptic arrival queue exceeded configured limit")
        spiking = tuple(i for i, yes in enumerate(self.simulator.spiked_this_tick) if yes)
        for population_index, population in enumerate(self.population_sets):
            self.spike_counts[population_index] += sum(i in population for i in spiking)
        self.game.advance_to(tick_us)
        decision = self.readout.observe(tick_us, spiking)
        if decision is not None:
            self.decisions.append(decision)
            self.game.apply_action(decision.action)
        newly_judged = self.game.result().judgements[self.resolved_count:]
        for offset, judgement in enumerate(newly_judged):
            index = self.resolved_count + offset
            scheduled = self.config.reward_utility_schedule
            delivered = (scheduled[index] if scheduled is not None
                         and index < self.training_notes else None)
            event = self.reward.process_judgement(
                judgement, learning_utility=delivered)
            changes = (self.simulator.apply_dopamine(event.modulation.amplitude)
                       if self.config.plasticity_enabled
                       and index < self.training_notes else ())
            self.feedback.append(FeedbackDelivery(event, tick_us, changes))
        self.resolved_count += len(newly_judged)

    def run_until(self, end_us: int) -> None:
        require_time_us(end_us, "end_us")
        if (end_us < self.simulator.current_time_us or end_us > self.end_us
                or end_us % self.config.dt_us):
            raise ValueError("end_us must be an in-range future tick")
        while self.simulator.current_time_us < end_us:
            self.step()

    def run(self) -> ClosedLoopResult:
        self.run_until(self.end_us)
        result = self.game.result()
        if result.resolved_notes != self.config.note_count:
            raise AssertionError("synthetic map did not resolve every note")
        return ClosedLoopResult(
            self.config, self.note_times_us, self.layout.graph.edge_count,
            len(self.layout.plastic_slots), *self.spike_counts,
            tuple(self.exploration_pulses), tuple(self.decisions),
            result.judgements, tuple(self.feedback),
            tuple(self.plasticity.effective_weight(slot)
                  for slot in self.layout.plastic_slots),
            self.initial_weights, self.peak_queue)

    def checkpoint_bytes(self) -> bytes:
        """Serialize all coupled state for same-version, trusted replay only."""
        return pickle.dumps(self, protocol=5)

    @classmethod
    def from_trusted_checkpoint_bytes(cls, data: bytes) -> TinyLaneSession:
        """Restore only bytes produced by this process; never load untrusted data."""
        session = pickle.loads(data)
        if type(session) is not cls:
            raise ValueError("checkpoint does not contain a TinyLaneSession")
        return session


def run_tiny_lane_one(config: TinyBrainConfig = TinyBrainConfig()) -> ClosedLoopResult:
    """Run causal note → sensory → spikes → decision → game → RPE → weight loop."""
    return TinyLaneSession(config).run()
