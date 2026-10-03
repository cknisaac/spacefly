from __future__ import annotations
import hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PINNED='da27300fcbfa246f87c3ba1a14cbd00b68c7e9a9'
SRC=ROOT/'work/osu_lazer_reference'
PROJ=SRC/'osu.Game.Rulesets.Mania.Tests/osu.Game.Rulesets.Mania.Tests.csproj'
PROBE=ROOT/'scripts/lazer_4k_probe/L0FreedomDiveReplayParityProbe.cs'
INJECTED=PROJ.parent/'L0FreedomDiveReplayParityProbe.cs'
INPUT=ROOT/'work/ea_mvp_fd5_lazer_chart_input.json'
OUT=ROOT/'runs/ea_mvp/fd5_lazer_parity_v1.json'
DOTNET=shutil.which('dotnet') or 'C:/Program Files/dotnet/dotnet.exe'
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def run_once(dst,env):
 dst.unlink(missing_ok=True); e=env.copy(); e['EA_MVP_FD5_INPUT']=str(INPUT.resolve()); e['EA_MVP_FD5_OUTPUT']=str(dst.resolve())
 cmd=[DOTNET,'test',str(PROJ),'-c','Release','--no-restore','--filter','FullyQualifiedName~L0FreedomDiveReplayParityProbe','-m:1','/nodeReuse:false','-p:BuildInParallel=false','-p:RunAnalyzers=false','--logger','console;verbosity=normal','-clp:ErrorsOnly']
 p=subprocess.run(cmd,cwd=PROJ.parent,env=e,capture_output=True,text=True)
 if p.stdout: print(p.stdout,end='')
 if p.stderr: print(p.stderr,end='',file=sys.stderr)
 if p.returncode:return p.returncode,None
 return 0,json.loads(dst.read_text(encoding='utf-8'))
def main():
 if not PROJ.is_file() or not PROBE.is_file() or not INPUT.is_file(): raise SystemExit('missing pinned source, probe, or frozen input')
 rev=subprocess.run(['git','-C',str(SRC),'rev-parse','HEAD'],check=True,capture_output=True,text=True).stdout.strip()
 if rev!=PINNED: raise SystemExit(f'lazer revision mismatch: {rev}')
 if INJECTED.exists() and INJECTED.read_bytes()!=PROBE.read_bytes(): raise SystemExit('refusing to overwrite pre-existing injected probe')
 INJECTED.write_bytes(PROBE.read_bytes()); work=ROOT/'work'; (work/'tmp').mkdir(parents=True,exist_ok=True)
 env=os.environ.copy(); env.update({'DOTNET_CLI_HOME':str(work/'dotnet_cli_home'),'NUGET_PACKAGES':str(work/'nuget_packages_online'),'APPDATA':str(work/'dotnet_appdata'),'TEMP':str(work/'tmp'),'TMP':str(work/'tmp'),'DOTNET_SKIP_FIRST_TIME_EXPERIENCE':'1','DOTNET_CLI_TELEMETRY_OPTOUT':'1','DOTNET_PROCESSOR_COUNT':'2'})
 out1=work/'ea_mvp_fd5_lazer_probe.json'; out2=work/'ea_mvp_fd5_lazer_probe_repeat.json'; existed=True
 try:
  code,first=run_once(out1,env)
  if code: return code
  code,second=run_once(out2,env)
  if code:return code
  if first!=second: raise RuntimeError('pinned ReplayPlayer output changed between identical full-chart runs')
  OUT.parent.mkdir(parents=True,exist_ok=True)
  result={'protocol':'EA-MVP-FD5-LAZER-PARITY-v1','status':'CAPTURED','pinned_commit':rev,'input_sha256':sha(INPUT),'probe_sha256':sha(PROBE),'repeat_exact':True,'replay_player':first}
  OUT.write_text(json.dumps(result,indent=2),encoding='utf-8')
  print(json.dumps({'status':result['status'],'pinned_commit':rev,'results':len(first['Results']),'actions':len(first['Actions']),'score':first['Score'],'accuracy':first['Accuracy'],'combo':first['Combo'],'max_combo':first['MaxCombo'],'repeat_exact':True,'output':str(OUT)},indent=2))
  return 0
 finally:
  INJECTED.unlink(missing_ok=True)
if __name__=='__main__': raise SystemExit(main())
