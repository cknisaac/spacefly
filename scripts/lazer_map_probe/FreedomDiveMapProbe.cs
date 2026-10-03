#nullable disable
using System;
using System.IO;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using NUnit.Framework;
using osu.Game.Beatmaps;
using osu.Game.Beatmaps.Formats;
using osu.Game.IO;
using osu.Game.Rulesets.Mania;
using osu.Game.Rulesets.Mania.Objects;
using osu.Game.Rulesets.Mania.Replays;
using osu.Game.Rulesets.Mods;
using osu.Game.Rulesets.Objects;
using osu.Game.Replays;
using osu.Game.Rulesets.Replays;
using osu.Game.Rulesets.Scoring;
using osu.Game.Scoring;
using osu.Game.Screens.Play;
using osu.Game.Tests.Beatmaps;
using osu.Game.Tests.Visual;
using osu.Framework.Screens;

namespace osu.Game.Rulesets.Mania.Tests
{
    [TestFixture]
    public class FreedomDiveMapProbe
    {
        [Test]
        public void DecodeRealFourKeyChart()
        {
            using var file = File.OpenRead(Environment.GetEnvironmentVariable("FREEDOM_OSU_PATH"));
            using var stream = new LineBufferedReader(file);
            var decoder = new LegacyBeatmapDecoder { ApplyOffsets = false };
            var decoded = decoder.Decode(stream);
            var playable = new TestWorkingBeatmap(decoded).GetPlayableBeatmap(
                new ManiaRuleset().RulesetInfo, Array.Empty<Mod>());
            var notes = playable.HitObjects.Select(obj => new
            {
                kind = obj is HoldNote ? "hold" : "tap",
                lane = ((ManiaHitObject)obj).Column,
                start_us = (long)Math.Round(obj.StartTime * 1000),
                end_us = (long)Math.Round(obj.GetEndTime() * 1000)
            }).OrderBy(obj => obj.start_us).ThenBy(obj => obj.lane)
              .ThenBy(obj => obj.end_us).ToArray();
            File.WriteAllText(Environment.GetEnvironmentVariable("FREEDOM_LAZER_OUTPUT"),
                JsonSerializer.Serialize(new { notes, od = decoded.Difficulty.OverallDifficulty }));
        }
    }

    public class FreedomDiveReplayProbe : ScreenTestScene
    {
        protected override osu.Game.Rulesets.Ruleset CreateRuleset() => new ManiaRuleset();

        [Test]
        public void ReplayEveryObjectInRealFourKeyChart()
        {
            using var file = File.OpenRead(Environment.GetEnvironmentVariable("FREEDOM_OSU_PATH"));
            using var stream = new LineBufferedReader(file);
            var decoded = new LegacyBeatmapDecoder { ApplyOffsets = false }.Decode(stream);
            var playable = new TestWorkingBeatmap(decoded).GetPlayableBeatmap(
                new ManiaRuleset().RulesetInfo, Array.Empty<Mod>());
            var transitions = playable.HitObjects.SelectMany(obj => new[]
            {
                (time: obj.StartTime, lane: ((ManiaHitObject)obj).Column, down: true),
                (time: obj is HoldNote ? obj.GetEndTime() : obj.StartTime + 1,
                 lane: ((ManiaHitObject)obj).Column, down: false)
            }).OrderBy(t => t.time).ThenBy(t => t.down ? 1 : 0).ToArray();
            var held = new bool[4];
            var frames = new List<ReplayFrame>();
            foreach (var group in transitions.GroupBy(t => t.time))
            {
                foreach (var transition in group)
                    held[transition.lane] = transition.down;
                frames.Add(new ManiaReplayFrame(group.Key,
                    Enumerable.Range(0, 4).Where(lane => held[lane])
                              .Select(lane => (ManiaAction)lane).ToArray()));
            }
            var counts = new Dictionary<string, int>();
            ScoreAccessibleReplayPlayer player = null;
            AddStep("load Freedom Dive", () =>
            {
                Beatmap.Value = CreateWorkingBeatmap(playable);
                player = new ScoreAccessibleReplayPlayer(
                    new Score { Replay = new Replay { Frames = frames } });
                player.OnLoadComplete += _ =>
                    player.ScoreProcessor.NewJudgement += result =>
                    {
                        string key = result.Type.ToString().ToUpperInvariant();
                        counts[key] = counts.GetValueOrDefault(key) + 1;
                    };
                LoadScreen(player);
            });
            AddUntilStep("player active", () => player.IsCurrentScreen());
            AddStep("accelerate virtual track", () => Beatmap.Value.Track.Tempo.Value = 20);
            AddUntilStep("full replay complete", () => player.ScoreProcessor.HasCompleted.Value);
            AddStep("capture final", () => File.WriteAllText(
                Environment.GetEnvironmentVariable("FREEDOM_LAZER_REPLAY_OUTPUT"),
                JsonSerializer.Serialize(new
                {
                    score = player.ScoreProcessor.TotalScore.Value,
                    accuracy = player.ScoreProcessor.Accuracy.Value,
                    combo = player.ScoreProcessor.Combo.Value,
                    counts,
                    tempo = Beatmap.Value.Track.AggregateTempo.Value
                })));
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
