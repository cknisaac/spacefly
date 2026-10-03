from __future__ import annotations
import hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; PINNED='da27300fcbfa246f87c3ba1a14cbd00b68c7e9a9'; SOURCE=ROOT/'work/osu_lazer_reference'; PROJECT=SOURCE/'osu.Game.Rulesets.Mania.Tests/osu.Game.Rulesets.Mania.Tests.csproj'; PROBE=ROOT/'scripts/lazer_4k_probe/L0FreedomDiveReplayParityProbeV5.cs'; INJECTED=PROJECT.parent/'L0FreedomDiveReplayParityProbeV5.cs'; INPUT=ROOT/'work/ea_mvp_fd5_lazer_chart_input_v4.json'; OUT=ROOT/'runs/ea_mvp/fd5_lazer_parity_probe_capture_v5.json'; DOTNET=shutil.which('dotnet') or 'C:/Program Files/dotnet/dotnet.exe'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def stable(rows):
 out=[]
 for row in rows:
  results=[{**q,'OffsetUs':None} if q['Result'] in ('MISS','IGNOREMISS') else q for q in row['Results']]
  results.sort(key=lambda q:(q['ObjectTimeUs'],q['Lane'],q['Component'],q['Result']))
  actions=sorted((q['TimeUs'],q['Lane'],q['Kind']) for q in row['Actions'])
  out.append((row['Id'],results,actions))
 return out
def once(dst,base):
 dst.unlink(missing_ok=True);env=base.copy();env['EA_MVP_FD5_INPUT']=str(INPUT.resolve());env['EA_MVP_FD5_OUTPUT']=str(dst.resolve());cmd=[DOTNET,'test',str(PROJECT),'-c','Release','--no-restore','--filter','FullyQualifiedName~L0FreedomDiveReplayParityProbeV5','-m:1','/nodeReuse:false','-p:BuildInParallel=false','-p:RunAnalyzers=false','--logger','console;verbosity=normal','-clp:ErrorsOnly'];p=subprocess.run(cmd,cwd=PROJECT.parent,env=env,capture_output=True,text=True);print(p.stdout,end='');print(p.stderr,end='',file=sys.stderr);return p.returncode,[json.loads(x) for x in dst.read_text(encoding='utf-8').splitlines()] if p.returncode==0 else []
def main():
 if not (PROJECT.is_file() and PROBE.is_file() and INPUT.is_file()):raise SystemExit('missing source/probe/input')
 rev=subprocess.run(['git','-C',str(SOURCE),'rev-parse','HEAD'],check=True,capture_output=True,text=True).stdout.strip()
 if rev!=PINNED:raise SystemExit('pinned lazer revision mismatch')
 if INJECTED.exists() and INJECTED.read_bytes()!=PROBE.read_bytes():raise SystemExit('refusing to overwrite pre-existing probe')
 INJECTED.write_bytes(PROBE.read_bytes());work=ROOT/'work';(work/'tmp').mkdir(parents=True,exist_ok=True);env=os.environ.copy();env.update({'DOTNET_CLI_HOME':str(work/'dotnet_cli_home'),'NUGET_PACKAGES':str(work/'nuget_packages_online'),'APPDATA':str(work/'dotnet_appdata'),'TEMP':str(work/'tmp'),'TMP':str(work/'tmp'),'DOTNET_SKIP_FIRST_TIME_EXPERIENCE':'1','DOTNET_CLI_TELEMETRY_OPTOUT':'1','DOTNET_PROCESSOR_COUNT':'2'})
 try:
  code,a=once(work/'ea_mvp_fd5_lazer_v5.jsonl',env)
  if code:return code
  code,b=once(work/'ea_mvp_fd5_lazer_v5_repeat.jsonl',env)
  if code:return code
  repeat=stable(a)==stable(b); data=json.loads(INPUT.read_text(encoding='utf-8')); expected={s['id']:s for s in data['segments']}; observed={x['Id']:x for x in a}
  action_checks=[]
  for sid,s in expected.items():
   exp=[{'time_us':x['time_us'],'lane':x['lane'],'kind':x['kind']} for x in s['actions']]
   got=[{'time_us':x['TimeUs'],'lane':x['Lane'],'kind':x['Kind']} for x in sorted(observed[sid]['Actions'],key=lambda q:q['Sequence'])]
   action_checks.append({'segment':sid,'exact':got==exp,'expected':len(exp),'observed':len(got)})
  result={'protocol':'EA-MVP-FD5-LAZER-PARITY-v5','status':'CAPTURED','pinned_commit':rev,'chart_sha256':data['chart_sha256'],'input_sha256':sha(INPUT),'probe_sha256':sha(PROBE),'repeat_exact':repeat,'action_transition_checks':action_checks,'replay_player':a}
  OUT.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({'status':result['status'],'segments':len(a),'actions':sum(len(x['Actions']) for x in a),'results':sum(len(x['Results']) for x in a),'exact_repeat':repeat,'all_action_transitions_exact':all(x['exact'] for x in action_checks),'scores_per_segment':[x['Score'] for x in a],'output':str(OUT)},indent=2));return 0
 finally:INJECTED.unlink(missing_ok=True)
if __name__=='__main__':raise SystemExit(main())
