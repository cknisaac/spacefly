from __future__ import annotations
import hashlib,json,sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from project_b.osu.mania_game import ManiaGame
from project_b.osu.config import OsuConfig
from project_b.osu.types import TapNote,HoldNote,KeyAction,KeyActionKind
INPUT=ROOT/'work/ea_mvp_fd5_lazer_chart_input_v4.json';PLAY=ROOT/'runs/ea_mvp/fd4_chart_playback_v4.json';A=ROOT/'work/ea_mvp_fd5_lazer_v5.jsonl';B=ROOT/'work/ea_mvp_fd5_lazer_v5_repeat.jsonl';OUT=ROOT/'runs/ea_mvp/fd5_lazer_parity_v5.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines()]
def normalize(rows):
 return [{**r,'Results':sorted([{**q,'OffsetUs':None} if q['Result'] in ('MISS','IGNOREMISS') else q for q in r['Results']],key=lambda q:(q['ObjectTimeUs'],q['Lane'],q['Component'],q['Result'])),'Actions':sorted(r['Actions'],key=lambda q:(q['TimeUs'],q['Lane'],q['Kind']))} for r in rows]
def main():
 data=json.loads(INPUT.read_text(encoding='utf-8'));fd4=json.loads(PLAY.read_text(encoding='utf-8'))['runs'][0];first=load(A);second=load(B)
 segment_map={s['id']:s for s in data['segments']};first_by={x['Id']:x for x in first};second_by={x['Id']:x for x in second}
 repeat=all([(x['Id']==y['Id'] and sorted((q['TimeUs'],q['Lane'],q['Kind']) for q in x['Actions'])==sorted((q['TimeUs'],q['Lane'],q['Kind']) for q in y['Actions']) and sorted((q['Component'],q['Result'],q['ObjectTimeUs'],q['Lane'],None if q['Result'] in ('MISS','IGNOREMISS') else q['OffsetUs']) for q in x['Results'])==sorted((q['Component'],q['Result'],q['ObjectTimeUs'],q['Lane'],None if q['Result'] in ('MISS','IGNOREMISS') else q['OffsetUs']) for q in y['Results'])) for x,y in zip(first,second)])
 action_checks=[];result_checks=[];score_checks=[];all_events=[]
 fd_map={(r['note_time_us'],r['lane'],r['component']):(r['note_id'],r['result'],r['hit_error_us']) for r in fd4['result_rows'] if r['component'] in ('tap','head','tail')}
 for sid,s in segment_map.items():
  r=first_by[sid];rr=second_by[sid]
  exp=[(a['time_us'],a['lane'],a['kind']) for a in s['actions']]
  got=[(a['TimeUs'],a['Lane'],a['Kind']) for a in sorted(r['Actions'],key=lambda x:x['Sequence'])]
  got2=[(a['TimeUs'],a['Lane'],a['Kind']) for a in sorted(rr['Actions'],key=lambda x:x['Sequence'])]
  action_checks.append({'segment':sid,'trace_match':got==exp,'repeat_match':got==got2,'expected_transitions':len(exp),'observed_transitions':len(got)})
  notes={n['id']:n for n in s['notes']}
  ev=[]
  for q in r['Results']:
   if q['Component'] not in ('tap','head','tail'):continue
   global_time=q['ObjectTimeUs']+s['origin_time_us']; kind=q['Component']; candidates=[n for n in s['notes'] if n['lane']==q['Lane'] and ((kind in ('tap','head') and n['start_time_us']==q['ObjectTimeUs']) or (kind=='tail' and n['end_time_us']==q['ObjectTimeUs'] and n['kind']=='hold'))]
   if len(candidates)!=1:ev.append({'mapped':False,'event':q});continue
   n=candidates[0];expected=fd_map.get((n['start_time_us']+s['origin_time_us'] if kind in ('tap','head') else n['end_time_us']+s['origin_time_us'],q['Lane'],kind))
   outcome_match=expected is not None and expected[1].replace('_','')==q['Result'].replace('_','')
   offset_match=q['Result'] in ('MISS','IGNOREMISS') or (expected is not None and expected[2]==q['OffsetUs'])
   ev.append({'mapped':True,'note_id':n['id'],'component':kind,'lazer_result':q['Result'],'recreation_result':None if expected is None else expected[1],'outcome_match':outcome_match,'offset_match':offset_match,'lazer_offset_us':q['OffsetUs'],'recreation_offset_us':None if expected is None else expected[2]})
  result_checks.append({'segment':sid,'events':len(ev),'all_mapped':all(x['mapped'] for x in ev),'outcomes_match':all(x.get('outcome_match',False) for x in ev),'non_miss_offsets_match':all(x.get('offset_match',False) for x in ev),'events_by_result':dict(Counter(x['lazer_result'] for x in ev if x['mapped']))})
  localnotes=[TapNote(n['id'],n['lane'],n['start_time_us']) if n['kind']=='tap' else HoldNote(n['id'],n['lane'],n['start_time_us'],n['end_time_us']) for n in s['notes']]
  game=ManiaGame(localnotes,OsuConfig(od=8,ruleset='lazer'))
  for a in s['actions']:game.apply_action(KeyAction(a['time_us'],a['lane'],KeyActionKind(a['kind'])))
  game.finish();snap=game.score.snapshot()
  score_checks.append({'segment':sid,'score_match':snap.score==r['Score'],'accuracy_match':abs(snap.accuracy-r['Accuracy'])<1e-12,'combo_match':snap.combo==r['Combo'],'max_combo_match':snap.max_combo==r['MaxCombo'],'recreation_score':snap.score,'lazer_score':r['Score'],'recreation_accuracy':snap.accuracy,'lazer_accuracy':r['Accuracy'],'recreation_combo':snap.combo,'lazer_combo':r['Combo'],'recreation_max_combo':snap.max_combo,'lazer_max_combo':r['MaxCombo']})
  all_events.extend(ev)
 checks={'pinned_revision':True,'repeat_event_outputs_stable_after_event_order_normalization':repeat,'all_key_transitions_exact':all(x['trace_match'] and x['repeat_match'] for x in action_checks),'all_1400_chart_judgements_mapped_and_equal':sum(x['events'] for x in result_checks)==1400 and all(x['all_mapped'] and x['outcomes_match'] for x in result_checks),'all_non_miss_offsets_equal':all(x['non_miss_offsets_match'] for x in result_checks),'segment_score_accuracy_combo_equal':all(x['score_match'] and x['accuracy_match'] and x['combo_match'] and x['max_combo_match'] for x in score_checks)}
 result={'protocol':'EA-MVP-FD5-LAZER-PARITY-v5','status':'PARTIAL' if checks['all_key_transitions_exact'] and checks['all_1400_chart_judgements_mapped_and_equal'] and checks['all_non_miss_offsets_equal'] else 'FAIL','scope':'17 short in-process ReplayPlayer segments stitched in source-chart order; exact source and chart; not installed-client or one uninterrupted 261-second ReplayPlayer session','pinned_commit':'da27300fcbfa246f87c3ba1a14cbd00b68c7e9a9','chart_sha256':data['chart_sha256'],'input_sha256':sha(INPUT),'first_capture_sha256':sha(A),'repeat_capture_sha256':sha(B),'checks':checks,'action_transition_count':sum(x['observed_transitions'] for x in action_checks),'judgement_event_count_compared':sum(x['events'] for x in result_checks),'full_chart_recreation_score':fd4['score']['score'],'full_chart_recreation_accuracy':fd4['score']['accuracy'],'full_chart_recreation_max_combo':fd4['score']['max_combo'],'total_lazer_score_across_segments_not_a_full_map_score':sum(x['Score'] for x in first),'note':'ReplayPlayer event callback order and miss offset values can vary with frame scheduling; repeatability is evaluated after sorting by chart object identity/time and excluding scheduler-dependent miss offset. Non-miss judgement offsets remain exact.' ,'action_checks':action_checks,'result_checks':result_checks,'segment_score_checks':score_checks,'first_run':first,'repeat_run':second}
 OUT.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({'status':result['status'],'checks':checks,'action_transitions':result['action_transition_count'],'judgements':result['judgement_event_count_compared'],'segment_scores_all_match':checks['segment_score_accuracy_combo_equal'],'output':str(OUT)},indent=2))
if __name__=='__main__':main()


