"""Frozen-weight full Freedom Dive replay; current frames only reach the fly."""
from __future__ import annotations
import gzip, hashlib, json
from pathlib import Path
from project_b.ea_mvp.continuous_multilane import ContinuousFourLaneFlyPolicy
from project_b.ea_mvp.multicue_adapter import HoldKeyState, LaneTTCBank, VisualFrame, VisualHead, frame_from_renderer, select_nearest_head
from project_b.ea_mvp.screen_ttc import ScreenTimeToContactEncoder
from project_b.malecns_continuous_position_learning.online_policy import load_position_config
from project_b.osu.beatmap import extract_osz, is_native_4k, load_mania_beatmap
from project_b.osu.config import OsuConfig
from project_b.osu.mania_game import ManiaGame
from project_b.osu.adapter import PolicyKeyTransition, PositionObservation
from project_b.osu.types import HoldNote, KeyAction, KeyActionKind
from project_b.osu.windows import ManiaHitWindows

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=Path(r'C:\Users\imdef\AppData\Roaming\osu\exports\xi - FREEDOM DiVE (razlteh).osz')
SOURCE=ROOT/'runs/ea_mvp/fd1_typed_frames_v1.jsonl.gz'
PROTOCOL=ROOT/'configs/ea_mvp_fd4_chart_playback_v4.json'
MODEL_CFG=ROOT/'configs/malecns_continuous_position_learning_v2_5.json'
WEIGHT_FILE=ROOT/'runs/ea_mvp/confirmation_fixed_v1/seed_907_learning_on.json.gz'
OUT=ROOT/'runs/ea_mvp/fd4_chart_playback_v4.json'
DT=1000; PIXEL=1/560; MAX_HEADS=14

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for block in iter(lambda:f.read(1<<20),b''): h.update(block)
 return h.hexdigest()

def chart():
 files=tuple(p for p in extract_osz(ARCHIVE) if is_native_4k(p) and '4K Normal' in p.name)
 if len(files)!=1: raise RuntimeError(f'expected one native 4K Normal, got {len(files)}')
 bm=load_mania_beatmap(files[0])
 if bm.sha256!='ced99e231e7eee354feef04bbcde6889178814cb688325bccdeeeacb00dcbff9': raise RuntimeError('map hash mismatch')
 return bm

def fast_policy_step(policy,observation):
 """Same causal policy step without copying complete simulator history each ms."""
 if observation.visible and observation.lane not in range(4): raise ValueError('invalid lane')
 if observation.visible and not policy._previous_visible: policy._active_lane=observation.lane
 translated=PositionObservation(observation.visible,0,observation.position if observation.visible else None)
 policy._time_us+=policy.dt_us; time_us=policy._time_us
 policy._sim._step(time_us)
 voltage=policy._sim._voltage_trace[-1].voltage_before_reset_mv
 new_spikes=policy._sim._spikes[policy._spike_count:]
 policy._spike_count=len(policy._sim._spikes)
 if translated.visible and not policy._previous_visible: policy._cue_start_time_us=time_us
 emitted=(); created_readout=False
 if (translated.visible and policy._readout is None and policy._cue_start_time_us is not None
     and any(spike.neuron_index<policy.n_kc and spike.time_us>=policy._cue_start_time_us for spike in new_spikes)):
  assert translated.position is not None
  policy._readout=policy._new_readout(time_us,translated.position)
  policy.readout_start_times.append(time_us); created_readout=True
 if policy._readout is not None and not created_readout:
  emitted=policy._readout.step(time_us,translated.position if translated.visible else None,voltage)
  if (not translated.visible and not policy._readout._key_down and policy._readout._last_position is None):
   policy._readout=None
 policy._sim.set_external_drive_mv(policy._drive(translated))
 policy._previous_visible=translated.visible
 return tuple(PolicyKeyTransition(event.time_us,policy._active_lane,event.kind) for event in emitted)

def check_fast_step_equivalence(config,weights):
 reference=ContinuousFourLaneFlyPolicy(config,weights); fast=ContinuousFourLaneFlyPolicy(config,weights)
 first=PositionObservation(True,0,1.0); reference.begin(first); fast.begin(first)
 ref_events=[]; fast_events=[]
 for i in range(1,502):
  obs=PositionObservation(True,0,max(0.0,1.0-i/500.0))
  ref_events.extend(reference.step(obs)); fast_events.extend(fast_policy_step(fast,obs))
 for _ in range(20):
  obs=PositionObservation(False,0,None)
  ref_events.extend(reference.step(obs)); fast_events.extend(fast_policy_step(fast,obs))
 reference.finish(); fast.finish()
 equivalent=(ref_events==fast_events and reference.weights==fast.weights
             and reference.readout_rearm_count==fast.readout_rearm_count
             and reference._sim.snapshot().voltage_trace==fast._sim.snapshot().voltage_trace
             and reference._sim.snapshot().spikes==fast._sim.snapshot().spikes)
 if not equivalent: raise RuntimeError('fast stepping differs from canonical policy on the frozen 500-ms cue')
 return {'pass':True,'actions':[{'time_us':e.episode_time_us,'lane':e.lane,'kind':e.kind.value} for e in fast_events],
         'spikes':fast.spike_count,'readout_rearms':fast.readout_rearm_count}

def lane_bank_control():
 bank=LaneTTCBank(); selected_track=[]
 for t in range(0,712):
  p0=min(1.0,t/500.0) if t<=500 else None
  p1=min(1.0,max(0.0,(t-200)/500.0))
  heads=[]
  if p0 is not None: heads.append(VisualHead(0,p0,'tap'))
  heads.append(VisualHead(1,p1,'tap'))
  states=bank.observe(t*DT,VisualFrame(tuple(heads)))
  if t in (500,511): selected_track.append({'t_ms':t,'lane0_q':states[0].countdown,'lane1_q':states[1].countdown,'lane1_active':states[1].cue_active})
 at_switch=selected_track[0]['lane1_q']; after_blank=selected_track[1]['lane1_q']
 passed=(at_switch is not None and after_blank is not None and 0<after_blank<at_switch and selected_track[1]['lane1_active'])
 if not passed: raise RuntimeError('per-lane TTC task-free switch control failed')
 return {'pass':True,'switch_samples':selected_track,'no_schedule_input':True}

def duplicate_down_control():
 down=set(); delivered=[]; suppressed=[]
 for t,lane,kind in ((0,2,'down'),(1,2,'down'),(10,2,'up')):
  if kind=='down' and lane in down:
   suppressed.append((t,lane,kind)); continue
  delivered.append((t,lane,kind))
  if kind=='down': down.add(lane)
  else: down.discard(lane)
 return {'pass':delivered==[(0,2,'down'),(10,2,'up')] and suppressed==[(1,2,'down')] and not down,
         'delivered':delivered,'suppressed':suppressed,'keys_released':not down}

def one_run(bm,config,weights):
 game=ManiaGame(bm.notes,OsuConfig(od=bm.od,ruleset='lazer')); bank=LaneTTCBank()
 policy=None; origin_us=None; policy_ticks=0; cue_latched=False; last_q=None; blank_remaining=0
 previous_selected=False; previous_position=None; previous_lanes=None; lane_kinds={}; cue_lanes=(0,)
 hold_keys=HoldKeyState(); tap_keys:set[int]=set(); output_down:set[int]=set(); suppressed_rows=[]; action_rows=[]; raw_frames=0; selected_frames=0
 boundary_count=0; valid_ttc=0; active_cues=0; max_voltage=0.0; max_heads=0; max_tails=0
 def apply(at_us,lane,kind,source):
  nonlocal action_rows
  event=game.apply_action(KeyAction(at_us,lane,kind))
  if kind is KeyActionKind.DOWN: output_down.add(lane)
  else: output_down.discard(lane)
  action_rows.append({'time_us':at_us,'lane':lane,'kind':kind.value,'source':source,
                      'disposition':event.disposition,'note_id':event.note_id})
 def neural_tick(at_us,frame,active,q,selected):
  nonlocal policy,origin_us,policy_ticks,cue_lanes,lane_kinds,tap_keys,suppressed_rows
  obs=PositionObservation(active,0,q if active else None)
  if policy is None:
   if not active:return
   policy=ContinuousFourLaneFlyPolicy(config,weights); policy.begin(obs); origin_us=at_us; return
  policy_ticks+=1
  if selected is not None and active:
   cue_lanes=selected.lanes; lane_kinds=dict(selected.kinds_by_lane)
  transitions=fast_policy_step(policy,obs)
  for event in transitions:
   event_time=origin_us+event.episode_time_us
   if event_time>at_us: raise RuntimeError('fly emitted a future action')
   if event.kind is KeyActionKind.DOWN:
    for lane in cue_lanes:
     if lane in output_down:
      suppressed_rows.append({'time_us':event_time,'lane':lane,'kind':'down','reason':'key_already_down'})
      continue
     if lane_kinds.get(lane)=='hold': hold_keys.key_down(lane,hold=True)
     else: tap_keys.add(lane)
     apply(event_time,lane,KeyActionKind.DOWN,'fly_down')
   else:
    # Pair the fixed 10-ms UP with its original DOWN lanes. Suppress it for holds.
    for lane in tuple(sorted(tap_keys)):
     apply(event_time,lane,KeyActionKind.UP,'fly_tap_release'); tap_keys.remove(lane)
  # Tail release is visual and independent of the game result stream.
  for lane in hold_keys.observe_tails(frame.tails):
   if lane in output_down: apply(at_us,lane,KeyActionKind.UP,'visible_hold_tail')
   else: hold_keys.held_lanes.discard(lane)

 with gzip.open(SOURCE,'rt',encoding='utf-8') as stream:
  for line in stream:
   row=json.loads(line); at_us=row['tick_us']; frame=frame_from_renderer(row['visible']); raw_frames+=1
   max_heads=max(max_heads,len(frame.heads)); max_tails=max(max_tails,len(frame.tails)); selected=select_nearest_head(frame)
   game.advance_to(at_us)
   if selected is None:
    if previous_selected:
     cue_latched=False; last_q=None; blank_remaining=11; boundary_count+=1
    previous_selected=False; previous_position=None; previous_lanes=None
    bank.observe(at_us,frame)
    if blank_remaining>0: blank_remaining-=1
    neural_tick(at_us,frame,False,None,None); continue
   selected_frames+=1; p=selected.position
   boundary=(previous_selected and ((p<previous_position-PIXEL) or selected.lanes!=previous_lanes))
   if boundary:
    cue_latched=False; last_q=None; blank_remaining=11; boundary_count+=1
   states=bank.observe(at_us,frame)
   estimates=[states[lane] for lane in selected.lanes if states[lane].countdown is not None]
   if estimates:
    valid_ttc+=len(estimates); raw_q=min(x.countdown for x in estimates)
    q=raw_q if last_q is None else min(last_q,raw_q); last_q=q
    if any(x.cue_active for x in estimates): cue_latched=True
   else:q=last_q
   active=cue_latched and q is not None and blank_remaining==0
   if active and (not previous_selected or boundary): active_cues+=1
   if blank_remaining>0: blank_remaining-=1
   neural_tick(at_us,frame,active,q,selected if active else None)
   previous_selected=True; previous_position=p; previous_lanes=selected.lanes
 # Flush game expiries and ensure any lingering hold/tap keys are reported rather than silently forced.
 tail_stop=max(bm.end_time_us+ManiaHitWindows.from_od(bm.od,'lazer').expiry_offset_us*2,game.now_us)
 for at_us in range(game.now_us+DT,tail_stop+DT,DT):
  game.advance_to(at_us)
  empty=VisualFrame()
  neural_tick(at_us,empty,False,None,None)
 if policy is not None:
  policy.finish(); snapshot=policy._sim.snapshot()
  max_voltage=max((abs(x.voltage_before_reset_mv) for x in snapshot.voltage_trace),default=0.0)
 game.finish()
 scores=game.score.snapshot()
 note_results=[x for x in game.results if x.component in ('tap','head')]
 counts={}
 for event in game.results: counts[event.result]=counts.get(event.result,0)+1
 return {'actions':action_rows,'suppressed_down_attempts':suppressed_rows,'result_rows':[{'note_id':x.note_id,'component':x.component,'lane':x.lane,
  'note_time_us':x.note_time_us,'time_us':x.time_us,'result':x.result,'hit_error_us':x.hit_error_us} for x in game.results],
  'score':{'score':scores.score,'accuracy':scores.accuracy,'combo':scores.combo,'max_combo':scores.max_combo,
   'judged_accuracy_objects':scores.judged_accuracy_objects,'total_accuracy_objects':scores.total_accuracy_objects,'result_counts':scores.result_counts},
  'counts':{'objects':len(bm.notes),'tap_objects':bm.tap_count,'hold_objects':bm.hold_count,'head_or_tap_results':len(note_results),
   'result_counts':counts,'actions':len(action_rows),'downs':sum(x['kind']=='down' for x in action_rows),
   'ups':sum(x['kind']=='up' for x in action_rows),'raw_frames':raw_frames,'selected_frames':selected_frames,
   'max_heads_after_crop':max_heads,'max_per_lane_tails':max_tails,'ttc_samples':valid_ttc,'cue_boundaries':boundary_count,
   'cue_starts':active_cues,'policy_ticks':policy_ticks,'neural_initializations':0 if policy is None else policy.neural_reset_count,
   'readout_rearms':0 if policy is None else policy.readout_rearm_count,'max_abs_mbon_voltage_mv':max_voltage,
   'stuck_game_keys':[i for i,v in enumerate(game.key_down) if v],'output_down_lanes':sorted(output_down),
   'active_hold_lanes':sorted(hold_keys.held_lanes),
   'pending_tap_lanes':sorted(tap_keys)},'weights_unchanged':policy is None or tuple(weights)==policy.weights}

def main():
 protocol=json.loads(PROTOCOL.read_text(encoding='utf-8-sig'))
 for relative,key in [('scripts/run_ea_mvp_fd4_chart_playback_v4.py','runner'),('src/project_b/ea_mvp/multicue_adapter.py','adapter'),
                      ('src/project_b/ea_mvp/screen_ttc.py','fd2_encoder'),('src/project_b/osu/mania_game.py','game_engine'),
                      ('scripts/build_ea_mvp_fd4_typed_renderer_stream.py','typed_builder'),
                      ('src/project_b/osu/playable.py','scroll_map'),
                      ('src/project_b/osu/beatmap.py','beatmap_parser'),
                      ('src/project_b/ea_mvp/continuous_v2.py','policy_source'),
                      ('src/project_b/simulation/spiking.py','spiking_simulator')]:
  if sha(ROOT/relative)!=protocol['frozen_code_sha256'][key]: raise RuntimeError(f'frozen source changed: {relative}')
 if sha(SOURCE)!=protocol['source_frame_sha256']: raise RuntimeError('typed current-frame source changed')
 bm=chart()
 if (len(bm.notes),bm.tap_count,bm.hold_count)!=(1310,1220,90): raise RuntimeError('chart object count mismatch')
 model=load_position_config(ROOT,str(MODEL_CFG.relative_to(ROOT)))
 with gzip.open(WEIGHT_FILE,'rt',encoding='utf-8') as f: weights=json.load(f)['final_weights']
 fast_step_check=check_fast_step_equivalence(model,weights)
 lane_bank_check=lane_bank_control()
 dedupe_check=duplicate_down_control()
 runs=[one_run(bm,model,weights) for _ in range(protocol['repeats'])]
 repeat=(runs[0]['actions']==runs[1]['actions'] and runs[0]['result_rows']==runs[1]['result_rows'])
 c=runs[0]['counts']; checks={'full_chart_head_or_tap_results':c['head_or_tap_results']==1310,
  'deterministic_repeat':repeat,'one_neural_initialization':c['neural_initializations']==1,
  'weights_unchanged':runs[0]['weights_unchanged'] and runs[1]['weights_unchanged'],
  'down_up_counts_match':c['downs']==c['ups'],'duplicate_down_guard':dedupe_check['pass'],
  'no_stuck_keys':not c['stuck_game_keys'] and not c['output_down_lanes'] and not c['active_hold_lanes'] and not c['pending_tap_lanes']}
 result={'protocol':'EA-MVP-FD4-CHART-PLAYBACK-v4','status':'PASS' if all(checks.values()) else 'FAIL',
  'chart':{'sha256':bm.sha256,'title':bm.title,'version':bm.version,'objects':len(bm.notes),'taps':bm.tap_count,'holds':bm.hold_count},
  'no_training':True,'no_game_feedback':True,'no_score_tuning':True,'fast_step_equivalence':fast_step_check,
  'lane_bank_task_free_control':lane_bank_check,'duplicate_down_task_free_control':dedupe_check,'checks':checks,'runs':runs,
  'protocol_sha256':sha(PROTOCOL),'runner_sha256':sha(Path(__file__)),'frame_source_sha256':sha(SOURCE)}
 OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps({k:v for k,v in result.items() if k!='runs'},indent=2))
if __name__=='__main__': main()
