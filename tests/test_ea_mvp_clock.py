"""Trial/game clock alignment for prospective variable-lead training."""

import unittest

from project_b.ea_mvp.clock import absolute_kc_spikes
from project_b.ea_mvp.local_learning import apply_local_teaching
from project_b.simulation import SpikeEvent


class ClockAlignmentTest(unittest.TestCase):
    def test_translation_preserves_spike_identity_and_offsets_time(self):
        spikes = (SpikeEvent(100_000, 0, 1.1), SpikeEvent(150_000, 1, 1.2))
        self.assertEqual(absolute_kc_spikes(spikes, trial_start_us=400_000),
                         (SpikeEvent(500_000, 0, 1.1), SpikeEvent(550_000, 1, 1.2)))
        with self.assertRaises(ValueError):
            absolute_kc_spikes(spikes, trial_start_us=-1)

    def test_local_update_is_invariant_to_trial_time_origin(self):
        kwargs = dict(weights=[1.0, 1.0], original_weights=[1.0, 1.0],
                      kc_source_ids=(1001, 1002), dan_coverage={9001: {1001, 1002}},
                      window_us=250_000, tau_us=1_000_000, eta=0.01,
                      minimum_fraction=0.2)
        relative = apply_local_teaching(
            **kwargs, spikes=(SpikeEvent(100_000, 0, 1.1), SpikeEvent(150_000, 1, 1.2)),
            dan_spikes={9001: (200_000,)})
        shifted = apply_local_teaching(
            **kwargs, spikes=absolute_kc_spikes(
                (SpikeEvent(100_000, 0, 1.1), SpikeEvent(150_000, 1, 1.2)),
                trial_start_us=400_000),
            dan_spikes={9001: (600_000,)})
        self.assertEqual(relative.weights_after, shifted.weights_after)
        self.assertEqual([row["edge_index"] for row in relative.changes],
                         [row["edge_index"] for row in shifted.changes])


if __name__ == "__main__":
    unittest.main()
