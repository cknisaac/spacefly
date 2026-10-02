"""Immutable 115-body anatomy plus separately classified electrical hypotheses."""

from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[3]
PARENT = ROOT / "data/processed/malecns_v1_traced"
CANDIDATES = ROOT / "data/processed/malecns_v1_route_closure/plastic_contact_candidates_anatomy_only.parquet"
EFFECTS = {"ACTIVE_FAST", "GRADED_INPUT", "GRADED_OUTPUT", "MODULATORY", "UNKNOWN"}
NUMERIC_EVIDENCE = {"LITERATURE-CONSTRAINED", "INFERRED", "ENGINEERING ASSUMPTION"}
V1_CONFIG = ROOT / "configs/electrical_model_v1.json"
V1_CONFIG_SHA = "fe7e0c488e5ce1beb3642cd003a19198e4f1d0758c6e6dd7ecb6c714bb935d0c"
ADDED_VISUAL_IDS = (12740, 13190)


class UnknownEdgePolicy(str, Enum):
    """Keep every anatomical edge while giving unmatched effects no current."""

    RETAIN_ANATOMY_INACTIVE = "RETAIN_ANATOMY_INACTIVE"

    @staticmethod
    def electrical_weight(connection: "SourceConnection") -> float | None:
        if connection.effect_state == "UNKNOWN":
            if connection.weight_pa is not None or connection.effect_evidence != "UNKNOWN":
                raise ValueError("UNKNOWN source edge acquired an electrical effect")
            return None
        return connection.weight_pa


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def parameter(spec: dict, *, positive: bool = False) -> float:
    if not isinstance(spec, dict) or spec.get("evidence") not in NUMERIC_EVIDENCE or not spec.get("source"):
        raise ValueError("Every numerical policy entry needs explicit provenance")
    value = spec.get("value")
    if type(value) not in (int, float) or not math.isfinite(value) or (positive and value <= 0):
        raise ValueError("Invalid numerical policy value")
    return float(value)


@dataclass(frozen=True)
class SourceCell:
    source_id: int
    kind: str
    source_runtime_index: int
    transmitter: str | None


@dataclass(frozen=True)
class SourceConnection:
    source_row: int
    pre: int  # local index, ordered by source ID
    post: int
    contacts: int
    effect_state: str
    effect_evidence: str
    weight_pa: float | None
    candidate_contacts: int = 0


@dataclass(frozen=True)
class CircuitDefinition:
    cells: tuple[SourceCell, ...]
    connections: tuple[SourceConnection, ...]
    candidate_partner_rows: tuple[int, ...]
    config: dict
    config_sha256: str
    parent_hashes: dict[str, str]

    def index(self, source_id: int) -> int:
        return next(i for i, c in enumerate(self.cells) if c.source_id == source_id)

    def counts(self) -> dict:
        effects = Counter(c.effect_state for c in self.connections)
        contacts = Counter()
        for c in self.connections:
            contacts[c.effect_state] += c.contacts
        return {"neurons": len(self.cells), "source_pairs": len(self.connections),
                "source_contacts": sum(c.contacts for c in self.connections),
                "effect_pairs": dict(effects), "effect_contacts": dict(contacts),
                "plastic_candidate_contacts": sum(c.candidate_contacts for c in self.connections),
                "plastic_candidate_pairs": sum(c.candidate_contacts > 0 for c in self.connections)}


def _kind(source_id: int, kcs: set[int], visual_ids: set[int]) -> str:
    if source_id in visual_ids:
        return "sensory"
    if source_id in kcs:
        return "KC"
    return {10540: "APL", 14182: "PPL103", 519131: "MBON32",
            519624: "DNa03", 523769: "DNa02"}[source_id]


def _effect(pre: SourceCell, post: SourceCell, config: dict) -> tuple[str, str, float | None]:
    pair = (pre.kind, post.kind)
    if pair in {("sensory", "KC"), ("KC", "MBON32"), ("MBON32", "DNa03"),
                ("MBON32", "DNa02"), ("DNa03", "DNa02")}:
        name = {("sensory", "KC"): "sensory_to_KC_pa_per_contact",
                ("KC", "MBON32"): "KC_to_MBON32_pa_per_contact",
                ("MBON32", "DNa03"): "MBON32_to_DNa03_pa_per_contact",
                ("MBON32", "DNa02"): "MBON32_to_DNa02_pa_per_contact",
                ("DNa03", "DNa02"): "DNa03_to_DNa02_pa_per_contact"}[pair]
        spec = config["effect_hypotheses"][name]
        per_contact = parameter(spec)
        if (pre.kind in {"sensory", "KC", "DNa03"} and per_contact <= 0) or (pre.kind == "MBON32" and per_contact >= 0):
            raise ValueError("Effect magnitude/sign contradicts the named hypothesis")
        expected_nt = {"sensory": "acetylcholine", "KC": "acetylcholine",
                       "MBON32": "gaba", "DNa03": "acetylcholine"}[pre.kind]
        if pre.transmitter != expected_nt:
            raise ValueError("Selected source transmitter annotation drifted")
        effect_evidence = "LITERATURE-CONSTRAINED" if pair == ("KC", "MBON32") else "INFERRED"
        return "ACTIVE_FAST", effect_evidence, per_contact
    if pair == ("KC", "APL"):
        return "GRADED_INPUT", "INFERRED", None
    if pair == ("APL", "KC"):
        if pre.transmitter != "gaba":
            raise ValueError("APL transmitter annotation drifted")
        return "GRADED_OUTPUT", "LITERATURE-CONSTRAINED", None
    if pre.kind == "PPL103" and post.kind in {"KC", "MBON32"}:
        if pre.transmitter != "dopamine":
            raise ValueError("DAN transmitter annotation drifted")
        return "MODULATORY", "INFERRED", None
    return "UNKNOWN", "UNKNOWN", None


def build_circuit(config_path: Path | None = None, *, parent: Path = PARENT,
                  candidate_path: Path = CANDIDATES) -> CircuitDefinition:
    """Verify sources and retain every induced pair, including inactive UNKNOWN.

    This builder never changes the validated parent or the earlier 140-body policy.
    """
    config_path = config_path or V1_CONFIG
    config_path = Path(config_path)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    version = config["schema_version"]
    if version not in {1, 2} or config["unknown_edge_policy"] != UnknownEdgePolicy.RETAIN_ANATOMY_INACTIVE:
        raise ValueError("Unsupported or unsafe Electrical Model V1 policy")
    if version == 2:
        if file_sha(V1_CONFIG) != V1_CONFIG_SHA or config.get("base_config_sha256") != V1_CONFIG_SHA:
            raise ValueError("Frozen V1 base changed")
        if config.get("added_visual_source_ids") != list(ADDED_VISUAL_IDS):
            raise ValueError("V1.1 added visual IDs differ from authorized boundary")
        h = config.get("visual_boundary_hypothesis", {})
        if (h.get("effect_evidence") != "INFERRED" or
                h.get("magnitude_evidence") != "ENGINEERING ASSUMPTION" or
                h.get("exact_pair_biology") != "UNKNOWN" or
                h.get("source") != "docs/ELECTRICAL_MODEL_V1_1_READINESS.md"):
            raise ValueError("V1.1 boundary hypothesis provenance missing")
        old = json.loads(V1_CONFIG.read_text(encoding="utf-8"))
        comparable = deepcopy(config)
        for key in ("base_config_sha256", "added_visual_source_ids", "visual_boundary_hypothesis"):
            comparable.pop(key)
        comparable["schema_version"] = 1
        comparable["model_id"] = old["model_id"]
        comparable["source_id_sha256"] = old["source_id_sha256"]
        if comparable != old or config["model_id"] != "male-cns-circuit-117-electrical-v1.1":
            raise ValueError("V1.1 changed a frozen V1 policy outside the visual boundary")
    elif config_path.resolve() != V1_CONFIG.resolve():
        raise ValueError("V1 must use the frozen default configuration")
    if (config["plasticity_enabled"] is not False or
            parameter(config["neutral_sensory_current_pa"]) != 0):
        raise ValueError("Neutral mode must disable plasticity and sensory transients")
    expected = {"neurons.parquet": config["parent_neurons_sha256"],
                "connections.parquet": config["parent_connections_sha256"]}
    for name, sha in expected.items():
        if file_sha(Path(parent) / name) != sha:
            raise ValueError(f"Pinned parent changed: {name}")
    if file_sha(Path(candidate_path)) != config["plastic_candidates_sha256"]:
        raise ValueError("Pinned candidate contact table changed")
    raw_nodes = pq.read_table(Path(parent) / "neurons.parquet", columns=[
        "source_id", "runtime_index", "cell_type", "soma_side", "status", "transmitter_consensus"]).to_pylist()
    kcs = {n["source_id"] for n in raw_nodes if n["cell_type"] == "KCg-d" and n["soma_side"] == "R"}
    if len(kcs) != 107:
        raise ValueError("Right KC class drifted")
    visual_ids = {13285, 13707, 13874} | (set(ADDED_VISUAL_IDS) if version == 2 else set())
    ids = kcs | visual_ids | {10540, 14182, 519131, 519624, 523769}
    expected_nodes = 117 if version == 2 else 115
    if len(ids) != expected_nodes or hashlib.sha256(np.asarray(sorted(ids), dtype="<i8").tobytes()).hexdigest() != config["source_id_sha256"]:
        raise ValueError("Selected source identity drifted")
    node_by_id = {n["source_id"]: n for n in raw_nodes if n["source_id"] in ids}
    if len(node_by_id) != expected_nodes or any(n["status"] != "Traced" for n in node_by_id.values()):
        raise ValueError("Missing/untraced selected source body")
    if version == 2 and any(node_by_id[i]["cell_type"] != "aMe12" or
                            node_by_id[i]["soma_side"] != "R" or
                            node_by_id[i]["transmitter_consensus"] != "acetylcholine"
                            for i in ADDED_VISUAL_IDS):
        raise ValueError("Added source bodies differ from audited right aMe12 identity")
    cells = tuple(SourceCell(i, _kind(i, kcs, visual_ids), node_by_id[i]["runtime_index"],
                             node_by_id[i]["transmitter_consensus"]) for i in sorted(ids))
    by_runtime = {c.source_runtime_index: i for i, c in enumerate(cells)}
    by_id = {c.source_id: i for i, c in enumerate(cells)}
    candidates = pq.read_table(candidate_path, columns=["body_pre", "body_post", "source_partner_row"]).to_pylist()
    candidate_by_pair: dict[tuple[int, int], int] = defaultdict(int)
    partner_rows = []
    for r in candidates:
        if r["body_pre"] not in kcs or r["body_post"] != 519131:
            raise ValueError("Candidate contact outside approved KC→MBON32 block")
        candidate_by_pair[(r["body_pre"], r["body_post"])] += 1
        partner_rows.append(r["source_partner_row"])
    if len(candidates) != 796 or len(candidate_by_pair) != 100 or len(set(partner_rows)) != 796:
        raise ValueError("Restricted plastic candidate mask drifted")
    connections = []
    for batch in pq.ParquetFile(Path(parent) / "connections.parquet").iter_batches(
            batch_size=500_000, columns=["source_row", "pre_index", "post_index", "synapse_count"]):
        pre, post = batch["pre_index"].to_numpy(), batch["post_index"].to_numpy()
        keep = np.isin(pre, list(by_runtime)) & np.isin(post, list(by_runtime))
        rows = np.flatnonzero(keep)
        count = batch["synapse_count"].to_numpy()
        source_row = batch["source_row"].to_numpy()
        for j in rows:
            pi, qi = by_runtime[int(pre[j])], by_runtime[int(post[j])]
            p, q = cells[pi], cells[qi]
            state, evidence, per_contact = _effect(p, q, config)
            n = int(count[j])
            cand = candidate_by_pair.get((p.source_id, q.source_id), 0)
            if cand > n or (cand and state != "ACTIVE_FAST"):
                raise ValueError("Plastic candidate exceeds or conflicts with source pair")
            connections.append(SourceConnection(int(source_row[j]), pi, qi, n, state, evidence,
                                                None if per_contact is None else per_contact * n, cand))
    connections.sort(key=lambda c: (c.pre, c.post, c.source_row))
    if version == 1 and (len(connections) != 10009 or sum(c.contacts for c in connections) != 45010):
        raise ValueError("115-body induced anatomy differs from audited route")
    if version == 2:
        added = [e for e in connections if cells[e.pre].source_id in ADDED_VISUAL_IDS and
                 cells[e.post].kind == "KC"]
        if len(added) != 48 or sum(e.contacts for e in added) != 569:
            raise ValueError("V1.1 visual→KC source pairs differ from B5.2 audit")
    if sum(c.candidate_contacts for c in connections) != 796 or sum(c.candidate_contacts > 0 for c in connections) != 100:
        raise ValueError("Candidate pair/contact mask differs from approved screen")
    if len({c.source_row for c in connections}) != len(connections):
        raise ValueError("Duplicate parent source row")
    return CircuitDefinition(cells, tuple(connections), tuple(sorted(partner_rows)), config,
                             file_sha(config_path), expected)
