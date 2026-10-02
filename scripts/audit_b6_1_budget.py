"""Reconcile completed C1 turn and current B6.1 research from local task events."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/figures/b6_1_pathway_comparison/budget_entry.json'
prior=json.loads((ROOT/'docs/figures/b6_candidate1_decision/budget_reconciliation.json').read_text())
path,=(Path.home()/'.codex/sessions/2026/10/01').glob('*01a0f50e-5cb5-7c23-aea0-6f90da065f26.jsonl')
data=path.read_bytes()
events={}
for line in data.splitlines():
    obj=json.loads(line);p=obj.get('payload',{})
    if obj.get('type')=='event_msg' and p.get('type') in ('task_started','task_complete','turn_aborted'):
        events.setdefault(p['turn_id'],{})[p['type']]=(obj,hashlib.sha256(line).hexdigest())
c1_id='01a0f778-d158-7193-aab9-c231d82a113c'
c2_id='01a0f788-255d-78a1-914d-7e5068a237ce'
old=next(x for x in prior['turns'] if x['turn_id']==c1_id)['charged_ms']
final=events[c1_id]['task_complete'][0]['payload']['duration_ms']
c1=prior['recorded_active_ms']-old+final
started=datetime.fromisoformat(events[c2_id]['task_started'][0]['timestamp'].replace('Z','+00:00'))
now=datetime.now(timezone.utc)
c2=int((now-started).total_seconds()*1000)
reserve=15*60*1000
entry={'stage_id':'MVP-B6.1','cutoff_utc':now.isoformat(),
       'candidate_slots_accounted':{'candidate_1_retired':True,'candidate_2_research_opened':True,
                                    'candidate_2_design_admitted':False,'candidate_3_started':False,
                                    'maximum_candidates':3},
       'source_log_snapshot':{'path':str(path),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()},
       'candidate_1':{'status':'retired','prior_cutoff_recorded_ms':prior['recorded_active_ms'],
                      'prior_B6_partial_ms':old,'B6_completed_ms':final,'final_recorded_ms':c1,
                      'unused_allowance_not_transferable_ms':28800000-c1,
                      'completed_event_sha256':events[c1_id]['task_complete'][1]},
       'candidate_2_research':{'turn_id':c2_id,'start_utc':started.isoformat(),
                               'start_event_sha256':events[c2_id]['task_started'][1],
                               'active_ms_through_cutoff':c2,'closeout_reserve_ms':reserve,
                               'committed_upper_bound_ms':c2+reserve,'cap_ms':28800000,
                               'remaining_after_reserve_ms':28800000-c2-reserve,
                               'design_or_implementation_started':False},
       'overall':{'cap_ms':86400000,'recorded_c1_plus_c2_ms':c1+c2,
                  'committed_upper_bound_ms':c1+c2+reserve,
                  'remaining_after_reserve_ms':86400000-c1-c2-reserve},
       'accounting_policy':'C1 completed B6 event replaces prior partial duration; prior C1 closeout reserve was not spent twice. C2 charges this B6.1 root turn from task_started to snapshot, with 15-minute reserve for closeout. Idle gaps and independent A6 work are excluded. Agent active time only; no claim about human or off-platform work.'}
assert c1<28800000 and c2+reserve<28800000 and c1+c2+reserve<86400000
OUT.write_text(json.dumps(entry,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'C1_final_ms':c1,'C2_active_ms':c2,'C2_committed_ms':c2+reserve,
                  'overall_committed_ms':c1+c2+reserve,'cutoff':now.isoformat()},indent=2))
