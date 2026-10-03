"""Frozen-policy test for a latched cue gate at constant map speeds."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from project_b.ea_mvp.continuous_multilane import ContinuousFourLaneFlyPolicy
from project_b.ea_mvp.screen_ttc import ScreenTimeToContactEncoder
from project_b.malecns_continuous_position_learning.online_policy import load_position_config
from project_b.osu.adapter import PositionObservation
from project_b.osu.types import KeyActionKind
from run_ea_mvp_fd2_ttc_validation_v2 import ROOT, MODEL_CFG, RECEIPT, BASE_MS, FACTORS, DT, TOL, arm, p_of

PROTOCOL=ROOT/'configs/ea_mvp_fd2_fixed_speed_latched_cue_v1.json'
OUT=ROOT/'runs/ea_mvp/fd2_fixed_speed_latched_cue_v1.json'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def run(config,weights,duration_ms,speed):
 enc=ScreenTimeToContactEncoder(); policy=None; start_tick=None; cue_latched=False; transitions=[]; valid_after_onset=0
 for t in range(duration_ms+151):
  p=p_of(t/duration_ms) if t<=duration_ms else None
  sample=enc.observe(t*DT,p)
  if sample is None and p is None: cue_latched=False
  if sample is not None and sample.cue_active: cue_latched=True
  active=cue_latched and sample is not None
  if active: valid_after_onset+=1
  if policy is None:
   if not active: continue
   policy=ContinuousFourLaneFlyPolicy(config,weights); start_tick=t
   policy.begin(PositionObservation(True,0,sample.countdown)); continue
  transitions.extend(policy.step(PositionObservation(active,0,sample.countdown if active else None)))
 if policy is not None:
  policy.finish()
  if tuple(weights)!=policy.weights: raise AssertionError('frozen weights changed')
 actions=[{'time_us':start_tick*DT+x.episode_time_us,'lane':x.lane,'kind':x.kind.value} for x in transitions]
 downs=[x for x in actions if x['kind']==KeyActionKind.DOWN.value]; ups=[x for x in actions if x['kind']==KeyActionKind.UP.value]
 ok=(len(downs)==1 and downs[0]['lane']==0 and abs(downs[0]['time_us']-duration_ms*DT)<=TOL
     and len(ups)==1 and ups[0]['time_us']==downs[0]['time_us']+10_000)
 return {'actions':actions,'pass':ok,'down_error_us':downs[0]['time_us']-duration_ms*DT if len(downs)==1 else None,
         'release_exact_10ms':len(ups)==1 and len(downs)==1 and ups[0]['time_us']==downs[0]['time_us']+10_000,
         'cue_start_ms':start_tick,'valid_active_samples':valid_after_onset}

def main():
 model=load_position_config(ROOT,str(MODEL_CFG.relative_to(ROOT))); cells=[]
 for seed in (907,1009,1103):
  weights=arm(seed,'learning_on')['final_weights']
  for speed in FACTORS:
   duration=round(BASE_MS/speed); reps=[run(model,weights,duration,speed) for _ in (1,2)]
   cells.append({'seed':seed,'speed_factor':speed,'duration_ms':duration,'repeats':reps,'exact_repeat':reps[0]['actions']==reps[1]['actions']})
 initial=arm(907,'untrained')['initial_weights']; untrained=run(model,initial,BASE_MS,1.0); untrained['silent']=not untrained['actions']
 passed=all(c['exact_repeat'] and all(r['pass'] for r in c['repeats']) for c in cells) and untrained['silent']
 result={'protocol':'EA-MVP-FD2-FIXED-SPEED-LATCHED-CUE-v1','status':'PASS' if passed else 'FAIL',
  'no_training':True,'no_game_or_score':True,'weights_unchanged':True,'seed_speed_cases':cells,'untrained_control':untrained,
  'protocol_sha256':sha(PROTOCOL),'runner_sha256':sha(Path(__file__)),
  'policy_probe_v1_sha256':sha(ROOT/'scripts/run_ea_mvp_fd2_fixed_speed_policy.py'),
  'encoder_sha256':sha(ROOT/'src/project_b/ea_mvp/screen_ttc.py')}
 OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps(result,indent=2))
if __name__=='__main__': main()
