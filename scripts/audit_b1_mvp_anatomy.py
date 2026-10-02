"""MVP-B1 read-only anatomical comparison; no simulation or learning."""
from pathlib import Path
import hashlib
import json
from collections import Counter
import numpy as np
import pyarrow.parquet as pq
import pyarrow as pa

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT / 'data/processed/malecns_v1_traced'
OUT = ROOT / 'docs/figures/b1_mvp_pathway_rule_selection'

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()

def main():
    ns = pq.read_table(PARENT/'neurons.parquet').to_pylist()
    es = pq.read_table(PARENT/'connections.parquet')
    pre = es['pre_index'].to_numpy()
    post = es['post_index'].to_numpy()
    count = es['synapse_count'].to_numpy()
    rows = es['source_row'].to_numpy()
    def neuron(i):
        n=ns[int(i)]
        assert n['runtime_index']==int(i)
        return {k:n[k] for k in ('source_id','cell_type','instance','soma_side','cell_class','superclass','transmitter_consensus')}
    def edge(j):
        return {'pre':neuron(pre[j]),'post':neuron(post[j]),'contacts':int(count[j]),'source_row':int(rows[j])}
    dn = np.array([i for i,n in enumerate(ns) if n['superclass']=='descending_neuron'],dtype=np.uint32)
    assert len(dn)>0
    to_dn=np.flatnonzero(np.isin(post,dn))
    candidates=[i for i,n in enumerate(ns) if n['cell_type'] in {'MBON01','MBON05','MBON11','MBON12','MBON32'}]
    kc=np.array([i for i,n in enumerate(ns) if n['cell_class']=='Kenyon_Cell'],dtype=np.uint32)
    dans=[i for i,n in enumerate(ns) if n['cell_class']=='DAN' and (str(n['cell_type']).startswith('PPL1') or 'y4' in str(n['instance']) or 'y5' in str(n['instance']))]
    result={'stage_id':'MVP-B1','source_hashes':{str(p.relative_to(ROOT)):sha(p) for p in [PARENT/'neurons.parquet',PARENT/'connections.parquet',ROOT/'configs/b1_mvp_pathway_rule_selection.json']},'kc_classes':dict(Counter((str(n['cell_type'])+'_'+str(n['soma_side'])) for n in ns if n['cell_class']=='Kenyon_Cell')),'dan_candidates':[neuron(i) for i in dans],'candidates':[]}
    for ci in candidates:
        outgoing=np.flatnonzero(pre==ci)
        kinput=np.flatnonzero((post==ci)&np.isin(pre,kc))
        groups={}
        for j in kinput:
            n=ns[int(pre[j])]; key=str(n['cell_type'])+'_'+str(n['soma_side'])
            g=groups.setdefault(key,{'pairs':0,'contacts':0});g['pairs']+=1;g['contacts']+=int(count[j])
        direct=[edge(j) for j in outgoing if int(post[j]) in set(map(int,dn))]
        relay={int(post[j]):j for j in outgoing if post[j]!=ci}
        two=[]
        for j in to_dn[np.isin(pre[to_dn],list(relay))]:
            a=relay[int(pre[j])]
            if post[j]==ci: continue
            two.append({'minimum_contacts':int(min(count[a],count[j])),'edges':[edge(a),edge(j)]})
        two.sort(key=lambda p:(-p['minimum_contacts'],p['edges'][0]['post']['source_id'],p['edges'][1]['post']['source_id']))
        item={'mbon':neuron(ci),'kc_inputs':groups,'all_in_contacts':int(count[post==ci].sum()),'direct_dn':sorted(direct,key=lambda r:-r['contacts']),'two_hop_route_count':len(two),'top_30_two_hop_routes':two[:30]}
        result['candidates'].append(item)
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'anatomy_comparison.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    by_id={n['source_id']:i for i,n in enumerate(ns)}
    chosen_kc=[i for i,n in enumerate(ns) if n['cell_type']=='KCg-m' and n['soma_side']=='L']
    chosen_da=[i for i,n in enumerate(ns) if n['cell_type']=='PAM08' and n['soma_side']=='L']
    chosen_apl=[i for i,n in enumerate(ns) if n['cell_type']=='APL' and n['soma_side']=='L']
    selected=set(chosen_kc+chosen_da+chosen_apl+[by_id[x] for x in (10495,11145,10713)])
    inside_pre=np.isin(pre,list(selected)); inside_post=np.isin(post,list(selected))
    def block(a,b):
        ix=np.flatnonzero(np.isin(pre,a)&np.isin(post,b))
        return {'pairs':len(ix),'contacts':int(count[ix].sum()),'unique_pre':len(np.unique(pre[ix])),'unique_post':len(np.unique(post[ix])),'edges':[edge(j) for j in ix]}
    blocks={
        'KCg-m_L_to_MBON05':block(chosen_kc,[by_id[10495]]),
        'PAM08_L_to_KCg-m_L':block(chosen_da,chosen_kc),
        'PAM08_L_to_MBON05':block(chosen_da,[by_id[10495]]),
        'KCg-m_L_to_MBON20_fixed_bypass':block(chosen_kc,[by_id[11145]]),
        'MBON05_to_MBON20':block([by_id[10495]],[by_id[11145]]),
        'MBON20_to_DNp42':block([by_id[11145]],[by_id[10713]]),
    }
    all_critical=[e for b in blocks.values() for e in b['edges']]
    requested={e['source_row']:e for e in all_critical}
    raw=ROOT/'data/raw/malecns_v1/connectome-weights-male-cns-v1.0-minconf-0.5-traced-only.feather'
    source_manifest=json.loads((raw.parent/'source_manifest.json').read_text())
    raw_record=next(r for r in source_manifest['objects'] if r['name']==raw.name)
    raw_hash=sha(raw)
    assert raw_hash==raw_record['sha256']
    reader=pa.ipc.open_file(pa.memory_map(str(raw)))
    offset=0; checked=0
    for bi in range(reader.num_record_batches):
        b=reader.get_batch(bi)
        needed=[r for r in requested if offset<=r<offset+len(b)]
        for r in needed:
            row=b.slice(r-offset,1).to_pylist()[0]; e=requested[r]
            assert int(row['body_pre'])==e['pre']['source_id'] and int(row['body_post'])==e['post']['source_id']
            assert int(row['weight'])==e['contacts']
            checked+=1
        offset+=len(b)
    assert checked==len(requested)
    receipt=json.loads((PARENT/'validation_receipt.json').read_text())
    for name in ('neurons.parquet','connections.parquet'):
        assert sha(PARENT/name)==receipt['files'][name]['sha256']
    chosen={'stage_id':'MVP-B1','status':'anatomical proposal only; no active plastic mask',
        'roster':[neuron(i) for i in sorted(selected)],
        'kc_source_ids':[ns[i]['source_id'] for i in chosen_kc],
        'dan_source_ids':[ns[i]['source_id'] for i in chosen_da],
        'apl_source_ids':[ns[i]['source_id'] for i in chosen_apl],
        'blocks':blocks,
        'induced_pairs':int((inside_pre&inside_post).sum()),
        'induced_contacts':int(count[inside_pre&inside_post].sum()),
        'outside_in_pairs':int((~inside_pre&inside_post).sum()),
        'outside_in_contacts':int(count[~inside_pre&inside_post].sum()),
        'boundary':{str(sid):{'total_in':int(count[post==by_id[sid]].sum()),'retained_in':int(count[(post==by_id[sid])&inside_pre].sum())} for sid in (10495,11145,10713)},
        'source_hashes':result['source_hashes'],
        'verification':{'raw_source_rows_checked':checked,'parent_hashes_match':True,'raw_source_sha256':raw_hash,'raw_hash_matches_manifest':True,'raw_source_schema':str(reader.schema)}}
    (OUT/'selected_anatomy.json').write_text(json.dumps(chosen,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'selected_cells':len(selected),'kc_cells':len(chosen_kc),'dan_cells':len(chosen_da),'apl_ids':chosen['apl_source_ids'],'blocks':{k:{a:v for a,v in b.items() if a!='edges'} for k,b in blocks.items()},'boundary':chosen['boundary'],'verification':chosen['verification']},indent=2))

if __name__=='__main__': main()
