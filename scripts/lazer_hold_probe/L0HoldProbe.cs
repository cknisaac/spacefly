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
    public class L0HoldProbe : RateAdjustedBeatmapTestScene
    {
        protected override Ruleset CreateRuleset() => new ManiaRuleset();

        private sealed record Case(string Id, (double time, bool down)[] Actions);

        [Test]
        public void RunLongNoteScenariosThroughReplayPlayer()
        {
            string output = Environment.GetEnvironmentVariable("LAZER_HOLD_OUTPUT");
            var cases = new[]
            {
                new Case("correct", new[] { (1500.0, true), (4000.0, false) }),
                new Case("no_input", Array.Empty<(double, bool)>()),
                new Case("early_break_repress", new[] { (1500.0, true), (1510.0, false),
                                                         (2500.0, true), (4000.0, false) }),
                new Case("early_break", new[] { (1500.0, true), (1510.0, false) }),
                new Case("late_release", new[] { (1500.0, true), (5250.0, false) }),
                new Case("head_miss_tail_meh", new[] { (4000.0, true), (4010.0, false) }),
            };

            foreach (var item in cases)
            {
                var beatmap = new ManiaBeatmap(new StageDefinition(4))
                {
                    HitObjects = new List<ManiaHitObject>
                    {
                        new HoldNote { StartTime = 1500, Duration = 2500, Column = 0 }
                    },
                    BeatmapInfo =
                    {
                        Ruleset = new ManiaRuleset().RulesetInfo,
                        Difficulty = new BeatmapDifficulty { OverallDifficulty = 8 }
                    }
                };
                beatmap.ControlPointInfo.Add(0, new EffectControlPoint { ScrollSpeed = 0.1f });
                var frames = item.Actions.Select(a => (ReplayFrame)new ManiaReplayFrame(
                    a.time, a.down ? new[] { ManiaAction.Key1 } : Array.Empty<ManiaAction>())).ToList();
                if (frames.Count == 0)
                    frames.Add(new ManiaReplayFrame(250));
                var results = new List<object>();
                ScoreAccessibleReplayPlayer player = null;

                AddStep($"load {item.Id}", () =>
                {
                    Beatmap.Value = CreateWorkingBeatmap(beatmap);
                    player = new ScoreAccessibleReplayPlayer(
                        new Score { Replay = new Replay { Frames = frames } });
                    player.OnLoadComplete += _ =>
                    {
                        player.ScoreProcessor.NewJudgement += result =>
                        {
                            string component = result.HitObject switch
                            {
                                HeadNote => "head",
                                TailNote => "tail",
                                HoldNoteBody => "body",
                                HoldNote => "parent",
                                _ => "unknown"
                            };
                            var processor = player.ScoreProcessor;
                            results.Add(new
                            {
                                component,
                                result = result.Type.ToString().ToUpperInvariant(),
                                combo_after = result.ComboAfterJudgement,
                                accuracy = processor.Accuracy.Value,
                                score = processor.TotalScore.Value,
                                observed_time_us = (long)Math.Round(result.TimeAbsolute * 1000)
                            });
                        };
                    };
                    LoadScreen(player);
                });
                AddUntilStep($"{item.Id}: beatmap starts", () => Beatmap.Value.Track.CurrentTime == 0);
                AddUntilStep($"{item.Id}: player active", () => player.IsCurrentScreen());
                AddUntilStep($"{item.Id}: replay complete", () => player.ScoreProcessor.HasCompleted.Value);
                AddStep($"capture {item.Id}", () => File.AppendAllText(output,
                    JsonSerializer.Serialize(new
                    {
                        id = item.Id,
                        results,
                        score = player.ScoreProcessor.TotalScore.Value,
                        accuracy = player.ScoreProcessor.Accuracy.Value,
                        combo = player.ScoreProcessor.Combo.Value,
                    }) + Environment.NewLine));
            }
        }

        private sealed class ScoreAccessibleReplayPlayer : ReplayPlayer
        {
            public new ScoreProcessor ScoreProcessor => base.ScoreProcessor;
            protected override bool PauseOnFocusLost => false;

            public ScoreAccessibleReplayPlayer(Score score)
                : base(score, new PlayerConfiguration { AllowPause = false, ShowResults = false })
            {
            }
        }
    }
}
