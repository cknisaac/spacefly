"""Read-only bounded shortest-path queries against VFB's hosted L1EM CATMAID.

This records graph paths only; it does not assign synaptic sign or effect.
The pass-through endpoint is public, read-only, and tied to CATMAID project 1.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
from collections import deque
from pathlib import Path


API = "https://v3-cached.virtualflybrain.org/catmaid/l1em/"
BASIN4 = {587_083, 3_040_481, 4_049_878, 1_815_127, 1_400_270}
GORO = {3_720_037, 5_206_247}
MBON_M1 = {4_022_539, 17_016_974}
MBON_D1 = {4_241_237, 7_055_857}
IPSIGORO = {3_979_181, 5_794_678}


def catmaid_get(command: str, params: dict[str, str]) -> dict:
    query = urllib.parse.urlencode({"project": "1", "raw": "true", **params})
    request = urllib.request.Request(API + command + "?" + query)
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def downstream(source_ids: list[int], batch_size: int = 50) -> dict[int, dict[int, int]]:
    result: dict[int, dict[int, int]] = {source: {} for source in source_ids}
    for start in range(0, len(source_ids), batch_size):
        batch = source_ids[start : start + batch_size]
        response = catmaid_get("connectivity", {"ids": ",".join(map(str, batch))})
        for target, details in response.get("outgoing", {}).items():
            target_id = int(target)
            for source, type_counts in details.get("skids", {}).items():
                source_id = int(source)
                if source_id in result:
                    # CATMAID returns counts per connector-link relation.
                    contacts = sum(int(value) for value in type_counts)
                    if contacts:
                        result[source_id][target_id] = contacts
    return result


def shortest_paths(sources: set[int], targets: set[int], max_hops: int) -> dict:
    queue = deque((source, [source], []) for source in sorted(sources))
    visited = set(sources)
    found: list[dict] = []
    found_hops: int | None = None
    expanded_by_layer: list[dict[str, int]] = []

    for depth in range(1, max_hops + 1):
        layer_count = len(queue)
        if layer_count == 0:
            break
        frontier = [queue.popleft() for _ in range(layer_count)]
        links = downstream([node for node, _, _ in frontier])
        expanded_by_layer.append({"depth": depth, "nodes_expanded": len(frontier)})
        for node, path, weights in frontier:
            for next_node, contacts in sorted(links[node].items()):
                if next_node in path:
                    continue
                next_path = path + [next_node]
                next_weights = weights + [contacts]
                if next_node in targets:
                    found.append(
                        {
                            "path_ids": next_path,
                            "contacts_per_edge": next_weights,
                            "bottleneck_contacts": min(next_weights),
                        }
                    )
                    found_hops = depth
                elif next_node not in visited:
                    visited.add(next_node)
                    queue.append((next_node, next_path, next_weights))
        if found_hops is not None:
            break

    found.sort(key=lambda row: (-row["bottleneck_contacts"], row["path_ids"]))
    return {
        "sources": sorted(sources),
        "targets": sorted(targets),
        "max_hops": max_hops,
        "shortest_hops_found": found_hops,
        "paths_at_shortest_depth": found,
        "expanded_by_layer": expanded_by_layer,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-hops", type=int, default=1)
    parser.add_argument(
        "--out", type=Path, default=Path("data/raw/larval_l1em/catmaid_route_audit.json")
    )
    args = parser.parse_args()
    basin_search = catmaid_get(
        "annotations_query_targets", {"name": "Basin-4", "types[0]": "neuron"}
    )
    basin_ids = {
        int(skeleton_id)
        for entity in basin_search.get("entities", [])
        for skeleton_id in entity.get("skeleton_ids", [])
    }
    audited_ids = sorted(MBON_M1 | MBON_D1 | IPSIGORO | GORO | basin_ids)
    neuron_names = catmaid_get("neuron_names", {"ids": ",".join(map(str, audited_ids))})
    result = {
        "source": "VFB CATMAID pass-through, L1EM instance, CATMAID project 1",
        "retrieved_unix_time": int(time.time()),
        "endpoint_root": API,
        "method": "read-only GET",
        "edge_direction": "presynaptic source skeleton -> postsynaptic target skeleton",
        "contact_count_note": "Counts are anatomical connector links; no sign or physiological efficacy is inferred.",
        "basin4_annotation_entities": basin_search.get("entities", []),
        "catmaid_neuron_names": neuron_names,
        "routes": {
            "rejected_L1_MBONm1_to_Basin4": shortest_paths(MBON_M1, basin_ids, args.max_hops),
            "L2_MBONd1_to_Ipsigoro": shortest_paths(MBON_D1, IPSIGORO, args.max_hops),
            "L2_Ipsigoro_to_Goro": shortest_paths(IPSIGORO, GORO, args.max_hops),
            "L2_MBONd1_to_Goro": shortest_paths(MBON_D1, GORO, args.max_hops),
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
