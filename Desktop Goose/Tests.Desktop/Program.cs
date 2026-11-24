using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Interop;
using System.Windows.Media;
using System.Windows.Threading;
using DesktopGoose.App;
using DesktopGoose.Core;

internal static class Program
{
    [STAThread]
    private static int Main()
    {
        var application = new Application { ShutdownMode = ShutdownMode.OnExplicitShutdown };
        using var input = new RawInput();
        input.CountsKeyboard = true;
        input.CountsKeyboard = false;
        Console.WriteLine("PASS Raw Input devices registered and keyboard unregistered");

        var work = WindowsDesktop.Selected("").WorkingArea;
        var area = new Rect(work.Left + 40, work.Top + 80, 128, 128);
        var under = new Window
        {
            Title = "Desktop Goose · Smoke fixture", WindowStyle = WindowStyle.None, Background = Brushes.Navy,
            ShowActivated = false, ShowInTaskbar = false, Topmost = true, Width = 128, Height = 128
        };
        var sprite = new SpriteWindow("Desktop Goose · Smoke sprite");
        var trail = new SpriteWindow("Desktop Goose · Smoke transparent sprite", true);
        nint underHandle = new WindowInteropHelper(under).EnsureHandle();
        var art = PixelArt.Goose(new(Rarity.Common, 0, -1, 0), Pose.Stand, 0, false);
        nint before = GetForegroundWindow();
        under.Show();
        WindowsDesktop.Place(underHandle, area);
        sprite.Display(art, area);
        nint spriteHandle = new WindowInteropHelper(sprite).Handle;
        int result = 1;
        var timer = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(250) };
        int step = 0;
        timer.Tick += (_, _) =>
        {
            try
            {
                if (step++ == 0)
                {
                    Require(GetForegroundWindow() == before, "sprite show did not activate");
                    Require(GetWindowRect(spriteHandle, out var actual) && actual.Left == area.Left && actual.Top == area.Top &&
                        actual.Right - actual.Left == 128 && actual.Bottom - actual.Top == 128, "128px physical position and size");
                    Require((GetWindowLongPtr(spriteHandle, -20) & 8) != 0, "topmost native window");
                    Require(WindowFromPoint(new((int)area.Left + 50, (int)area.Top + 72)) == spriteHandle,
                        "opaque body receives hit tests");
                    Require(WindowFromPoint(new((int)area.Left + 2, (int)area.Top + 2)) == underHandle,
                        "transparent corner exposes lower window");
                    trail.Display(art, area);
                    return;
                }
                Require(WindowFromPoint(new((int)area.Left + 50, (int)area.Top + 72)) == spriteHandle,
                    "visible passive sprite passes through opaque pixels");
                Console.WriteLine($"DPI checked at {GetDpiForWindow(spriteHandle)}");
                result = 0;
            }
            catch (Exception error) { Console.Error.WriteLine($"FAIL {error.Message}"); }
            timer.Stop();
            trail.Close();
            sprite.Close();
            under.Close();
            application.Shutdown(result);
        };
        timer.Start();
        return application.Run();
    }

    private static void Require(bool condition, string label)
    {
        if (!condition)
            throw new InvalidOperationException(label);
        Console.WriteLine($"PASS {label}");
    }

    [StructLayout(LayoutKind.Sequential)] private readonly record struct NativePoint(int X, int Y);
    [StructLayout(LayoutKind.Sequential)] private struct NativeRect { public int Left, Top, Right, Bottom; }
    [DllImport("user32.dll")] private static extern nint WindowFromPoint(NativePoint point);
    [DllImport("user32.dll")] private static extern nint GetForegroundWindow();
    [DllImport("user32.dll")] private static extern bool GetWindowRect(nint window, out NativeRect rect);
    [DllImport("user32.dll", EntryPoint = "GetWindowLongPtrW")] private static extern nint GetWindowLongPtr(nint window, int index);
    [DllImport("user32.dll")] private static extern uint GetDpiForWindow(nint window);
}
