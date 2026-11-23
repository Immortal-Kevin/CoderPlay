using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Interop;
using System.Windows.Threading;

namespace DesktopCleaner;

public partial class MainWindow : Window
{
    private const int WmMove = 0x0003, WmSize = 0x0005, WmSettingChange = 0x001A, WmDisplayChange = 0x007E,
        WmSysCommand = 0x0112, WmEnterSizeMove = 0x0231, WmExitSizeMove = 0x0232, WmDpiChanged = 0x02E0;
    private readonly DesktopIconManager manager;
    private readonly DispatcherTimer settle;
    private readonly DispatcherTimer slowOperation;
    private readonly WindowMovement movement = new();
    private HwndSource? source;
    private nint handle;
    private bool busy, arranged, closingApproved, closeRequested, closeFlow, reconcileRequested, recheckFrame;
    private PixelRect? appliedBounds;

    public MainWindow(DesktopIconManager manager)
    {
        this.manager = manager;
        InitializeComponent();
        settle = new DispatcherTimer(DispatcherPriority.Background) { Interval = TimeSpan.FromMilliseconds(120) };
        settle.Tick += Reconcile;
        slowOperation = new DispatcherTimer { Interval = TimeSpan.FromSeconds(5) };
        slowOperation.Tick += (_, _) =>
        {
            slowOperation.Stop();
            Detail.Text = "仍在等待 Explorer 响应。恢复数据会在操作完成前保留。";
        };
        Loaded += async (_, _) => await Inspect();
    }

    protected override void OnSourceInitialized(EventArgs e)
    {
        base.OnSourceInitialized(e);
        handle = new WindowInteropHelper(this).Handle;
        source = HwndSource.FromHwnd(handle);
        source.AddHook(WindowMessage);
        // Windows 11 uses the native title bar and caption buttons.
        int dark = 1;
        _ = DwmSetWindowAttribute(handle, 20, ref dark, sizeof(int));
    }

    private nint WindowMessage(nint window, int message, nint wParam, nint lParam, ref bool handled)
    {
        switch (message)
        {
            case WmSysCommand when busy:
                int command = wParam.ToInt32() & 0xfff0;
                handled = command is 0xf000 or 0xf010 or 0xf020 or 0xf030 or 0xf120;
                break;
            case WmEnterSizeMove:
                settle.Stop();
                if (arranged)
                    movement.Begin(Native.WindowPlacementBounds(window));
                break;
            case WmExitSizeMove when movement.InMoveLoop:
                if (movement.End(Native.WindowPlacementBounds(window)) != WindowChange.None || reconcileRequested)
                    RequestReconcile(immediate: true);
                break;
            case WmMove or WmSize when arranged && !movement.InMoveLoop:
                RequestReconcile();
                break;
            case WmDpiChanged or WmDisplayChange or WmSettingChange when arranged:
                recheckFrame = true;
                RequestReconcile();
                break;
        }
        return 0;
    }

    private void RequestReconcile(bool immediate = false)
    {
        reconcileRequested = true;
        if (movement.InMoveLoop || busy)
            return;
        settle.Stop();
        if (immediate)
            Dispatcher.BeginInvoke(DispatcherPriority.Background, new Action(() => Reconcile(null, EventArgs.Empty)));
        else
            settle.Start();
    }

    private async void Reconcile(object? sender, EventArgs e)
    {
        settle.Stop();
        if (!arranged || !reconcileRequested || !movement.CanApply(WindowState == WindowState.Minimized, busy))
            return;
        reconcileRequested = false;
        bool force = recheckFrame;
        recheckFrame = false;
        await During("正在整理", "正在将图标移到窗口后方…", async () =>
        {
            var window = Native.WindowBounds(handle);
            if (window != appliedBounds || force)
                await ArrangeAt(window, first: false, force);
            else
                SetOrganizedStatus();
        });
    }

    protected override void OnStateChanged(EventArgs e)
    {
        base.OnStateChanged(e);
        if (arranged && WindowState == WindowState.Minimized)
            ShowStatus("未整理", "窗口已最小化，桌面图标可见。");
    }

    private async Task Inspect()
    {
        await During("未整理", "正在读取桌面图标…", async () =>
        {
            bool pending = manager.Pending;
            if (pending)
                ShowStatus("未整理", "检测到待恢复的原始布局。请点击「恢复桌面」。");
            var info = await OnShell(manager.Inspect);
            UpdateCount(info.Count);
            ShowStatus("未整理", pending ? "检测到待恢复的原始布局。请点击「恢复桌面」。" :
                info.AutoArrange ? "请先关闭 Windows 的「自动排列图标」。" :
                "整理后拖动标题栏，松开时图标会随窗口迁移。");
        });
    }

    private async void ArrangeClicked(object sender, RoutedEventArgs e)
    {
        if (busy || movement.InMoveLoop)
            return;
        await During("正在整理", "正在检查窗口容量并保存原始布局…", async () =>
        {
            var window = Native.WindowBounds(handle);
            var larger = await OnShell(() => manager.SuggestLargerWindow(window));
            if (larger is { } target && WindowState == WindowState.Normal)
            {
                if (!SetWindowPos(handle, 0, target.Left, target.Top, target.Width, target.Height, 0x0214))
                    throw new Win32Exception();
                await Dispatcher.InvokeAsync(() => { }, DispatcherPriority.Loaded);
                window = Native.WindowBounds(handle);
            }
            await ArrangeAt(window, first: true);
        });
    }

    private async Task ArrangeAt(PixelRect window, bool first, bool force = false)
    {
        int count = await OnShell(() => manager.Arrange(window, first, force));
        if (count >= 0)
            UpdateCount(count);
        arranged = manager.Pending;
        appliedBounds = arranged ? window : null;
        if (arranged && WindowState != WindowState.Minimized && Native.WindowBounds(handle) != window)
        {
            RequestReconcile();
            return;
        }
        SetOrganizedStatus();
    }

    private void SetOrganizedStatus()
    {
        if (arranged && WindowState != WindowState.Minimized)
            ShowStatus("桌面已整理完毕", "拖动标题栏时图标留在原处，松开鼠标后迁移。");
        else if (arranged)
            ShowStatus("未整理", "窗口已最小化，桌面图标可见。");
        else
            ShowStatus("未整理", "当前桌面没有需要整理的图标。");
    }

    private async void RestoreClicked(object sender, RoutedEventArgs e) => await Restore();

    private async Task<bool> Restore()
    {
        bool complete = false;
        await During("正在恢复", "正在匹配原始图标并核对坐标…", async () =>
        {
            arranged = false;
            appliedBounds = null;
            reconcileRequested = false;
            var result = await OnShell(manager.Restore);
            complete = result.Complete;
            ShowStatus(complete ? "恢复完成" : "操作失败", result.ToString());
            if (complete)
            {
                try { UpdateCount((await OnShell(manager.Inspect)).Count); }
                catch { Count.Text = "桌面图标 · —"; }
            }
        });
        return complete;
    }

    private async Task During(string status, string detail, Func<Task> operation)
    {
        if (busy)
            return;
        busy = true;
        ShowStatus(status, detail);
        UpdateButtons();
        slowOperation.Start();
        try { await operation(); }
        catch (Exception error)
        {
            arranged = false;
            appliedBounds = null;
            ShowStatus("操作失败", error.Message);
        }
        finally
        {
            slowOperation.Stop();
            busy = false;
            UpdateButtons();
            if (closeRequested)
            {
                closeRequested = false;
                _ = Dispatcher.BeginInvoke(new Action(Close));
            }
            else if (arranged && reconcileRequested)
                RequestReconcile();
        }
    }

    private void UpdateButtons()
    {
        try
        {
            bool pending = manager.Pending;
            ArrangeButton.IsEnabled = !busy && !pending;
            RestoreButton.IsEnabled = !busy && pending;
        }
        catch (Exception error)
        {
            ArrangeButton.IsEnabled = RestoreButton.IsEnabled = false;
            ShowStatus("操作失败", error.Message);
        }
    }

    protected override async void OnClosing(CancelEventArgs e)
    {
        base.OnClosing(e);
        if (closingApproved)
            return;
        e.Cancel = true;
        if (closeFlow)
            return;
        if (busy)
        {
            closeRequested = true;
            Detail.Text = "当前操作结束后将恢复桌面并关闭。";
            return;
        }

        closeFlow = true;
        // Leave the cancellable closing event before attempting a second Close().
        await Dispatcher.Yield(DispatcherPriority.Background);
        while (IsLoaded && !busy && !closingApproved)
        {
            string reason;
            try
            {
                if (!manager.Pending || await Restore())
                {
                    closingApproved = true;
                    Close();
                    return;
                }
                reason = Detail.Text;
            }
            catch (Exception error) { reason = error.Message; }

            var choice = MessageBox.Show(this,
                $"{reason}\n\n「是」重试恢复，「否」保留快照并退出，「取消」返回窗口。",
                "桌面布局仍待恢复", MessageBoxButton.YesNoCancel, MessageBoxImage.Warning);
            if (choice == MessageBoxResult.Cancel)
                break;
            if (choice == MessageBoxResult.No)
            {
                closingApproved = true;
                Close();
                return;
            }
        }
        closeFlow = false;
    }

    protected override void OnClosed(EventArgs e)
    {
        settle.Stop();
        slowOperation.Stop();
        source?.RemoveHook(WindowMessage);
        base.OnClosed(e);
    }

    private void ShowStatus(string title, string detail) => (Status.Text, Detail.Text) = (title, detail);
    private void UpdateCount(int count) => Count.Text = $"桌面图标 · {count}";

    private static Task<T> OnShell<T>(Func<T> work)
    {
        var result = new TaskCompletionSource<T>(TaskCreationOptions.RunContinuationsAsynchronously);
        var thread = new Thread(() =>
        {
            try { result.SetResult(work()); }
            catch (Exception error) { result.SetException(error); }
        }) { IsBackground = true, Name = "Desktop Cleaner Shell STA" };
        thread.SetApartmentState(ApartmentState.STA);
        thread.Start();
        return result.Task;
    }

    [DllImport("dwmapi")] private static extern int DwmSetWindowAttribute(nint window, int attribute, ref int value, int size);
    [DllImport("user32", SetLastError = true)]
    private static extern bool SetWindowPos(nint window, nint insertAfter, int x, int y, int width, int height, uint flags);
}
