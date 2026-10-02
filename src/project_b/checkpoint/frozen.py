"""Selected-weight-only policy capture for fresh frozen MVP-C1 runs."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from project_b.plasticity import Gamma4Plasticity


def _graph_identity(rule: Gamma4Plasticity) -> str:
    graph = rule.graph
    data = {"source_ids_by_index": rule.source_ids_by_index,
            "edges": [[int(graph.pre_indices[s]), int(graph.post_indices[s]),
                       float(graph.weights_mv[s]).hex(), int(graph.delays_us[s])]
                      for s in range(graph.edge_count)],
            "mask_sha256": rule.mask.mask_sha256,
            "parameters": [rule.parameters.kc_trace_tau_us,
                           rule.parameters.pam_trace_tau_us, float(rule.parameters.eta).hex(),
                           float(rule.parameters.trace_cap).hex(),
                           float(rule.parameters.minimum_weight_factor).hex(),
                           float(rule.parameters.maximum_weight_factor).hex()]}
    return hashlib.sha256(json.dumps(data, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class FrozenPolicySnapshot:
    candidate_id: str
    graph_sha256: str
    mask_sha256: str
    selected_weights: tuple[tuple[int, float], ...]

    @classmethod
    def capture(cls, rule: Gamma4Plasticity) -> "FrozenPolicySnapshot":
        policy = rule.frozen_policy_state()
        return cls("MVP-C1", _graph_identity(rule), policy["mask_sha256"],
                   tuple((int(k), v) for k, v in sorted(
                       policy["selected_plastic_weights_by_kc_source_id"].items(),
                       key=lambda item: int(item[0]))))

    def install_into_fresh_rule(self, rule: Gamma4Plasticity) -> None:
        if (self.candidate_id != "MVP-C1" or self.graph_sha256 != _graph_identity(rule)
                or self.mask_sha256 != rule.mask.mask_sha256):
            raise ValueError("frozen policy graph or mask identity differs")
        rule.load_frozen_policy({
            "mask_sha256": self.mask_sha256,
            "selected_plastic_weights_by_kc_source_id":
                {str(kc): value for kc, value in self.selected_weights}})
