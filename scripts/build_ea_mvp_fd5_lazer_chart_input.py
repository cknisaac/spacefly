from __future__ import annotations
import gzip, hashlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from project_b.osu.beatmap import extract_osz,is_native_4k,load_mania_beatmap
ARCHIVE=Path(r'C:\Users\imdef\AppData\Roaming\osu\exports\xi - FREEDOM DiVE (razlteh).osz')
RUN=ROOT/'runs/ea_mvp/fd4_chart_playback_v4.json'
OUT=ROOT/'work/ea_mvp_fd5_lazer_chart_input.json'
expected='ced99e231e7eee354feef04bbcde6889178814cb688325bccdeeeacb00dcbff9'
files=[p for p in extract_osz(ARCHIVE) if is_native_4k(p) and '4K Normal' in p.name]
if len(files)!=1: raise SystemExit(f'expected one map, got {len(files)}')
bm=load_mania_beatmap(files[0])
if bm.sha256!=expected: raise SystemExit('chart SHA mismatch')
played=json.loads(RUN.read_text(encoding='utf-8'))
if played['status']!='PASS': raise SystemExit('FD4 source run not PASS')
notes=[{'id':n.note_id,'lane':n.lane,'start_time_us':int(n.time_us),'end_time_us':int(n.end_time_us) if hasattr(n,'end_time_us') else int(n.time_us),'kind':'hold' if hasattr(n,'end_time_us') and n.end_time_us>n.time_us else 'tap'} for n in bm.notes]
actions=[{'time_us':x['time_us'],'lane':x['lane'],'kind':x['kind']} for x in played['runs'][0]['actions']]
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps({'schema_version':1,'chart_sha256':bm.sha256,'od':int(bm.od),'notes':notes,'actions':actions},separators=(',',':')),encoding='utf-8')
print(json.dumps({'output':str(OUT),'notes':len(notes),'taps':sum(n['kind']=='tap' for n in notes),'holds':sum(n['kind']=='hold' for n in notes),'actions':len(actions),'sha256':hashlib.sha256(OUT.read_bytes()).hexdigest()},indent=2))


