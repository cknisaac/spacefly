"""Extract exact critical-route partner contacts, with immutable source-row provenance."""
from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/raw/malecns_v1/syn-partners-male-cns-v1.0-minconf-0.5-traced-only.feather"
DEST = ROOT / "data/processed/malecns_v1_route_closure"


def main():
    receipt = json.loads(SOURCE.with_name(SOURCE.name + ".receipt.json").read_text())
    assert SOURCE.stat().st_size == receipt["bytes"]
    prior = json.loads((ROOT / "docs/figures/circuit_v1_critical_route_anatomy.json").read_text())
    kcs = np.array(prior["kc_ids"], dtype=np.int64)
    DEST.mkdir(exist_ok=True)
    reader = pa.ipc.open_file(pa.memory_map(str(SOURCE)))
    selected = []
    offset = 0
    for index in range(reader.num_record_batches):
        b = reader.get_batch(index)
        pre, post = b["body_pre"].to_numpy(), b["body_post"].to_numpy()
        keep = (np.isin(pre, [14182, 11752]) | np.isin(post, [519624, 523769]) |
                (np.isin(pre, kcs) & (post == 519131)) |
                ((pre == 519131) & np.isin(post, [10975, 10360])))
        if keep.any():
            t = pa.Table.from_batches([b]).filter(pa.array(keep))
            t = t.append_column("source_partner_row", pa.array(np.flatnonzero(keep) + offset))
            selected.append(t)
        offset += len(b)
    assert offset == 124025046, offset
    table = pa.concat_tables(selected)
    pq.write_table(table, DEST / "critical_partners.parquet", compression="zstd")
    rows = table.to_pylist()
    blocks = {
        "KCg-d_R_to_MBON32": [r for r in rows if r["body_pre"] in set(kcs) and r["body_post"] == 519131],
        "PPL103_R_to_KCg-d_R": [r for r in rows if r["body_pre"] == 14182 and r["body_post"] in set(kcs)],
        "PPL103_L_to_KCg-d_R": [r for r in rows if r["body_pre"] == 11752 and r["body_post"] in set(kcs)],
    }
    for pre, post in [(14182,519131),(11752,519131),(519131,519624),(519131,523769),
                      (519624,523769),(519131,10975),(519131,10360)]:
        blocks[f"{pre}_to_{post}"] = [r for r in rows if r["body_pre"] == pre and r["body_post"] == post]
    summaries = {}
    for name, block in blocks.items():
        summaries[name] = {"contacts": len(block),
            "pairs": len({(r["body_pre"],r["body_post"]) for r in block}),
            "primary_post": dict(Counter(r["primary_post"] for r in block)),
            "unique_presynaptic_sites": len({(r["x_pre"],r["y_pre"],r["z_pre"]) for r in block}),
            "post_xyz_min": [min((r[f"{axis}_post"] for r in block),default=None) for axis in "xyz"],
            "post_xyz_max": [max((r[f"{axis}_post"] for r in block),default=None) for axis in "xyz"]}
    assert summaries["KCg-d_R_to_MBON32"]["contacts"] == 1129
    assert summaries["PPL103_R_to_KCg-d_R"]["contacts"] == 743
    for name, count in [("14182_to_519131",219),("519131_to_519624",38),
                        ("519131_to_523769",55),("519624_to_523769",255)]:
        assert summaries[name]["contacts"] == count, (name,summaries[name])
    for body, expected in [(519624,17716),(523769,23957)]:
        assert sum(r["body_post"]==body for r in rows)==expected
    report = {"source": receipt, "source_rows": offset,"extracted_rows":len(rows),
              "blocks":summaries,"output_sha256":hashlib.sha256((DEST/"critical_partners.parquet").read_bytes()).hexdigest()}
    (ROOT/"docs/figures/circuit_v1_route_closure_partners.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))


if __name__ == "__main__":
    main()
