using System.Runtime.InteropServices;

namespace DesktopCleaner;

[StructLayout(LayoutKind.Sequential)]
public readonly record struct Pixel(int X, int Y);

[StructLayout(LayoutKind.Sequential)]
public readonly record struct PixelRect(int Left, int Top, int Right, int Bottom)
{
    public int Width => Right - Left;
    public int Height => Bottom - Top;
    public PixelRect Intersect(PixelRect other) => new(Math.Max(Left, other.Left),
        Math.Max(Top, other.Top), Math.Min(Right, other.Right), Math.Min(Bottom, other.Bottom));
    public bool Contains(PixelRect other) => other.Width > 0 && other.Height > 0 &&
        Left <= other.Left && Top <= other.Top && Right >= other.Right && Bottom >= other.Bottom;
}

public sealed record ScreenInfo(string Device, PixelRect Bounds, PixelRect WorkArea, uint DpiX, uint DpiY);
public sealed record DesktopIcon(string Id, string Name, Pixel Position);
public sealed record DesktopFrame(Pixel Origin, Pixel Spacing, ScreenInfo[] Screens, uint Dpi)
{
    public bool SameCoordinates(DesktopFrame other) => Origin == other.Origin &&
        Spacing == other.Spacing && Dpi == other.Dpi && Screens.SequenceEqual(other.Screens);
}

public sealed record DesktopState(DesktopFrame Frame, DesktopIcon[] Icons, bool AutoArrange);
public sealed record IconMove(string Id, Pixel Position);

public interface IDesktopView : IDisposable
{
    DesktopState Read();
    void Position(IReadOnlyList<IconMove> moves);
    PixelRect[] ReadIconBounds(int count);
}


