"""Frozen-policy test with a monotone TTC signal for fixed-speed approaches."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from project_b.ea_mvp.continuous_multilane import ContinuousFourLaneFlyPolicy
from project_b.ea_mvp.screen_ttc import ScreenTimeToContactEncoder
from project_b.malecns_continuous_position_learning.online_policy import load_position_config
from project_b.osu.adapter import PositionObservation
from project_b.osu.types import KeyActionKind
from run_ea_mvp_fd2_ttc_validation_v2 import ROOT, MODEL_CFG, RECEIPT, BASE_MS, FACTORS, DT, TOL, arm, p_of

PROTOCOL=ROOT/'configs/ea_mvp_fd2_fixed_speed_monotonic_ttc_v1.json'
OUT=ROOT/'runs/ea_mvp/fd2_fixed_speed_monotonic_ttc_v1.json'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def run(config,weights,duration_ms):
 enc=ScreenTimeToContactEncoder(); policy=None; start_tick=None; cue=False; last_q=None; transitions=[]; q_rises=0
 for t in range(duration_ms+151):
  p=p_of(t/duration_ms) if t<=duration_ms else None
  sample=enc.observe(t*DT,p)
  if p is None: cue=False; last_q=None
  elif sample is not None and sample.cue_active: cue=True
  if cue and sample is not None:
   raw=sample.countdown
   q=raw if last_q is None else min(last_q,raw)
   if last_q is not None and raw>last_q: q_rises+=1
   last_q=q
  else: q=last_q
  active=cue and q is not None
  if policy is None:
   if not active: continue
   policy=ContinuousFourLaneFlyPolicy(config,weights); start_tick=t
   policy.begin(PositionObservation(True,0,q)); continue
  transitions.extend(policy.step(PositionObservation(active,0,q if active else None)))
 if policy is not None:
  policy.finish()
  if tuple(weights)!=policy.weights: raise AssertionError('frozen weights changed')
 actions=[{'time_us':start_tick*DT+x.episode_time_us,'lane':x.lane,'kind':x.kind.value} for x in transitions]
 downs=[x for x in actions if x['kind']==KeyActionKind.DOWN.value]; ups=[x for x in actions if x['kind']==KeyActionKind.UP.value]
 ok=(len(downs)==1 and downs[0]['lane']==0 and abs(downs[0]['time_us']-duration_ms*DT)<=TOL
     and len(ups)==1 and ups[0]['time_us']==downs[0]['time_us']+10_000)
 return {'actions':actions,'pass':ok,'down_error_us':downs[0]['time_us']-duration_ms*DT if len(downs)==1 else None,
  'release_exact_10ms':len(ups)==1 and len(downs)==1 and ups[0]['time_us']==downs[0]['time_us']+10_000,
  'cue_start_ms':start_tick,'clipped_upward_samples':q_rises}

def main():
 model=load_position_config(ROOT,str(MODEL_CFG.relative_to(ROOT))); cells=[]
 for seed in (907,1009,1103):
  weights=arm(seed,'learning_on')['final_weights']
  for speed in FACTORS:
   duration=round(BASE_MS/speed); reps=[run(model,weights,duration) for _ in (1,2)]
   cells.append({'seed':seed,'speed_factor':speed,'duration_ms':duration,'repeats':reps,'exact_repeat':reps[0]['actions']==reps[1]['actions']})
 initial=arm(907,'untrained')['initial_weights']; untrained=run(model,initial,BASE_MS); untrained['silent']=not untrained['actions']
 passed=all(c['exact_repeat'] and all(r['pass'] for r in c['repeats']) for c in cells) and untrained['silent']
 result={'protocol':'EA-MVP-FD2-FIXED-SPEED-MONOTONIC-TTC-v1','status':'PASS' if passed else 'FAIL',
  'no_training':True,'no_game_or_score':True,'weights_unchanged':True,'seed_speed_cases':cells,'untrained_control':untrained,
  'protocol_sha256':sha(PROTOCOL),'runner_sha256':sha(Path(__file__)),
  'prior_latched_runner_sha256':sha(ROOT/'scripts/run_ea_mvp_fd2_latched_cue.py'),
  'encoder_sha256':sha(ROOT/'src/project_b/ea_mvp/screen_ttc.py')}
 OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps(result,indent=2))
if __name__=='__main__': main()
