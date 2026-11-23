using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Text;
using Microsoft.Win32.SafeHandles;

namespace DesktopCleaner;

public static class Native
{
    private const int DwmExtendedFrameBounds = 9;

    public static PixelRect WindowBounds(nint window)
    {
        if (DwmGetWindowAttribute(window, DwmExtendedFrameBounds, out var bounds, 16) == 0 &&
            bounds.Width > 0 && bounds.Height > 0)
            return bounds;
        throw new InvalidOperationException("无法获取窗口的实际遮挡边界。");
    }

    public static PixelRect WindowPlacementBounds(nint window) =>
        GetWindowRect(window, out var bounds) ? bounds : default;

    internal static DesktopFrame ReadFrame(nint window, Pixel spacing)
    {
        Pixel origin = default;
        if (!ClientToScreen(window, ref origin))
            throw new Win32Exception();
        var screens = new List<ScreenInfo>();
        bool complete = true;
        bool listed = EnumDisplayMonitors(0, 0, (nint monitor, nint _, nint _, nint _) =>
        {
            var info = new MonitorInfo { Size = Marshal.SizeOf<MonitorInfo>() };
            if (!GetMonitorInfo(monitor, ref info) ||
                GetDpiForMonitor(monitor, 0, out uint dpiX, out uint dpiY) != 0)
            {
                complete = false;
                return false;
            }
            screens.Add(new(info.Device, info.Bounds, info.WorkArea, dpiX, dpiY));
            return true;
        }, 0);
        uint dpi = GetDpiForWindow(window);
        if (!listed || !complete || screens.Count == 0 || dpi == 0)
            throw new InvalidOperationException("无法读取完整的显示器和 DPI 配置。");
        return new(origin, spacing, screens.OrderBy(s => s.Device, StringComparer.Ordinal).ToArray(), dpi);
    }

    internal static nint FindIconSurface(nint view)
    {
        var surfaces = new List<nint>();
        EnumChildWindows(view, (window, _) =>
        {
            var name = new StringBuilder(64);
            GetClassName(window, name, name.Capacity);
            if (name.ToString() == "SysListView32")
                surfaces.Add(window);
            return true;
        }, 0);
        if (surfaces.Count != 1 || !IsWindowVisible(surfaces[0]))
            throw new InvalidOperationException("桌面图标视图不可用。请确认 Windows 已开启「显示桌面图标」。");
        return surfaces[0];
    }

    internal static string FileIdentity(string path)
    {
        const uint readAttributes = 0x80;
        const uint shareAll = 7;
        const uint openExisting = 3;
        const uint openDirectoryOrLink = 0x02200000;
        using var file = CreateFile(path, readAttributes, shareAll, 0, openExisting, openDirectoryOrLink, 0);
        if (file.IsInvalid || !GetFileInformationByHandle(file, out var info))
            throw new Win32Exception(Marshal.GetLastPInvokeError(), "无法读取桌面项目的文件标识：" + path);
        if (info.IndexHigh == 0 && info.IndexLow == 0)
            throw new InvalidOperationException("文件系统未提供稳定的桌面项目标识：" + path);
        return $"file:{info.Volume:x8}:{info.IndexHigh:x8}{info.IndexLow:x8}:{info.CreationHigh:x8}{info.CreationLow:x8}:{path}";
    }

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    private struct MonitorInfo
    {
        public int Size;
        public PixelRect Bounds, WorkArea;
        public uint Flags;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)] public string Device;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct FileInfo
    {
        public uint Attributes, CreationLow, CreationHigh, AccessLow, AccessHigh, WriteLow, WriteHigh,
            Volume, SizeHigh, SizeLow, Links, IndexHigh, IndexLow;
    }

    private delegate bool EnumMonitorProc(nint monitor, nint dc, nint rect, nint data);
    private delegate bool EnumWindowProc(nint window, nint data);
    [DllImport("user32")] private static extern bool GetWindowRect(nint hwnd, out PixelRect bounds);
    [DllImport("dwmapi")] private static extern int DwmGetWindowAttribute(nint hwnd, int attribute, out PixelRect value, int size);
    [DllImport("user32", SetLastError = true)] private static extern bool ClientToScreen(nint hwnd, ref Pixel point);
    [DllImport("user32")] private static extern bool EnumDisplayMonitors(nint dc, nint clip, EnumMonitorProc callback, nint data);
    [DllImport("user32", CharSet = CharSet.Unicode)] private static extern bool GetMonitorInfo(nint monitor, ref MonitorInfo info);
    [DllImport("shcore")] private static extern int GetDpiForMonitor(nint monitor, int kind, out uint x, out uint y);
    [DllImport("user32")] private static extern uint GetDpiForWindow(nint window);
    [DllImport("user32")] private static extern bool EnumChildWindows(nint window, EnumWindowProc callback, nint data);
    [DllImport("user32", CharSet = CharSet.Unicode)] private static extern int GetClassName(nint window, StringBuilder name, int capacity);
    [DllImport("user32")] private static extern bool IsWindowVisible(nint window);
    [DllImport("kernel32", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern SafeFileHandle CreateFile(string path, uint access, uint share, nint security,
        uint disposition, uint flags, nint template);
    [DllImport("kernel32", SetLastError = true)]
    private static extern bool GetFileInformationByHandle(SafeFileHandle file, out FileInfo info);
}
