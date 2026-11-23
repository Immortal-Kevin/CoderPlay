namespace DesktopCleaner;

public sealed record RestoreResult(int Restored, int Failed, int Missing, string? Detail = null)
{
    public bool Complete => Failed == 0 && Detail is null;
    public override string ToString() => $"恢复 {Restored} 个，失败 {Failed} 个，缺失 {Missing} 个。" +
        (Detail is null ? "" : $" {Detail}");
}

public sealed class DesktopIconManager(SnapshotStore store, Func<IDesktopView> openView)
{
    private int busy;
    private PixelRect? lastTarget;
    public bool Pending => store.Pending;

    public (int Count, bool AutoArrange) Inspect() => Run(() =>
    {
        using var view = openView();
        var state = view.Read();
        return (state.Icons.Length, state.AutoArrange);
    });

    public PixelRect? SuggestLargerWindow(PixelRect window) => Run<PixelRect?>(() =>
    {
        using var view = openView();
        var state = view.Read();
        if (state.AutoArrange || state.Icons.Length == 0)
            return null;
        var bounds = view.ReadIconBounds(state.Icons.Length);
        try { GridPlanner.Plan(state, bounds, window); return null; }
        catch (CapacityException)
        {
            var suggested = GridPlanner.SuggestWindow(state, window);
            try { GridPlanner.Plan(state, bounds, suggested); return suggested; }
            catch (CapacityException)
            {
                var workArea = state.Frame.Screens.First(screen => screen.WorkArea.Contains(suggested)).WorkArea;
                GridPlanner.Plan(state, bounds, workArea);
                return workArea;
            }
        }
    });

    public int Arrange(PixelRect window, bool first, bool force = false) => Run(() =>
    {
        bool pending = store.Pending;
        if (first && pending)
            throw new InvalidOperationException("存在待恢复的桌面布局，请先恢复。");
        if (!first && (!pending || (!force && lastTarget == window)))
            return -1;

        bool attempted = false;
        try
        {
            using var view = openView();
            var before = view.Read();
            if (before.Icons.Length == 0 && first)
                return 0;
            if (before.AutoArrange)
                throw new InvalidOperationException("Windows 已启用「自动排列图标」。请关闭该选项后重试。");
            var original = pending ? store.Load() : null;
            if (original is not null && !before.Frame.SameCoordinates(original.Frame))
                throw new InvalidOperationException("显示器配置或桌面网格已变化，原始快照仍待恢复。");
            if (original is not null && before.Icons.ExceptBy(original.Icons.Select(i => i.Id), i => i.Id).Any())
                throw new InvalidOperationException("桌面出现了新的图标。请恢复后重新整理。");

            var moves = GridPlanner.Plan(before, view.ReadIconBounds(before.Icons.Length), window);
            if (!pending)
                _ = store.Save(before);
            // Recheck immediately before issuing the batch with fresh PIDLs.
            var ready = view.Read();
            if (ready.AutoArrange || !ready.Frame.SameCoordinates(before.Frame) ||
                !ready.Icons.ToHashSet().SetEquals(before.Icons))
                throw new InvalidOperationException("备份后桌面状态已改变，请重试。");

            var changed = moves.Where(move => ready.Icons.Any(icon =>
                icon.Id == move.Id && icon.Position != move.Position)).ToArray();
            attempted = changed.Length > 0;
            view.Position(changed);
            var landed = view.Read();
            if (!landed.Frame.SameCoordinates(before.Frame) || landed.Icons.Length != moves.Length ||
                !landed.Icons.Select(icon => new IconMove(icon.Id, icon.Position)).ToHashSet().SetEquals(moves))
                throw new InvalidOperationException("Explorer 未将所有图标放到目标网格，可能受网格对齐设置影响。");
            if (!view.ReadIconBounds(landed.Icons.Length).All(window.Contains))
                throw new InvalidOperationException("Explorer 的图标或标签超出了窗口的实际遮挡范围。");

            lastTarget = window;
            return landed.Icons.Length;
        }
        catch (Exception error)
        {
            if ((!pending && !attempted) || !store.Pending)
                throw;
            string recovery;
            try { recovery = RestoreCore().ToString(); }
            catch (Exception recoveryError) { recovery = "恢复失败：" + recoveryError.Message; }
            throw new InvalidOperationException(error.Message + " " + recovery, error);
        }
    });

    public RestoreResult Restore() => Run(RestoreCore);

    private RestoreResult RestoreCore()
    {
        lastTarget = null;
        if (!store.Pending)
            return new(0, 0, 0);
        var original = store.Load();
        using var view = openView();
        var before = view.Read();
        var saved = original.Icons.ToDictionary(icon => icon.Id, StringComparer.Ordinal);
        var live = before.Icons.ToDictionary(icon => icon.Id, StringComparer.Ordinal);
        var existing = original.Icons.Where(icon => live.ContainsKey(icon.Id)).ToArray();
        int missing = original.Count - existing.Length;
        if (!before.Frame.SameCoordinates(original.Frame))
            return new(0, existing.Length, missing, "请恢复备份时的显示器、缩放和图标间距后重试。");

        var changed = existing.Where(icon => live[icon.Id].Position != icon.Position).ToArray();
        if (before.AutoArrange && changed.Length > 0)
            return new(existing.Length - changed.Length, changed.Length, missing, "请关闭「自动排列图标」后重试。");

        var newIcons = before.Icons.Where(icon => !saved.ContainsKey(icon.Id)).ToArray();
        foreach (var icon in changed)
        {
            if (newIcons.Any(added => added.Position == icon.Position))
                return new(existing.Length - changed.Length, changed.Length, missing,
                    "有新增图标占用了原始坐标，请将其移开后重试。");
        }

        string? batchError = null;
        if (changed.Length > 0)
        {
            try { view.Position(changed.Select(icon => new IconMove(icon.Id, icon.Position)).ToArray()); }
            catch (Exception error) { batchError = error.Message; }
        }
        var after = view.Read();
        var verified = after.Icons.ToDictionary(icon => icon.Id, StringComparer.Ordinal);
        int restored = original.Icons.Count(icon => verified.TryGetValue(icon.Id, out var found) &&
            found.Position == icon.Position);
        missing = original.Icons.Count(icon => !verified.ContainsKey(icon.Id));
        int failed = original.Count - missing - restored;

        if (!after.Frame.SameCoordinates(original.Frame))
            return new(0, original.Count - missing, missing, "恢复期间显示器或桌面网格已变化。");
        if (newIcons.Any(icon => verified.TryGetValue(icon.Id, out var found) && found.Position != icon.Position))
            return new(restored, failed, missing, "Explorer 同时改变了新增图标的坐标，已保留快照。");
        if (failed == 0)
        {
            store.ClearAfterVerification();
            return new(restored, 0, missing);
        }
        return new(restored, failed, missing, batchError ?? "Explorer 回读坐标与原始快照不一致。");
    }

    private T Run<T>(Func<T> action)
    {
        if (Interlocked.Exchange(ref busy, 1) == 1)
            throw new InvalidOperationException("已有桌面图标操作正在执行。");
        try { return action(); }
        finally { Volatile.Write(ref busy, 0); }
    }
}
