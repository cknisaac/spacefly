"""Apply frozen crop/inversion/TTC logic to the FD-1 frame-only artifact."""
from __future__ import annotations
import gzip, hashlib, json
from pathlib import Path
from project_b.ea_mvp.multicue_adapter import frame_from_renderer, select_nearest_head
from project_b.ea_mvp.screen_ttc import ScreenTimeToContactEncoder

ROOT=Path(__file__).resolve().parents[1]
SOURCE=Path(r'C:\Users\imdef\Documents\Codex\2026-10-03\https-claude-ai-artifact-1szgu2m2uaoex2fa4s3fnc-https\outputs\FD1_FREEDOM_DIVE_VISIBLE_FRAMES.jsonl.gz')
PROTOCOL=ROOT/'configs/ea_mvp_fd4_renderer_preflight_v2.json'
OUT=ROOT/'runs/ea_mvp/fd4_renderer_preflight_v2.json'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for block in iter(lambda:f.read(1<<20),b''): h.update(block)
 return h.hexdigest()

def main():
 enc=ScreenTimeToContactEncoder(); last_q=None; prior_position=None
 frames=0; raw_objects=0; raw_heads=0; raw_tails=0; kept_heads=0; dropped_heads=0
 tails=0; max_heads=0; max_tails=0; max_raw_tails=0; samples=0; bounded=True; monotone=True; reverse_resets=0
 pixel=1/560
 with gzip.open(SOURCE,'rt',encoding='utf-8') as handle:
  for line in handle:
   row=json.loads(line); frames+=1; raw_objects+=len(row['visible'])
   raw_heads+=sum(x['part']=='head' for x in row['visible']); tr=[x for x in row['visible'] if x['part']=='tail']
   raw_tails+=len(tr); max_raw_tails=max(max_raw_tails,len(tr))
   frame=frame_from_renderer(row['visible']); max_heads=max(max_heads,len(frame.heads)); max_tails=max(max_tails,len(frame.tails)); tails+=len(frame.tails)
   kept_heads+=len(frame.heads); dropped_heads+=sum(1 for x in row['visible'] if x['part']=='head')-len(frame.heads)
   selected=select_nearest_head(frame)
   if selected is None:
    enc.reset(); prior_position=None; last_q=None; continue
   p=selected.position
   if prior_position is not None and p < prior_position-pixel:
    enc.reset(); last_q=None; reverse_resets+=1
   sample=enc.observe(row['tick_us'],p)
   if sample is not None:
    samples+=1; bounded &= 0<=sample.countdown<=1 and sample.remaining_us>=0
    q=sample.countdown if last_q is None else min(last_q,sample.countdown)
    monotone &= last_q is None or q<=last_q; last_q=q
   prior_position=p
 protocol=json.loads(PROTOCOL.read_text(encoding='utf-8-sig'))
 checks={'exact_frame_count':frames==261636,'max_heads_le_14':max_heads<=14,
  'raw_tail_fragments_le_6':max_raw_tails<=6,'per_lane_tails_le_4':max_tails<=4,
  'all_countdown_bounded':bounded,'postfiltered_countdown_nonincreasing':monotone,
  'positive_valid_estimates':samples>0,'source_hash_matches_frozen_protocol':sha(SOURCE)==protocol['source_sha256']}
 result={'protocol':'EA-MVP-FD4-RENDERER-PREFLIGHT-v2','status':'PASS' if all(checks.values()) else 'FAIL',
  'no_training':True,'no_game_or_score':True,'source_sha256':sha(SOURCE),
  'counts':{'frames':frames,'raw_objects':raw_objects,'raw_heads':raw_heads,'raw_tail_fragments':raw_tails,
   'kept_heads':kept_heads,'dropped_heads':dropped_heads,'per_lane_tails':tails,'max_heads_per_frame':max_heads,
   'max_tail_fragments_per_frame':max_raw_tails,'max_per_lane_tails_per_frame':max_tails,'ttc_samples':samples,
   'selected_head_reverse_resets':reverse_resets},'checks':checks,'checks_pass':all(checks.values()),
  'protocol_sha256':sha(PROTOCOL),'runner_sha256':sha(Path(__file__)),
  'adapter_sha256':sha(ROOT/'src/project_b/ea_mvp/multicue_adapter.py'),
  'encoder_sha256':sha(ROOT/'src/project_b/ea_mvp/screen_ttc.py')}
 OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps(result,indent=2))
if __name__=='__main__': main()
