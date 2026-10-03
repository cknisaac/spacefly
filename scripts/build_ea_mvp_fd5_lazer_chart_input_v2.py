from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from project_b.osu.beatmap import extract_osz,is_native_4k,load_mania_beatmap
ARCHIVE=Path(r'C:\Users\imdef\AppData\Roaming\osu\exports\xi - FREEDOM DiVE (razlteh).osz');PLAY=ROOT/'runs/ea_mvp/fd4_chart_playback_v4.json';OUT=ROOT/'work/ea_mvp_fd5_lazer_chart_input_v2.json';EXPECT='ced99e231e7eee354feef04bbcde6889178814cb688325bccdeeeacb00dcbff9'
paths=[p for p in extract_osz(ARCHIVE) if is_native_4k(p) and '4K Normal' in p.name]
if len(paths)!=1:raise SystemExit('expected exact one map')
bm=load_mania_beatmap(paths[0]);run=json.loads(PLAY.read_text(encoding='utf-8'))
if bm.sha256!=EXPECT or run['status']!='PASS':raise SystemExit('chart or FD4 gate mismatch')
notes=[]
for n in bm.notes:
 end=int(n.end_time_us) if hasattr(n,'end_time_us') else int(n.time_us);start=int(n.time_us)
 notes.append({'id':n.note_id,'lane':n.lane,'start_time_us':start,'end_time_us':end,'kind':'hold' if end>start else 'tap'})
actions=[{'time_us':a['time_us'],'lane':a['lane'],'kind':a['kind']} for a in run['runs'][0]['actions']]
segments=[];i=0
while i<len(notes):
 start=notes[i]['start_time_us'];j=i
 while j<len(notes) and notes[j]['start_time_us']<start+15_000_000:j+=1
 if j>=len(notes):end=max(n['end_time_us'] for n in notes[i:])+2_000_000
 else:
  end=notes[j]['start_time_us']
  while True:
   crossing=[n['end_time_us'] for n in notes if n['kind']=='hold' and n['start_time_us']<end<n['end_time_us']]
   if not crossing:break
   end=max(crossing)+1_000_000
   while j<len(notes) and notes[j]['start_time_us']<end:j+=1
  end=max(end,max(n['end_time_us'] for n in notes[i:j])+1_000_000)
 subset=[n for n in notes[i:j] if n['start_time_us']<end]
 if not subset:raise SystemExit('empty segment')
 origin=subset[0]['start_time_us']-1_000_000
 localnotes=[{**n,'start_time_us':n['start_time_us']-origin,'end_time_us':n['end_time_us']-origin} for n in subset]
 locala=[{**a,'time_us':a['time_us']-origin} for a in actions if origin<=a['time_us']<end]
 segments.append({'id':f'segment-{len(segments):02d}','origin_time_us':origin,'end_time_us':end,'notes':localnotes,'actions':locala});i=j
payload={'schema_version':2,'chart_sha256':bm.sha256,'od':int(bm.od),'notes':notes,'actions':actions,'segments':segments}
OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(payload,separators=(',',':')),encoding='utf-8')
print(json.dumps({'segments':len(segments),'durations_ms':[round((x['end_time_us']-x['origin_time_us'])/1000) for x in segments],'actions':[len(x['actions']) for x in segments],'sha256':hashlib.sha256(OUT.read_bytes()).hexdigest()},indent=2))
