"""Map critical contact coordinates to pinned public MaleCNS subcompartment masks.

Data evidence only. No electrical, dopamine diffusion or plasticity model.
Decoder follows Neuroglancer's public compressed-segmentation specification.
"""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import base64
import gzip
import hashlib
import json
from pathlib import Path
import struct
import urllib.error
import urllib.request
from urllib.parse import quote

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data/raw/malecns_v1/route_closure_roi"
VOLUME = "rois/malecns-subcompartments-v3"
SCENE = "v1.0/database/neuprint-inputs/male-cns:v1.0.json"


def fetch(name):
    path = CACHE / name
    receipt_path = path.with_name(path.name + ".receipt.json")
    if path.exists() and receipt_path.exists():
        receipt = json.loads(receipt_path.read_text())
        data = path.read_bytes()
        assert hashlib.sha256(data).hexdigest() == receipt["sha256"]
    else:
        with urllib.request.urlopen("https://storage.googleapis.com/storage/v1/b/flyem-male-cns/o/" + quote(name, safe=""), timeout=40) as r:
            meta = json.load(r)
        url = "https://storage.googleapis.com/flyem-male-cns/" + quote(name, safe="/") + "?generation=" + meta["generation"]
        req = urllib.request.Request(url, headers={"Accept-Encoding": "gzip"})
        with urllib.request.urlopen(req, timeout=40) as r:
            data = r.read()
        assert len(data) == int(meta["size"]), name
        assert base64.b64encode(hashlib.md5(data, usedforsecurity=False).digest()).decode() == meta["md5Hash"], name
        receipt = {"name": name, "url": url, "generation": meta["generation"],
                   "bytes": len(data), "md5_base64": meta["md5Hash"], "sha256": hashlib.sha256(data).hexdigest()}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    decoded = gzip.decompress(data) if data[:2] == b"\x1f\x8b" else data
    return decoded, receipt


def sample_chunk(data, xyz, shape, block):
    words = np.frombuffer(data, dtype="<u4")
    assert int(words[0]) == 1
    w = words[1:]
    grid = (np.array(shape) + block - 1) // block
    block_pos = xyz // block
    index = block_pos[:, 0] + grid[0] * (block_pos[:, 1] + grid[1] * block_pos[:, 2])
    first, encoded = w[2 * index], w[2 * index + 1].astype(np.int64)
    bits = (first >> 24).astype(np.int64)
    assert set(bits) <= {0, 1, 2, 4, 8, 16, 32}
    lookup = (first & 0xffffff).astype(np.int64)
    local = xyz % block
    position = local[:, 0] + block[0] * (local[:, 1] + block[1] * local[:, 2])
    bit_offset = bits * position
    code = np.zeros(len(xyz), dtype=np.uint64)
    active = bits > 0
    code[active] = ((w[encoded[active] + bit_offset[active] // 32].astype(np.uint64) >>
                     (bit_offset[active] % 32).astype(np.uint64)) &
                    ((np.uint64(1) << bits[active].astype(np.uint64)) - np.uint64(1)))
    ix = lookup + 2 * code.astype(np.int64)
    return w[ix].astype(np.uint64) | (w[ix + 1].astype(np.uint64) << np.uint64(32))


def decoder_check():
    # Independent manually packed two-label block, including a nonzero high word.
    data = struct.pack('<8I', 1, 3 | (1 << 24), 2, 0b10100110, 196, 0, 7, 1)
    xyz = np.array([[x, y, z] for z in range(2) for y in range(2) for x in range(2)])
    expected = [196, 2**32+7, 2**32+7, 196, 196, 2**32+7, 196, 2**32+7]
    assert sample_chunk(data, xyz, np.array([2,2,2]), np.array([2,2,2])).tolist() == expected
    constant = struct.pack('<5I', 1, 2, 0, 196, 0)
    assert (sample_chunk(constant, xyz, np.array([2,2,2]), np.array([2,2,2])) == 196).all()


def main():
    decoder_check()
    receipts = []
    scene, rec = fetch(SCENE); receipts.append(rec)
    assert VOLUME in scene.decode()
    raw, rec = fetch(VOLUME + "/info"); receipts.append(rec); info = json.loads(raw)
    raw, rec = fetch(VOLUME + "/segment_properties/info"); receipts.append(rec); props = json.loads(raw)["inline"]
    labels = {0: "<unspecified>", 2**64-1: "UNKNOWN_MISSING_CHUNK"}
    labels.update({int(i): name for i, name in zip(props["ids"],props["properties"][0]["values"])})
    scale = info["scales"][0]
    assert scale["resolution"] == [256.0]*3 and scale["voxel_offset"] == [0]*3
    assert info["data_type"] == "uint64" and info["num_channels"] == 1
    size = np.array(scale["size"]); chunk = np.array(scale["chunk_sizes"][0]); block = np.array(scale["compressed_segmentation_block_size"])
    table = pq.read_table(ROOT / "data/processed/malecns_v1_route_closure/critical_partners.parquet")
    kcs = set(json.loads((ROOT / "docs/figures/circuit_v1_critical_route_anatomy.json").read_text())["kc_ids"])
    rows = [r for r in table.to_pylist() if r["body_pre"] in [14182,11752] or (r["body_pre"] in kcs and r["body_post"]==519131)]
    coords = np.array([[r[f"{ax}_{side}"] for ax in "xyz"] for side in ["pre","post"] for r in rows])
    voxels = coords // 32  # 8-nm source coordinates -> 256-nm mask coordinates.
    assert ((voxels >= 0) & (voxels < size)).all()
    keys = voxels // chunk
    unique_keys, inverse = np.unique(keys, axis=0, return_inverse=True)
    jobs = []
    for i, key in enumerate(unique_keys):
        start=key*chunk;end=np.minimum(start+chunk,size)
        name=VOLUME+'/'+scale['key']+'/'+ '_'.join(f'{a}-{b}' for a,b in zip(start,end))
        jobs.append((i,name,start,end-start))
    def worker(job):
        i,name,start,shape=job
        ix=np.flatnonzero(inverse==i)
        try:
            data,rec=fetch(name)
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                raise
            # Never promote an absent ROI chunk into a known compartment.
            return ix,np.full(len(ix),2**64-1,dtype=np.uint64),{'name':name,'bytes':0,'status':'HTTP_404_UNKNOWN'}
        return ix,sample_chunk(data,voxels[ix]-start,shape,block),rec
    mapped=np.empty(len(coords),dtype=np.uint64)
    with ThreadPoolExecutor(max_workers=8) as pool:
        for ix, values, rec in pool.map(worker,jobs):
            mapped[ix]=values;receipts.append(rec)
    for i,r in enumerate(rows):
        r['subprimary_pre_mask']=labels[int(mapped[i])]
        r['subprimary_post_mask']=labels[int(mapped[i+len(rows)])]
    dest=ROOT/'data/processed/malecns_v1_route_closure/compartment_contacts.parquet'
    pq.write_table(pa.Table.from_pylist(rows),dest,compression='zstd')
    groups={
        'KC_to_MBON32':[r for r in rows if r['body_pre'] in kcs and r['body_post']==519131],
        'PPL103_R_to_KCs':[r for r in rows if r['body_pre']==14182 and r['body_post'] in kcs],
        'PPL103_L_to_KCs':[r for r in rows if r['body_pre']==11752 and r['body_post'] in kcs],
        'PPL103_R_to_MBON32':[r for r in rows if r['body_pre']==14182 and r['body_post']==519131],
        'PPL103_L_to_MBON32':[r for r in rows if r['body_pre']==11752 and r['body_post']==519131],
    }
    summary={}
    for name, rs in groups.items():
        safe=[r for r in rs if r['subprimary_pre_mask']==r['subprimary_post_mask']=='g2(R)']
        summary[name]={'contacts':len(rs), 'pre_roi':dict(Counter(r['subprimary_pre_mask'] for r in rs)),
          'post_roi':dict(Counter(r['subprimary_post_mask'] for r in rs)),
          'both_g2_R_contacts':len(safe),'both_g2_R_pairs':len({(r['body_pre'],r['body_post']) for r in safe})}
    report={'source_scene':SCENE,'volume':VOLUME,'resolution_nm':256,'coordinate_conversion':'floor(source_xyz_8nm / 32)',
      'decoder_spec':'https://raw.githubusercontent.com/google/neuroglancer/master/src/sliceview/compressed_segmentation/README.md',
      'decoder_manual_fixtures':'passed','source_receipts':receipts,'groups':summary,
      'output_sha256':hashlib.sha256(dest.read_bytes()).hexdigest()}
    (ROOT/'docs/figures/circuit_v1_route_closure_roi.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'chunks':len(jobs),'download_bytes':sum(r['bytes'] for r in receipts),'groups':summary},indent=2))


if __name__ == '__main__':
    main()
