from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from project_b.osu.beatmap import extract_osz,is_native_4k,load_mania_beatmap
ARCHIVE=Path(r'C:\Users\imdef\AppData\Roaming\osu\exports\xi - FREEDOM DiVE (razlteh).osz');PLAY=ROOT/'runs/ea_mvp/fd4_chart_playback_v4.json';OUT=ROOT/'work/ea_mvp_fd5_lazer_chart_input_v3.json';EXPECT='ced99e231e7eee354feef04bbcde6889178814cb688325bccdeeeacb00dcbff9'
paths=[p for p in extract_osz(ARCHIVE) if is_native_4k(p) and '4K Normal' in p.name]
if len(paths)!=1:raise SystemExit('expected one pinned 4K Normal')
bm=load_mania_beatmap(paths[0]);play=json.loads(PLAY.read_text(encoding='utf-8'))
if bm.sha256!=EXPECT or play['status']!='PASS':raise SystemExit('chart/source mismatch')
notes=[]
for n in bm.notes:
 st=int(n.time_us);en=int(n.end_time_us) if hasattr(n,'end_time_us') else st
 notes.append({'id':n.note_id,'lane':n.lane,'start_time_us':st,'end_time_us':en,'kind':'hold' if en>st else 'tap'})
actions=[{'time_us':a['time_us'],'lane':a['lane'],'kind':a['kind']} for a in play['runs'][0]['actions']]
segments=[];i=0;origin=notes[0]['start_time_us']-1_000_000
while i<len(notes):
 target=notes[i]['start_time_us']+15_000_000;j=i
 while j<len(notes) and notes[j]['start_time_us']<target:j+=1
 if j>=len(notes):end=max(n['end_time_us'] for n in notes[i:])+2_000_000
 else:
  end=notes[j]['start_time_us']
  while True:
   crossing=[n['end_time_us'] for n in notes if n['kind']=='hold' and n['start_time_us']<end<n['end_time_us']]
   if not crossing:break
   end=max(crossing)+1_000_000
   while j<len(notes) and notes[j]['start_time_us']<end:j+=1
 subset=[n for n in notes[i:j] if n['start_time_us']<end]
 if not subset:raise SystemExit('empty segment')
 localnotes=[{**n,'start_time_us':n['start_time_us']-origin,'end_time_us':n['end_time_us']-origin} for n in subset]
 locala=[{**a,'time_us':a['time_us']-origin} for a in actions if origin<=a['time_us']<end]
 segments.append({'id':f'segment-{len(segments):02d}','origin_time_us':origin,'end_time_us':end,'notes':localnotes,'actions':locala})
 i=j;origin=end
payload={'schema_version':3,'chart_sha256':bm.sha256,'od':int(bm.od),'notes':notes,'actions':actions,'segments':segments}
OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(payload,separators=(',',':')),encoding='utf-8')
print(json.dumps({'segments':len(segments),'durations_ms':[round((x['end_time_us']-x['origin_time_us'])/1000) for x in segments],'action_counts':[len(x['actions']) for x in segments],'total_actions':sum(len(x['actions']) for x in segments),'sha256':hashlib.sha256(OUT.read_bytes()).hexdigest()},indent=2))
