import unittest
from pathlib import Path

from project_b.malecns_continuous_position_learning.lazer_capacity import (
    _load_inputs,
    _weights_for_condition,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = "configs/lazer_mvp_capacity.json"


class LazerCapacityContractTests(unittest.TestCase):
    def test_frozen_capacity_plan_hashes_and_conditions_validate(self):
        stage, candidate, refs = _load_inputs(ROOT, CONFIG)
        self.assertEqual(stage["status"], "frozen_before_capacity_run")
        self.assertEqual(refs["game"].ruleset, "lazer")
        self.assertEqual(refs["source_ids"], [
            int(cell["source_id"]) for cell in candidate["circuit"]["selected_kcs"]
        ])
        self.assertEqual(stage["intervention"]["maximum_local_ltd_fraction_of_original"],
                         0.2)

    def test_target_and_matched_control_change_only_frozen_kcs_to_floor(self):
        stage, candidate, _ = _load_inputs(ROOT, CONFIG)
        cells = candidate["circuit"]["selected_kcs"]
        total = sum(cell["plastic_contact_rows"] for cell in cells)
        initial = [cell["plastic_contact_rows"] / total for cell in cells]
        source_ids = [int(cell["source_id"]) for cell in cells]

        for condition, selected_key in (
            ("target_good_window_floor", "target_kc_source_ids"),
            ("matched_out_of_window_floor", "out_of_window_control_kc_source_ids"),
        ):
            with self.subTest(condition=condition):
                weights, selected = _weights_for_condition(candidate, stage, condition)
                expected = set(stage["intervention"][selected_key])
                self.assertEqual(set(selected), expected)
                self.assertEqual(len(selected), 5)
                for index, source_id in enumerate(source_ids):
                    if source_id in expected:
                        self.assertEqual(weights[index], initial[index] * 0.2)
                    else:
                        self.assertEqual(weights[index], initial[index])

    def test_baseline_and_plasticity_off_are_identical_initial_states(self):
        stage, candidate, _ = _load_inputs(ROOT, CONFIG)
        baseline, baseline_ids = _weights_for_condition(
            candidate, stage, "baseline_initial")
        control, control_ids = _weights_for_condition(
            candidate, stage, "plasticity_off")
        self.assertEqual(baseline, control)
        self.assertEqual(baseline_ids, [])
        self.assertEqual(control_ids, [])


if __name__ == "__main__":
    unittest.main()
