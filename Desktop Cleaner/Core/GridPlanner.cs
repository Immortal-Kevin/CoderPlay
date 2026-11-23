namespace DesktopCleaner;

public static class GridPlanner
{
    public static IconMove[] Plan(DesktopState desktop, PixelRect[] iconBounds, PixelRect window)
    {
        if (desktop.Icons.Length == 0)
            return [];

        var (left, top, right, bottom) = Footprint(desktop, iconBounds);
        var (stepX, stepY) = desktop.Frame.Spacing;
        var (originX, originY) = desktop.Frame.Origin;
        var cells = new List<Pixel>();
        foreach (var screen in desktop.Frame.Screens)
        {
            var region = window.Intersect(screen.WorkArea);
            if (region.Width <= 0 || region.Height <= 0)
                continue;
            // Leave safety space at the rounded visible corners of the window.
            int inset = (int)Math.Ceiling(10 * screen.DpiX / 96.0);
            var localIcons = desktop.Icons.Where(icon => screen.Bounds.Contains(new(
                icon.Position.X + originX, icon.Position.Y + originY,
                icon.Position.X + originX + 1, icon.Position.Y + originY + 1))).ToArray();
            var anchors = localIcons.Length == 0 ? desktop.Icons : localIcons;
            int phaseX = CommonPhase(anchors.Select(i => i.Position.X + originX - screen.Bounds.Left), stepX);
            int phaseY = CommonPhase(anchors.Select(i => i.Position.Y + originY - screen.Bounds.Top), stepY);
            int minX = region.Left + inset - left;
            int minY = region.Top + inset - top;
            int firstX = minX + Mod(screen.Bounds.Left + phaseX - minX, stepX);
            int firstY = minY + Mod(screen.Bounds.Top + phaseY - minY, stepY);
            for (int y = firstY; y + bottom <= region.Bottom - inset; y += stepY)
                for (int x = firstX; x + right <= region.Right - inset; x += stepX)
                {
                    var point = new Pixel(x - originX, y - originY);
                    if (point != default)
                        cells.Add(point);
                }
        }

        Pixel[] unique = cells.Distinct().ToArray();
        if (unique.Length < desktop.Icons.Length)
            throw new CapacityException(unique.Length, desktop.Icons.Length);

        return desktop.Icons.OrderBy(i => i.Id, StringComparer.Ordinal)
            .Zip(unique, (icon, position) => new IconMove(icon.Id, position)).ToArray();
    }

    public static PixelRect SuggestWindow(DesktopState desktop, PixelRect window)
    {
        var screen = desktop.Frame.Screens.MaxBy(screen =>
        {
            var overlap = window.Intersect(screen.WorkArea);
            return (long)Math.Max(0, overlap.Width) * Math.Max(0, overlap.Height);
        })!;
        var work = screen.WorkArea;
        int fitColumns = Math.Max(1, work.Width / desktop.Frame.Spacing.X - 1);
        int columns = Math.Min(fitColumns, Math.Max(1, (int)Math.Ceiling(Math.Sqrt(
            desktop.Icons.Length * 1.45 * desktop.Frame.Spacing.Y / desktop.Frame.Spacing.X))));
        int rows = (desktop.Icons.Length + columns - 1) / columns;
        int width = Math.Min(work.Width, Math.Max(window.Width, (columns + 1) * desktop.Frame.Spacing.X + 24));
        int height = Math.Min(work.Height, Math.Max(window.Height, (rows + 1) * desktop.Frame.Spacing.Y + 24));
        if (height == work.Height)
            width = work.Width;
        int x = Math.Clamp(window.Left + (window.Width - width) / 2, work.Left, work.Right - width);
        int y = Math.Clamp(window.Top + (window.Height - height) / 2, work.Top, work.Bottom - height);
        return new(x, y, x + width, y + height);
    }

    private static PixelRect Footprint(DesktopState desktop, PixelRect[] bounds)
    {
        // MSAA returns the rendered icon and label bounds. Match by the Shell anchor's proximity
        // so enumeration order does not determine the measured overhang.
        if (bounds.Length != desktop.Icons.Length)
            throw new InvalidOperationException("无法测量全部图标的边界。");
        int left = 0, top = 0, right = 0, bottom = 0;
        var (originX, originY) = desktop.Frame.Origin;
        var unused = new HashSet<PixelRect>(bounds);
        foreach (var icon in desktop.Icons)
        {
            int x = icon.Position.X + originX;
            int y = icon.Position.Y + originY;
            var closest = unused.Where(b => x >= b.Left && x < b.Right &&
                    Math.Abs(b.Top - y) < desktop.Frame.Spacing.Y / 2)
                .MinBy(b => Math.Abs(b.Top - y));
            if (!unused.Remove(closest))
                throw new InvalidOperationException("无法对齐 Shell 图标坐标和可访问性边界。");
            left = Math.Min(left, closest.Left - x);
            top = Math.Min(top, closest.Top - y);
            right = Math.Max(right, closest.Right - x);
            bottom = Math.Max(bottom, closest.Bottom - y);
        }
        return new(left, top, right, bottom);
    }

    private static int CommonPhase(IEnumerable<int> offsets, int step) =>
        offsets.Select(offset => Mod(offset, step)).GroupBy(offset => offset)
            .OrderByDescending(group => group.Count()).ThenBy(group => group.Key).First().Key;

    private static int Mod(int value, int step) => (value % step + step) % step;
}

public sealed class CapacityException(int capacity, int count)
    : InvalidOperationException($"当前窗口可遮挡 {capacity} 个图标，桌面共有 {count} 个图标。");

