"""Build the current-frame-only typed visual stream using the existing renderer math."""
from __future__ import annotations
import gzip, hashlib, json
from collections import defaultdict
from pathlib import Path
from project_b.osu.beatmap import extract_osz, is_native_4k, load_mania_beatmap
from project_b.osu.playable import ScrollMap
from project_b.osu.types import HoldNote

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=Path(r'C:\Users\imdef\AppData\Roaming\osu\exports\xi - FREEDOM DiVE (razlteh).osz')
PROTOCOL=ROOT/'configs/ea_mvp_fd4_typed_renderer_stream_v1.json'
OUT=ROOT/'runs/ea_mvp/fd1_typed_frames_v1.jsonl.gz'
SUMMARY=ROOT/'runs/ea_mvp/fd4_typed_renderer_stream_v1.json'
TOP=75; LINE=635; HEIGHT=560; RANGE_US=11_485_000/8; DT=1000
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
def tickceil(t): return ((t+DT-1)//DT)*DT

def main():
 protocol=json.loads(PROTOCOL.read_text(encoding='utf-8-sig'))
 maps=tuple(p for p in extract_osz(ARCHIVE) if is_native_4k(p) and '4K Normal' in p.name)
 if len(maps)!=1: raise RuntimeError(f'expected one 4K Normal map, found {len(maps)}')
 bm=load_mania_beatmap(maps[0])
 if bm.sha256!=protocol['chart_sha256']: raise RuntimeError('chart SHA mismatch')
 scroll=ScrollMap(bm); rows=defaultdict(list)
 def y_at(target_us,at_us):
  return LINE-int((scroll.position(target_us)-scroll.position(at_us))*HEIGHT/RANGE_US)
 timeline_end=max(note.end_time_us if isinstance(note,HoldNote) else note.time_us for note in bm.notes)
 for note in bm.notes:
  start=max(0,note.time_us-6_000_000); stop=min(timeline_end+300_000,note.time_us+300_000)
  for at in range(tickceil(start),stop+1,DT):
   y=y_at(note.time_us,at)
   if TOP-24<=y<=LINE+35:
    raw=(LINE-y)/HEIGHT
    rows[at].append({'lane':note.lane,'normalized_position':raw,'part':'head',
                     'kind':'hold' if isinstance(note,HoldNote) else 'tap'})
  if isinstance(note,HoldNote):
   start=max(0,note.time_us-6_000_000); stop=min(timeline_end+300_000,note.end_time_us+300_000)
   for at in range(tickceil(start),stop+1,DT):
    y=y_at(note.end_time_us,at)
    if TOP-22<=y<=LINE+30:
     rows[at].append({'lane':note.lane,'normalized_position':(LINE-y)/HEIGHT,'part':'tail'})
 end=tickceil(timeline_end+300_000); frames=(end//DT)+1; heads=0; tails=0; max_heads=0; max_tails=0
 OUT.parent.mkdir(parents=True,exist_ok=True)
 with gzip.open(OUT,'wt',encoding='utf-8',compresslevel=9) as stream:
  for at in range(0,end+1,DT):
   vals=rows.get(at,[]); vals.sort(key=lambda x:(x['lane'],x['normalized_position'],x['part'],x.get('kind','')))
   h=sum(x['part']=='head' for x in vals); t=sum(x['part']=='tail' for x in vals)
   heads+=h; tails+=t; max_heads=max(max_heads,h); max_tails=max(max_tails,t)
   stream.write(json.dumps({'tick_us':at,'visible':vals},separators=(',',':'))+'\n')
 result={'protocol':'EA-MVP-FD4-TYPED-RENDERER-STREAM-v1','status':'PASS' if max_heads<=14 and max_tails<=6 else 'FAIL',
  'chart_sha256':bm.sha256,'frame_stream_sha256':sha(OUT),'frames':frames,'heads':heads,'tails':tails,
  'max_heads_per_frame':max_heads,'max_tail_fragments_per_frame':max_tails,
  'typed_hold_heads':sum(isinstance(n,HoldNote) for n in bm.notes),'typed_tap_heads':sum(not isinstance(n,HoldNote) for n in bm.notes),
  'timeline_end_us':end,'protocol_sha256':sha(PROTOCOL),'runner_sha256':sha(Path(__file__)),
  'scroll_map_sha256':sha(ROOT/'src/project_b/osu/playable.py'),'beatmap_parser_sha256':sha(ROOT/'src/project_b/osu/beatmap.py'),
  'no_fly_or_game_run':True,'no_ids_or_schedule_in_frame_rows':True}
 SUMMARY.write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps(result,indent=2))
if __name__=='__main__': main()
