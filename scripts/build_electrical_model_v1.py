"""Materialize the separately labelled 115-body electrical overlay, without running it."""

import hashlib
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from project_b.electrical_v1 import build_circuit


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/processed/malecns_v1_electrical_v1'


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    c = build_circuit()
    OUT.mkdir(parents=True, exist_ok=True)
    nodes = [{'local_index': i, 'source_id': cell.source_id, 'kind': cell.kind,
              'source_runtime_index': cell.source_runtime_index,
              'transmitter_consensus': cell.transmitter} for i, cell in enumerate(c.cells)]
    edges = [{'source_row': e.source_row,
              'pre_source_id': c.cells[e.pre].source_id, 'post_source_id': c.cells[e.post].source_id,
              'pre_local_index': e.pre, 'post_local_index': e.post,
              'source_contacts': e.contacts, 'effect_state': e.effect_state,
              'effect_evidence': e.effect_evidence, 'model_weight_pa': e.weight_pa,
              'candidate_contacts': e.candidate_contacts,
              'remaining_fixed_contacts': e.contacts - e.candidate_contacts}
             for e in c.connections]
    pq.write_table(pa.Table.from_pylist(nodes), OUT / 'neurons.parquet', compression='zstd')
    pq.write_table(pa.Table.from_pylist(edges), OUT / 'connections.parquet', compression='zstd')
    candidates = [{'source_partner_row': i} for i in c.candidate_partner_rows]
    pq.write_table(pa.Table.from_pylist(candidates), OUT / 'plastic_contact_mask_anatomy_only.parquet',
                   compression='zstd')
    files = {name: _sha(OUT / name) for name in
             ('neurons.parquet', 'connections.parquet', 'plastic_contact_mask_anatomy_only.parquet')}
    manifest = {'schema_version': 1, 'model_id': c.config['model_id'],
                'anatomy_status': 'source immutable; all induced edges retained',
                'plasticity_enabled': False, 'unknown_edge_policy': c.config['unknown_edge_policy'],
                'selected_source_id_sha256': c.config['source_id_sha256'],
                'parent_sha256': c.parent_hashes,
                'candidate_source_sha256': c.config['plastic_candidates_sha256'],
                'config_sha256': c.config_sha256, 'artifact_sha256': files,
                **c.counts()}
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
