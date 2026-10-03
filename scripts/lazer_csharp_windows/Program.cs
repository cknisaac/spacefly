using System.Text.Json;
using osu.Game.Rulesets.Mania.Scoring;
using osu.Game.Rulesets.Mania.Objects.Drawables;
using osu.Game.Rulesets.Mania.UI;
using osu.Game.Rulesets.Objects;
using osu.Game.Rulesets.Scoring;
using osu.Game.Rulesets.UI;

const string expectedRelease = "2026.1001.0-tachyon";
const string expectedCommit = "da27300fcbfa246f87c3ba1a14cbd00b68c7e9a9";

if (args.Length != 1)
    throw new ArgumentException("Usage: LazerCSharpWindowsReference <corpus.json>");

using var corpus = JsonDocument.Parse(File.ReadAllText(args[0]));
var root = corpus.RootElement;
var reference = root.GetProperty("reference");

if (reference.GetProperty("release").GetString() != expectedRelease ||
    reference.GetProperty("commit").GetString() != expectedCommit ||
    reference.GetProperty("ruleset").GetString() != "osu!mania" ||
    reference.GetProperty("od").GetInt32() != 8 ||
    reference.GetProperty("mods").GetArrayLength() != 0 ||
    reference.GetProperty("rate").GetDouble() != 1.0)
{
    throw new InvalidOperationException("Corpus metadata differs from the pinned OD8 reference.");
}

var windows = new ManiaHitWindows();
windows.SetDifficulty(8);

var vectorResults = new List<object>();
foreach (var vector in root.GetProperty("judgement_vectors").EnumerateArray())
{
    string id = vector.GetProperty("id").GetString()
                ?? throw new InvalidDataException("Vector id is missing.");
    long offsetUs = vector.GetProperty("offset_us").GetInt64();
    double offsetMs = offsetUs / 1000.0;
    HitResult result = windows.ResultFor(offsetMs);
    vectorResults.Add(new { id, result = result switch
    {
        HitResult.None => "NO_PRESS_JUDGEMENT",
        HitResult.Perfect => "PERFECT",
        HitResult.Great => "GREAT",
        HitResult.Good => "GOOD",
        HitResult.Ok => "OK",
        HitResult.Meh => "MEH",
        HitResult.Miss => "MISS",
        _ => throw new InvalidOperationException($"Unexpected result: {result}")
    }});
}

var sourcePolicyResults = new List<object>();
foreach (var vector in root.GetProperty("source_policy_vectors").EnumerateArray())
{
    var noteRows = vector.GetProperty("notes").EnumerateArray().ToArray();
    var drawables = noteRows
        .Select(row => new DrawableManiaHitObject(new HitObject(
            row.GetProperty("id").GetString()!,
            row.GetProperty("start_time_us").GetDouble(),
            row.GetProperty("end_time_us").GetDouble())))
        .OrderBy(drawable => drawable.HitObject.StartTime)
        .ToArray();
    var oldNote = drawables[0];
    var newNote = drawables[1];
    var policy = new OrderedHitPolicy(new HitObjectContainer(drawables));
    double beforeUs = vector.GetProperty("probe_before_next_start_us").GetDouble();
    double atUs = vector.GetProperty("probe_at_next_start_us").GetDouble();
    HitResult oldBeforeResult = windows.ResultFor(
        (beforeUs - oldNote.HitObject.StartTime) / 1000.0);
    HitResult newAtResult = windows.ResultFor(
        (atUs - newNote.HitObject.StartTime) / 1000.0);

    policy.HandleHit(newNote);
    sourcePolicyResults.Add(new
    {
        id = vector.GetProperty("id").GetString(),
        old_hittable_before = policy.IsHittable(oldNote, beforeUs),
        old_hittable_at = policy.IsHittable(oldNote, atUs),
        new_hittable_at = policy.IsHittable(newNote, atUs),
        old_result_before = oldBeforeResult switch
        {
            HitResult.None => "NO_PRESS_JUDGEMENT",
            HitResult.Perfect => "PERFECT",
            HitResult.Great => "GREAT",
            HitResult.Good => "GOOD",
            HitResult.Ok => "OK",
            HitResult.Meh => "MEH",
            HitResult.Miss => "MISS",
            _ => throw new InvalidOperationException($"Unexpected result: {oldBeforeResult}")
        },
        new_result_at = newAtResult switch
        {
            HitResult.None => "NO_PRESS_JUDGEMENT",
            HitResult.Perfect => "PERFECT",
            HitResult.Great => "GREAT",
            HitResult.Good => "GOOD",
            HitResult.Ok => "OK",
            HitResult.Meh => "MEH",
            HitResult.Miss => "MISS",
            _ => throw new InvalidOperationException($"Unexpected result: {newAtResult}")
        },
        force_missed_ids_after_new_hit = oldNote.Judged
            ? new[] { oldNote.HitObject.Id }
            : Array.Empty<string>()
    });
}

var output = new
{
    scope = "pinned-source-subset",
    schema_version = root.GetProperty("schema_version").GetInt32(),
    reference,
    judgement_vectors = vectorResults,
    source_policy_vectors = sourcePolicyResults
};

Console.WriteLine(JsonSerializer.Serialize(output, new JsonSerializerOptions
{
    WriteIndented = true
}));
