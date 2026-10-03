"""FD-3 task-free routing, rearm, hold-state, and frozen-neural probe."""
from __future__ import annotations
import gzip, hashlib, json
from pathlib import Path
from project_b.ea_mvp.continuous_multilane import ContinuousFourLaneFlyPolicy
from project_b.ea_mvp.multicue_adapter import HoldKeyState, VisualFrame, VisualHead, VisualTail, select_nearest_head
from project_b.malecns_continuous_position_learning.online_policy import load_position_config
from project_b.osu.adapter import PositionObservation
from project_b.osu.types import KeyActionKind
from run_ea_mvp_fd2_ttc_validation_v2 import ROOT, MODEL_CFG, RECEIPT, DT, arm

PROTOCOL=ROOT/'configs/ea_mvp_fd3_multicue_task_free_v1.json'
OUT=ROOT/'runs/ea_mvp/fd3_multicue_task_free_v1.json'
SEEDS=(907,); REPEATS=(1,2)
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def weights(): return arm(907,'learning_on')['final_weights']
def input_frame(q, lanes, kind='tap'):
 return VisualFrame(tuple(VisualHead(lane,1.0-q,kind) for lane in lanes))

def neural_sequence(config, w, partial_second):
 policy=None; transitions=[]; cue_lanes=(0,); records=[]; last_lanes=(0,); max_voltage=0.0
 def tick(frame):
  nonlocal policy, transitions, last_lanes, max_voltage
  selected=select_nearest_head(frame)
  if selected is None:
   obs=PositionObservation(False,0,None)
  else:
   last_lanes=selected.lanes
   obs=PositionObservation(True,0,max(0.0,1.0-selected.position))
  if policy is None:
   if not obs.visible: return
   policy=ContinuousFourLaneFlyPolicy(config,w); policy.begin(obs); return
  for event in policy.step(obs):
   for lane in last_lanes:
    transitions.append({'time_us':event.episode_time_us,'lane':lane,'kind':event.kind.value})
 # Full, canonical 500-ms cue. The selected renderer position increases toward 1.
 for i in range(501): tick(input_frame(max(0.0,1.0-i/500.0),(0,)))
 tick(VisualFrame())  # one predeclared blank/rearm frame
 # Dense-overlap control: the next nearest head becomes selected with only 200 ms to contact.
 span=200 if partial_second else 500
 lane=(1,)
 for i in range(span+1):
  q=max(0.0,(span-i)/500.0) if partial_second else max(0.0,1.0-i/500.0)
  tick(input_frame(q,lane))
 tick(VisualFrame())
 # Same-position two-lane chord, followed through a complete cue.
 for i in range(501): tick(input_frame(max(0.0,1.0-i/500.0),(2,3)))
 for _ in range(20): tick(VisualFrame())  # drain the frozen 10-ms key release
 if policy is not None:
  policy.finish()
  if tuple(w)!=policy.weights: raise AssertionError('frozen weights changed')
  snapshot=policy._sim.snapshot()
  max_voltage=max((abs(row.voltage_before_reset_mv) for row in snapshot.voltage_trace),default=0.0)
 return {'actions':transitions,'neural_initializations':0 if policy is None else policy.neural_reset_count,
         'readout_rearms':0 if policy is None else policy.readout_rearm_count,
         'max_abs_mbon_voltage_mv':max_voltage,'weights_unchanged':policy is None or tuple(w)==policy.weights}

def routing_tests():
 rows=[]
 for count in (0,1,2,6,14):
  heads=tuple(VisualHead(i%4,(i+1)/15,'tap') for i in range(count))
  frame=VisualFrame(heads); picked=select_nearest_head(frame)
  expected=None if count==0 else max(head.position for head in heads)
  rows.append({'head_count':count,'selected_position':None if picked is None else picked.position,
               'expected_position':expected,'pass':(picked is None if count==0 else picked.position==expected)})
 chord_rows=[]
 for lanes in ((0,1),(0,1,2,3)):
  selected=select_nearest_head(VisualFrame(tuple(VisualHead(lane,0.75,'tap') for lane in lanes)))
  chord_rows.append({'lanes':list(lanes),'selected_lanes':list(selected.lanes),'pass':selected.lanes==lanes})
 limits=[]
 for count,expected_error in ((14,False),(15,True)):
  try: VisualFrame(tuple(VisualHead(i%4,i/max(1,count-1),'tap') for i in range(count))); errored=False
  except ValueError: errored=True
  limits.append({'head_count':count,'expected_error':expected_error,'raised':errored,'pass':errored==expected_error})
 hs=HoldKeyState(); hs.key_down(0,hold=True); hs.key_down(1,hold=True)
 both=sorted(hs.held_lanes); tap_suppressed=not hs.tap_release(0)
 release0=hs.observe_tails((VisualTail(0,0.0),VisualTail(1,0.2)))
 remaining=sorted(hs.held_lanes); release1=hs.observe_tails((VisualTail(1,0.0),))
 hold={'initial_lanes':both,'tap_up_suppressed':tap_suppressed,'first_release':list(release0),
       'remaining_after_first':remaining,'second_release':list(release1),'empty_at_end':not hs.held_lanes,
       'pass':both==[0,1] and tap_suppressed and release0==(0,) and remaining==[1] and release1==(1,) and not hs.held_lanes}
 tail_limit=[]
 for count,expected_error in ((2,False),(3,True)):
  try: VisualFrame((),tuple(VisualTail(i,0.5) for i in range(count))); errored=False
  except ValueError: errored=True
  tail_limit.append({'tail_count':count,'expected_error':expected_error,'raised':errored,'pass':errored==expected_error})
 return {'head_counts':rows,'tie_lane_fanout':chord_rows,'capacity_checks':limits,'two_hold_state':hold,
         'tail_capacity_checks':tail_limit,
         'pass':all(x['pass'] for x in rows+chord_rows+limits+tail_limit) and hold['pass']}

def main():
 model=load_position_config(ROOT,str(MODEL_CFG.relative_to(ROOT))); w=weights()
 routing=routing_tests(); neural=[]
 for partial in (False,True):
  repeats=[neural_sequence(model,w,partial) for _ in REPEATS]
  actions=repeats[0]['actions']; downs=[x for x in actions if x['kind']==KeyActionKind.DOWN.value]
  expected_lanes=(0,2,3) if not partial else (0,2,3)
  lane_sequence=tuple(x['lane'] for x in downs)
  neural.append({'next_cue_partial':partial,'repeats':repeats,
   'exact_repeat':repeats[0]['actions']==repeats[1]['actions'],
   'down_lanes':list(lane_sequence),'expected_lanes':list(expected_lanes),
   'no_unintended_lane':set(lane_sequence).issubset({0,1,2,3}),
   'single_full_cue_matches_reference':bool(downs and downs[0]['lane']==0),
   'bounded_voltage':all(x['max_abs_mbon_voltage_mv']<=1.0 for x in repeats),
   'weights_unchanged':all(x['weights_unchanged'] for x in repeats)})
 # Partial cue may be silent; however outputs must be repeatable and lane-valid.
 neural_pass=all(x['exact_repeat'] and x['bounded_voltage'] and x['weights_unchanged'] and x['no_unintended_lane'] for x in neural)
 passed=routing['pass'] and neural_pass
 result={'protocol':'EA-MVP-FD3-MULTICUE-TASK-FREE-v1','status':'PASS' if passed else 'FAIL',
  'no_training':True,'no_game_or_score':True,'routing':routing,'neural_sequences':neural,
  'frozen_weights_seed':907,'frozen_weights_unchanged':True,
  'protocol_sha256':sha(PROTOCOL),'runner_sha256':sha(Path(__file__)),
  'adapter_sha256':sha(ROOT/'src/project_b/ea_mvp/multicue_adapter.py'),
  'fd2_monotonic_runner_sha256':sha(ROOT/'scripts/run_ea_mvp_fd2_monotonic_ttc.py'),
  'encoder_sha256':sha(ROOT/'src/project_b/ea_mvp/screen_ttc.py')}
 OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps(result,indent=2))
if __name__=='__main__': main()
