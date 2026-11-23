using DesktopCleaner;

var tests = new (string Name, Action Run)[]
{
    ("read coordinates and snapshot round-trip", () => WithDesktop((store, desktop, manager) =>
    {
        Equal(3, manager.Inspect().Count);
        var snapshot = store.Save(desktop.Read());
        Equal(new Pixel(110, 10), store.Load().Icons[1].Position);
        Equal("同名", snapshot.Icons[0].Name);
        Equal(1, snapshot.Version);
        Equal(144u, snapshot.Frame.Screens.Single().DpiY);
        var original = store.Load();
        Throws<IOException>(() => store.Save(desktop.Read()));
        Equal(original.SavedAt, store.Load().SavedAt);
    })),
    ("checksum tampering blocks all Shell writes", () => WithDesktop((store, desktop, manager) =>
    {
        manager.Arrange(Home, first: true);
        var path = Directory.EnumerateFiles(Root, "original-layout.json").Single();
        File.WriteAllText(path, File.ReadAllText(path).Replace("\"Width\":1200", "\"Width\":1201"));
        int writes = desktop.Writes;
        Throws<InvalidDataException>(() => manager.Restore());
        Equal(writes, desktop.Writes);
        True(store.Pending);
    })),
    ("snapshot directory write failure blocks all Shell writes", () => WithDesktop((store, desktop, _) =>
    {
        string path = Path.Combine(Root, "blocked");
        File.WriteAllText(path, "file");
        var manager = new DesktopIconManager(new SnapshotStore(Path.Combine(path, "folder")), () => desktop);
        Throws<IOException>(() => manager.Arrange(Home, first: true));
        Equal(0, desktop.Writes);
    })),
    ("new window target and ten drag cycles preserve backup", () => WithDesktop((store, desktop, manager) =>
    {
        var originals = desktop.Read().Icons;
        var movement = new WindowMovement();
        Equal(3, manager.Arrange(Home, first: true));
        var savedAt = store.Load().SavedAt;
        var current = Home;
        for (int index = 0; index < 10; index++)
        {
            var target = new PixelRect(405 + index * 36, 205 + index * 9, 815 + index * 36, 515 + index * 9);
            movement.Begin(current);
            var positions = desktop.Read().Icons;
            int writes = desktop.Writes;
            True(!movement.CanApply(minimized: false, busy: false));
            True(positions.SequenceEqual(desktop.Read().Icons));
            Equal(writes, desktop.Writes);
            True(movement.End(target).HasFlag(WindowChange.Position));
            True(movement.CanApply(minimized: false, busy: false));
            Equal(3, manager.Arrange(target, first: false));
            True(desktop.ReadIconBounds(3).All(target.Contains));
            Equal(savedAt, store.Load().SavedAt);
            current = target;
        }
        Equal(new RestoreResult(3, 0, 0), manager.Restore());
        True(desktop.Read().Icons.ToHashSet().SetEquals(originals));
        True(!store.Pending);
    })),
    ("same-position drag and duplicate target perform no writes", () => WithDesktop((_, desktop, manager) =>
    {
        var movement = new WindowMovement();
        movement.Begin(Home);
        Equal(WindowChange.None, movement.End(Home));
        movement.Begin(Home);
        Equal(WindowChange.Size, movement.End(Home with { Bottom = Home.Bottom + 40 }));
        True(!movement.CanApply(minimized: true, busy: false));
        True(!movement.CanApply(minimized: false, busy: true));
        manager.Arrange(Home, first: true);
        int writes = desktop.Writes;
        Equal(-1, manager.Arrange(Home, first: false));
        Equal(writes, desktop.Writes);
    })),
    ("empty desktop does not create a snapshot", () => WithDesktop((store, desktop, manager) =>
    {
        desktop.Icons.Clear();
        Equal(0, manager.Arrange(Home, first: true));
        Equal(0, desktop.Writes);
        True(!store.Pending);
    })),
    ("window capacity and auto-arrange guard before writing", () => WithDesktop((store, desktop, manager) =>
    {
        Throws<CapacityException>(() => manager.Arrange(new(300, 200, 339, 239), first: true));
        desktop.AutoArrange = true;
        Throws<InvalidOperationException>(() => manager.Arrange(Home, first: true));
        Equal(0, desktop.Writes);
        True(!store.Pending);
    })),
    ("new or deleted items and duplicate display names", () => WithDesktop((store, desktop, manager) =>
    {
        Pixel original = desktop.Icons["a"].Position;
        manager.Arrange(Home, first: true);
        desktop.Icons.Remove("b");
        desktop.Icons.Add("replacement", new("replacement", "同名", new(950, 650)));
        Equal(new RestoreResult(2, 0, 1), manager.Restore());
        Equal(original, desktop.Icons["a"].Position);
        Equal(new Pixel(950, 650), desktop.Icons["replacement"].Position);
        True(!store.Pending);
    })),
    ("new icon occupying original point is protected", () => WithDesktop((store, desktop, manager) =>
    {
        manager.Arrange(Home, first: true);
        desktop.Icons.Add("replacement", new("replacement", "同名", new(110, 10)));
        var result = manager.Restore();
        Equal(3, result.Failed);
        True(!result.Complete && store.Pending);
        Equal(1, desktop.Writes);
    })),
    ("failed restore retains snapshot and fresh manager can recover", () => WithDesktop((store, desktop, manager) =>
    {
        manager.Arrange(Home, first: true);
        desktop.IgnoreWrites = true;
        var failure = manager.Restore();
        Equal(3, failure.Failed);
        True(store.Pending);
        desktop.IgnoreWrites = false;
        Equal(new RestoreResult(3, 0, 0), new DesktopIconManager(store, () => desktop).Restore());
        True(!store.Pending);
    })),
    ("partial Shell write rolls back and verifies coordinates", () => WithDesktop((store, desktop, manager) =>
    {
        var originals = desktop.Read().Icons;
        desktop.FailAfterFirst = true;
        Throws<Exception>(() => manager.Arrange(Home, first: true));
        Equal(2, desktop.Writes);
        True(desktop.Read().Icons.ToHashSet().SetEquals(originals));
        True(!store.Pending);
    })),
    ("uncovered label triggers verified rollback", () => WithDesktop((store, desktop, manager) =>
    {
        var originals = desktop.Read().Icons;
        desktop.AfterWrite = () => desktop.BoundsOverride = [new(0, 0, 5, 5)];
        Throws<Exception>(() => manager.Arrange(Home, first: true));
        True(desktop.Read().Icons.ToHashSet().SetEquals(originals));
        True(!store.Pending);
    })),
    ("DPI/topology change keeps pending snapshot", () => WithDesktop((store, desktop, manager) =>
    {
        manager.Arrange(Home, first: true);
        var original = desktop.Frame;
        desktop.Frame = original with { Dpi = 96 };
        var result = manager.Restore();
        True(!result.Complete && store.Pending);
        Equal(1, desktop.Writes);
        desktop.Frame = original;
        True(manager.Restore().Complete);
    })),
    ("prevent concurrent operations and competing recovery instance", () => WithDesktop((store, desktop, manager) =>
    {
        using var entered = new ManualResetEventSlim();
        using var release = new ManualResetEventSlim();
        desktop.AfterWrite = () => { entered.Set(); release.Wait(TimeSpan.FromSeconds(5)); };
        var task = Task.Run(() => manager.Arrange(Home, first: true));
        try
        {
            True(entered.Wait(TimeSpan.FromSeconds(5)));
            Throws<InvalidOperationException>(() => manager.Restore());
            Throws<IOException>(() => store.Acquire());
        }
        finally { release.Set(); }
        Equal(3, task.GetAwaiter().GetResult());
        Equal(1, desktop.Writes);
    })),
    ("negative-monitor coordinates and invalid origin point", () =>
    {
        var desktop = new FakeDesktop();
        desktop.Frame = desktop.Frame with
        {
            Screens = [new("left", new(-1000, -500, 0, 300), new(-1000, -500, 0, 300), 96, 96)]
        };
        var area = new PixelRect(-970, -470, -370, 100);
        var plan = GridPlanner.Plan(desktop.Read(), desktop.ReadIconBounds(3), area);
        desktop.Position(plan);
        True(desktop.ReadIconBounds(3).All(area.Contains));
        True(plan.All(move => move.Position != default));
    })
};

int failures = 0;
foreach (var test in tests)
{
    try { test.Run(); Console.WriteLine($"PASS {test.Name}"); }
    catch (Exception error) { failures++; Console.Error.WriteLine($"FAIL {test.Name}: {error}"); }
}
Console.WriteLine($"{tests.Length - failures}/{tests.Length} passed");
return failures == 0 ? 0 : 1;

partial class Program
{
    private static string Root { get; set; } = "";
    private static PixelRect Home => new(290, 180, 700, 490);

    private static void WithDesktop(Action<SnapshotStore, FakeDesktop, DesktopIconManager> test)
    {
        Root = Path.Combine(Path.GetTempPath(), $"DesktopCleaner.Tests-{Guid.NewGuid():N}");
        try
        {
            var store = new SnapshotStore(Root);
            using var lease = store.Acquire();
            var desktop = new FakeDesktop();
            test(store, desktop, new DesktopIconManager(store, () => desktop));
        }
        finally { Directory.Delete(Root, recursive: true); }
    }

    private static void True(bool value)
    {
        if (!value) throw new InvalidOperationException("Expected true.");
    }

    private static void Equal<T>(T expected, T actual)
    {
        if (!EqualityComparer<T>.Default.Equals(expected, actual))
            throw new InvalidOperationException($"Expected {expected}; got {actual}.");
    }

    private static void Throws<T>(Action action) where T : Exception
    {
        try { action(); }
        catch (T) { return; }
        throw new InvalidOperationException($"Expected {typeof(T).Name}.");
    }
}

sealed class FakeDesktop : IDesktopView
{
    public DesktopFrame Frame = new(new(0, 0), new(100, 100),
        [new("main", new(0, 0, 1200, 900), new(0, 0, 1200, 860), 144, 144)], 144);
    public Dictionary<string, DesktopIcon> Icons { get; } = new(StringComparer.Ordinal)
    {
        ["a"] = new("a", "同名", new(10, 10)),
        ["b"] = new("b", "同名", new(110, 10)),
        ["c"] = new("c", "Picture", new(210, 10))
    };
    public bool AutoArrange, IgnoreWrites, FailAfterFirst;
    public Action? AfterWrite;
    public PixelRect[]? BoundsOverride;
    public int Writes { get; private set; }

    public DesktopState Read() => new(Frame, Icons.Values.ToArray(), AutoArrange);
    public PixelRect[] ReadIconBounds(int count) => BoundsOverride ?? Icons.Values.Select(icon =>
    {
        int x = icon.Position.X + Frame.Origin.X, y = icon.Position.Y + Frame.Origin.Y;
        return new PixelRect(x - 10, y + 2, x + 70, y + 75);
    }).ToArray();

    public void Position(IReadOnlyList<IconMove> moves)
    {
        if (moves.Count == 0)
            return;
        Writes++;
        foreach (var move in moves)
        {
            if (!IgnoreWrites)
                Icons[move.Id] = Icons[move.Id] with { Position = move.Position };
            if (FailAfterFirst)
            {
                FailAfterFirst = false;
                throw new IOException("Simulated Explorer failure after the first write.");
            }
        }
        AfterWrite?.Invoke();
    }

    public void Dispose() { }
}
