// HitWindows only mentions HitObject in XML documentation. This namespace
// stub keeps its pinned source file buildable without compiling the full game.
namespace osu.Game.Rulesets.Objects;

public sealed class HitObject(string id, double startTime, double endTime)
{
    public string Id { get; } = id;
    public double StartTime { get; } = startTime;
    public double EndTime { get; } = endTime;

    public double GetEndTime() => EndTime;
}
