"""Independent exact-coordinate spot checks against the release syn-point table."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from scripts.inspect_malecns_synapse_sources import RangeFile

ROOT=Path(__file__).resolve().parents[1]
URL='https://storage.googleapis.com/flyem-male-cns/v1.0/connectome-data/flat-connectome/syn-points-male-cns-v1.0-minconf-0.5.feather?generation=1780494991007477'


class AuditedRange(RangeFile):
    def __init__(self):
        super().__init__(URL,13061489098)
        self.ranges=[]

    def read(self,size=-1):
        start=self.pos
        data=super().read(size)
        self.ranges.append({'start':start,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
        return data


def main():
    table=pq.read_table(ROOT/'data/processed/malecns_v1_route_closure/compartment_contacts.parquet')
    chosen={}
    for row in table.to_pylist():
        if row['body_post']!=519131:
            continue
        for side in ('pre','post'):
            label=row['subprimary_'+side+'_mask']
            key=(side,label)
            if key not in chosen and label in ('g2(R)','g3(R)','<unspecified>',"a'1(R)"):
                chosen[key]=row
    remote=AuditedRange()
    f=pa.PythonFile(remote)
    reader=pa.ipc.open_file(f)
    cols=[reader.schema.get_field_index(x) for x in ['point_id','x','y','z','body','kind','subprimary']]
    reader=pa.ipc.open_file(f,options=pa.ipc.IpcReadOptions(included_fields=cols))
    cache={}
    def batch(i):
        if i not in cache:cache[i]=reader.get_batch(i)
        return cache[i]
    results=[]
    for (side,label),r in chosen.items():
        x,y,z=[r[f'{a}_{side}'] for a in 'xyz'];target=(int(z)<<42)|(int(y)<<21)|int(x)
        low,high=0,reader.num_record_batches-1
        found=None
        while low<=high:
            mid=(low+high)//2;b=batch(mid);ids=b['point_id'].to_numpy()
            assert (ids[1:]>=ids[:-1]).all(), 'Source order unsuitable for lookup'
            if target<int(ids[0]):high=mid-1
            elif target>int(ids[-1]):low=mid+1
            else:
                at=np.flatnonzero(ids==target)
                if len(at)==1:found=b.slice(int(at[0]),1).to_pylist()[0]
                break
        assert found is not None,(side,label,target)
        assert [found[a] for a in 'xyz']==[x,y,z]
        assert found['body']==r['body_'+side]
        assert found['kind']==('PreSyn' if side=='pre' else 'PostSyn')
        assert found['subprimary']==label,(side,label,found)
        results.append({'source_partner_row':r['source_partner_row'],'side':side,'mask_label':label,'source_point':found})
        print(side,label,'exact source point MATCH',flush=True)
    output={'source_url':URL,'method':'exact found coordinate/body/kind/ROI matches; source batch search, not a global sort certification',
            'checks':results,'transferred_bytes':remote.transferred,'read_ranges':remote.ranges}
    (ROOT/'docs/figures/circuit_v1_route_closure_roi_checks.json').write_text(json.dumps(output,indent=2)+'\n')
    print('All independent source-point checks passed',len(results),'bytes',remote.transferred,flush=True)


if __name__=='__main__':main()
