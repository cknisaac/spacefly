"""Resolve the B2.1 engineering addendum and statically audit source coverage.

Data/config checks only. Does not construct or run a neural model.
"""

from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "configs/b2_candidate1_design.json"
ADD = ROOT / "configs/b2_1_candidate1_dynamics_addendum.json"
MASK = ROOT / "configs/b2_candidate1_runtime_mask.json"
B1 = ROOT / "docs/figures/b1_mvp_pathway_rule_selection/selected_anatomy.json"
B2_AUDIT = ROOT / "docs/figures/b2_candidate_design/gamma4_contact_audit.json"
OUT = ROOT / "configs/b2_1_candidate1_resolved.json"
COVERAGE = ROOT / "docs/figures/b2_1_candidate1_dynamics/source_coverage.json"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def category(pre: int, post: int, kc: set[int], pam: set[int]) -> str:
    if pre in kc:
        if post in kc:
            return "KC_to_KC"
        if post == 10495:
            return "KC_to_MBON05"
        if post == 11145:
            return "KC_to_MBON20"
        if post == 10977:
            return "KC_to_APL_graded_input"
    if pre == 10977:
        return "APL_to_measured_targets_graded_output"
    if pre in pam:
        return "PAM08_modulatory_anatomy"
    if (pre, post) == (10495, 11145):
        return "MBON05_to_MBON20"
    if (pre, post) == (11145, 10713):
        return "MBON20_to_DNp42"
    return "UNKNOWN_QUARANTINED_NO_CURRENT"


def main() -> None:
    base, add, mask, b1, b2_audit = map(read, (BASE, ADD, MASK, B1, B2_AUDIT))
    assert (base["candidate_id"], add["candidate_id"], mask["candidate_id"]) == ("MVP-C1",) * 3
    assert len(b1["roster"]) == 718 and len(b1["kc_source_ids"]) == 689 and len(b1["dan_source_ids"]) == 25
    assert base["plastic_contact_mask"]["contacts"] == b2_audit["same_kc_screen"]["candidate_contacts"] == 13957
    assert len(mask["kc_pairs"]) == 689 and mask["b2_audit_sha256"] == sha(B2_AUDIT)
    assert mask["b1_anatomy_sha256"] == sha(B1)
    assert mask["source_partner_sha256"] == b2_audit["source_partner_sha256"]
    selected_partner_rows = [row for pair in mask["kc_pairs"] for row in pair["plastic_contact_rows"]]
    assert len(selected_partner_rows) == len(set(selected_partner_rows)) == 13957
    assert set(selected_partner_rows) == set(b2_audit["same_kc_screen"]["candidate_source_partner_rows"])
    assert add["chemical_current"]["delay_us"] == base["generic_neuron_assumptions"]["chemical_delay_us"]
    assert add["graded_apl"]["tau_apl_us"] == base["apl"]["time_constant_us"]
    assert add["graded_apl"]["kc_input_delay_us"] == add["chemical_current"]["delay_us"]
    assert add["autonomous_boundary"]["nominal_means_threshold_units"] == base["boundary"]["nominal_mean_current_threshold_units_by_source_id"]
    assert add["autonomous_boundary"]["amplitude_fraction"] == base["boundary"]["telegraph_amplitude_fraction"]
    assert sorted(add["autonomous_boundary"]["level_multipliers"].values()) == sorted(base["boundary"]["low_nominal_high_mean_factors"])
    assert add["event_ties"]["threshold_grid_us"] == base["generic_neuron_assumptions"]["integration_step_us"]
    assert add["chemical_current"]["tau_syn_us"] > 0
    assert add["graded_apl"]["tau_apl_us"] > 0
    assert len(set(add["autonomous_boundary"]["stream_names"])) == 3
    assert add["autonomous_boundary"]["targets_source_ids"] == [10495, 11145, 10713]
    assert len(add["full_runner_interface"]["future_event_owners"]) == 12
    assert set(add["full_runner_interface"]["future_event_owners"].values()) <= set(add["full_runner_interface"]["owners"])
    assert max(1, round(-100000 * math.log1p(-0.0))) == 1
    assert max(1, round(-100000 * math.log1p(-0.5))) == 69315

    neurons = ROOT / "data/processed/malecns_v1_traced/neurons.parquet"
    connections = ROOT / "data/processed/malecns_v1_traced/connections.parquet"
    source_hashes = b1["source_hashes"]
    assert sha(neurons) == source_hashes["data\\processed\\malecns_v1_traced\\neurons.parquet"]
    assert sha(connections) == source_hashes["data\\processed\\malecns_v1_traced\\connections.parquet"]
    source_ids = pq.read_table(neurons, columns=["source_id"])["source_id"].to_numpy()
    selected = {cell["source_id"] for cell in b1["roster"]}
    kc = set(b1["kc_source_ids"])
    pam = set(b1["dan_source_ids"])
    indices = np.flatnonzero(np.isin(source_ids, list(selected)))
    counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for batch in pq.ParquetFile(connections).iter_batches(
            columns=["pre_index", "post_index", "synapse_count"], batch_size=500000):
        pre = batch["pre_index"].to_numpy()
        post = batch["post_index"].to_numpy()
        contact = batch["synapse_count"].to_numpy()
        inside = np.flatnonzero(np.isin(pre, indices) & np.isin(post, indices))
        for row in inside:
            name = category(int(source_ids[pre[row]]), int(source_ids[post[row]]), kc, pam)
            counts[name][0] += 1
            counts[name][1] += int(contact[row])
    assert sum(v[0] for v in counts.values()) == b1["induced_pairs"] == 153854
    assert sum(v[1] for v in counts.values()) == b1["induced_contacts"] == 333380
    assert counts["KC_to_APL_graded_input"] == [689, 37593]
    assert counts["APL_to_measured_targets_graded_output"] == [702, 40739]
    assert counts["MBON05_to_MBON20"] == [1, 169]
    assert counts["MBON20_to_DNp42"] == [1, 191]
    assert counts["PAM08_modulatory_anatomy"] == [7079, 11783]
    assert counts["UNKNOWN_QUARANTINED_NO_CURRENT"] == [7793, 13122]

    active_names = set(add["full_runner_interface"]["active_classes"])
    assert active_names == set(counts) - {"PAM08_modulatory_anatomy", "UNKNOWN_QUARANTINED_NO_CURRENT"}
    coverage = {
        "stage_id": "MVP-B2.1", "classification": "source anatomy plus explicit engineering effect policy",
        "source_neurons_sha256": sha(neurons), "source_connections_sha256": sha(connections),
        "roster_cells": len(selected), "spiking_cells": len(selected) - 1,
        "induced_pairs": b1["induced_pairs"], "induced_contacts": b1["induced_contacts"],
        "categories": {key: {"pairs": value[0], "contacts": value[1]}
                       for key, value in sorted(counts.items())},
        "active_electrical_pairs": sum(counts[n][0] for n in active_names),
        "active_electrical_contacts": sum(counts[n][1] for n in active_names),
        "modulatory_pairs": counts["PAM08_modulatory_anatomy"][0],
        "quarantined_pairs": counts["UNKNOWN_QUARANTINED_NO_CURRENT"][0],
        "source_classification_complete": True,
    }
    resolved = {
        "stage_id": "MVP-B2.1", "candidate_id": "MVP-C1",
        "version": add["version"], "status": "resolved_design_only_no_runner",
        "identity": {"B2_design_sha256": sha(BASE), "B2_1_addendum_sha256": sha(ADD),
                     "B2_runtime_mask_sha256": sha(MASK), "B1_anatomy_sha256": sha(B1),
                     "B2_contact_audit_sha256": sha(B2_AUDIT),
                     "source_neurons_sha256": coverage["source_neurons_sha256"],
                     "source_connections_sha256": coverage["source_connections_sha256"],
                     "source_partner_sha256": mask["source_partner_sha256"]},
        "B2_base_design": base, "B2_1_dynamics_addendum": add,
        "source_graph_coverage": coverage,
        "checkpoint_identity_mapping": {
            "B2_design_sha256": "historical configs/b2_candidate1_design.json hash",
            "effect_and_boundary_overlay_sha256": "B2.1 addendum hash",
            "resolved_config_sha256": "hash of this resolved file; placed in run/checkpoint manifest, not embedded recursively",
        },
    }
    COVERAGE.parent.mkdir(parents=True, exist_ok=True)
    COVERAGE.write_text(json.dumps(coverage, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    OUT.write_text(json.dumps(resolved, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": resolved["status"], "resolved_sha256": sha(OUT),
                      "active_electrical_pairs": coverage["active_electrical_pairs"],
                      "modulatory_pairs": coverage["modulatory_pairs"],
                      "quarantined_pairs": coverage["quarantined_pairs"]}, indent=2))


if __name__ == "__main__":
    main()
