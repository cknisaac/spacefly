"""Read-only provenance, effect-coverage, and connectivity audit for Circuit V1.

The diagnostic graph policies classify reachability only. They never assign a
current, conductance, delay, or simulator-ready status to an anatomical edge.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict, deque
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.feather as feather
import pyarrow.parquet as pq

from project_b.connectome.malecns import ANNOTATIONS, TRANSMITTERS


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/malecns_v1"
PARENT = ROOT / "data/processed/malecns_v1_traced"
SUBSET = ROOT / "data/processed/malecns_v1_circuit_v1"
POLICY = ROOT / "data/processed/malecns_v1_circuit_v1_policy_v1"
OUT = ROOT / "docs/figures/circuit_v1_sign_audit.json"


def tally(rows: list[dict]) -> dict:
    return {"pairs": len(rows), "contacts": sum(r["synapse_count"] for r in rows)}


def by_state(rows: list[dict]) -> dict:
    return {state: tally([r for r in rows if r["effect_state"] == state])
            for state in ("EXCITATORY", "INHIBITORY", "MODULATORY", "UNKNOWN")}


def reachable(edges: list[dict], starts: set[int], targets: set[int]) -> bool:
    graph = defaultdict(set)
    for edge in edges:
        graph[edge["pre_source_id"]].add(edge["post_source_id"])
    queue = deque(starts)
    seen = set(starts)
    while queue:
        node = queue.popleft()
        if node in targets:
            return True
        for next_node in graph[node] - seen:
            seen.add(next_node)
            queue.append(next_node)
    return False


def main() -> None:
    nodes = pq.read_table(SUBSET / "neurons.parquet").to_pylist()
    edges = pq.read_table(POLICY / "connection_policy.parquet").to_pylist()
    anatomy = pq.read_table(SUBSET / "connections.parquet").to_pylist()
    ids = {n["source_id"] for n in nodes}
    assert len(nodes) == len(ids) == 140
    assert len(edges) == len(anatomy) == 12153
    assert sum(e["synapse_count"] for e in edges) == 57771

    # Compare source annotations with the normalized parent and selected rows.
    raw_nt = feather.read_table(RAW / TRANSMITTERS,
                                columns=["body", "cell_type", "predicted_nt", "predicted_nt_confidence",
                                         "celltype_predicted_nt", "celltype_predicted_nt_confidence",
                                         "consensus_nt", "ground_truth"])
    raw_an = feather.read_table(RAW / ANNOTATIONS,
                                columns=["bodyId", "receptorType", "type", "instance"])
    raw_nt = raw_nt.filter(pc.is_in(raw_nt["body"], pa.array(sorted(ids))))
    raw_an = raw_an.filter(pc.is_in(raw_an["bodyId"], pa.array(sorted(ids))))
    nt = {r["body"]: r for r in raw_nt.to_pylist()}
    ann = {r["bodyId"]: r for r in raw_an.to_pylist()}
    assert set(nt) == set(ann) == ids
    parent = pq.read_table(PARENT / "neurons.parquet",
                           filters=[("source_id", "in", sorted(ids))]).to_pylist()
    par = {r["source_id"]: r for r in parent}
    assert set(par) == ids
    fields = ("transmitter_predicted", "transmitter_confidence",
              "transmitter_consensus", "transmitter_ground_truth", "receptor_type_annotation")
    raw_fields = ("predicted_nt", "predicted_nt_confidence", "consensus_nt",
                  "ground_truth", "receptorType")
    for node in nodes:
        source_id = node["source_id"]
        expected = [nt[source_id][key] for key in raw_fields[:4]] + [ann[source_id]["receptorType"]]
        for key, value in zip(fields, expected):
            assert par[source_id][key] == node[key] == value, (source_id, key)
        assert nt[source_id]["cell_type"] == node["cell_type"]
        assert node["cell_type"] == ann[source_id]["type"]
        assert node["instance"] == ann[source_id]["instance"]
    node_by_id = {n["source_id"]: n for n in nodes}
    source_edges = {(r["pre_source_id"], r["post_source_id"]): r for r in anatomy}
    for edge in edges:
        pre, post = edge["pre_source_id"], edge["post_source_id"]
        source = source_edges[(pre, post)]
        assert (edge["source_row"], edge["synapse_count"]) == (source["source_row"], source["synapse_count"])
        assert edge["pre_transmitter_consensus"] == node_by_id[pre]["transmitter_consensus"]
        assert edge["post_receptor_type_annotation"] == node_by_id[post]["receptor_type_annotation"]

    # Mutually exclusive diagnostic reasons for UNKNOWN. The decision order is
    # explicit: missing/lost metadata, source-label conflict, dopamine-like
    # non-binary effects, and unresolved target receptor/effect.
    unknown = [e for e in edges if e["effect_state"] == "UNKNOWN"]
    categories = defaultdict(list)
    for edge in unknown:
        pre = node_by_id[edge["pre_source_id"]]
        if not pre["transmitter_consensus"]:
            reason = "presynaptic_transmitter_missing"
        elif edge["pre_transmitter_consensus"] != pre["transmitter_consensus"]:
            reason = "source_to_policy_mapping_lost"
        elif pre["transmitter_predicted"] not in (None, pre["transmitter_consensus"]):
            reason = "conflicting_predicted_vs_consensus"
        elif pre["transmitter_consensus"] in ("dopamine", "serotonin", "octopamine", "tyramine"):
            reason = "modulatory_nonbinary_unresolved"
        else:
            reason = "transmitter_known_target_effect_unknown"
        categories[reason].append(edge)
    assert sum(len(v) for v in categories.values()) == len(unknown)

    role_ids = defaultdict(set)
    for edge in edges:
        role_ids[edge["pre_role"]].add(edge["pre_source_id"])
        role_ids[edge["post_role"]].add(edge["post_source_id"])
    role_pairs = defaultdict(list)
    for edge in edges:
        role_pairs[(edge["pre_role"], edge["post_role"])].append(edge)
    role_result = {}
    for role in sorted(role_ids):
        role_result[role] = {
            "incoming": by_state([e for e in edges if e["post_role"] == role]),
            "outgoing": by_state([e for e in edges if e["pre_role"] == role]),
        }

    def group(key: str) -> set[str]:
        if key == "sensory":
            return {r for r in role_ids if r.startswith("visual_input_")}
        if key == "KC":
            return {"visual_kenyon_cells"}
        if key == "APL":
            return {"apl_local_feedback"}
        if key == "DAN":
            return {"ppl1_gamma1_teaching", "pam_gamma5_teaching_cohort"}
        if key == "learning_MBON":
            return {"mbon11_gamma1_learning_output", "mbon01_gamma5_learning_output"}
        if key == "relay_MBON":
            return {"mbon26_output_relay", "mbon27_visual_output", "mbon32_competing_output"}
        if key == "all_MBON":
            return {r for r in role_ids if r.startswith("mbon")}
        if key == "DN":
            return {"dna03_descending_relay", "dna02_action_boundary"}
        raise KeyError(key)

    group_result = {}
    for key in ("sensory", "KC", "APL", "DAN", "learning_MBON", "relay_MBON", "all_MBON", "DN"):
        roles = group(key)
        group_result[key] = {
            "neurons": len(set.union(*(role_ids[r] for r in roles))),
            "incoming": by_state([e for e in edges if e["post_role"] in roles]),
            "outgoing": by_state([e for e in edges if e["pre_role"] in roles]),
        }

    stages = {
        "sensory_to_KC": (group("sensory"), group("KC")),
        "KC_to_learning_MBON": (group("KC"), group("learning_MBON")),
        "KC_to_relay_MBON": (group("KC"), group("relay_MBON")),
        "learning_MBON_to_relay_MBON": (group("learning_MBON"), group("relay_MBON")),
        "relay_MBON_to_DN": (group("relay_MBON"), group("DN")),
        "DN_to_DN": (group("DN"), group("DN")),
        "DAN_to_KC": (group("DAN"), group("KC")),
        "DAN_to_learning_MBON": (group("DAN"), group("learning_MBON")),
    }
    stage_result = {name: by_state([e for e in edges if e["pre_role"] in pre and e["post_role"] in post])
                    for name, (pre, post) in stages.items()}

    key_ids = {key: set().union(*(role_ids[r] for r in group(key)))
               for key in ("sensory", "KC", "DAN", "learning_MBON", "relay_MBON", "DN")}
    key_ids["action"] = role_ids["dna02_action_boundary"]
    graph_result = {}
    for name, active in (("A_signed", {"EXCITATORY", "INHIBITORY"}),
                         ("B_signed_plus_modulatory", {"EXCITATORY", "INHIBITORY", "MODULATORY"}),
                         ("C_all_anatomy_unknown_inactive", {"EXCITATORY", "INHIBITORY", "MODULATORY"})):
        functional = [e for e in edges if e["effect_state"] in active]
        retained = edges if name.startswith("C_") else functional
        active_ids = {i for e in functional for i in (e["pre_source_id"], e["post_source_id"])}
        graph_result[name] = {
            "retained": tally(retained), "functionally_active": tally(functional),
            "functional_isolates": sorted(ids - active_ids),
            "functional_isolates_by_role": {r: len(role_ids[r] - active_ids) for r in sorted(role_ids)},
            "sensory_to_KC": reachable(functional, key_ids["sensory"], key_ids["KC"]),
            "sensory_to_learning_MBON": reachable(functional, key_ids["sensory"], key_ids["learning_MBON"]),
            "sensory_to_action": reachable(functional, key_ids["sensory"], key_ids["action"]),
            "KC_to_action": reachable(functional, key_ids["KC"], key_ids["action"]),
            "DAN_to_KC": reachable(functional, key_ids["DAN"], key_ids["KC"]),
            "DAN_to_learning_MBON": reachable(functional, key_ids["DAN"], key_ids["learning_MBON"]),
        }

    unknown_role_pairs = []
    for (pre, post), rows in role_pairs.items():
        unk = [r for r in rows if r["effect_state"] == "UNKNOWN"]
        if unk:
            unknown_role_pairs.append({"pre": pre, "post": post, **tally(unk)})
    unknown_role_pairs.sort(key=lambda x: (-x["contacts"], -x["pairs"], x["pre"], x["post"]))
    result = {
        "source": "MaleCNS v1.0, 140-body Circuit V1 exact induced graph",
        "provenance": {"raw_nt_rows": len(nt), "raw_annotation_rows": len(ann),
                       "parent_subset_field_matches": len(nodes) * len(fields),
                       "policy_endpoint_metadata_matches": len(edges) * 2,
                       "policy_anatomical_rows_match": len(edges)},
        "totals": by_state(edges),
        "unknown_categories": {k: {**tally(v),
                                   "top_pre_roles": Counter(e["pre_role"] for e in v).most_common(8),
                                   "top_post_roles": Counter(e["post_role"] for e in v).most_common(8),
                                   "top_pre_roles_by_contacts": Counter({
                                       role: sum(e["synapse_count"] for e in v if e["pre_role"] == role)
                                       for role in {e["pre_role"] for e in v}}).most_common(8),
                                   "top_post_roles_by_contacts": Counter({
                                       role: sum(e["synapse_count"] for e in v if e["post_role"] == role)
                                       for role in {e["post_role"] for e in v}}).most_common(8)}
                               for k, v in sorted(categories.items())},
        "selected_transmitter_consensus": dict(Counter(n["transmitter_consensus"] for n in nodes)),
        "selected_predicted_consensus_disagreements": [
            {"source_id": n["source_id"], "cell_type": n["cell_type"],
             "predicted": n["transmitter_predicted"], "consensus": n["transmitter_consensus"],
             "confidence": n["transmitter_confidence"],
             "celltype_predicted": nt[n["source_id"]]["celltype_predicted_nt"],
             "celltype_confidence": nt[n["source_id"]]["celltype_predicted_nt_confidence"]}
            for n in nodes if n["transmitter_predicted"] not in (None, n["transmitter_consensus"])],
        "roles": role_result, "groups": group_result, "stages": stage_result,
        "unknown_role_pairs": unknown_role_pairs,
        "graph_policies": graph_result,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}; matched {len(nodes)} source nodes and {len(edges)} policy rows")


if __name__ == "__main__":
    main()
