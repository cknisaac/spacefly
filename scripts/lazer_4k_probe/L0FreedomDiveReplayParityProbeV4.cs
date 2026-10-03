#nullable disable
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using NUnit.Framework;
using osu.Framework.Screens;
using osu.Game.Beatmaps;
using osu.Game.Beatmaps.ControlPoints;
using osu.Game.Replays;
using osu.Game.Rulesets;
using osu.Game.Rulesets.Mania;
using osu.Game.Rulesets.Mania.Beatmaps;
using osu.Game.Rulesets.Mania.Objects;
using osu.Game.Rulesets.Mania.Replays;
using osu.Game.Rulesets.Replays;
using osu.Game.Rulesets.Scoring;
using osu.Game.Scoring;
using osu.Game.Screens.Play;
using osu.Game.Tests.Visual;
namespace osu.Game.Rulesets.Mania.Tests
{
 public class L0FreedomDiveReplayParityProbeV4 : RateAdjustedBeatmapTestScene
 {
  protected override Ruleset CreateRuleset()=>new ManiaRuleset();
  private sealed class ResultRow{public string Component{get;set;}public string Result{get;set;}public long ObjectTimeUs{get;set;}public int Lane{get;set;}public long OffsetUs{get;set;}}
  private sealed class ActionRow{public long TimeUs{get;set;}public int Lane{get;set;}public string Kind{get;set;}public int Sequence{get;set;}}
  private sealed class OutputRow{public string Id{get;set;}public List<ResultRow> Results{get;set;}public List<ActionRow> Actions{get;set;}public long Score{get;set;}public double Accuracy{get;set;}public int Combo{get;set;}public int MaxCombo{get;set;}}
  [Test] public void RunFreedomDiveSegmentsThroughReplayPlayer()
  {
   string input=Environment.GetEnvironmentVariable("EA_MVP_FD5_INPUT"),output=Environment.GetEnvironmentVariable("EA_MVP_FD5_OUTPUT");using var doc=JsonDocument.Parse(File.ReadAllText(input));
   foreach(var seg in doc.RootElement.GetProperty("segments").EnumerateArray())
   {
    string id=seg.GetProperty("id").GetString();var objects=seg.GetProperty("notes").EnumerateArray().ToArray();
    var notes=objects.Select(x=>{double st=x.GetProperty("start_time_us").GetInt64()/1000.0;int lane=x.GetProperty("lane").GetInt32();if(x.GetProperty("kind").GetString()=="hold")return(ManiaHitObject)new HoldNote{StartTime=st,EndTime=x.GetProperty("end_time_us").GetInt64()/1000.0,Column=lane};return new Note{StartTime=st,Column=lane};}).ToList();
    var actionRows=seg.GetProperty("actions").EnumerateArray().ToArray();var frames=new List<ReplayFrame>();var held=new HashSet<int>();
    foreach(var a in actionRows){long at=a.GetProperty("time_us").GetInt64();int lane=a.GetProperty("lane").GetInt32();if(a.GetProperty("kind").GetString()=="down")held.Add(lane);else held.Remove(lane);frames.Add(new ManiaReplayFrame(at/1000.0,held.OrderBy(k=>k).Select(keyForLane).ToArray()));}
    frames.Add(new ManiaReplayFrame((objects.Max(x=>x.GetProperty("end_time_us").GetInt64())+2_000_000)/1000.0,Array.Empty<ManiaAction>()));
    var results=new List<ResultRow>();var actions=new List<ActionRow>();var captured=new OutputRow{Id=id,Results=results,Actions=actions};ScoreAccessibleReplayPlayer player=null;
    AddStep($"load {id}",()=>{var beatmap=new ManiaBeatmap(new StageDefinition(4)){HitObjects=notes,BeatmapInfo={Ruleset=new ManiaRuleset().RulesetInfo,Difficulty=new BeatmapDifficulty{OverallDifficulty=8}}};beatmap.ControlPointInfo.Add(0,new EffectControlPoint{ScrollSpeed=0.1f});Beatmap.Value=CreateWorkingBeatmap(beatmap);player=new ScoreAccessibleReplayPlayer(new Score{Replay=new Replay{Frames=frames}});player.OnLoadComplete+=_=>{player.AttachRecorder(actions);player.ScoreProcessor.NewJudgement+=r=>{var o=(ManiaHitObject)r.HitObject;string c=r.HitObject switch{HeadNote=>"head",TailNote=>"tail",HoldNoteBody=>"body",HoldNote=>"parent",Note=>"tap",_=>"unknown"};results.Add(new ResultRow{Component=c,Result=r.Type.ToString().ToUpperInvariant(),ObjectTimeUs=(long)Math.Round(o.StartTime*1000),Lane=o.Column,OffsetUs=(long)Math.Round(r.TimeOffset*1000)});};};LoadScreen(player);});
    AddUntilStep($"{id} starts",()=>Beatmap.Value.Track.CurrentTime==0);AddUntilStep($"{id} active",()=>player.IsCurrentScreen());AddUntilStep($"{id} complete",()=>player.ScoreProcessor.HasCompleted.Value);
    AddStep($"capture {id}",()=>{captured.Score=player.ScoreProcessor.TotalScore.Value;captured.Accuracy=player.ScoreProcessor.Accuracy.Value;captured.Combo=player.ScoreProcessor.Combo.Value;captured.MaxCombo=player.ScoreProcessor.HighestCombo.Value;File.AppendAllText(output,JsonSerializer.Serialize(captured)+Environment.NewLine);});
   }
  }
  private static ManiaAction keyForLane(int l)=>l switch{0=>ManiaAction.Key1,1=>ManiaAction.Key2,2=>ManiaAction.Key3,3=>ManiaAction.Key4,_=>throw new ArgumentOutOfRangeException(nameof(l))};
  private sealed class ScoreAccessibleReplayPlayer:ReplayPlayer{public new ScoreProcessor ScoreProcessor=>base.ScoreProcessor;public osu.Game.Rulesets.UI.DrawableRuleset ActiveRuleset=>DrawableRuleset;protected override bool PauseOnFocusLost=>false;public ScoreAccessibleReplayPlayer(Score s):base(s,new PlayerConfiguration{AllowPause=false,ShowResults=false}){}public void AttachRecorder(List<ActionRow> rows){var p=ActiveRuleset.GetType().GetProperty("KeyBindingInputManager",System.Reflection.BindingFlags.Instance|System.Reflection.BindingFlags.NonPublic);var m=p?.GetValue(ActiveRuleset) as ManiaInputManager;if(m==null)throw new InvalidOperationException("No mania input manager");var h=m.GetType().GetProperty("ReplayInputHandler")?.GetValue(m);m.KeyBindingContainer.Add(new Recorder(rows,()=>{var f=h.GetType().GetProperty("CurrentFrame")?.GetValue(h) as ReplayFrame;if(f==null)throw new InvalidOperationException("No replay frame");return(long)Math.Round(f.Time*1000);}));}}
  private sealed class Recorder:osu.Framework.Graphics.Containers.CompositeDrawable,osu.Framework.Input.Bindings.IKeyBindingHandler<ManiaAction>{private readonly List<ActionRow> rows;private readonly Func<long> now;public Recorder(List<ActionRow> r,Func<long> n){rows=r;now=n;}public bool OnPressed(osu.Framework.Input.Events.KeyBindingPressEvent<ManiaAction> e){record(e.Action,"down");return false;}public void OnReleased(osu.Framework.Input.Events.KeyBindingReleaseEvent<ManiaAction> e)=>record(e.Action,"up");private void record(ManiaAction a,string k){int l=(int)a;if(l>=0&&l<4)rows.Add(new ActionRow{TimeUs=now(),Lane=l,Kind=k,Sequence=rows.Count});}}
 }
}
