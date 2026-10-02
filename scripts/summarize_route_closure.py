"""Reproduce contact candidacy and DN boundary accounting; no neural model."""
from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "docs/figures"
DATA = ROOT / "data/processed/malecns_v1_route_closure"
PARENT = ROOT / "data/processed/malecns_v1_traced"


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    expected = {
        "neurons.parquet": "7d9a410d61d4caa934fa3639f9d204291ff0d18c445b2384054b95286d6350eb",
        "connections.parquet": "da21af867d4e8e4c627c9916e55af4332302b611a296de1d0a8bc7dd6ebcff7a",
    }
    for name, sha in expected.items():
        assert digest(PARENT / name) == sha
    prior = json.loads((FIG / "circuit_v1_critical_route_anatomy.json").read_text())
    kcs = set(prior["kc_ids"])
    selected = kcs | {13285, 13707, 13874, 10540, 14182, 519131, 519624, 523769}
    assert len(selected) == 115
    assert hashlib.sha256(np.array(sorted(selected), dtype="<i8").tobytes()).hexdigest() == "7b19610ab5c6ec6d295bde7de59da3898b7f27503e553a40b3ceee9e8ec12969"
    rows = pq.read_table(DATA / "compartment_contacts.parquet").to_pylist()
    def gamma2(r):
        return r["subprimary_pre_mask"] == r["subprimary_post_mask"] == "g2(R)"
    kc_mbon = [r for r in rows if r["body_pre"] in kcs and r["body_post"] == 519131]
    da_kc = [r for r in rows if r["body_pre"] == 14182 and r["body_post"] in kcs and gamma2(r)]
    da_targets = {r["body_post"] for r in da_kc}
    gamma_candidates = [r for r in kc_mbon if gamma2(r)]
    candidates = [r for r in gamma_candidates if r["body_pre"] in da_targets]
    assert (len(kc_mbon), len(gamma_candidates), len(candidates)) == (1129, 808, 796)
    assert len({r["body_pre"] for r in candidates}) == 100
    assert len(da_targets) == 102 and len(da_kc) == 408
    critical = [r for r in rows if r in kc_mbon or
                (r["body_pre"] in {14182, 11752} and r["body_post"] in kcs | {519131})]
    assert not any("UNKNOWN_MISSING_CHUNK" in (r["subprimary_pre_mask"], r["subprimary_post_mask"]) for r in critical)
    dest = DATA / "plastic_contact_candidates_anatomy_only.parquet"
    pq.write_table(pa.Table.from_pylist(candidates), dest, compression="zstd")
    candidate_summary = {
        "classification": "INFERRED anatomical candidacy, not measured plasticity or an active mask",
        "rule": "KC->519131 both endpoints g2(R), and 14182->same KC has >=1 both-endpoints g2(R) contact",
        "all_contacts": len(kc_mbon), "both_gamma2_contacts": len(gamma_candidates),
        "both_gamma2_kc_ids": sorted({r["body_pre"] for r in gamma_candidates}),
        "candidate_contacts": len(candidates), "candidate_kc_ids": sorted({r["body_pre"] for r in candidates}),
        "excluded_contacts": len(kc_mbon) - len(candidates),
        "gamma2_kcs_without_strict_same_kc_dan_contact": sorted({r["body_pre"] for r in gamma_candidates} - da_targets),
        "joint_roi_counts": dict(Counter(r["subprimary_pre_mask"] + " -> " + r["subprimary_post_mask"] for r in kc_mbon)),
        "output_sha256": digest(dest),
    }
    nodes = pq.read_table(PARENT / "neurons.parquet").to_pylist()
    ids = np.array([n["source_id"] for n in nodes])
    dn_ix = np.flatnonzero(np.isin(ids, [519624, 523769]))
    incoming = {str(i): [] for i in [519624, 523769]}
    for batch in pq.ParquetFile(PARENT / "connections.parquet").iter_batches(
            columns=["pre_index", "post_index", "synapse_count", "source_row"], batch_size=500000):
        pre, post = batch["pre_index"].to_numpy(), batch["post_index"].to_numpy()
        counts, source = batch["synapse_count"].to_numpy(), batch["source_row"].to_numpy()
        for j in np.flatnonzero(np.isin(post, dn_ix)):
            n = nodes[int(pre[j])]
            incoming[str(ids[post[j]])].append({"pre": n["source_id"], "cell_type": n["cell_type"],
                "instance": n["instance"], "nt": n["transmitter_consensus"], "contacts": int(counts[j]),
                "source_row": int(source[j]), "retained": n["source_id"] in selected})
    partner_rows = pq.read_table(DATA / "critical_partners.parquet").to_pylist()
    dn_summary = {}
    outside = set()
    pfl_ids = set()
    for dn, ins in incoming.items():
        direct = Counter(r["body_pre"] for r in partner_rows if r["body_post"] == int(dn))
        assert direct == {r["pre"]: r["contacts"] for r in ins}, dn
        retained = [r for r in ins if r["retained"]]
        missing = [r for r in ins if not r["retained"]]
        total = sum(r["contacts"] for r in ins)
        kept = sum(r["contacts"] for r in retained)
        nt, types = Counter(), Counter()
        for r in missing:
            outside.add(r["pre"])
            nt[r["nt"]] += r["contacts"]
            types[r["cell_type"] or "UNKNOWN"] += r["contacts"]
        pfl = [r for r in missing if r["cell_type"] in {"PFL2", "PFL3"}]
        pfl_ids.update(r["pre"] for r in pfl)
        pfl_contacts = sum(r["contacts"] for r in pfl)
        dn_summary[dn] = {"parent_pairs": len(ins), "parent_contacts": total,
            "retained_pairs": len(retained), "retained_contacts": kept, "retained_sources": retained,
            "missing_pairs": len(missing), "missing_contacts": total - kept,
            "missing_percent_contacts": 100 * (total - kept) / total,
            "missing_contacts_by_consensus_transmitter": dict(nt),
            "top_missing_types": types.most_common(12), "PFL2_PFL3_additional_contacts": pfl_contacts,
            "retained_percent_after_hypothetical_PFL_expansion": 100 * (kept + pfl_contacts) / total}
    assert (dn_summary["519624"]["parent_contacts"], dn_summary["519624"]["retained_contacts"]) == (17716, 42)
    assert (dn_summary["523769"]["parent_contacts"], dn_summary["523769"]["retained_contacts"]) == (23957, 310)
    assert len(outside) == 1420 and len(pfl_ids) == 24
    (FIG / "circuit_v1_route_closure_dn_inputs.json").write_text(json.dumps(incoming, indent=2) + "\n")
    report = {"purpose": "data-only route closure", "parent_sha256": expected,
        "candidates": candidate_summary, "descending_inputs": dn_summary,
        "distinct_missing_presynaptic_bodies": len(outside), "hypothetical_PFL_expansion_ids": sorted(pfl_ids),
        "source_data_sha256": {p.name: digest(p) for p in [DATA / "critical_partners.parquet", DATA / "compartment_contacts.parquet"]}}
    (FIG / "circuit_v1_route_closure_summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"candidate_contacts": len(candidates), "candidate_pairs": 100,
        "DN03_missing_contacts": 17674, "DN02_missing_contacts": 23647,
        "parent_partner_agreement": "every incoming source pair/count matched", "status": "passed"}, indent=2))


if __name__ == "__main__":
    main()
