#nullable disable
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text.Json;
using NUnit.Framework;
using osu.Framework.Input.Bindings;
using osu.Framework.Input.Events;
using osu.Framework.Graphics;
using osu.Framework.Screens;
using osu.Game.Beatmaps;
using osu.Game.Beatmaps.ControlPoints;
using osu.Game.Replays;
using osu.Game.Rulesets.Judgements;
using osu.Game.Rulesets.Mania;
using osu.Game.Rulesets.Mania.Beatmaps;
using osu.Game.Rulesets.Mania.Objects;
using osu.Game.Rulesets.Mania.Replays;
using osu.Game.Rulesets.Objects;
using osu.Game.Rulesets.Scoring;
using osu.Game.Rulesets.Replays;
using osu.Game.Scoring;
using osu.Game.Screens.Play;
using osu.Game.Tests.Visual;

namespace osu.Game.Rulesets.Mania.Tests
{
    public partial class L0ParityProbe : RateAdjustedBeatmapTestScene
    {
        protected override Ruleset CreateRuleset() => new ManiaRuleset();

        private sealed class ObservedJudgement
        {
            public string NoteId { get; init; }
            public string Result { get; init; }
            public long NoteTimeUs { get; init; }
            public int Lane { get; init; }
            public long OffsetUs { get; init; }
            public long ObservedGameTimeUs { get; init; }
        }

        private sealed class ObservedAction
        {
            public long TimeUs { get; init; }
            public int Lane { get; init; }
            public string Kind { get; init; }
            public int Sequence { get; init; }
        }

        private sealed class ObservedScenario
        {
            public string Id { get; init; }
            public List<ObservedJudgement> Judgements { get; init; }
            public List<ObservedAction> Actions { get; init; }
        }

        private sealed class ExpectedJudgement
        {
            public string NoteId { get; init; }
            public string Result { get; init; }
            public long NoteTimeUs { get; init; }
            public int Lane { get; init; }
            public long? HitErrorUs { get; init; }
            public long LogicalEventTimeUs { get; init; }
        }

        private sealed class ObservedVector
        {
            public string Id { get; init; }
            public string Result { get; init; }
            public long OffsetUs { get; init; }
            public long ObservedGameTimeUs { get; init; }
            public bool JudgedAtPress { get; init; }
        }

        [Test]
        public void RunFrozenScenariosThroughReplayPlayer()
        {
            string corpusPath = Environment.GetEnvironmentVariable("LAZER_PARITY_CORPUS");
            string outputPath = Environment.GetEnvironmentVariable("LAZER_PARITY_OUTPUT");
            using var corpus = JsonDocument.Parse(File.ReadAllText(corpusPath));
            foreach (var scenario in corpus.RootElement.GetProperty("scenarios").EnumerateArray())
            {
                string scenarioId = scenario.GetProperty("id").GetString();
                var noteIds = scenario.GetProperty("notes").EnumerateArray().ToDictionary(
                    row => (row.GetProperty("time_us").GetInt64(), row.GetProperty("lane").GetInt32()),
                    row => row.GetProperty("id").GetString());
                List<ManiaHitObject> notes = scenario.GetProperty("notes").EnumerateArray().Select(row => new Note
                {
                    StartTime = row.GetProperty("time_us").GetInt64() / 1000.0,
                    Column = row.GetProperty("lane").GetInt32(),
                }).Cast<ManiaHitObject>().ToList();

                var frames = new List<ReplayFrame>();
                var held = new HashSet<int>();
                foreach (var action in scenario.GetProperty("actions").EnumerateArray())
                {
                    int lane = action.GetProperty("lane").GetInt32();
                    if (action.GetProperty("kind").GetString() == "down") held.Add(lane);
                    else held.Remove(lane);
                    frames.Add(new ManiaReplayFrame(action.GetProperty("time_us").GetInt64() / 1000.0,
                        held.OrderBy(k => k).Select(actionForLane).ToArray()));
                }

                var observed = new List<ObservedJudgement>();
                var observedActions = new List<ObservedAction>();
                var output = new ObservedScenario { Id = scenarioId, Judgements = observed, Actions = observedActions };
                ScoreAccessibleReplayPlayer player = null;

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

                AddStep($"load {scenarioId}", () =>
                {
                    Beatmap.Value = CreateWorkingBeatmap(beatmap);
                    player = new ScoreAccessibleReplayPlayer(new Score { Replay = new Replay { Frames = frames } });
                    player.OnLoadComplete += _ =>
                    {
                        player.AttachTransitionRecorder(observedActions);
                        player.ScoreProcessor.NewJudgement += result =>
                        {
                            var judgedObject = (ManiaHitObject)result.HitObject;
                            long noteTimeUs = (long)Math.Round(judgedObject.StartTime * 1000);
                            observed.Add(new ObservedJudgement
                            {
                                NoteId = noteIds[(noteTimeUs, judgedObject.Column)],
                                Result = result.Type.ToString().ToUpperInvariant(),
                                NoteTimeUs = noteTimeUs,
                                Lane = judgedObject.Column,
                                OffsetUs = (long)Math.Round(result.TimeOffset * 1000),
                                ObservedGameTimeUs = (long)Math.Round(result.TimeAbsolute * 1000),
                            });
                        };
                    };
                    LoadScreen(player);
                });
                AddUntilStep($"{scenarioId}: beatmap starts", () => Beatmap.Value.Track.CurrentTime == 0);
                AddUntilStep($"{scenarioId}: player active", () => player.IsCurrentScreen());
                AddUntilStep($"{scenarioId}: replay complete", () => player.ScoreProcessor.HasCompleted.Value);

                var expected = scenario.GetProperty("expected_events").EnumerateArray()
                    .Where(e => e.GetProperty("kind").GetString() == "judgement")
                    .Select(e => new ExpectedJudgement
                    {
                        NoteId = e.GetProperty("note_id").GetString(),
                        Result = e.GetProperty("result").GetString(),
                        NoteTimeUs = e.GetProperty("note_time_us").GetInt64(),
                        Lane = e.GetProperty("lane").GetInt32(),
                        HitErrorUs = e.GetProperty("hit_error_us").ValueKind == JsonValueKind.Null
                            ? (long?)null
                            : e.GetProperty("hit_error_us").GetInt64(),
                        LogicalEventTimeUs = e.GetProperty("logical_event_time_us").GetInt64(),
                    })
                    .ToList();
                var expectedIdentityAndOrder = expected.Select(r =>
                    $"{r.NoteId}:{r.Lane}:{r.NoteTimeUs}:{r.Result}").ToArray();
                AddAssert($"{scenarioId}: judged note identity, lane, result, and order",
                    () => observed.Select(r => $"{r.NoteId}:{r.Lane}:{r.NoteTimeUs}:{r.Result}").ToArray(),
                    () => Is.EqualTo(expectedIdentityAndOrder));

                var expectedPressErrors = expected.Where(r => r.HitErrorUs.HasValue)
                    .Select(r => $"{r.NoteId}:{r.HitErrorUs.Value}").ToArray();
                var expectedPressErrorByNote = expected.Where(r => r.HitErrorUs.HasValue)
                    .ToDictionary(r => r.NoteId, r => r.HitErrorUs.Value);
                AddAssert($"{scenarioId}: action-caused judgement offsets",
                    () => observed.Where(r => expectedPressErrorByNote.ContainsKey(r.NoteId))
                        .Select(r => $"{r.NoteId}:{r.OffsetUs}").ToArray(),
                    () => Is.EqualTo(expectedPressErrors));

                var exactEventTimes = expected.Where(r => r.HitErrorUs.HasValue)
                    .Select(r => $"{r.NoteId}:{r.LogicalEventTimeUs}").ToArray();
                AddAssert($"{scenarioId}: action-caused judgement times",
                    () => observed.Where(r => expectedPressErrorByNote.ContainsKey(r.NoteId))
                        .Select(r => $"{r.NoteId}:{r.ObservedGameTimeUs}").ToArray(),
                    () => Is.EqualTo(exactEventTimes));
                AddStep($"capture {scenarioId}", () => File.AppendAllText(outputPath, JsonSerializer.Serialize(output) + Environment.NewLine));
            }
        }

        [Test]
        public void RunTimingBoundariesThroughReplayPlayer()
        {
            string corpusPath = Environment.GetEnvironmentVariable("LAZER_PARITY_CORPUS");
            string outputPath = Environment.GetEnvironmentVariable("LAZER_PARITY_OUTPUT");
            using var corpus = JsonDocument.Parse(File.ReadAllText(corpusPath));
            var vectors = corpus.RootElement.GetProperty("judgement_vectors").EnumerateArray()
                .Select(row => (
                    Id: row.GetProperty("id").GetString(),
                    OffsetUs: row.GetProperty("offset_us").GetInt64(),
                    Expected: row.GetProperty("expected").GetString()))
                .ToList();
            var notes = new List<ManiaHitObject>();
            var frames = new List<ReplayFrame>();
            var pressTimes = new Dictionary<double, long>();

            for (int i = 0; i < vectors.Count; i++)
            {
                double noteTime = 2000 + i * 600;
                long offsetUs = vectors[i].OffsetUs;
                notes.Add(new Note { StartTime = noteTime, Column = 0 });
                double pressTime = noteTime + offsetUs / 1000.0;
                pressTimes[noteTime] = (long)Math.Round(pressTime * 1000);
                frames.Add(new ManiaReplayFrame(pressTime, ManiaAction.Key1));
                frames.Add(new ManiaReplayFrame(pressTime + 0.001));
            }

            var observed = new List<ObservedVector>();
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
            ScoreAccessibleReplayPlayer player = null;

            AddStep("load OD8 timing-boundary beatmap", () =>
            {
                Beatmap.Value = CreateWorkingBeatmap(beatmap);
                player = new ScoreAccessibleReplayPlayer(new Score { Replay = new Replay { Frames = frames } });
                player.OnLoadComplete += _ => player.ScoreProcessor.NewJudgement += result =>
                {
                    var judgedObject = (ManiaHitObject)result.HitObject;
                    long noteTimeUs = (long)Math.Round(judgedObject.StartTime * 1000);
                    long eventTimeUs = (long)Math.Round(result.TimeAbsolute * 1000);
                    var vector = vectors[(int)((judgedObject.StartTime - 2000) / 600)];
                    observed.Add(new ObservedVector
                    {
                        Id = vector.Id,
                        Result = result.Type.ToString().ToUpperInvariant(),
                        OffsetUs = (long)Math.Round(result.TimeOffset * 1000),
                        ObservedGameTimeUs = eventTimeUs,
                        // HitWindows.ResultFor() has a late MISS band beyond the
                        // note's active lifetime. At +127.501 ms and later, the
                        // automatic MISS runs before the replayed press.
                        JudgedAtPress = vector.OffsetUs <= 127500
                                        && eventTimeUs == pressTimes[judgedObject.StartTime],
                    });
                };
                LoadScreen(player);
            });
            AddUntilStep("boundary beatmap starts", () => Beatmap.Value.Track.CurrentTime == 0);
            AddUntilStep("boundary player active", () => player.IsCurrentScreen());
            AddUntilStep("boundary replay complete", () => player.ScoreProcessor.HasCompleted.Value);

            var expectedLabels = vectors.Select(row =>
            {
                string reachableResult = row.OffsetUs > 127500 ? "NO_PRESS_JUDGEMENT" : row.Expected;
                return $"{row.Id}:{reachableResult}";
            }).ToArray();
            AddAssert("24 pinned OD8 boundary press outcomes", () => observed.Select(row =>
            {
                string result = row.JudgedAtPress ? row.Result : "NO_PRESS_JUDGEMENT";
                return $"{row.Id}:{result}";
            }).ToArray(), () => Is.EqualTo(expectedLabels));

            var expectedOffsets = vectors.Where(row => row.Expected != "NO_PRESS_JUDGEMENT" && row.OffsetUs <= 127500)
                .Select(row => $"{row.Id}:{row.OffsetUs}")
                .ToArray();
            AddAssert("pressed judgment offsets preserve every frozen microsecond", () => observed.Where(row => row.JudgedAtPress)
                .Select(row => $"{row.Id}:{row.OffsetUs}").ToArray(), () => Is.EqualTo(expectedOffsets));

            AddStep("capture timing boundary output", () => File.AppendAllText(outputPath,
                JsonSerializer.Serialize(new { Id = "OD8_timing_boundaries", Judgements = observed }) + Environment.NewLine));
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

            public ScoreAccessibleReplayPlayer(Score score)
                : base(score, new PlayerConfiguration { AllowPause = false, ShowResults = false })
            {
            }

            public void AttachTransitionRecorder(List<ObservedAction> actions)
            {
                var property = ActiveRuleset.GetType().GetProperty(
                    "KeyBindingInputManager", BindingFlags.Instance | BindingFlags.NonPublic);
                var inputManager = property?.GetValue(ActiveRuleset) as ManiaInputManager;
                if (inputManager == null)
                    throw new InvalidOperationException("Could not access the active mania input manager.");
                var replayHandler = inputManager.GetType()
                    .GetProperty("ReplayInputHandler", BindingFlags.Instance | BindingFlags.Public)
                    ?.GetValue(inputManager);
                if (replayHandler == null)
                    throw new InvalidOperationException("The active mania input manager has no replay handler.");
                inputManager.KeyBindingContainer.Add(new ReplayActionRecorder(
                    actions, () =>
                    {
                        var frame = replayHandler.GetType()
                            .GetProperty("CurrentFrame", BindingFlags.Instance | BindingFlags.Public)
                            ?.GetValue(replayHandler) as ReplayFrame;
                        if (frame == null)
                            throw new InvalidOperationException("Replay key transition has no current frame.");
                        return (long)Math.Round(frame.Time * 1000);
                    }));
            }
        }

        private sealed class ReplayActionRecorder : Component, IKeyBindingHandler<ManiaAction>
        {
            private readonly List<ObservedAction> actions;
            private readonly Func<long> getTimeUs;

            public ReplayActionRecorder(List<ObservedAction> actions, Func<long> getTimeUs)
            {
                this.actions = actions;
                this.getTimeUs = getTimeUs;
            }

            public bool OnPressed(KeyBindingPressEvent<ManiaAction> e)
            {
                record(e.Action, "down");
                return false;
            }

            public void OnReleased(KeyBindingReleaseEvent<ManiaAction> e) => record(e.Action, "up");

            private void record(ManiaAction action, string kind)
            {
                int lane = (int)action;
                if (lane < 0 || lane > 3)
                    return;
                actions.Add(new ObservedAction
                {
                    TimeUs = getTimeUs(),
                    Lane = lane,
                    Kind = kind,
                    Sequence = actions.Count,
                });
            }
        }
    }
}




