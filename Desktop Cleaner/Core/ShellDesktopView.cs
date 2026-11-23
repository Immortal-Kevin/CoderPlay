using System.Runtime.InteropServices;

namespace DesktopCleaner;

public sealed class ShellDesktopView : IDesktopView
{
    private static readonly Guid ShellWindows = new("9BA05972-F6A8-11CF-A442-00A0C90A8F39");
    private static readonly Guid TopLevelBrowser = new("4C96BE40-915C-11CF-99D3-00AA004AE837");
    private const uint AllViewItems = 2;
    private const uint PositionItem = 0x80;
    private readonly IShellView shellView;
    private readonly IFolderView folderView;
    private readonly Dictionary<string, nint> children = new(StringComparer.Ordinal);

    public ShellDesktopView()
    {
        var windows = (IShellWindows)Activator.CreateInstance(Type.GetTypeFromCLSID(ShellWindows, true)!)!;
        try
        {
            object desktop = 0;
            object? root = null;
            RequireOk(windows.FindWindowSW(ref desktop, ref root, 8, out _, 1, out var dispatch),
                "查找 Windows 桌面");
            try
            {
                Guid browserId = typeof(IShellBrowser).GUID;
                RequireOk(((IShellServiceProvider)dispatch).QueryService(TopLevelBrowser, browserId, out var browser),
                    "连接 Explorer 桌面服务");
                try
                {
                    RequireOk(((IShellBrowser)browser).QueryActiveShellView(out shellView), "读取桌面 Shell 视图");
                    try { folderView = (IFolderView)shellView; }
                    catch { Marshal.ReleaseComObject(shellView); throw; }
                }
                finally { Marshal.ReleaseComObject(browser); }
            }
            finally { Marshal.ReleaseComObject(dispatch); }
        }
        finally { Marshal.ReleaseComObject(windows); }
    }

    public DesktopState Read()
    {
        FreeChildren();
        RequireOk(shellView.GetWindow(out nint window), "读取桌面视图句柄");
        nint surface = Native.FindIconSurface(window);
        RequireOk(folderView.GetSpacing(out var spacing), "读取桌面图标网格");
        if (spacing.X <= 0 || spacing.Y <= 0)
            throw new InvalidOperationException("Explorer 返回了无效的桌面图标间距。");
        int arrange = folderView.GetAutoArrange();
        if (arrange != 1)
            RequireOk(arrange, "检查自动排列设置");
        RequireOk(folderView.ItemCount(AllViewItems, out int count), "读取图标数量");
        var icons = new List<DesktopIcon>(count);
        for (int index = 0; index < count; index++)
        {
            RequireOk(folderView.Item(index, out nint child), "读取图标 PIDL");
            try
            {
                string name = Name(child, 0);
                string id = TryName(child, 0x80058000) is { } path
                    ? Native.FileIdentity(path)
                    : "shell:" + Name(child, 0x80028000);
                RequireOk(folderView.GetItemPosition(child, out var position), "读取图标坐标");
                if (!children.TryAdd(id, child))
                    throw new InvalidOperationException("Explorer 返回了重复的桌面项目标识。");
                child = 0;
                icons.Add(new(id, name, position));
            }
            finally { Marshal.FreeCoTaskMem(child); }
        }

        RequireOk(folderView.ItemCount(AllViewItems, out int checkedCount), "复查图标数量");
        if (checkedCount != count)
            throw new InvalidOperationException("读取过程中桌面图标发生变化，请重试。");
        return new(Native.ReadFrame(surface, spacing), icons.ToArray(), arrange == 0);
    }

    public void Position(IReadOnlyList<IconMove> moves)
    {
        if (moves.Count == 0)
            return;
        nint[] pidls = moves.Select(move => children[move.Id]).ToArray();
        Pixel[] positions = moves.Select(move => move.Position).ToArray();
        RequireOk(folderView.SelectAndPositionItems((uint)moves.Count, pidls, positions, PositionItem),
            "移动桌面图标");
    }

    public PixelRect[] ReadIconBounds(int count)
    {
        RequireOk(shellView.GetWindow(out nint window), "读取桌面视图句柄");
        return IconBounds.Read(Native.FindIconSurface(window), count);
    }

    public void Dispose()
    {
        FreeChildren();
        Marshal.ReleaseComObject(shellView);
    }

    private void FreeChildren()
    {
        foreach (nint child in children.Values)
            Marshal.FreeCoTaskMem(child);
        children.Clear();
    }

    private static string Name(nint item, uint format) =>
        TryName(item, format) ?? throw new InvalidOperationException("Explorer 无法解析桌面项目的名称。");

    private static string? TryName(nint item, uint format)
    {
        // Children of the desktop namespace are already rooted at the desktop.
        int result = SHGetNameFromIDList(item, format, out nint value);
        try { return result == 0 ? Marshal.PtrToStringUni(value) : null; }
        finally { Marshal.FreeCoTaskMem(value); }
    }

    private static void RequireOk(int result, string operation)
    {
        if (result != 0)
            throw new InvalidOperationException($"{operation}失败（HRESULT 0x{result:X8}）。",
                Marshal.GetExceptionForHR(result));
    }

    [DllImport("shell32")] private static extern int SHGetNameFromIDList(nint pidl, uint format, out nint name);
}
