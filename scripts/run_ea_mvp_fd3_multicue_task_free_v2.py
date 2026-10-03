"""FD-3 task-free multi-cue test with lane-stable events and 11-ms rearm."""
from __future__ import annotations
import gzip, hashlib, json
from pathlib import Path
from project_b.ea_mvp.continuous_multilane import ContinuousFourLaneFlyPolicy
from project_b.ea_mvp.multicue_adapter import HoldKeyState, VisualFrame, VisualHead, VisualTail, select_nearest_head
from project_b.malecns_continuous_position_learning.online_policy import load_position_config
from project_b.osu.adapter import PositionObservation
from project_b.osu.types import KeyActionKind
from run_ea_mvp_fd2_ttc_validation_v2 import ROOT, MODEL_CFG, RECEIPT, DT, arm

PROTOCOL=ROOT/'configs/ea_mvp_fd3_multicue_task_free_v2.json'
OUT=ROOT/'runs/ea_mvp/fd3_multicue_task_free_v2.json'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def input_frame(q,lanes,kind='tap'):
 return VisualFrame(tuple(VisualHead(lane,1-q,kind) for lane in lanes))

def routing_tests():
 rows=[]
 for count in (0,1,2,6,14):
  heads=tuple(VisualHead(i%4,(i+1)/15,'tap') for i in range(count)); picked=select_nearest_head(VisualFrame(heads))
  expected=None if count==0 else max(h.position for h in heads)
  rows.append({'count':count,'selected':None if picked is None else picked.position,'expected':expected,
               'pass':(picked is None if count==0 else picked.position==expected)})
 ties=[]
 for lanes in ((0,1),(0,1,2,3)):
  picked=select_nearest_head(VisualFrame(tuple(VisualHead(l,0.75,'tap') for l in lanes)))
  ties.append({'expected':list(lanes),'got':list(picked.lanes),'pass':picked.lanes==lanes})
 hold_head=select_nearest_head(VisualFrame((VisualHead(0,0.8,'hold'),)))
 shape={'lane_kind':list(hold_head.kinds_by_lane),'pass':hold_head.kinds_by_lane==((0,'hold'),)}
 bounds=[]
 for count,should_error in ((14,False),(15,True)):
  try: VisualFrame(tuple(VisualHead(i%4,i/max(1,count-1),'tap') for i in range(count))); errored=False
  except ValueError: errored=True
  bounds.append({'heads':count,'should_error':should_error,'raised':errored,'pass':errored==should_error})
 hs=HoldKeyState(); hs.key_down(0,hold=True); hs.key_down(1,hold=True)
 tap_up_suppressed=not hs.tap_release(0)
 first=hs.observe_tails((VisualTail(0,0.0),VisualTail(1,0.2))); mid=sorted(hs.held_lanes)
 second=hs.observe_tails((VisualTail(1,0.0),))
 hold_pass=(first==(0,) and mid==[1] and second==(1,) and not hs.held_lanes and tap_up_suppressed)
 chord_heads=select_nearest_head(VisualFrame((VisualHead(0,0.8,'hold'),VisualHead(1,0.8,'hold'))))
 overlap=HoldKeyState(); [overlap.key_down(lane,hold=True) for lane in chord_heads.lanes]
 overlap_release_a=overlap.observe_tails((VisualTail(0,0.0),VisualTail(1,0.3)))
 overlap_mid=sorted(overlap.held_lanes)
 overlap_release_b=overlap.observe_tails((VisualTail(1,0.0),))
 overlap_pass=(chord_heads.lanes==(0,1) and overlap_release_a==(0,) and overlap_mid==[1] and overlap_release_b==(1,) and not overlap.held_lanes)
 return {'head_counts':rows,'same_position_lane_fanout':ties,'bounds':bounds,'hold_head_identity':shape,
  'two_hold_states':{'tap_up_suppressed':tap_up_suppressed,'first_release':list(first),'remaining':mid,'second_release':list(second),'pass':hold_pass},
  'two_hold_chord_tail_independence':{'lanes':list(chord_heads.lanes),'first_release':list(overlap_release_a),'remaining':overlap_mid,'second_release':list(overlap_release_b),'pass':overlap_pass},
  'pass':all(x['pass'] for x in rows+ties+bounds) and hold_pass and overlap_pass and shape['pass']}

def neural_sequence(config,weights,partial_next):
 policy=None; held=set(); actions=[]; last_lanes=(0,); last_cue_id=0; cue_downs={0:[],1:[],2:[]}; max_voltage=0.0; now_us=0
 def tick(frame,cue_id):
  nonlocal policy,last_lanes,last_cue_id,max_voltage,now_us
  picked=select_nearest_head(frame)
  if picked is not None:
   last_lanes=picked.lanes; last_cue_id=cue_id if cue_id is not None else last_cue_id; q=max(0.0,1.0-picked.position)
   obs=PositionObservation(True,0,q)
  else: obs=PositionObservation(False,0,None)
  if policy is None:
   if not obs.visible: now_us+=DT; return
   policy=ContinuousFourLaneFlyPolicy(config,weights); policy.begin(obs); now_us+=DT; return
  emitted=policy.step(obs)
  for event in emitted:
   if event.kind is KeyActionKind.DOWN:
    lanes=last_lanes
    held.update(lanes)
    for lane in lanes: cue_downs[last_cue_id].append(lane)
    for lane in lanes: actions.append({'time_us':event.episode_time_us,'lane':lane,'kind':'down','cue':last_cue_id})
   else:
    lanes=tuple(sorted(held))
    for lane in lanes: actions.append({'time_us':event.episode_time_us,'lane':lane,'kind':'up','cue':cue_id})
    held.difference_update(lanes)
  now_us+=DT
 def cue(q_values,lanes,cue_id):
  for q in q_values: tick(input_frame(q,lanes),cue_id)
 def blank(n):
  for _ in range(n): tick(VisualFrame(),None)
 cue((max(0,1-i/500) for i in range(501)),(0,),0)
 blank(11)
 if partial_next: cue((max(0,(200-i)/500) for i in range(201)),(1,),1)
 else: cue((max(0,1-i/500) for i in range(501)),(1,),1)
 blank(11)
 cue((max(0,1-i/500) for i in range(501)),(2,3),2)
 blank(20)
 if policy is not None:
  policy.finish(); snapshot=policy._sim.snapshot()
  max_voltage=max((abs(x.voltage_before_reset_mv) for x in snapshot.voltage_trace),default=0.0)
  if tuple(weights)!=policy.weights: raise AssertionError('weights changed')
 downs=[a for a in actions if a['kind']=='down']; ups=[a for a in actions if a['kind']=='up']
 return {'actions':actions,'downs_by_cue':cue_downs,'rearms':policy.readout_rearm_count,
  'neural_initializations':policy.neural_reset_count,'max_abs_mbon_voltage_mv':max_voltage,
  'all_ups_match_active_downs':not held and len(downs)==len(ups) and [a['lane'] for a in downs]==[a['lane'] for a in ups],
  'weights_unchanged':tuple(weights)==policy.weights}

def main():
 model=load_position_config(ROOT,str(MODEL_CFG.relative_to(ROOT)))
 with gzip.open(RECEIPT/'seed_907_learning_on.json.gz','rt',encoding='utf-8') as f: weights=json.load(f)['final_weights']
 routing=routing_tests(); neural=[]
 for partial in (False,True):
  reps=[neural_sequence(model,weights,partial) for _ in (1,2)]
  one=all(l==0 for l in reps[0]['downs_by_cue'][0]) and len(reps[0]['downs_by_cue'][0])==1
  second=(len(reps[0]['downs_by_cue'][1])<=1 and all(lane==1 for lane in reps[0]['downs_by_cue'][1]) if partial else reps[0]['downs_by_cue'][1]==[1])
  chord=sorted(reps[0]['downs_by_cue'][2])==[2,3]
  expected=(one and second and chord)
  neural.append({'partial_next_cue':partial,'repeats':reps,'exact_repeat':reps[0]['actions']==reps[1]['actions'],
   'single_correct_lane':one,'next_cue_behavior':second,'chord_correct_lanes':chord,
   'lane_event_integrity':all(r['all_ups_match_active_downs'] for r in reps),
   'bounded_voltage':all(r['max_abs_mbon_voltage_mv']<1.0 for r in reps),
   'weights_unchanged':all(r['weights_unchanged'] for r in reps),'pass':expected and all(r['all_ups_match_active_downs'] and r['max_abs_mbon_voltage_mv']<1 and r['weights_unchanged'] for r in reps) and reps[0]['actions']==reps[1]['actions']})
 passed=routing['pass'] and all(x['pass'] for x in neural)
 result={'protocol':'EA-MVP-FD3-MULTICUE-TASK-FREE-v2','status':'PASS' if passed else 'FAIL',
  'no_training':True,'no_game_or_score':True,'routing':routing,'neural_sequences':neural,
  'seed':907,'weights_unchanged':True,'protocol_sha256':sha(PROTOCOL),'runner_sha256':sha(Path(__file__)),
  'adapter_sha256':sha(ROOT/'src/project_b/ea_mvp/multicue_adapter.py'),
  'encoder_sha256':sha(ROOT/'src/project_b/ea_mvp/screen_ttc.py')}
 OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps(result,indent=2))
if __name__=='__main__': main()
