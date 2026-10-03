#nullable disable
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using NUnit.Framework;
using osu.Game.Rulesets.Judgements;
using osu.Game.Rulesets.Mania;
using osu.Game.Rulesets.Mania.Beatmaps;
using osu.Game.Rulesets.Mania.Objects;
using osu.Game.Rulesets.Mania.Scoring;
using osu.Game.Rulesets.Scoring;

namespace osu.Game.Rulesets.Mania.Tests
{
    [TestFixture]
    public class L0ScoreProbe
    {
        private static readonly HitResult[] scoreResults =
        {
            HitResult.Perfect, HitResult.Great, HitResult.Good,
            HitResult.Ok, HitResult.Meh, HitResult.Miss,
        };

        [Test]
        public void GeneratePinnedScoreVectors()
        {
            string outputPath = Environment.GetEnvironmentVariable("LAZER_SCORE_OUTPUT");
            if (string.IsNullOrEmpty(outputPath))
                throw new InvalidOperationException("LAZER_SCORE_OUTPUT is required.");

            var scenarios = new List<object>
            {
                runSingle("one_perfect", HitResult.Perfect),
                runSingle("one_great", HitResult.Great),
                runSingle("one_good", HitResult.Good),
                runSingle("one_ok", HitResult.Ok),
                runSingle("one_meh", HitResult.Meh),
                runSingle("one_miss", HitResult.Miss),
                runSequence("combo_break_and_recovery", new[]
                {
                    HitResult.Perfect, HitResult.Great, HitResult.Miss,
                    HitResult.Meh, HitResult.Perfect,
                }, resetAfter: false),
                runSequence("reset_after_scoring", new[]
                {
                    HitResult.Great, HitResult.Miss,
                }, resetAfter: true),
            };

            var output = new
            {
                schema_version = 1,
                reference = new
                {
                    repository = "https://github.com/ppy/osu",
                    commit = "da27300fcbfa246f87c3ba1a14cbd00b68c7e9a9",
                    release = "2026.1001.0-tachyon",
                    ruleset = "osu!mania",
                    mods = Array.Empty<string>(),
                    scoring_mode = "ScoreV2 default",
                },
                scope = "tap notes only; no mods; score processor driven by pinned HitResult values",
                scenarios,
            };

            Directory.CreateDirectory(Path.GetDirectoryName(outputPath));
            File.WriteAllText(outputPath, JsonSerializer.Serialize(output, new JsonSerializerOptions
            {
                WriteIndented = true,
            }) + Environment.NewLine);
        }

        private static object runSingle(string id, HitResult result)
            => runSequence(id, new[] { result }, resetAfter: false);

        private static object runSequence(string id, HitResult[] results, bool resetAfter)
        {
            var notes = results.Select((_, index) => new Note
            {
                StartTime = 1000 + index * 1000,
                Column = 0,
            }).ToList();
            var beatmap = createBeatmap(notes);
            var processor = new ManiaScoreProcessor();
            processor.ApplyBeatmap(beatmap);

            long previousScore = processor.TotalScore.Value;
            var events = new List<object>();
            for (int i = 0; i < results.Length; i++)
            {
                var note = notes[i];
                var judgement = note.CreateJudgement();
                var result = new JudgementResult(note, judgement) { Type = results[i] };
                processor.ApplyResult(result);

                var statistics = processor.GetScoreProcessorStatistics();
                long totalScore = processor.TotalScore.Value;
                events.Add(new
                {
                    note_index = i,
                    hit_result = results[i].ToString().ToUpperInvariant(),
                    result_max = judgement.MaxResult.ToString().ToUpperInvariant(),
                    base_accuracy_points = processor.GetBaseScoreForResult(results[i]),
                    maximum_accuracy_points = processor.GetBaseScoreForResult(judgement.MaxResult),
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
                    total_score_delta = totalScore - previousScore,
                    maximum_total_score = processor.MaximumTotalScore,
                    maximum_combo = processor.MaximumCombo,
                });
                previousScore = totalScore;
            }

            object reset = null;
            if (resetAfter)
            {
                processor.ApplyBeatmap(beatmap);
                var statistics = processor.GetScoreProcessorStatistics();
                reset = new
                {
                    total_score_without_mods = processor.TotalScoreWithoutMods.Value,
                    total_score = processor.TotalScore.Value,
                    accuracy = processor.Accuracy.Value,
                    minimum_accuracy = processor.MinimumAccuracy.Value,
                    maximum_accuracy = processor.MaximumAccuracy.Value,
                    accuracy_numerator = statistics.BaseScore,
                    accuracy_denominator = statistics.MaximumBaseScore,
                    accuracy_judgement_count = statistics.AccuracyJudgementCount,
                    combo_score_portion = statistics.ComboPortion,
                    combo = processor.Combo.Value,
                    highest_combo = processor.HighestCombo.Value,
                    maximum_total_score = processor.MaximumTotalScore,
                    maximum_combo = processor.MaximumCombo,
                };
            }

            return new
            {
                id,
                note_count = notes.Count,
                maximum_combo_score_portion = calculateMaximumComboPortion(beatmap, notes),
                events,
                reset,
            };
        }

        private static double calculateMaximumComboPortion(ManiaBeatmap beatmap, List<Note> notes)
        {
            var processor = new ManiaScoreProcessor();
            processor.ApplyBeatmap(beatmap);
            foreach (var note in notes)
            {
                processor.ApplyResult(new JudgementResult(note, note.CreateJudgement())
                {
                    Type = HitResult.Perfect,
                });
            }
            return processor.GetScoreProcessorStatistics().ComboPortion;
        }

        private static ManiaBeatmap createBeatmap(List<Note> notes)
            => new ManiaBeatmap(new StageDefinition(4))
            {
                HitObjects = notes.Cast<ManiaHitObject>().ToList(),
                BeatmapInfo =
                {
                    Ruleset = new ManiaRuleset().RulesetInfo,
                    Difficulty = new osu.Game.Beatmaps.BeatmapDifficulty { OverallDifficulty = 8 },
                },
            };
    }
}
