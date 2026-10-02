"""A1.3 local rule and adapter checks; no candidate training or B3 probe."""

import json
import math
import unittest
from pathlib import Path

from project_b.neurons import LIFParameters
from project_b.checkpoint import FrozenPolicySnapshot
from project_b.plasticity import Gamma4ContactMask, Gamma4Parameters, Gamma4Plasticity
from project_b.simulation import SpikingSimulator
from project_b.synapses import SparseGraph, Synapse


ROOT = Path(__file__).resolve().parents[1]


def fixture():
    mask = Gamma4ContactMask({
        "candidate_id": "MVP-C1", "compartment": "g4(L)", "mbon_source_id": 30,
        "kc_pairs": [{"kc_source_id": 10, "total_contacts": 2,
                      "plastic_contact_rows": [101]},
                     {"kc_source_id": 11, "total_contacts": 3,
                      "plastic_contact_rows": []}],
    })
    graph = SparseGraph(4, [Synapse(0, 3, 1.0, 2000),
                            Synapse(1, 3, 2.0, 2000)])
    return graph, Gamma4Plasticity(graph, (10, 11, 20, 30), mask, (20,))


class Gamma4Tests(unittest.TestCase):
    def test_pinned_mask_has_exact_source_contacts_and_fixed_only_kc(self):
        path = ROOT / "configs/b2_candidate1_runtime_mask.json"
        audit = ROOT / "docs/figures/b2_candidate_design/gamma4_contact_audit.json"
        mask = Gamma4ContactMask.load_b2(path, audit)
        self.assertEqual((len(mask.pairs), sum(p.plastic_contacts for p in mask.pairs)),
                         (689, 13957))
        self.assertEqual(sum(bool(p.plastic_contacts) for p in mask.pairs), 688)
        self.assertEqual(mask.by_kc[51583].plastic_contacts, 0)
        self.assertEqual(sum(p.total_contacts for p in mask.pairs), 16398)

    def test_full_b2_mask_binds_688_pairs_without_changing_fixed_contributions(self):
        mask = Gamma4ContactMask.load_b2(
            ROOT / "configs/b2_candidate1_runtime_mask.json",
            ROOT / "docs/figures/b2_candidate_design/gamma4_contact_audit.json")
        b1 = json.loads((ROOT / "docs/figures/b1_mvp_pathway_rule_selection/selected_anatomy.json")
                        .read_text(encoding="utf-8"))
        ids = tuple(sorted(mask.by_kc)) + tuple(b1["dan_source_ids"]) + (10495,)
        index = {source: i for i, source in enumerate(ids)}
        edges = [Synapse(index[p.kc_source_id], index[10495],
                         p.total_contacts / 16398, 2000) for p in mask.pairs]
        graph = SparseGraph(len(ids), edges)
        rule = Gamma4Plasticity.from_b2_design(graph, ids, ROOT)
        wrong = SparseGraph(len(ids), [Synapse(e.pre, e.post,
                                             e.weight_mv * (1.01 if i == 0 else 1.0),
                                             e.delay_us) for i, e in enumerate(edges)])
        with self.assertRaises(ValueError):
            Gamma4Plasticity.from_b2_design(wrong, ids, ROOT)
        kc = next(p.kc_source_id for p in mask.pairs if p.plastic_contacts)
        unchanged = {s: rule.effective_weight(s) for s in range(graph.edge_count)}
        rule.observe_spikes(1000, [index[kc]])
        record = rule.observe_spikes(2000, [index[b1["dan_source_ids"][0]]])
        self.assertEqual((len(rule._slot_by_kc), len(record.updates)), (688, 688))
        changed = [s for s in unchanged if rule.effective_weight(s) != unchanged[s]]
        self.assertEqual(changed, [rule._slot_by_kc[kc]])
        self.assertEqual(rule.effective_weight(
            next(s for s in graph.outgoing_slots(index[51583]))),
            unchanged[next(s for s in graph.outgoing_slots(index[51583]))])
        self.assertEqual(tuple(graph.weights_mv), tuple(unchanged[s] for s in unchanged))

    def test_temporal_polarity_fixed_split_and_zero_events(self):
        graph, rule = fixture()
        slot = 0
        self.assertEqual(rule.effective_weight(slot), 1.0)
        zero = rule.observe_spikes(1000, [0])
        self.assertEqual(zero.updates[0].proposed_plastic_weight, 0.5)
        self.assertEqual(rule.effective_weight(slot), 1.0)
        depression = rule.observe_spikes(2000, [2]).updates[0]
        expected = 0.5 - 0.001 * 0.5 * math.exp(-1000 / 1_000_000)
        self.assertAlmostEqual(depression.applied_plastic_weight, expected)
        self.assertEqual(rule.effective_weight(1), graph.weights_mv[1])
        self.assertEqual(graph.weights_mv[slot], 1.0)
        before = rule.effective_weight(slot)
        potentiation = rule.observe_spikes(3000, [0]).updates[0]
        self.assertEqual(potentiation.branch, "pam_before_kc_potentiation")
        self.assertGreater(rule.effective_weight(slot), before)
        self.assertEqual(potentiation.mask_sha256, rule.mask.mask_sha256)

    def test_coincidence_depresses_and_batch_order_is_invariant(self):
        _, a = fixture()
        _, b = fixture()
        record_a = a.observe_spikes(1000, [0, 2])
        record_b = b.observe_spikes(1000, [2, 0])
        self.assertEqual(record_a, record_b)
        self.assertEqual(record_a.updates[0].branch, "coincident_depression")
        self.assertAlmostEqual(a.effective_weight(0), 0.9995)

    def test_rejected_batch_has_no_partial_state_change(self):
        _, rule = fixture()
        before = (rule.effective_weight(0), rule._kc_trace.copy(), rule._pam_trace)
        for action in (lambda: rule.observe_spikes(1000, [0, 99]),
                       lambda: rule.observe_spikes(1000, [0], compartment="g1(L)"),
                       lambda: rule.observe_spikes(1000, [0, 0])):
            with self.assertRaises(ValueError):
                action()
            self.assertEqual((rule.effective_weight(0), rule._kc_trace,
                              rule._pam_trace), before)
        rule.observe_spikes(1000, [0])
        with self.assertRaises(ValueError):
            rule.observe_spikes(1000, [2])

    def test_clipping_and_simulator_weight_capture(self):
        graph, rule = fixture()
        rule.parameters = Gamma4Parameters(eta=1.0)
        rule.observe_spikes(1000, [0, 2])
        self.assertAlmostEqual(rule.effective_weight(0), 0.75)
        self.assertTrue(rule.observe_spikes(2000, [0, 2]).updates[0].clipped)
        self.assertAlmostEqual(rule.effective_weight(0), 0.75)
        graph, fresh = fixture()
        simulator = SpikingSimulator([LIFParameters(refractory_us=100_000)] * 4,
                                     graph, [20.0, 0.0, 20.0, 0.0],
                                     plasticity=fresh, record_arrivals=True)
        simulator.run_until(1000)
        self.assertEqual(simulator.last_plasticity_record.updates[0].branch,
                         "coincident_depression")
        with self.assertRaises(RuntimeError):
            simulator.apply_dopamine(-1.0)
        result = simulator.run_until(3000)
        self.assertEqual(result.arrivals[0].weight_mv, 1.0)
        self.assertAlmostEqual(fresh.effective_weight(0), 0.9995)

    def test_gamma4_checkpoint_and_frozen_policy_reset_transients(self):
        _, original = fixture()
        original.observe_spikes(1000, [0])
        original.observe_spikes(2000, [2])
        state = original.state()
        _, restored = fixture()
        restored.restore(state)
        self.assertEqual(restored.state(), state)
        self.assertEqual(original.observe_spikes(3000, [0]),
                         restored.observe_spikes(3000, [0]))
        self.assertEqual(original.state(), restored.state())
        policy = original.frozen_policy_state()
        _, frozen = fixture()
        frozen.load_frozen_policy(policy)
        self.assertFalse(frozen.enabled)
        self.assertEqual(frozen._pam_trace, (0.0, 0))
        self.assertTrue(all(trace == (0.0, 0) for trace in frozen._kc_trace.values()))
        self.assertEqual(frozen._plastic_by_slot, original._plastic_by_slot)
        previous = frozen.effective_weight(0)
        frozen.observe_spikes(1000, [0, 2])
        self.assertEqual(frozen.effective_weight(0), previous)
        tampered = original.state()
        tampered["selected_plastic_weights_by_kc_source_id"]["10"] = -1.0
        before = restored.state()
        with self.assertRaises(ValueError):
            restored.restore(tampered)
        self.assertEqual(restored.state(), before)

    def test_simulator_and_gamma4_resume_with_pending_captured_arrival(self):
        graph, rule = fixture()
        params = [LIFParameters(refractory_us=100_000)] * 4
        uninterrupted = SpikingSimulator(params, graph, [20.0, 0.0, 20.0, 0.0],
                                          plasticity=rule, record_spikes=True,
                                          record_arrivals=True)
        uninterrupted.run_until(1000)
        self.assertEqual(uninterrupted.snapshot().queued_arrivals, 1)
        sim_state, rule_state = uninterrupted.state(), rule.state()
        other_graph, other_rule = fixture()
        resumed = SpikingSimulator(params, other_graph, [20.0, 0.0, 20.0, 0.0],
                                   plasticity=other_rule, record_spikes=True,
                                   record_arrivals=True)
        other_rule.restore(rule_state)
        resumed.restore(sim_state)
        self.assertEqual(resumed.state(), sim_state)
        self.assertEqual(uninterrupted.run_until(5000), resumed.run_until(5000))
        self.assertEqual(uninterrupted.state(), resumed.state())
        bad = resumed.state()
        bad["queue"] = [[5000, 3, 0, 0, 0, 1.0]]
        before = resumed.state()
        with self.assertRaises(ValueError):
            resumed.restore(bad)
        self.assertEqual(resumed.state(), before)

    def test_frozen_policy_snapshot_keeps_weights_but_resets_traces(self):
        _, trained = fixture()
        trained.observe_spikes(1000, [0])
        trained.observe_spikes(2000, [2])
        snapshot = FrozenPolicySnapshot.capture(trained)
        _, fresh = fixture()
        snapshot.install_into_fresh_rule(fresh)
        self.assertEqual(fresh._plastic_by_slot, trained._plastic_by_slot)
        self.assertEqual(fresh._pam_trace, (0.0, 0))
        self.assertFalse(fresh.enabled)
        previous = fresh.effective_weight(0)
        fresh.observe_spikes(1000, [0, 2])
        self.assertEqual(fresh.effective_weight(0), previous)
        _, altered = fixture()
        altered.parameters = Gamma4Parameters(eta=0.002)
        with self.assertRaises(ValueError):
            snapshot.install_into_fresh_rule(altered)


if __name__ == "__main__":
    unittest.main()
