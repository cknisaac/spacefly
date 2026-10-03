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
using osu.Game.Rulesets.Judgements;
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
    public class L0FreedomDiveReplayParityProbe : RateAdjustedBeatmapTestScene
    {
        protected override Ruleset CreateRuleset() => new ManiaRuleset();

        private sealed class ObservedResult
        {
            public string Component { get; set; }
            public string Result { get; set; }
            public long ObjectTimeUs { get; set; }
            public int Lane { get; set; }
            public long OffsetUs { get; set; }
            public long ObservedGameTimeUs { get; set; }
        }

        private sealed class ObservedAction
        {
            public long TimeUs { get; set; }
            public int Lane { get; set; }
            public string Kind { get; set; }
            public int Sequence { get; set; }
        }

        private sealed class Output
        {
            public string Id { get; set; }
            public List<ObservedResult> Results { get; set; }
            public List<ObservedAction> Actions { get; set; }
            public long Score { get; set; }
            public double Accuracy { get; set; }
            public int Combo { get; set; }
            public int MaxCombo { get; set; }
        }

        [Test]
        public void RunFreedomDiveTraceThroughReplayPlayer()
        {
            string inputPath = Environment.GetEnvironmentVariable("EA_MVP_FD5_INPUT");
            string outputPath = Environment.GetEnvironmentVariable("EA_MVP_FD5_OUTPUT");
            using var document = JsonDocument.Parse(File.ReadAllText(inputPath));
            var root = document.RootElement;
            var objects = root.GetProperty("notes").EnumerateArray().ToArray();
            var idsByStart = objects.ToDictionary(
                x => (x.GetProperty("start_time_us").GetInt64(), x.GetProperty("lane").GetInt32()),
                x => x.GetProperty("id").GetString());
            var notes = objects.Select(x =>
            {
                double start = x.GetProperty("start_time_us").GetInt64() / 1000.0;
                int lane = x.GetProperty("lane").GetInt32();
                if (x.GetProperty("kind").GetString() == "hold")
                    return (ManiaHitObject)new HoldNote
                    {
                        StartTime = start,
                        EndTime = x.GetProperty("end_time_us").GetInt64() / 1000.0,
                        Column = lane,
                    };
                return new Note { StartTime = start, Column = lane };
            }).ToList();

            var actionRows = root.GetProperty("actions").EnumerateArray().ToArray();
            var frames = new List<ReplayFrame>();
            var held = new HashSet<int>();
            foreach (var group in actionRows.GroupBy(x => x.GetProperty("time_us").GetInt64()).OrderBy(g => g.Key))
            {
                foreach (var action in group)
                {
                    int lane = action.GetProperty("lane").GetInt32();
                    if (action.GetProperty("kind").GetString() == "down") held.Add(lane);
                    else held.Remove(lane);
                }
                frames.Add(new ManiaReplayFrame(group.Key / 1000.0,
                    held.OrderBy(k => k).Select(actionForLane).ToArray()));
            }

            long finalTimeUs = actionRows.Last().GetProperty("time_us").GetInt64() + 2_000_000;
            frames.Add(new ManiaReplayFrame(finalTimeUs / 1000.0, Array.Empty<ManiaAction>()));

            var observedResults = new List<ObservedResult>();
            var observedActions = new List<ObservedAction>();
            var output = new Output { Id = "freedom-dive-4k-normal", Results = observedResults, Actions = observedActions };
            ScoreAccessibleReplayPlayer player = null;
            AddStep("load Freedom Dive fly trace", () =>
            {
                var beatmap = new ManiaBeatmap(new StageDefinition(4))
                {
                    HitObjects = notes,
                    BeatmapInfo =
                    {
                        Ruleset = new ManiaRuleset().RulesetInfo,
                        Difficulty = new BeatmapDifficulty { OverallDifficulty = 8 },
                    },
                };
                beatmap.ControlPointInfo.Add(0, new EffectControlPoint { ScrollSpeed = 0.1f });
                Beatmap.Value = CreateWorkingBeatmap(beatmap);
                player = new ScoreAccessibleReplayPlayer(new Score { Replay = new Replay { Frames = frames } });
                player.OnLoadComplete += _ =>
                {
                    player.AttachTransitionRecorder(observedActions);
                    player.ScoreProcessor.NewJudgement += result =>
                    {
                        var judged = (ManiaHitObject)result.HitObject;
                        string component = result.HitObject switch
                        {
                            HeadNote => "head",
                            TailNote => "tail",
                            HoldNoteBody => "body",
                            HoldNote => "parent",
                            _ => "unknown"
                        };
                        long objectTime = (long)Math.Round(judged.StartTime * 1000);
                        observedResults.Add(new ObservedResult
                        {
                            Component = component,
                            Result = result.Type.ToString().ToUpperInvariant(),
                            ObjectTimeUs = objectTime,
                            Lane = judged.Column,
                            OffsetUs = (long)Math.Round(result.TimeOffset * 1000),
                            ObservedGameTimeUs = (long)Math.Round(result.TimeAbsolute * 1000),
                        });
                    };
                };
                LoadScreen(player);
            });
            AddUntilStep("beatmap starts", () => Beatmap.Value.Track.CurrentTime == 0);
            AddUntilStep("player active", () => player.IsCurrentScreen());
            AddUntilStep("replay complete", () => player.ScoreProcessor.HasCompleted.Value);
            AddStep("capture full chart", () =>
            {
                output.Score = player.ScoreProcessor.TotalScore.Value;
                output.Accuracy = player.ScoreProcessor.Accuracy.Value;
                output.Combo = player.ScoreProcessor.Combo.Value;
                output.MaxCombo = player.ScoreProcessor.HighestCombo.Value;
                File.WriteAllText(outputPath, JsonSerializer.Serialize(output) + Environment.NewLine);
            });
        }

        private static ManiaAction actionForLane(int lane) => lane switch
        {
            0 => ManiaAction.Key1,
            1 => ManiaAction.Key2,
            2 => ManiaAction.Key3,
            3 => ManiaAction.Key4,
            _ => throw new ArgumentOutOfRangeException(nameof(lane)),
        };

        private sealed class ScoreAccessibleReplayPlayer : ReplayPlayer
        {
            public new ScoreProcessor ScoreProcessor => base.ScoreProcessor;
            public osu.Game.Rulesets.UI.DrawableRuleset ActiveRuleset => DrawableRuleset;
            protected override bool PauseOnFocusLost => false;
            public ScoreAccessibleReplayPlayer(Score score) : base(score, new PlayerConfiguration { AllowPause = false, ShowResults = false }) { }
            public void AttachTransitionRecorder(List<ObservedAction> actions)
            {
                var property = ActiveRuleset.GetType().GetProperty("KeyBindingInputManager", System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic);
                var inputManager = property?.GetValue(ActiveRuleset) as ManiaInputManager;
                if (inputManager == null) throw new InvalidOperationException("No active mania input manager");
                var handler = inputManager.GetType().GetProperty("ReplayInputHandler")?.GetValue(inputManager);
                if (handler == null) throw new InvalidOperationException("No replay handler");
                inputManager.KeyBindingContainer.Add(new Recorder(actions, () =>
                {
                    var frame = handler.GetType().GetProperty("CurrentFrame")?.GetValue(handler) as ReplayFrame;
                    if (frame == null) throw new InvalidOperationException("No replay frame");
                    return (long)Math.Round(frame.Time * 1000);
                }));
            }
        }

        private sealed class Recorder : osu.Framework.Graphics.Containers.CompositeDrawable, osu.Framework.Input.Bindings.IKeyBindingHandler<ManiaAction>
        {
            private readonly List<ObservedAction> actions;
            private readonly Func<long> time;
            public Recorder(List<ObservedAction> actions, Func<long> time) { this.actions = actions; this.time = time; }
            public bool OnPressed(osu.Framework.Input.Events.KeyBindingPressEvent<ManiaAction> e) { record(e.Action, "down"); return false; }
            public void OnReleased(osu.Framework.Input.Events.KeyBindingReleaseEvent<ManiaAction> e) => record(e.Action, "up");
            private void record(ManiaAction action, string kind)
            {
                int lane = (int)action;
                if (lane >= 0 && lane < 4) actions.Add(new ObservedAction { TimeUs = time(), Lane = lane, Kind = kind, Sequence = actions.Count });
            }
        }
    }
}




