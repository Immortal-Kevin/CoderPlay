using System.Windows;
using System.Windows.Controls;
using System.Windows.Interop;
using System.Windows.Media;

namespace DesktopGoose.App;

internal sealed class SpriteWindow : Window
{
    private readonly Image image = new() { Stretch = Stretch.Fill };
    private readonly bool through;
    private nint handle;
    public Rect Pixels { get; private set; } = Rect.Empty;
    public SpriteFrame? Frame { get; private set; }

    public SpriteWindow(string title, bool through = false)
    {
        this.through = through;
        Title = title;
        Width = Height = 100;
        WindowStyle = WindowStyle.None;
        ResizeMode = ResizeMode.NoResize;
        AllowsTransparency = true;
        Background = Brushes.Transparent;
        ShowInTaskbar = false;
        ShowActivated = false;
        Topmost = true;
        Focusable = false;
        Content = image;
        RenderOptions.SetBitmapScalingMode(image, BitmapScalingMode.NearestNeighbor);
        SourceInitialized += (_, _) =>
        {
            handle = new WindowInteropHelper(this).Handle;
            WindowsDesktop.NonActivating(handle, through);
            HwndSource.FromHwnd(handle).AddHook(HitTest);
        };
    }

    private nint HitTest(nint hwnd, int msg, nint w, nint l, ref bool handled)
    {
        if (msg == 0x0021)
        {
            handled = true;
            return 3; // MA_NOACTIVATE: deliver the click without taking focus.
        }
        if (msg == 0x02E0)
        {
            // WPF still receives its DPI notification. Place() restores our physical bounds.
            Dispatcher.BeginInvoke(() => { if (!Pixels.IsEmpty) WindowsDesktop.Place(handle, Pixels); });
        }
        return 0;
    }

    public void Display(SpriteFrame frame, Rect rect)
    {
        if (Frame != frame)
        {
            Frame = frame;
            image.Source = frame.Bitmap;
        }
        bool changed = Pixels != rect;
        Pixels = rect;
        if (!IsVisible)
        {
            new WindowInteropHelper(this).EnsureHandle();
            WindowsDesktop.Place(handle, rect);
            Show();
            changed = true;
        }
        if (changed)
            WindowsDesktop.Place(handle, rect);
    }

    public double Distance(Point p)
    {
        if (!IsVisible || Frame is null || Pixels.IsEmpty)
            return double.PositiveInfinity;
        double dx = Math.Max(0, Math.Max(Pixels.Left - p.X, p.X - Pixels.Right));
        double dy = Math.Max(0, Math.Max(Pixels.Top - p.Y, p.Y - Pixels.Bottom));
        if (dx * dx + dy * dy > 10000)
            return double.PositiveInfinity;
        double x = (p.X - Pixels.X) * 64 / Pixels.Width;
        double y = (p.Y - Pixels.Y) * 64 / Pixels.Height;
        return Frame.Distance(x, y) * Pixels.Width / 64;
    }
}
