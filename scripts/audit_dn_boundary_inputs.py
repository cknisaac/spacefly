"""Data-only DN boundary composition; no electrical model or parameter fitting."""
from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / 'docs/figures'


def main():
    path = ROOT / 'data/processed/malecns_v1_traced/neurons.parquet'
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    assert sha == '7d9a410d61d4caa934fa3639f9d204291ff0d18c445b2384054b95286d6350eb'
    nodes = {n['source_id']: n for n in pq.read_table(path).to_pylist()}
    ledger_path = FIG / 'circuit_v1_route_closure_dn_inputs.json'
    ledger = json.loads(ledger_path.read_text())
    omitted = {dn: [r for r in rows if not r['retained']] for dn, rows in ledger.items()}
    sets = [{r['pre'] for r in rows} for rows in omitted.values()]
    common = set.intersection(*sets)
    assert len(common) == 430 and len(set.union(*sets)) == 1420
    results = {}
    for dn, rows in omitted.items():
        nt, classes, superclass = Counter(), Counter(), Counter()
        confidence, missing, conflict, annotated = [], [], [], []
        for r in rows:
            n = nodes[r['pre']]
            assert n['cell_type'] == r['cell_type'] and n['transmitter_consensus'] == r['nt']
            nt[r['nt']] += r['contacts']
            classes[r['cell_type'] or 'UNKNOWN'] += r['contacts']
            superclass[n['superclass'] or 'UNKNOWN'] += r['contacts']
            c = n['transmitter_confidence']
            (missing if c is None else confidence).append(r if c is None else c)
            if n['transmitter_predicted'] != n['transmitter_consensus']:
                conflict.append(r)
            if n['transmitter_ground_truth'] is not None:
                annotated.append(r)
        c = np.array(confidence)
        shared_contacts = sum(r['contacts'] for r in rows if r['pre'] in common)
        results[dn] = {
            'omitted_pairs': len(rows), 'omitted_contacts': sum(r['contacts'] for r in rows),
            'distinct_cell_types_including_unknown': len(classes),
            'top_types_by_contacts': classes.most_common(12),
            'contacts_by_superclass': dict(superclass), 'contacts_by_consensus_nt': dict(nt),
            'common_parent_contacts': shared_contacts,
            'prediction_confidence_unweighted_parent_quantiles_min_q25_median_q75_max': np.quantile(c,[0,.25,.5,.75,1]).tolist(),
            'missing_prediction_confidence_pairs': len(missing),
            'missing_prediction_confidence_contacts': sum(r['contacts'] for r in missing),
            'prediction_consensus_disagreement_pairs': len(conflict),
            'prediction_consensus_disagreement_contacts': sum(r['contacts'] for r in conflict),
            'ground_truth_annotation_nonnull_pairs': len(annotated),
            'ground_truth_annotation_nonnull_contacts': sum(r['contacts'] for r in annotated),
        }
    report = {'purpose': 'anatomical and annotation audit, not physiological inference',
        'parent_neurons_sha256': sha, 'input_ledger_sha256': hashlib.sha256(ledger_path.read_bytes()).hexdigest(),
        'common_omitted_parent_ids': sorted(common), 'common_parent_count': len(common),
        'distinct_omitted_parent_count': len(set.union(*sets)), 'targets': results,
        'confidence_semantics': 'presynaptic individual predicted_nt_confidence, not consensus confidence or target-effect probability'}
    (FIG / 'dn_boundary_input_audit.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'shared_parents':len(common),'targets':results},indent=2))


if __name__ == '__main__':
    main()
