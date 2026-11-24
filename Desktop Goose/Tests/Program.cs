using DesktopGoose.Core;

var tests = new (string Name, Action Run)[]
{
    ("Exact rarity boundaries", Boundaries),
    ("Rarity statistical distribution", Distribution),
    ("Geometric waiting times and local 04:00", Waiting),
    ("Cross-day production, rollback and restart", Lay),
    ("Cross-generation production limit", SameDay),
    ("Failed offline settlement rolls back the full interval", InterruptedProduction),
    ("Incubating, paused and ready recovery", Incubate),
    ("Locked rarity, choose, naming and idempotent release", RecoverHatch),
    ("Permanent diamond nest with release only", Diamond),
    ("Seven validated backups and restore", Backup),
    ("Daily visit decision and start idempotency", Visit)
};

int failed = 0;
foreach (var test in tests)
{
    try { test.Run(); Console.WriteLine($"PASS {test.Name}"); }
    catch (Exception e) { failed++; Console.Error.WriteLine($"FAIL {test.Name}: {e}"); }
}
Console.WriteLine($"{tests.Length - failed}/{tests.Length} passed");
return failed == 0 ? 0 : 1;

static void Equal<T>(T expected, T actual)
{
    if (!EqualityComparer<T>.Default.Equals(expected, actual))
        throw new InvalidOperationException($"Expected {expected}, got {actual}");
}

static void Boundaries()
{
    Check(EggKind.Ordinary, [85000, 10000, 4500, 480, 18, 2]);
    Check(EggKind.Metallic, [85000L * 969, 10000L * 969, 4500L * 969, 480L * 969, 2999400, 99980]);
    Check(EggKind.Diamond, [0, 0, 360, 35, 4, 1]);

    static void Check(EggKind kind, long[] weights)
    {
        var r = new Fixed();
        long start = 0;
        for (int i = 0; i < weights.Length; i++)
        {
            if (weights[i] == 0) continue;
            foreach (long boundary in new[] { start, start + weights[i] - 1 })
            {
                r.Roll = boundary;
                Equal((Rarity)i, RarityEngine.Draw(kind, r));
                Equal(weights.Sum(), r.LastLimit);
            }
            start += weights[i];
        }
    }
}

static void Distribution()
{
    Check(EggKind.Ordinary, [.85, .10, .045, .0048, .00018, .00002]);
    Check(EggKind.Metallic, [.85 / .9998 * .969, .10 / .9998 * .969, .045 / .9998 * .969, .0048 / .9998 * .969, .03, .001]);
    Check(EggKind.Diamond, [0, 0, .90, .0875, .01, .0025]);

    static void Check(EggKind kind, double[] probabilities)
    {
        const int count = 500000;
        var r = new Seeded(670319);
        var results = new int[6];
        for (int i = 0; i < count; i++)
            results[(int)RarityEngine.Draw(kind, r)]++;
        for (int i = 0; i < results.Length; i++)
        {
            double expected = probabilities[i] * count;
            double tolerance = 6 * Math.Sqrt(expected * (1 - probabilities[i]));
            if (Math.Abs(results[i] - expected) > tolerance)
                throw new InvalidOperationException($"{kind}: tier {i}, drew {results[i]}, expected {expected}");
        }
    }
}

static void Waiting()
{
    Equal(1L, Production.WaitSeconds(new Fixed()));
    Equal(59888L, Production.WaitSeconds(new Fixed { Probability = .5 }));
    var eastern = TimeZoneInfo.FindSystemTimeZoneById("Eastern Standard Time");
    Equal(23 * 3600L, Production.Boundary(new(2026, 3, 8), eastern) - Production.Boundary(new(2026, 3, 7), eastern));
    Equal(25 * 3600L, Production.Boundary(new(2026, 11, 1), eastern) - Production.Boundary(new(2026, 10, 31), eastern));
    var edge = Production.Boundary(new(2026, 3, 8), eastern);
    Equal(new DateOnly(2026, 3, 7), Production.Day(edge - 1, eastern));
    Equal(new DateOnly(2026, 3, 8), Production.Day(edge, eastern));
}

static void Lay()
{
    using var f = new Fixture();
    long start = f.Time.Now.ToUnixTimeSeconds();
    f.Time.Now = f.Time.Now.AddSeconds(1);
    Equal(1, f.Store.SettleProduction());
    f.Time.Now = f.Time.Now.AddDays(12);
    Equal(4, f.Store.SettleProduction());
    Equal(5, f.Store.Eggs().Select(e => e.Day).Distinct().Count());
    Equal(start + 1, f.Store.Eggs().Last().Laid);
    f.Reopen();
    Equal(0, f.Store.SettleProduction());
    f.Time.Now = f.Time.Now.AddDays(-10);
    Equal(0, f.Store.SettleProduction());
    f.Time.Zone = TimeZoneInfo.FindSystemTimeZoneById("China Standard Time");
    f.Time.Now = f.Time.Now.AddDays(25);
    Equal(0, f.Store.SettleProduction());
}

static void InterruptedProduction()
{
    using var f = new Fixture(5);
    f.Time.Now = f.Time.Now.AddDays(3);
    f.Random.FailAfter = 1;
    bool interrupted = false;
    try { f.Store.SettleProduction(); }
    catch (IOException) { interrupted = true; }
    Equal(true, interrupted);
    f.Reopen();
    Equal(0, f.Store.Eggs().Count);
    f.Random.FailAfter = null;
    Equal(4, f.Store.SettleProduction());
    f.Reopen();
    Equal(0, f.Store.SettleProduction());
}

static void SameDay()
{
    using var f = new Fixture(5);
    var egg = f.Ready();
    f.Store.Crack(egg.Id);
    f.Store.FinishCrack(egg.Id);
    f.Store.Choose(egg.Id, f.Store.Choice(egg.Id).Offspring);
    f.Store.NameChild(egg.Id, "新鹅", null);
    f.Store.Release(egg.Id);
    f.Time.Now = f.Time.Now.AddSeconds(10);
    Equal(0, f.Store.SettleProduction());
    f.Time.Now = f.Time.Now.AddDays(1);
    Equal(1, f.Store.SettleProduction());
    Equal(f.Store.Resident!.Id, f.Store.Eggs()[0].Parent);
}

static void Incubate()
{
    using var f = new Fixture();
    f.Time.Now = f.Time.Now.AddDays(1);
    Equal(2, f.Store.SettleProduction());
    long egg = f.Store.Eggs()[0].Id;
    Equal(true, f.Store.Start(egg, .26, .33));
    Equal(false, f.Store.Start(f.Store.Eggs()[1].Id, .75, .8));
    f.Store.Count(egg, 2900);
    f.Reopen();
    Equal(HatchStage.INCUBATING, f.Store.ActiveEgg!.Stage);
    f.Store.Pause(egg);
    f.Store.MoveNest(egg, .45, .42);
    f.Reopen();
    f.Store.Count(egg, 30);
    Equal(2900, f.Store.ActiveEgg!.Progress);
    Equal(.45, f.Store.ActiveEgg!.NestX);
    Equal(HatchStage.PAUSED, f.Store.ActiveEgg!.Stage);
    f.Store.Resume(egg);
    f.Store.Count(egg, 8000);
    f.Reopen();
    Equal(HatchStage.READY, f.Store.ActiveEgg!.Stage);
    Equal(5000, f.Store.ActiveEgg!.Progress);
    Equal(null, f.Store.ActiveEgg!.Offspring);
}

static void RecoverHatch()
{
    using var f = new Fixture();
    var egg = f.Ready();
    var parent = f.Store.Resident!;
    f.Store.UnlockAbility(parent.Id);
    var ability = f.Store.Abilities(parent.Id).Single();
    var original = f.Store.Crack(egg.Id)!;
    f.Reopen();
    Equal(HatchStage.READY, f.Store.ActiveEgg!.Stage);
    f.Random.Roll = 99999;
    Equal(original, f.Store.Crack(egg.Id));
    f.Store.FinishCrack(egg.Id);
    f.Reopen();
    Equal(HatchStage.CHOOSE, f.Store.ActiveEgg!.Stage);
    f.Store.Choose(egg.Id, original.Id);
    f.Reopen();
    Equal(HatchStage.NAME_NEW, f.Store.ActiveEgg!.Stage);
    Equal(original.Id, f.Store.Choice(egg.Id).Keep);
    f.Store.NameChild(egg.Id, "小金", ability);
    f.Reopen();
    Equal(HatchStage.RELEASE, f.Store.ActiveEgg!.Stage);
    f.Store.Release(egg.Id);
    f.Store.Release(egg.Id);
    f.Reopen();
    Equal(original.Id, f.Store.Resident!.Id);
    Equal(ability, f.Store.Abilities(original.Id).Single());
    Equal("released", f.Store.FindGoose(parent.Id)!.Status);
    Equal(HatchStage.COMPLETED, f.Store.Eggs().Single().Stage);
    Equal(2, f.Store.Family().Count);
}

static void Diamond()
{
    using var f = new Fixture();
    var egg = f.Ready();
    f.Random.Roll = 99999;
    var child = f.Store.Crack(egg.Id)!;
    Equal(Rarity.Legendary, child.Look.Rarity);
    Equal(EggKind.Diamond, child.Look.EggKind);
    f.Store.FinishCrack(egg.Id);
    f.Store.Choose(egg.Id, f.Store.Resident!.Id);
    f.Store.NameChild(egg.Id, "钻石", null);
    Equal(false, f.Store.DiamondUnlocked);
    f.Reopen();
    f.Store.Release(egg.Id);
    f.Store.Release(egg.Id);
    f.Reopen();
    Equal(true, f.Store.DiamondUnlocked);
}

static void Backup()
{
    using var f = new Fixture();
    for (int i = 0; i < 9; i++)
    {
        f.Time.Now = f.Time.Now.AddMinutes(1);
        f.Store.Backup();
    }
    Equal(7, f.Store.Backups().Count);
    var source = f.Store.Backups()[1];
    f.Store.Rename("新名字");
    f.Store.Restore(source);
    Equal("测试鹅", f.Store.Resident!.Name);
    Equal(7, f.Store.Backups().Count);
}

static void Visit()
{
    using var f = new Fixture();
    Equal(null, f.Store.PlanVisit(new Settings()));
    var egg = f.Ready();
    var child = f.Store.Crack(egg.Id)!;
    f.Store.FinishCrack(egg.Id);
    f.Store.Choose(egg.Id, f.Store.Resident!.Id);
    f.Store.NameChild(egg.Id, "访客", null);
    f.Store.Release(egg.Id);
    var visit = f.Store.PlanVisit(new Settings())!;
    Equal(child.Id, visit.Guest);
    Equal(visit, f.Store.PlanVisit(new Settings()));
    Equal(true, f.Store.BeginVisit(visit));
    Equal(false, f.Store.BeginVisit(visit));
    Equal(null, f.Store.PlanVisit(new Settings()));
}

sealed class Fixture : IDisposable
{
    private readonly string directory = Path.Combine(Path.GetTempPath(), "DesktopGooseTests", Guid.NewGuid().ToString("N"));
    public TestClock Time { get; } = new();
    public Fixed Random { get; } = new();
    public GameStore Store { get; private set; }
    private string Pathname => Path.Combine(directory, "goose.sqlite");

    public Fixture(int hour = 3)
    {
        Time.Now = Time.Now.AddHours(hour - 3);
        Store = new(Pathname, Time, Random);
        Store.Initialize("测试鹅");
    }

    public Egg Ready()
    {
        Time.Now = Time.Now.AddSeconds(2);
        if (Store.SettleProduction() != 1)
            throw new InvalidOperationException("Fixture egg was not laid.");
        var egg = Store.Eggs().Single();
        Store.Start(egg.Id, 0, 0);
        Store.Count(egg.Id, 5000);
        return egg;
    }

    public void Reopen()
    {
        Store.Dispose();
        Store = new(Pathname, Time, Random);
        Store.Recover();
    }

    public void Dispose()
    {
        Store.Dispose();
        Directory.Delete(directory, true);
    }
}

sealed class TestClock : IClock
{
    public DateTimeOffset Now { get; set; } = new(2026, 11, 24, 3, 59, 57, TimeSpan.Zero);
    public TimeZoneInfo Zone { get; set; } = TimeZoneInfo.Utc;
}

sealed class Fixed : IRandomSource
{
    public long Roll { get; set; }
    public long LastLimit { get; private set; }
    public double Probability { get; init; }
    public int? FailAfter { get; set; }
    public int Next(int max) => 0;
    public long NextInt64(long max) { LastLimit = max; return Roll; }
    public double Unit()
    {
        if (FailAfter == 0)
            throw new IOException("Simulated settlement failure.");
        if (FailAfter is int remaining)
            FailAfter = remaining - 1;
        return Probability;
    }
}

sealed class Seeded(int seed) : IRandomSource
{
    private readonly Random r = new(seed);
    public int Next(int max) => r.Next(max);
    public long NextInt64(long max) => r.NextInt64(max);
    public double Unit() => r.NextDouble();
}
