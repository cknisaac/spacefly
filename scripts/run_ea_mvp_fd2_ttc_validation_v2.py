"""Run frozen FD-2 TTC and 500-ms cue-gate controls; no training or scoring."""
from __future__ import annotations
import gzip, hashlib, json, math
from pathlib import Path

from project_b.ea_mvp.continuous_multilane import ContinuousFourLaneFlyPolicy
from project_b.ea_mvp.screen_ttc import ScreenTimeToContactEncoder
from project_b.malecns_continuous_position_learning.online_policy import load_position_config
from project_b.osu.adapter import PositionObservation
from project_b.osu.types import KeyActionKind

ROOT=Path(__file__).resolve().parents[1]
CFG=ROOT/'configs/ea_mvp_fd2_ttc_validation_v2.json'
MODEL_CFG=ROOT/'configs/malecns_continuous_position_learning_v2_5.json'
RECEIPT=ROOT/'runs/ea_mvp/confirmation_fixed_v1'
OUT=ROOT/'runs/ea_mvp/fd2_ttc_validation_v2.json'
DT=1000; WINDOW=50_000; LEAD=500_000; HEIGHT_PX=560; TOL=73_500
FACTORS=(0.5,0.75,1.0,1.25,1.5); BASE_MS=1499

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def arm(seed,name):
 with gzip.open(RECEIPT/f'seed_{seed}_{name}.json.gz','rt',encoding='utf-8') as f: return json.load(f)
def clamp(x,lo,hi): return min(hi,max(lo,x))
def p_of(progress): return math.floor(clamp(progress,0.0,1.0)*HEIGHT_PX)/HEIGHT_PX

def stationary_control():
 enc=ScreenTimeToContactEncoder()
 return all(enc.observe(t*DT,0.5) is None for t in range(100))

def ramp_samples(factor):
 duration_ms=round(BASE_MS/factor); enc=ScreenTimeToContactEncoder(); rows=[]
 for t in range(duration_ms+1):
  p=p_of(t/duration_ms); sample=enc.observe(t*DT,p)
  if sample is not None:
   expected=clamp((duration_ms-t)/500.0,0.0,1.0)
   rows.append({'t_ms':t,'p':p,'q':sample.countdown,'ttc_hat_ms':sample.remaining_us/1000,
                'q_expected':expected,'ttc_error_ms':(sample.countdown-expected)*500.0,
                'v_per_s':sample.velocity_per_us*1_000_000})
 return duration_ms,rows

def step_control(old_factor,new_factor):
 switch_ms=round(BASE_MS*0.4)
 v_old=old_factor/(BASE_MS/1000); v_new=new_factor/(BASE_MS/1000)
 # Keep position continuous at the switch using distance accumulated at v_old.
 p_switch=p_of(v_old*switch_ms/1000)
 crossing_ms=switch_ms+(1-p_switch)/v_new*1000; end_ms=math.ceil(crossing_ms)
 enc=ScreenTimeToContactEncoder(); rows=[]
 for t in range(end_ms+1):
  progress=(v_old*t/1000 if t<=switch_ms else p_switch+v_new*(t-switch_ms)/1000)
  p=p_of(progress); sample=enc.observe(t*DT,p)
  if sample is not None:
   true_v=v_old if t<=switch_ms else v_new
   true_ttc_ms=max(0.0,(1-p)/true_v*1000)
   rows.append({'t_ms':t,'p':p,'ttc_hat_ms':sample.remaining_us/1000,
                'true_local_ttc_ms':true_ttc_ms,'error_ms':sample.remaining_us/1000-true_ttc_ms,
                'v_hat_per_s':sample.velocity_per_us*1_000_000})
 post=[r for r in rows if r['t_ms']>=switch_ms+50]
 return {'old_factor':old_factor,'new_factor':new_factor,'switch_ms':switch_ms,
         'position_continuous':True,'switch_position':p_switch,
         'post_window_samples':len(post),'max_abs_ttc_error_ms':max((abs(r['error_ms']) for r in post),default=0),
         'final_estimated_velocity_per_s':post[0]['v_hat_per_s'] if post else None,
         'expected_velocity_per_s':v_new,'post_window_rows':post[:1]+post[-1:]}

def policy_ramp(config,weights,duration_ms,factor):
 enc=ScreenTimeToContactEncoder(); policy=None; start_tick=None; transitions=[]
 end_ms=round(BASE_MS/factor)
 for t in range(end_ms+151):
  p=p_of(t/end_ms) if t<=end_ms else None
  sample=enc.observe(t*DT,p)
  if policy is None:
   if sample is None or not sample.cue_active: continue
   policy=ContinuousFourLaneFlyPolicy(config,weights); start_tick=t
   policy.begin(PositionObservation(True,0,sample.countdown)); continue
  active=sample is not None and sample.cue_active
  obs=PositionObservation(active,0,sample.countdown if active else None)
  transitions.extend(policy.step(obs))
 if policy is not None:
  policy.finish(); assert tuple(weights)==policy.weights
 actions=[{'time_us':start_tick*DT+row.episode_time_us,'lane':row.lane,'kind':row.kind.value}
          for row in transitions]
 return actions,start_tick,end_ms

def policy_check(actions,duration_ms):
 downs=[x for x in actions if x['kind']==KeyActionKind.DOWN.value]
 ups=[x for x in actions if x['kind']==KeyActionKind.UP.value]
 if len(downs)!=1 or downs[0]['lane']!=0: return False,f'expected one DOWN, got {downs}'
 if abs(downs[0]['time_us']-duration_ms*DT)>TOL: return False,f"DOWN error {downs[0]['time_us']-duration_ms*DT} us"
 if len(ups)!=1 or ups[0]['time_us']!=downs[0]['time_us']+10_000: return False,f'UP mismatch {ups}'
 return True,'single timed press and exact 10-ms release'

def main():
 model=load_position_config(ROOT,str(MODEL_CFG.relative_to(ROOT)))
 stationary=stationary_control(); ramps=[]
 for factor in FACTORS:
  duration,rows=ramp_samples(factor); q=[r['q'] for r in rows]
  errors=[abs(r['ttc_error_ms']) for r in rows if r['q']<0.999]
  ramps.append({'speed_factor':factor,'duration_ms':duration,'samples':len(rows),
    'countdown_bounded':all(0<=v<=1 for v in q),
    'maximum_positive_q_step':max((b-a for a,b in zip(q,q[1:])),default=0),
    'max_abs_ttc_error_ms_during_final_500ms':max(errors,default=0),'final_q':q[-1] if q else None})
 steps=[step_control(*pair) for pair in ((1.0,0.5),(1.0,1.5),(0.5,1.5),(1.5,0.5))]
 encoder_pass=stationary and all(r['countdown_bounded'] and r['final_q']==0 and r['max_abs_ttc_error_ms_during_final_500ms']<=55 for r in ramps) and all(s['max_abs_ttc_error_ms']<=55 for s in steps)
 policy_rows=[]
 if encoder_pass:
  for seed in (907,1009,1103):
   weights=arm(seed,'learning_on')['final_weights']
   for factor in FACTORS:
    duration=round(BASE_MS/factor); pair=[]
    for repeat in (1,2):
     actions,start,end=policy_ramp(model,weights,duration,factor); ok,note=policy_check(actions,duration)
     pair.append({'repeat':repeat,'actions':actions,'pass':ok,'note':note,'cue_start_tick_ms':start})
    policy_rows.append({'arm':'learning_on','seed':seed,'factor':factor,'duration_ms':duration,
                        'repeats':pair,'exact_repeat':pair[0]['actions']==pair[1]['actions']})
  initial=arm(907,'untrained')['initial_weights']; actions,start,end=policy_ramp(model,initial,BASE_MS,1.0)
  policy_rows.append({'arm':'untrained','seed':907,'factor':1.0,'duration_ms':BASE_MS,
                      'repeats':[{'repeat':1,'actions':actions,'pass':not actions,'note':'silent' if not actions else 'unexpected output'}]})
 policy_cells=[r for r in policy_rows if r['arm']=='learning_on']
 policy_pass=bool(policy_cells) and all(x['pass'] for r in policy_cells for x in r['repeats']) and all(r['exact_repeat'] for r in policy_cells) and policy_rows[-1]['repeats'][0]['pass']
 result={'protocol':'EA-MVP-FD2-TTC-VALIDATION-v2','status':'PASS' if encoder_pass and policy_pass else 'FAIL',
  'encoder_control_status':'PASS' if encoder_pass else 'FAIL',
  'frozen_policy_status':'PASS' if policy_pass else ('FAIL' if policy_rows else 'NOT_RUN'),
  'no_training':True,'no_game_or_score':True,'estimator':{'window_us':WINDOW,'target_lead_us':LEAD,'tick_us':DT,'speed_factors':list(FACTORS)},
  'source_config_sha256':sha(MODEL_CFG),'protocol_sha256':sha(CFG),'runner_sha256':sha(Path(__file__)),
  'encoder_source_sha256':sha(ROOT/'src/project_b/ea_mvp/screen_ttc.py'),
  'stationary_blank_pass':stationary,'constant_speed_ramps':ramps,'abrupt_speed_step_controls':steps,
  'action_tolerance_us':TOL,'frozen_policy_cases':policy_rows}
 OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps(result,indent=2))
if __name__=='__main__': main()
