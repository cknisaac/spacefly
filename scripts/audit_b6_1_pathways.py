"""Read-only MaleCNS pair/identity audit for the bounded B6.1 pathways."""
from pathlib import Path
from collections import defaultdict
import hashlib, json
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

ROOT=Path(__file__).resolve().parents[1]
PARENT=ROOT/'data/processed/malecns_v1_traced'
OUT=ROOT/'docs/figures/b6_1_pathway_comparison'
OUT.mkdir(parents=True,exist_ok=True)
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()
receipt=json.loads((PARENT/'validation_receipt.json').read_text())
for name in ('neurons.parquet','connections.parquet'):
    assert sha(PARENT/name)==receipt['files'][name]['sha256']
ns=pq.read_table(PARENT/'neurons.parquet').to_pylist()
es=pq.read_table(PARENT/'connections.parquet')
pre=es['pre_index'].to_numpy();post=es['post_index'].to_numpy()
count=es['synapse_count'].to_numpy();source_row=es['source_row'].to_numpy()
by_id={n['source_id']:i for i,n in enumerate(ns)}
kc_indices=np.array([i for i,n in enumerate(ns) if n['cell_class']=='Kenyon_Cell'],dtype=np.uint32)
kc_pre_mask=np.isin(pre,kc_indices)
ref=json.loads((ROOT/'docs/figures/b1_mvp_pathway_rule_selection/anatomy_comparison.json').read_text())
families={
 'gamma2_alpha_prime1':{'mbon':'MBON12','dan':['PPL103']},
 'gamma5_beta_prime2a':{'mbon':'MBON01','dan':['PAM01','PAM15']},
 'gamma1pedc':{'mbon':'MBON11','dan':['PPL101']},
}
def cell(i):
    n=ns[int(i)]
    return {k:n[k] for k in ('source_id','cell_type','instance','soma_side','cell_class','superclass','transmitter_consensus')}
def edge(j):
    return {'pre_id':ns[int(pre[j])]['source_id'],'post_id':ns[int(post[j])]['source_id'],
            'contacts':int(count[j]),'source_row':int(source_row[j])}
result={'stage_id':'MVP-B6.1','dataset':'MaleCNS v1.0 traced-only minconf-0.5',
        'parent_hashes':{name:receipt['files'][name]['sha256'] for name in ('neurons.parquet','connections.parquet')},
        'source_manifest_sha256':sha(ROOT/'data/raw/malecns_v1/source_manifest.json'),
        'scope':'Aggregate cell-pair counts; no per-contact ROI or synaptic physiology in this product.',
        'families':{}}
for key,spec in families.items():
    mb=[i for i,n in enumerate(ns) if n['cell_type']==spec['mbon']]
    da=[i for i,n in enumerate(ns) if n['cell_type'] in spec['dan'] and n['cell_class']=='DAN']
    mb_set=set(mb);da_set=set(da)
    family={'mbons':[cell(i) for i in mb], 'dans':[cell(i) for i in da], 'mbon_cases':[]}
    for mi in mb:
        b1=next(c for c in ref['candidates'] if c['mbon']['source_id']==ns[mi]['source_id'])
        kin=np.flatnonzero((post==mi)&kc_pre_mask)
        # Reuse the exact B1 KC-class screen, then select only those source indices.
        kset={int(pre[j]) for j in kin}
        din=np.flatnonzero((post==mi)&np.isin(pre,da))
        dkc=np.flatnonzero(np.isin(pre,da)&np.isin(post,list(kset)))
        route=b1['top_30_two_hop_routes'][0] if b1['top_30_two_hop_routes'] else None
        direct=b1['direct_dn']
        selected=set(kset)|da_set|mb_set
        if route:
            selected|={by_id[route['edges'][0]['post']['source_id']],by_id[route['edges'][1]['post']['source_id']]}
        chosen_route={'first':{'pre_id':route['edges'][0]['pre']['source_id'],'post_id':route['edges'][0]['post']['source_id'],'post_type':route['edges'][0]['post']['cell_type'],'contacts':route['edges'][0]['contacts'],'source_row':route['edges'][0]['source_row']},
                      'second':{'pre_id':route['edges'][1]['pre']['source_id'],'post_id':route['edges'][1]['post']['source_id'],'post_type':route['edges'][1]['post']['cell_type'],'contacts':route['edges'][1]['contacts'],'source_row':route['edges'][1]['source_row']}} if route else None
        endpoints=[mi]
        if route:endpoints += [by_id[route['edges'][0]['post']['source_id']],by_id[route['edges'][1]['post']['source_id']]]
        coverage=[]
        for ei in endpoints:
            mask=post==ei
            coverage.append({'source_id':ns[ei]['source_id'],'all_in_contacts':int(count[mask].sum()),
                             'retained_in_contacts_if_only_listed_roster':int(count[mask&np.isin(pre,list(selected))].sum())})
        family['mbon_cases'].append({'mbon_id':ns[mi]['source_id'],
            'kc_population':[cell(i) for i in sorted(kset,key=lambda i:ns[i]['source_id'])],
            'kc_to_mbon_candidate_pairs':[edge(j) for j in kin],
            'dan_to_mbon_pairs':[edge(j) for j in din],
            'dan_to_kc_pairs':[edge(j) for j in dkc],
            'direct_descending_pairs':[{'post_id':r['post']['source_id'],'post_type':r['post']['cell_type'],'contacts':r['contacts'],'source_row':r['source_row']} for r in direct],
            'top_two_hop_descending_route':chosen_route,
            'illustrative_roster_incoming_coverage':coverage})
    result['families'][key]=family
raw=ROOT/'data/raw/malecns_v1/connectome-weights-male-cns-v1.0-minconf-0.5-traced-only.feather'
source_manifest=json.loads((ROOT/'data/raw/malecns_v1/source_manifest.json').read_text())
expected=next(x['sha256'] for x in source_manifest['objects'] if x['name']==raw.name)
assert sha(raw)==expected
requested={}
for family in result['families'].values():
    for case in family['mbon_cases']:
        for label in ('kc_to_mbon_candidate_pairs','dan_to_mbon_pairs','dan_to_kc_pairs'):
            for item in case[label]:requested[item['source_row']]=item
        route=case['top_two_hop_descending_route']
        if route:
            for label in ('first','second'):
                item=route[label];requested[item['source_row']]=item
reader=pa.ipc.open_file(pa.memory_map(str(raw)))
row_ids=np.array(sorted(requested),dtype=np.int64)
offset=checked=0
for bi in range(reader.num_record_batches):
    batch=reader.get_batch(bi)
    lo=np.searchsorted(row_ids,offset);hi=np.searchsorted(row_ids,offset+len(batch))
    for rid in row_ids[lo:hi]:
        item=requested[int(rid)];record=batch.slice(int(rid)-offset,1).to_pylist()[0]
        assert int(record['body_pre'])==item['pre_id'] and int(record['body_post'])==item['post_id']
        assert int(record['weight'])==item['contacts']
        checked+=1
    offset+=len(batch)
assert checked==len(requested)
result['raw_verification']={'raw_source_sha256':expected,'unique_critical_rows_checked':checked,
                            'normalized_parent_hashes_match':True}
(OUT/'malecns_identity_ledger.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:[{'mbon':v['mbon_id'],'kc':len(v['kc_population']),
                      'plastic_pair_contacts':sum(e['contacts'] for e in v['kc_to_mbon_candidate_pairs']),
                      'dan_kc_pairs':len(v['dan_to_kc_pairs']),
                      'dan_mbon_pairs':len(v['dan_to_mbon_pairs']),
                      'route':v['top_two_hop_descending_route'],
                      'coverage':v['illustrative_roster_incoming_coverage']} for v in f['mbon_cases']]
                  for k,f in result['families'].items()},indent=2))
