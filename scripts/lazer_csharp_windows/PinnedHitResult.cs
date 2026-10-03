// Minimal dependency for the pinned HitWindows and ManiaHitWindows source.
// The numeric order of these first seven values matches HitResult.cs at the
// pinned osu!lazer commit; later, unrelated enum values are unused here.
namespace osu.Game.Rulesets.Scoring;

public enum HitResult
{
    None,
    Miss,
    Meh,
    Ok,
    Good,
    Great,
    Perfect,
}
