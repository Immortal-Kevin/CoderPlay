namespace DesktopCleaner;

[Flags]
public enum WindowChange
{
    None = 0,
    Position = 1,
    Size = 2
}

public sealed class WindowMovement
{
    private PixelRect start;
    public bool InMoveLoop { get; private set; }

    public void Begin(PixelRect bounds)
    {
        start = bounds;
        InMoveLoop = true;
    }

    public WindowChange End(PixelRect bounds)
    {
        if (!InMoveLoop)
            return WindowChange.None;
        InMoveLoop = false;
        var change = WindowChange.None;
        if (start.Left != bounds.Left || start.Top != bounds.Top)
            change |= WindowChange.Position;
        if (start.Width != bounds.Width || start.Height != bounds.Height)
            change |= WindowChange.Size;
        return change;
    }

    public bool CanApply(bool minimized, bool busy) => !InMoveLoop && !minimized && !busy;
}

