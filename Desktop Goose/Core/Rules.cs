using System.Globalization;
using System.Text;

namespace DesktopGoose.Core;

public interface IRandomSource
{
    int Next(int max);
    long NextInt64(long max);
    double Unit();
}

public sealed class GameRandom : IRandomSource
{
    public int Next(int max) => Random.Shared.Next(max);
    public long NextInt64(long max) => Random.Shared.NextInt64(max);
    public double Unit() => Random.Shared.NextDouble();
}

public interface IClock
{
    DateTimeOffset Now { get; }
    TimeZoneInfo Zone { get; }
}

public sealed class GameClock : IClock
{
    public DateTimeOffset Now => DateTimeOffset.UtcNow;
    public TimeZoneInfo Zone
    {
        get
        {
            TimeZoneInfo.ClearCachedData();
            return TimeZoneInfo.Local;
        }
    }
}

public enum Rarity { Common, Rare, UncommonPattern, Epic, Special, Legendary }
public enum EggKind { Ordinary, Metallic, Diamond }
public enum Temperament { Lively, Shy, Lazy, Grumpy }
public enum Ability { Spin, Flip, Slide, FancyDance, PlayDead, Backwards }
public enum HatchStage { STORED, INCUBATING, PAUSED, READY, CRACKING, CHOOSE, NAME_NEW, RELEASE, COMPLETED }

public readonly record struct Plumage(Rarity Rarity, int Color, int Accent, int Pattern)
{
    public EggKind EggKind => Rarity switch
    {
        Rarity.Legendary => EggKind.Diamond,
        Rarity.Epic or Rarity.Special => EggKind.Metallic,
        _ => EggKind.Ordinary
    };
}

public static class RarityEngine
{
    private static readonly long[] ordinary = [85000, 10000, 4500, 480, 18, 2];
    private static readonly long[] metallic = [
        85000L * 969, 10000L * 969, 4500L * 969, 480L * 969, 99980L * 30, 99980L
    ];
    private static readonly long[] diamond = [0, 0, 360, 35, 4, 1];

    public static Rarity Draw(EggKind kind, IRandomSource random)
    {
        var weights = kind switch
        {
            EggKind.Ordinary => ordinary,
            EggKind.Metallic => metallic,
            EggKind.Diamond => diamond,
            _ => throw new ArgumentOutOfRangeException(nameof(kind))
        };
        long roll = random.NextInt64(weights.Sum());
        for (var index = 0; index < weights.Length; index++)
        {
            if (roll < weights[index])
                return (Rarity)index;
            roll -= weights[index];
        }
        throw new InvalidOperationException("Random source returned an out-of-range value.");
    }

    public static Plumage Offspring(EggKind kind, IRandomSource random)
    {
        var rarity = Draw(kind, random);
        return rarity switch
        {
            Rarity.Common => new(rarity, random.Next(4), -1, 0),
            Rarity.Rare => new(rarity, 4 + random.Next(4), -1, 0),
            Rarity.UncommonPattern => Striped(random),
            Rarity.Epic => new(rarity, 8 + random.Next(2), -1, 0),
            Rarity.Special => MetallicPattern(random),
            _ => new(rarity, 10, 8, 0)
        };
    }

    private static Plumage Striped(IRandomSource random)
    {
        int color = random.Next(4);
        int accent = random.Next(7);
        return new(Rarity.UncommonPattern, color, accent >= color ? accent + 1 : accent, random.Next(6));
    }

    private static Plumage MetallicPattern(IRandomSource random)
    {
        int color = random.Next(2);
        return new(Rarity.Special, 8 + color, 9 - color, random.Next(12));
    }
}

public static class Production
{
    public const int HatchTarget = 5000;
    public const int LifetimeLimit = 5;
    public static long WaitSeconds(IRandomSource random) =>
        1 + (long)Math.Floor(double.LogP1(-random.Unit()) / double.LogP1(-1d / 86400));

    public static DateOnly Day(long second, TimeZoneInfo zone)
    {
        var local = TimeZoneInfo.ConvertTime(DateTimeOffset.FromUnixTimeSeconds(second), zone);
        var date = DateOnly.FromDateTime(local.DateTime);
        return local.Hour < 4 ? date.AddDays(-1) : date;
    }

    public static string Key(DateOnly date) => date.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);

    public static long Boundary(DateOnly day, TimeZoneInfo zone)
    {
        var local = day.ToDateTime(new TimeOnly(4, 0));
        while (zone.IsInvalidTime(local))
            local = local.AddMinutes(1);
        var offset = zone.IsAmbiguousTime(local) ? zone.GetAmbiguousTimeOffsets(local).Max() : zone.GetUtcOffset(local);
        return new DateTimeOffset(local, offset).ToUnixTimeSeconds();
    }

    public static string Name(string text)
    {
        string name = text.Trim();
        if (name.EnumerateRunes().Count() is < 1 or > 16 || name.Any(char.IsControl))
            throw new ArgumentException("名字需要 1–16 个字符。");
        return name;
    }
}

public sealed record Goose(long Id, string Name, Plumage Look, Temperament Temperament,
    long Born, long? Released, string Status);
public sealed record Egg(long Id, long Parent, EggKind Kind, long Laid, string Day, int Progress,
    HatchStage Stage, long? Offspring, double NestX, double NestY);
public sealed record HatchChoice(long Offspring, long? Keep);
public sealed record Visit(long Guest, long Resident, long Due);
public sealed record RangeBox(double X, double Y, double Width, double Height);
public sealed record Settings
{
    public int Size { get; init; } = 100;
    public int Fps { get; init; } = 30;
    public int Energy { get; init; } = 1;
    public int Volume { get; init; } = 50;
    public int QuietFrom { get; init; } = 22 * 60;
    public int QuietTo { get; init; } = 8 * 60;
    public bool QuietEnabled { get; init; } = true;
    public string Monitor { get; init; } = "";
    public RangeBox? Range { get; init; }
    public bool Visits { get; init; } = true;
    public int VisitChance { get; init; } = 10;
    public int VisitSeconds { get; init; } = 30;
    public bool DiamondNest { get; init; }
    public bool Sparkles { get; init; } = true;
    public bool Footprints { get; init; } = true;
    public bool Hidden { get; init; }
    public bool Paused { get; init; }
    public string MemoDay { get; init; } = "";
    public string[] Memos { get; init; } = [];
}
