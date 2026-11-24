using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Interop;
using Forms = System.Windows.Forms;

namespace DesktopGoose.App;

internal static class WindowsDesktop
{
    internal const int TopmostNoActivate = 0x0210;
    public static bool LeftDown => GetAsyncKeyState(1) < 0;
    public static Point Cursor => new(Forms.Cursor.Position.X, Forms.Cursor.Position.Y);

    public static Forms.Screen Selected(string name) =>
        Forms.Screen.AllScreens.FirstOrDefault(s => s.DeviceName == name) ?? Forms.Screen.PrimaryScreen!;

    public static (bool Fullscreen, bool Desktop) Foreground()
    {
        nint active = GetForegroundWindow();
        if (active == 0 || active == GetShellWindow() || active == GetDesktopWindow())
            return (false, true);
        var buffer = new System.Text.StringBuilder(128);
        GetClassName(active, buffer, buffer.Capacity);
        if (buffer.ToString() is "Progman" or "WorkerW" or "Shell_TrayWnd" or "Shell_SecondaryTrayWnd")
            return (false, true);
        if (buffer.ToString() == "DesktopGoose" ||
            (GetWindowThreadProcessId(active, out uint process) != 0 && process == Environment.ProcessId))
            return (false, false);

        var screen = Forms.Screen.FromHandle(active).Bounds;
        if (DwmGetWindowAttribute(active, 9, out NativeRect rect, 16) != 0 && !GetWindowRect(active, out rect))
            return (false, false);
        long style = GetWindowLongPtr(active, -16);
        bool fullBounds = rect.Left <= screen.Left + 1 && rect.Top <= screen.Top + 1 &&
            rect.Right >= screen.Right - 1 && rect.Bottom >= screen.Bottom - 1;
        bool decorated = (style & 0x00C00000) == 0x00C00000;
        return (fullBounds && !decorated, false);
    }

    public static bool PresentationFullscreen()
    {
        return SHQueryUserNotificationState(out int state) == 0 && state == 3;
    }

    public static uint IdleMilliseconds()
    {
        var input = new LastInput { Size = 8 };
        return GetLastInputInfo(ref input) ? unchecked((uint)Environment.TickCount - input.Time) : 0;
    }

    public static void NonActivating(nint window, bool through)
    {
        long exStyle = GetWindowLongPtr(window, -20);
        SetWindowLongPtr(window, -20, (nint)(exStyle | 0x08000080 | (through ? 0x20L : 0L)));
    }

    public static void Place(nint window, Rect rect) =>
        SetWindowPos(window, -1, (int)Math.Round(rect.X), (int)Math.Round(rect.Y),
            Math.Max(1, (int)Math.Round(rect.Width)), Math.Max(1, (int)Math.Round(rect.Height)), TopmostNoActivate);

    [StructLayout(LayoutKind.Sequential)]
    private struct NativeRect { public int Left, Top, Right, Bottom; }
    [StructLayout(LayoutKind.Sequential)]
    private struct LastInput { public uint Size, Time; }

    [DllImport("user32.dll")] private static extern short GetAsyncKeyState(int key);
    [DllImport("user32.dll")] private static extern nint GetForegroundWindow();
    [DllImport("user32.dll")] private static extern nint GetDesktopWindow();
    [DllImport("user32.dll")] private static extern nint GetShellWindow();
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] private static extern int GetClassName(nint h, System.Text.StringBuilder text, int max);
    [DllImport("user32.dll")] private static extern uint GetWindowThreadProcessId(nint h, out uint process);
    [DllImport("user32.dll")] private static extern bool GetLastInputInfo(ref LastInput data);
    [DllImport("user32.dll")] private static extern bool GetWindowRect(nint h, out NativeRect rect);
    [DllImport("dwmapi.dll")] private static extern int DwmGetWindowAttribute(nint h, int attribute, out NativeRect data, int size);
    [DllImport("shell32.dll")] private static extern int SHQueryUserNotificationState(out int state);
    [DllImport("user32.dll", EntryPoint = "GetWindowLongPtrW")] private static extern nint GetWindowLongPtr(nint h, int index);
    [DllImport("user32.dll", EntryPoint = "SetWindowLongPtrW")] private static extern nint SetWindowLongPtr(nint h, int index, nint value);
    [DllImport("user32.dll")] private static extern bool SetWindowPos(nint h, nint insertAfter, int x, int y, int w, int hgt, int flags);
}

internal interface IInputCounter : IDisposable
{
    event Action? Operation;
    event Action<Point>? MousePressed;
    bool CountsKeyboard { get; set; }
}

internal sealed class RawInput : IInputCounter
{
    private readonly HwndSource source;
    private readonly HashSet<(nint Device, int Scan)> pressed = [];
    private readonly byte[] buffer = new byte[128];
    private bool keyboard;
    public event Action? Operation;
    public event Action<Point>? MousePressed;

    public RawInput()
    {
        source = new HwndSource(new HwndSourceParameters("Desktop Goose raw input") { ParentWindow = -3 });
        source.AddHook(Message);
        try { Register(2, true); }
        catch { source.Dispose(); throw; }
    }

    public bool CountsKeyboard
    {
        get => keyboard;
        set
        {
            if (keyboard == value)
                return;
            Register(6, value);
            pressed.Clear();
            keyboard = value;
        }
    }

    private void Register(ushort usage, bool enable)
    {
        var device = new Device { Page = 1, Usage = usage, Flags = enable ? 0x2100u : 1u, Target = enable ? source.Handle : 0 };
        if (!RegisterRawInputDevices([device], 1, (uint)Marshal.SizeOf<Device>()))
            throw new Win32Exception(Marshal.GetLastWin32Error());
    }

    private nint Message(nint hwnd, int msg, nint wParam, nint lParam, ref bool handled)
    {
        if (msg == 0x00FE && wParam == 2)
            pressed.RemoveWhere(key => key.Device == lParam);
        if (msg != 0x00FF)
            return 0;

        uint size = (uint)buffer.Length;
        uint header = (uint)(8 + IntPtr.Size * 2);
        uint read = GetRawInputData(lParam, 0x10000003, buffer, ref size, header);
        if (read == uint.MaxValue || read < header + 16)
            return 0;
        int start = (int)header;
        nint device = (nint)BitConverter.ToInt64(buffer, 8);
        if (device == 0)
            return 0;
        uint type = BitConverter.ToUInt32(buffer, 0);
        if (type == 0)
        {
            ushort buttons = BitConverter.ToUInt16(buffer, start + 4);
            int count = ((buttons & 1) != 0 ? 1 : 0) + ((buttons & 4) != 0 ? 1 : 0) + ((buttons & 16) != 0 ? 1 : 0);
            if (count > 0)
            {
                for (int i = 0; i < count; i++)
                    Operation?.Invoke();
                MousePressed?.Invoke(WindowsDesktop.Cursor);
            }
        }
        else if (type == 1 && keyboard)
        {
            ushort flags = BitConverter.ToUInt16(buffer, start + 2);
            ushort scan = BitConverter.ToUInt16(buffer, start);
            ushort vk = BitConverter.ToUInt16(buffer, start + 6);
            if (scan == 0xff || vk == 0xff)
                return 0;
            int key = (scan == 0 ? 0x10000 + vk : scan) | (flags & 6) << 8;
            if ((flags & 1) != 0)
                pressed.Remove((device, key));
            else if (pressed.Add((device, key)))
            {
                Operation?.Invoke();
                if (vk == 0x13) // Pause does not have a hardware break packet.
                    pressed.Remove((device, key));
            }
        }
        return 0;
    }

    public void Dispose()
    {
        try { CountsKeyboard = false; Register(2, false); }
        finally { source.Dispose(); }
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct Device { public ushort Page, Usage; public uint Flags; public nint Target; }
    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool RegisterRawInputDevices(Device[] devices, uint count, uint size);
    [DllImport("user32.dll")]
    private static extern uint GetRawInputData(nint raw, uint command, [Out] byte[] data, ref uint size, uint headerSize);
}
