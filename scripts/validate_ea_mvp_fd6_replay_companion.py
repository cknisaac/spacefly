from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from project_b.osu.beatmap import extract_osz,is_native_4k,load_mania_beatmap
from project_b.ea_mvp.replay_companion import DEFAULT_MAP,DEFAULT_TRACE,EXPECTED_MAP_SHA256,load_actions,rebuild_game
trace=json.loads(DEFAULT_TRACE.read_text(encoding='utf-8'));maps=[p for p in extract_osz(DEFAULT_MAP) if is_native_4k(p) and '4K Normal' in p.name]
if len(maps)!=1:raise SystemExit('expected one source chart')
bm=load_mania_beatmap(maps[0]);actions=load_actions(trace)
if bm.sha256!=EXPECTED_MAP_SHA256 or trace['chart']['sha256']!=bm.sha256:raise SystemExit('map hash mismatch')
game,index=rebuild_game(bm,actions,bm.end_time_us+2_000_000);game.finish()
rows=[{'note_id':x.note_id,'component':x.component,'lane':x.lane,'note_time_us':x.note_time_us,'time_us':x.time_us,'result':x.result,'hit_error_us':x.hit_error_us} for x in game.results]
expected=trace['runs'][0]['result_rows'];score=game.score.snapshot();checks={'all_actions_replayed':index==len(actions),'ordered_results_exact':rows==expected,'score_exact':score.score==trace['runs'][0]['score']['score'],'accuracy_exact':score.accuracy==trace['runs'][0]['score']['accuracy'],'combo_exact':score.combo==trace['runs'][0]['score']['combo'],'max_combo_exact':score.max_combo==trace['runs'][0]['score']['max_combo'],'no_stuck_keys':not any(game.key_down)}
print(json.dumps({'status':'PASS' if all(checks.values()) else 'FAIL','checks':checks,'action_count':index,'result_count':len(rows),'score':score.score,'accuracy':score.accuracy,'max_combo':score.max_combo},indent=2))
if not all(checks.values()):raise SystemExit(1)

