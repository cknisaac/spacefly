#nullable disable
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text.Json;
using NUnit.Framework;
using osu.Framework.Graphics;
using osu.Framework.Input.Bindings;
using osu.Framework.Input.Events;
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
using osu.Game.Rulesets.Replays;
using osu.Game.Rulesets.Scoring;
using osu.Game.Scoring;
using osu.Game.Screens.Play;
using osu.Game.Tests.Visual;

namespace osu.Game.Rulesets.Mania.Tests
{
    public class L0FourKScoreProbe : RateAdjustedBeatmapTestScene
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
            public object Score { get; init; }
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

        [Test]
        public void RunFourKScoreScenariosThroughReplayPlayer()
        {
            string corpusPath = Environment.GetEnvironmentVariable("LAZER_4K_SCORE_CORPUS");
            string outputPath = Environment.GetEnvironmentVariable("LAZER_4K_SCORE_OUTPUT");
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
                    frames.Add(new ManiaReplayFrame(
                        action.GetProperty("time_us").GetInt64() / 1000.0,
                        held.OrderBy(k => k).Select(actionForLane).ToArray()));
                }

                var observedJudgements = new List<ObservedJudgement>();
                var observedActions = new List<ObservedAction>();
                var output = new ObservedScenario
                {
                    Id = scenarioId,
                    Judgements = observedJudgements,
                    Actions = observedActions,
                };
                ScoreAccessibleReplayPlayer player = null;
                long previousTotalScore = 0;

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
                    player = new ScoreAccessibleReplayPlayer(
                        new Score { Replay = new Replay { Frames = frames } });
                    player.OnLoadComplete += _ =>
                    {
                        player.AttachTransitionRecorder(observedActions);
                        player.ScoreProcessor.NewJudgement += result =>
                        {
                            var judgedObject = (ManiaHitObject)result.HitObject;
                            long noteTimeUs = (long)Math.Round(judgedObject.StartTime * 1000);
                            var processor = player.ScoreProcessor;
                            var statistics = processor.GetScoreProcessorStatistics();
                            long totalScore = processor.TotalScore.Value;
                            observedJudgements.Add(new ObservedJudgement
                            {
                                NoteId = noteIds[(noteTimeUs, judgedObject.Column)],
                                Result = result.Type.ToString().ToUpperInvariant(),
                                NoteTimeUs = noteTimeUs,
                                Lane = judgedObject.Column,
                                OffsetUs = (long)Math.Round(result.TimeOffset * 1000),
                                ObservedGameTimeUs = (long)Math.Round(result.TimeAbsolute * 1000),
                                Score = new
                                {
                                    base_accuracy_points = processor.GetBaseScoreForResult(result.Type),
                                    maximum_accuracy_points = processor.GetBaseScoreForResult(result.Judgement.MaxResult),
                                    combo_before = result.ComboAtJudgement,
                                    combo_after = result.ComboAfterJudgement,
                                    highest_combo_after = result.HighestComboAfterJudgement,
                                    accuracy_numerator = statistics.BaseScore,
                                    accuracy_denominator = statistics.MaximumBaseScore,
                                    accuracy_judgement_count = statistics.AccuracyJudgementCount,
                                    accuracy = processor.Accuracy.Value,
                                    minimum_accuracy = processor.MinimumAccuracy.Value,
                                    maximum_accuracy = processor.MaximumAccuracy.Value,
                                    combo_score_portion = statistics.ComboPortion,
                                    total_score_without_mods = processor.TotalScoreWithoutMods.Value,
                                    total_score = totalScore,
                                    total_score_delta = totalScore - previousTotalScore,
                                    maximum_total_score = processor.MaximumTotalScore,
                                    maximum_combo = processor.MaximumCombo,
                                },
                            });
                            previousTotalScore = totalScore;
                        };
                    };
                    LoadScreen(player);
                });
                AddUntilStep($"{scenarioId}: beatmap starts", () => Beatmap.Value.Track.CurrentTime == 0);
                AddUntilStep($"{scenarioId}: player active", () => player.IsCurrentScreen());
                AddUntilStep($"{scenarioId}: replay complete", () => player.ScoreProcessor.HasCompleted.Value);
                AddStep($"capture {scenarioId}", () => File.AppendAllText(
                    outputPath, JsonSerializer.Serialize(output) + Environment.NewLine));
            }
        }

        [Test]
        public void RunHeadlessFourKEpisodesThroughReplayPlayer()
        {
            string episodesPath = Environment.GetEnvironmentVariable("LAZER_4K_ADAPTER_EPISODES");
            string outputPath = Environment.GetEnvironmentVariable("LAZER_4K_ADAPTER_OUTPUT");
            using var episodesDocument = JsonDocument.Parse(File.ReadAllText(episodesPath));

            foreach (var episodeRow in episodesDocument.RootElement.GetProperty("episodes").EnumerateArray())
            {
                string episodeId = episodeRow.GetProperty("id").GetString();
                var episode = episodeRow.GetProperty("episode");
                var noteIds = episode.GetProperty("beatmap_notes").EnumerateArray().ToDictionary(
                    row => (row.GetProperty("time_us").GetInt64(), row.GetProperty("lane").GetInt32()),
                    row => row.GetProperty("id").GetString());
                List<ManiaHitObject> notes = episode.GetProperty("beatmap_notes").EnumerateArray()
                    .Select(row => new Note
                    {
                        StartTime = row.GetProperty("time_us").GetInt64() / 1000.0,
                        Column = row.GetProperty("lane").GetInt32(),
                    }).Cast<ManiaHitObject>().ToList();

                var frames = new List<ReplayFrame>();
                var held = new HashSet<int>();
                foreach (var action in episode.GetProperty("game_actions").EnumerateArray())
                {
                    int lane = action.GetProperty("lane").GetInt32();
                    if (action.GetProperty("kind").GetString() == "down") held.Add(lane);
                    else held.Remove(lane);
                    frames.Add(new ManiaReplayFrame(
                        action.GetProperty("time_us").GetInt64() / 1000.0,
                        held.OrderBy(k => k).Select(actionForLane).ToArray()));
                }

                var observedJudgements = new List<ObservedJudgement>();
                var observedActions = new List<ObservedAction>();
                var output = new ObservedScenario
                {
                    Id = episodeId,
                    Judgements = observedJudgements,
                    Actions = observedActions,
                };
                ScoreAccessibleReplayPlayer player = null;
                long previousTotalScore = 0;

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

                AddStep($"load headless episode {episodeId}", () =>
                {
                    Beatmap.Value = CreateWorkingBeatmap(beatmap);
                    player = new ScoreAccessibleReplayPlayer(
                        new Score { Replay = new Replay { Frames = frames } });
                    player.OnLoadComplete += _ =>
                    {
                        player.AttachTransitionRecorder(observedActions);
                        player.ScoreProcessor.NewJudgement += result =>
                        {
                            var judgedObject = (ManiaHitObject)result.HitObject;
                            long noteTimeUs = (long)Math.Round(judgedObject.StartTime * 1000);
                            var processor = player.ScoreProcessor;
                            var statistics = processor.GetScoreProcessorStatistics();
                            long totalScore = processor.TotalScore.Value;
                            observedJudgements.Add(new ObservedJudgement
                            {
                                NoteId = noteIds[(noteTimeUs, judgedObject.Column)],
                                Result = result.Type.ToString().ToUpperInvariant(),
                                NoteTimeUs = noteTimeUs,
                                Lane = judgedObject.Column,
                                OffsetUs = (long)Math.Round(result.TimeOffset * 1000),
                                ObservedGameTimeUs = (long)Math.Round(result.TimeAbsolute * 1000),
                                Score = new
                                {
                                    base_accuracy_points = processor.GetBaseScoreForResult(result.Type),
                                    maximum_accuracy_points = processor.GetBaseScoreForResult(result.Judgement.MaxResult),
                                    combo_before = result.ComboAtJudgement,
                                    combo_after = result.ComboAfterJudgement,
                                    highest_combo_after = result.HighestComboAfterJudgement,
                                    accuracy_numerator = statistics.BaseScore,
                                    accuracy_denominator = statistics.MaximumBaseScore,
                                    accuracy_judgement_count = statistics.AccuracyJudgementCount,
                                    accuracy = processor.Accuracy.Value,
                                    minimum_accuracy = processor.MinimumAccuracy.Value,
                                    maximum_accuracy = processor.MaximumAccuracy.Value,
                                    combo_score_portion = statistics.ComboPortion,
                                    total_score_without_mods = processor.TotalScoreWithoutMods.Value,
                                    total_score = totalScore,
                                    total_score_delta = totalScore - previousTotalScore,
                                    maximum_total_score = processor.MaximumTotalScore,
                                    maximum_combo = processor.MaximumCombo,
                                },
                            });
                            previousTotalScore = totalScore;
                        };
                    };
                    LoadScreen(player);
                });
                AddUntilStep($"{episodeId}: beatmap starts", () => Beatmap.Value.Track.CurrentTime == 0);
                AddUntilStep($"{episodeId}: player active", () => player.IsCurrentScreen());
                AddUntilStep($"{episodeId}: replay complete", () => player.ScoreProcessor.HasCompleted.Value);
                AddStep($"capture headless episode {episodeId}", () => File.AppendAllText(
                    outputPath, JsonSerializer.Serialize(output) + Environment.NewLine));
            }
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
