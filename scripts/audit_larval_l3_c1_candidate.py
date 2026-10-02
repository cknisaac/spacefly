"""Audit a revised larval DAN-c1 / MBON-c1 candidate from S1.

This script reports anatomical counts only; it does not infer signs, efficacy,
plasticity, or functional motor control.
"""
from __future__ import annotations
import csv, hashlib, io, json, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'data/raw/larval_l1em/supplementary_data_s1.zip'
OUTPUT = ROOT / 'data/raw/larval_l1em/candidate_l3_c1_audit.json'
ROLES = {
    'DAN-c1': {15_592_096, 16_240_569},
    'MBON-c1': {8_980_589, 16_223_537},
    'MBON-m1': {4_022_539, 17_016_974},
    'MBON-d1': {4_241_237, 7_055_857},
}

def main() -> None:
    with zipfile.ZipFile(ARCHIVE) as archive:
        raw_annotations = archive.open('Supplementary-Data-S1/annotations.csv')
        annotations: dict[int, dict[str, str]] = {}
        for row in csv.DictReader(io.TextIOWrapper(raw_annotations, encoding='utf-8-sig', newline='')):
            for side, field in (('L', 'left_id'), ('R', 'right_id')):
                if row[field] != 'no pair':
                    annotations[int(row[field])] = {
                        'celltype': row['celltype'],
                        'label': row['additional_annotations'],
                        'hemisphere': side,
                    }
        wanted_targets = set().union(*ROLES.values())
        role_by_id = {neuron_id: role for role, ids in ROLES.items() for neuron_id in ids}
        dan_edges: list[dict] = []
        mbon_outputs: dict[int, list[dict]] = {i: [] for i in ROLES['MBON-c1']}
        kc_ids = {i for i, ann in annotations.items() if ann['celltype'] == 'KC'}
        kc_edges: list[dict] = []
        with archive.open('Supplementary-Data-S1/ad_connectivity_matrix.csv') as raw:
            reader = csv.reader(io.TextIOWrapper(raw, encoding='utf-8-sig', newline=''))
            target_ids = [int(value) for value in next(reader)[1:]]
            target_index = {neuron_id: i for i, neuron_id in enumerate(target_ids)}
            for row in reader:
                pre = int(row[0])
                if pre in ROLES['DAN-c1']:
                    for post in ROLES['MBON-c1'] | ROLES['MBON-m1'] | ROLES['MBON-d1']:
                        if post in target_index:
                            contacts = int(float(row[target_index[post] + 1]))
                            if contacts:
                                dan_edges.append({'pre_id': pre, 'post_id': post,
                                                  'contacts': contacts,
                                                  'post_role': role_by_id[post]})
                if pre in ROLES['MBON-c1']:
                    for post, value in zip(target_ids, row[1:]):
                        contacts = int(float(value))
                        ann = annotations.get(post)
                        if contacts and ann and ann['celltype'] in {'DN-VNC', 'pre-DN-VNC'}:
                            mbon_outputs[pre].append({'post_id': post, 'contacts': contacts,
                                                     'celltype': ann['celltype'],
                                                     'label': ann['label']})
                if pre in kc_ids:
                    for post in ROLES['MBON-c1']:
                        if post in target_index:
                            contacts = int(float(row[target_index[post] + 1]))
                            if contacts:
                                kc_edges.append({'pre_id': pre, 'post_id': post,
                                                 'contacts': contacts})
    result = {
        'candidate_id': 'larval_L3_DAN-c1_MBON-c1_provisional',
        'source': 'Winding et al. 2023 Supplementary Data S1 / ad_connectivity_matrix.csv',
        'archive_sha256': hashlib.sha256(ARCHIVE.read_bytes()).hexdigest().upper(),
        'direction': 'row/presynaptic -> column/postsynaptic',
        'ids_by_role': {role: sorted(ids) for role, ids in ROLES.items()},
        'DANc1_to_MBON_edges': sorted(dan_edges, key=lambda e: (e['pre_id'], e['post_id'])),
        'KC_to_MBONc1_edges': sorted(kc_edges, key=lambda e: (e['pre_id'], e['post_id'])),
        'KC_to_MBONc1_edge_count': len(kc_edges),
        'KC_to_MBONc1_contact_count': sum(e['contacts'] for e in kc_edges),
        'KC_to_MBONc1_pair_counts': {
            str(post): {'edge_count': sum(e['post_id'] == post for e in kc_edges),
                        'contacts': sum(e['contacts'] for e in kc_edges if e['post_id'] == post)}
            for post in sorted(ROLES['MBON-c1'])
        },
        'MBONc1_direct_descending_edges': {
            str(pre): sorted(rows, key=lambda e: (-e['contacts'], e['post_id']))
            for pre, rows in sorted(mbon_outputs.items())
        },
        'limits': [
            'Anatomical contacts do not establish sign, efficacy, plasticity, or action control.',
            'KC partner counts are whole-cell totals; local contact coordinates are not included here.',
            'Connectome is first-instar; functional DAN-c1 learning studies are third-instar.',
        ],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(f'Wrote {OUTPUT.relative_to(ROOT)}')
    print(json.dumps({k: result[k] for k in ('candidate_id', 'archive_sha256',
          'DANc1_to_MBON_edges', 'KC_to_MBONc1_edge_count',
          'KC_to_MBONc1_contact_count', 'KC_to_MBONc1_pair_counts')}, indent=2))

if __name__ == '__main__':
    main()
