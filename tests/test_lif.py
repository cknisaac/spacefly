"""Analytical proof of constant-drive rise, threshold, reset, and refractory."""

import math
import unittest

from project_b.neurons import LIFParameters, advance_lif
from project_b.simulation import SpikingSimulator
from project_b.synapses import SparseGraph


class LIFTests(unittest.TestCase):
    def test_constant_drive_matches_closed_form_until_threshold(self) -> None:
        parameters = LIFParameters(refractory_us=3_000)
        simulator = SpikingSimulator([parameters], SparseGraph(1, []), [2.0],
                                     record_neurons=[0], record_spikes=True)
        result = simulator.run_until(30_000)
        samples = {sample.time_us: sample for sample in result.voltage_trace}
        for time_us in range(1_000, 7_000, 1_000):
            expected_mv = 2.0 * (1.0 - math.exp(-time_us / 10_000))
            with self.subTest(time_us=time_us):
                self.assertAlmostEqual(samples[time_us].voltage_before_reset_mv,
                                       expected_mv, places=12)
                self.assertFalse(samples[time_us].spiked)
        self.assertEqual([(spike.time_us, spike.neuron_index) for spike in result.spikes],
                         [(7_000, 0), (17_000, 0), (27_000, 0)])
        self.assertGreaterEqual(samples[7_000].voltage_before_reset_mv,
                                parameters.v_threshold_mv)
        self.assertEqual(samples[7_000].voltage_after_reset_mv,
                         parameters.v_reset_mv)
        self.assertTrue(samples[7_000].spiked)

    def test_refractory_clamps_voltage_and_blocks_spikes(self) -> None:
        parameters = LIFParameters(refractory_us=3_000)
        simulator = SpikingSimulator([parameters], SparseGraph(1, []), [2.0],
                                     record_neurons=[0], record_spikes=True)
        result = simulator.run_until(18_000)
        samples = {sample.time_us: sample for sample in result.voltage_trace}
        for time_us in (8_000, 9_000, 10_000):
            with self.subTest(time_us=time_us):
                self.assertEqual(samples[time_us].voltage_after_reset_mv, 0.0)
                self.assertFalse(samples[time_us].spiked)
        self.assertGreater(samples[11_000].voltage_after_reset_mv, 0.0)
        self.assertEqual(result.refractory_until_us, (20_000,))

    def test_strong_drive_respects_exact_refractory_ticks(self) -> None:
        simulator = SpikingSimulator([LIFParameters(refractory_us=3_000)],
                                     SparseGraph(1, []), [20.0], record_spikes=True)
        result = simulator.run_until(12_000)
        self.assertEqual([spike.time_us for spike in result.spikes],
                         [1_000, 5_000, 9_000])
        self.assertEqual(result.spike_counts, (3,))

    def test_off_grid_refractory_end_resumes_partial_step_integration(self) -> None:
        parameters = LIFParameters(refractory_us=2_500)
        simulator = SpikingSimulator([parameters], SparseGraph(1, []), [20.0],
                                     record_neurons=[0], record_spikes=True)
        result = simulator.run_until(5_000)
        samples = {sample.time_us: sample for sample in result.voltage_trace}
        self.assertEqual([spike.time_us for spike in result.spikes], [1_000, 5_000])
        self.assertEqual(samples[3_000].voltage_after_reset_mv, 0.0)
        self.assertAlmostEqual(samples[4_000].voltage_before_reset_mv,
                               20.0 * (1.0 - math.exp(-500 / 10_000)), places=12)

    def test_no_drive_remains_quiet(self) -> None:
        simulator = SpikingSimulator([LIFParameters()], SparseGraph(1, []), [0.0],
                                     record_spikes=True)
        result = simulator.run_until(100_000)
        self.assertEqual(result.spikes, ())
        self.assertEqual(result.voltage_mv, (0.0,))

    def test_synaptic_decay_and_equal_time_constants(self) -> None:
        parameters = LIFParameters(tau_m_us=5_000, tau_syn_us=5_000)
        voltage, synaptic = advance_lif(0.0, 4.0, 0.0, 1_000, parameters)
        self.assertAlmostEqual(synaptic, 4.0 * math.exp(-0.2), places=12)
        self.assertAlmostEqual(voltage, 4.0 * 0.2 * math.exp(-0.2), places=12)
        self.assertEqual(advance_lif(0.3, 2.0, 1.0, 0, parameters), (0.3, 2.0))

    def test_invalid_lif_parameters_and_step(self) -> None:
        for kwargs in ({"tau_m_us": 0}, {"tau_syn_us": -1},
                       {"refractory_us": -1}, {"v_threshold_mv": 0.0},
                       {"v_rest_mv": float("nan")}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                LIFParameters(**kwargs)
        with self.assertRaises(ValueError):
            advance_lif(0.0, 0.0, 1.0, -1, LIFParameters())


if __name__ == "__main__":
    unittest.main()
