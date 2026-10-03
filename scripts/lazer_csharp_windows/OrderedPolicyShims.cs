using osu.Game.Rulesets.Objects;
using osu.Game.Rulesets.Objects.Drawables;

namespace osu.Framework.Extensions.IEnumerableExtensions
{
    public static class OrderedSequenceExtensions
    {
        public static T? GetNext<T>(this IEnumerable<T> source, T current)
            where T : class
        {
            bool found = false;
            foreach (T item in source)
            {
                if (found)
                    return item;
                if (ReferenceEquals(item, current))
                    found = true;
            }
            return null;
        }
    }
}

namespace osu.Game.Rulesets.Objects.Drawables
{
    public class DrawableHitObject(HitObject hitObject)
    {
        public HitObject HitObject { get; } = hitObject;
        public bool Judged { get; set; }
        public IReadOnlyList<DrawableHitObject> NestedHitObjects { get; init; } = [];
    }
}

namespace osu.Game.Rulesets.Mania.Objects.Drawables
{
    public class DrawableManiaHitObject(HitObject hitObject) : DrawableHitObject(hitObject)
    {
        public void MissForcefully() => Judged = true;
    }
}

namespace osu.Game.Rulesets.UI
{
    public sealed class HitObjectContainer(IEnumerable<DrawableHitObject> aliveObjects)
    {
        public IEnumerable<DrawableHitObject> AliveObjects { get; } = aliveObjects;
    }
}
