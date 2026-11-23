using DesktopCleaner;

internal static class Program
{
    [STAThread]
    private static int Main(string[] args)
    {
        try
        {
            if (args is ["--probe"])
                return Probe();
            if (args is not [] and not ["--restore"])
            {
                Console.Error.WriteLine("DesktopCleaner.Recovery [--restore | --probe]");
                return 2;
            }

            var store = SnapshotStore.ForCurrentUser();
            using var lease = store.Acquire();
            if (!store.Pending)
            {
                Console.WriteLine("没有待恢复的桌面布局。");
                return 0;
            }

            var result = new DesktopIconManager(store, () => new ShellDesktopView()).Restore();
            Console.WriteLine(result);
            return result.Complete ? 0 : 1;
        }
        catch (Exception error)
        {
            Console.Error.WriteLine(error.Message);
            return 1;
        }
        finally
        {
            if (args.Length == 0 && !Console.IsInputRedirected)
            {
                Console.WriteLine("按 Enter 键退出。");
                Console.ReadLine();
            }
        }
    }

    private static int Probe()
    {
        using var view = new ShellDesktopView();
        var state = view.Read();
        var bounds = view.ReadIconBounds(state.Icons.Length);
        var again = view.Read();
        bool stable = state.Frame.SameCoordinates(again.Frame) && state.Icons.ToHashSet().SetEquals(again.Icons);
        Console.WriteLine($"Shell read: {state.Icons.Length} items; distinct coordinates: {state.Icons.Select(i => i.Position).Distinct().Count()}; stable: {stable}");
        Console.WriteLine($"Accessible bounds: {bounds.Length}; auto-arrange: {state.AutoArrange}; spacing: {state.Frame.Spacing}");
        foreach (var monitor in state.Frame.Screens)
        {
            Console.WriteLine($"{monitor.Device}: {monitor.Bounds.Width}×{monitor.Bounds.Height} / {monitor.DpiX} DPI");
            try
            {
                int capacity = GridPlanner.Plan(state, bounds, monitor.WorkArea).Length;
                var work = monitor.WorkArea;
                int x = work.Left + work.Width / 2;
                int y = work.Top + work.Height / 2;
                var suggested = GridPlanner.SuggestWindow(state, new(x - 230, y - 170, x + 230, y + 170));
                int suggestedCount = GridPlanner.Plan(state, bounds, suggested).Length;
                Console.WriteLine($"  Read-only placement plan: {capacity} items fit the work area; {suggestedCount} fit the suggested window.");
            }
            catch (CapacityException error) { Console.WriteLine($"  Read-only placement plan: {error.Message}"); }
        }
        return stable ? 0 : 1;
    }
}
