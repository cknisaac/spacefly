"""Frozen EA13 policy probe at constant pre-map speeds; does not train or score."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from project_b.ea_mvp.continuous_multilane import ContinuousFourLaneFlyPolicy
from project_b.ea_mvp.screen_ttc import ScreenTimeToContactEncoder
from project_b.malecns_continuous_position_learning.online_policy import load_position_config
from project_b.osu.adapter import PositionObservation
from project_b.osu.types import KeyActionKind
from run_ea_mvp_fd2_ttc_validation_v2 import ROOT, CFG as HELPERS, MODEL_CFG, RECEIPT, BASE_MS, FACTORS, DT, TOL, arm, p_of

PROTOCOL=ROOT/'configs/ea_mvp_fd2_fixed_speed_policy_v1.json'
OUT=ROOT/'runs/ea_mvp/fd2_fixed_speed_policy_v1.json'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def run_policy(config,weights,duration_ms,factor):
 enc=ScreenTimeToContactEncoder(); policy=None; start_tick=None; transitions=[]
 for t in range(duration_ms+151):
  p=p_of(t/duration_ms) if t<=duration_ms else None
  sample=enc.observe(t*DT,p)
  if policy is None:
   if sample is None or not sample.cue_active: continue
   policy=ContinuousFourLaneFlyPolicy(config,weights); start_tick=t
   policy.begin(PositionObservation(True,0,sample.countdown)); continue
  active=sample is not None and sample.cue_active
  transitions.extend(policy.step(PositionObservation(active,0,sample.countdown if active else None)))
 if policy is not None:
  policy.finish()
  if tuple(weights)!=policy.weights: raise AssertionError('frozen weights changed')
 actions=[{'time_us':start_tick*DT+x.episode_time_us,'lane':x.lane,'kind':x.kind.value} for x in transitions]
 downs=[x for x in actions if x['kind']==KeyActionKind.DOWN.value]
 ups=[x for x in actions if x['kind']==KeyActionKind.UP.value]
 ok=(len(downs)==1 and downs[0]['lane']==0 and abs(downs[0]['time_us']-duration_ms*DT)<=TOL
     and len(ups)==1 and ups[0]['time_us']==downs[0]['time_us']+10_000)
 return {'actions':actions,'pass':ok,'down_error_us':downs[0]['time_us']-duration_ms*DT if len(downs)==1 else None,
         'release_exact_10ms':len(ups)==1 and len(downs)==1 and ups[0]['time_us']==downs[0]['time_us']+10_000}

def main():
 model=load_position_config(ROOT,str(MODEL_CFG.relative_to(ROOT))); cells=[]
 for seed in (907,1009,1103):
  weights=arm(seed,'learning_on')['final_weights']
  for speed in FACTORS:
   duration=round(BASE_MS/speed); reps=[run_policy(model,weights,duration,speed) for _ in range(2)]
   cells.append({'seed':seed,'speed_factor':speed,'duration_ms':duration,'repeats':reps,
                 'exact_repeat':reps[0]['actions']==reps[1]['actions']})
 initial=arm(907,'untrained')['initial_weights']; untrained=run_policy(model,initial,BASE_MS,1.0)
 untrained['silent']=not untrained['actions']
 passed=all(c['exact_repeat'] and all(r['pass'] for r in c['repeats']) for c in cells) and untrained['silent']
 result={'protocol':'EA-MVP-FD2-FIXED-SPEED-POLICY-v1','status':'PASS' if passed else 'FAIL',
  'no_training':True,'no_game_or_score':True,'assumption':'constant note speed within each run; fresh estimator per speed',
  'protocol_sha256':sha(PROTOCOL),'helper_v2_sha256':sha(HELPERS),'runner_sha256':sha(Path(__file__)),
  'encoder_sha256':sha(ROOT/'src/project_b/ea_mvp/screen_ttc.py'),'frozen_weights_unchanged':True,
  'seed_speed_cases':cells,'untrained_control':untrained}
 OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps(result,indent=2))
if __name__=='__main__': main()
