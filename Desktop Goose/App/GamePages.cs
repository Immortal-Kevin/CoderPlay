using System.ComponentModel;
using System.Globalization;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Interop;
using System.Windows.Media;
using System.Windows.Shapes;
using DesktopGoose.Core;
using Forms = System.Windows.Forms;

namespace DesktopGoose.App;

internal sealed partial class Game
{
    private void ShowPage(string key, Window window)
    {
        if (pages.TryGetValue(key, out var previous))
            previous.Close();
        pages[key] = window;
        window.Closed += (_, _) => pages.Remove(key);
        window.Show();
        window.Activate();
    }

    private void Warehouse(long? parent = null, long? highlight = null)
    {
        var panel = PixelUi.Page("鹅蛋仓库", out var scroll);
        var filters = new WrapPanel();
        string[] status = ["活跃记录", "全部", "未孵化", "孵化中", "已暂停", "可破壳", "已孵化"];
        var filter = PixelUi.Pick(status, highlight.HasValue ? 1 : 0);
        var order = PixelUi.Pick(["最近产蛋", "亲代", "状态"], 0);
        filters.Children.Add(filter);
        filters.Children.Add(order);
        if (parent is long id)
            filters.Children.Add(PixelUi.Button($"亲代：{store.FindGoose(id)?.Name} ×", () => Warehouse()));
        panel.Children.Add(filters);
        var records = new StackPanel();
        panel.Children.Add(records);

        var window = PixelUi.Window("鹅蛋仓库", scroll);
        void Refresh()
        {
            records.Children.Clear();
            var geese = store.Family().ToDictionary(g => g.Id);
            IEnumerable<Egg> items = store.Eggs().Where(e => parent is null || parent == e.Parent);
            items = filter.SelectedIndex switch
            {
                0 => items.Where(e => e.Stage != HatchStage.COMPLETED),
                2 => items.Where(e => e.Stage == HatchStage.STORED),
                3 => items.Where(e => e.Stage == HatchStage.INCUBATING),
                4 => items.Where(e => e.Stage == HatchStage.PAUSED),
                5 => items.Where(e => e.Stage == HatchStage.READY),
                6 => items.Where(e => e.Stage == HatchStage.COMPLETED),
                _ => items
            };
            items = order.SelectedIndex switch
            {
                1 => items.OrderBy(e => geese[e.Parent].Name, StringComparer.CurrentCulture),
                2 => items.OrderBy(e => e.Stage), _ => items
            };
            if (inputLimited || !desktop && egg?.Stage == HatchStage.INCUBATING)
                records.Children.Add(PixelUi.Text("受保护或高权限应用可能限制输入计数。"));
            var activeId = egg?.Id;
            bool any = false;
            foreach (var item in items)
            {
                any = true;
                var row = new StackPanel { Margin = new Thickness(8, 6, 7, 6) };
                var head = new DockPanel();
                var picture = PixelUi.Image(PixelArt.Cracking(item.Kind == EggKind.Diamond, 0), 43);
                DockPanel.SetDock(picture, Dock.Left);
                head.Children.Add(picture);
                var laid = DateTimeOffset.FromUnixTimeSeconds(item.Laid).ToLocalTime();
                string kind = item.Kind == EggKind.Diamond ? "钻石蛋" : "普通蛋";
                head.Children.Add(PixelUi.Text($"{kind} #{item.Id} · {PixelUi.StageName(item.Stage)} · {item.Progress}/5000\n{laid:yyyy-MM-dd HH:mm} · {geese[item.Parent].Name}"));
                row.Children.Add(head);
                var actions = new WrapPanel();
                actions.Children.Add(PixelUi.Button("查看亲代", () => Family(item.Parent)));
                if (item.Stage == HatchStage.COMPLETED && item.Offspring is long offspring)
                    actions.Children.Add(PixelUi.Button("查看后代", () => Family(offspring)));
                if (item.Stage == HatchStage.STORED && activeId is null)
                    actions.Children.Add(PixelUi.Button("开始孵化", () => { StartHatch(item.Id); Refresh(); }));
                if (item.Stage == HatchStage.INCUBATING)
                    actions.Children.Add(PixelUi.Button("暂停孵化", () => { PauseHatch(); Refresh(); }));
                if (item.Stage == HatchStage.PAUSED)
                    actions.Children.Add(PixelUi.Button("继续孵化", () => { ResumeHatch(); Refresh(); }));
                if (item.Stage == HatchStage.READY)
                    actions.Children.Add(PixelUi.Text("点击桌面鹅窝里的蛋破壳。"));
                row.Children.Add(actions);
                var card = new Border { Child = row, Background = highlight == item.Id ? PixelUi.Accent : PixelUi.White,
                    BorderThickness = new Thickness(2), BorderBrush = PixelUi.Ink, Margin = new Thickness(0, 0, 0, 7) };
                records.Children.Add(card);
                if (highlight == item.Id)
                    card.Loaded += (_, _) => card.BringIntoView();
            }
            if (!any)
                records.Children.Add(PixelUi.Text("这里还没有鹅蛋。"));
        }
        filter.SelectionChanged += (_, _) => Refresh();
        order.SelectionChanged += (_, _) => Refresh();
        var refreshTimer = new System.Windows.Threading.DispatcherTimer { Interval = TimeSpan.FromSeconds(1) };
        Egg? displayed = egg;
        refreshTimer.Tick += (_, _) =>
        {
            if (displayed != egg)
            {
                displayed = egg;
                Refresh();
            }
        };
        window.Closed += (_, _) => refreshTimer.Stop();
        Refresh();
        ShowPage("warehouse", window);
        refreshTimer.Start();
    }

    private void Family(long? selected = null, bool tree = false)
    {
        var family = store.Family();
        var eggs = store.Eggs();
        var origins = eggs.Where(e => e.Offspring.HasValue).ToDictionary(e => e.Offspring!.Value);
        var panel = PixelUi.Page(tree ? "鹅家族树" : "鹅家族", out var scroll);
        panel.Children.Add(PixelUi.Button(tree ? "查看档案" : "查看家族树", () => Family(selected, !tree)));
        if (tree)
        {
            var view = new TreeView { Background = PixelUi.White, BorderBrush = PixelUi.Ink };
            var nodes = new Dictionary<long, TreeViewItem>();
            foreach (var member in family)
            {
                var node = new TreeViewItem { Header = PixelUi.Button(member.Name, () => Family(member.Id)), IsExpanded = true };
                nodes[member.Id] = node;
                if (origins.TryGetValue(member.Id, out var origin) && nodes.TryGetValue(origin.Parent, out var parent))
                    parent.Items.Add(node);
                else
                    view.Items.Add(node);
            }
            panel.Children.Add(view);
        }
        else
        {
            var list = PixelUi.Pick(family.Select(g => $"{g.Name} · {(g.Status == "resident" ? "当前饲养" : "已放生")} · #{g.Id}"),
                Math.Max(0, Array.FindIndex(family.ToArray(), g => g.Id == (selected ?? resident.Id))));
            panel.Children.Add(list);
            var body = new StackPanel();
            panel.Children.Add(body);
            void Detail()
            {
                if (list.SelectedIndex < 0)
                    return;
                var member = family[list.SelectedIndex];
                body.Children.Clear();
                body.Children.Add(PixelUi.Image(PixelArt.Goose(member.Look, Pose.Stand, 0, false), 108));
                var abilities = store.Abilities(member.Id);
                string abilityText = abilities.Count == 0 ? "尚未掌握" : string.Join("、", abilities.Select(PixelUi.AbilityName));
                var birth = DateTimeOffset.FromUnixTimeSeconds(member.Born).ToLocalTime();
                body.Children.Add(PixelUi.Text($"{member.Name} · {PixelUi.RarityName(member.Look.Rarity)}\n" +
                    $"{PixelUi.ColorName(member.Look)} · {PixelUi.TemperamentName(member.Temperament)}\n" +
                    $"特殊动作  {abilityText}\n出生  {birth:yyyy-MM-dd HH:mm}"));
                if (member.Released is long when)
                    body.Children.Add(PixelUi.Text($"放生  {DateTimeOffset.FromUnixTimeSeconds(when).ToLocalTime():yyyy-MM-dd HH:mm}"));
                if (origins.TryGetValue(member.Id, out var origin))
                {
                    body.Children.Add(PixelUi.Button($"查看亲代 {store.FindGoose(origin.Parent)?.Name}", () => Family(origin.Parent)));
                    body.Children.Add(PixelUi.Button($"查看出生鹅蛋 #{origin.Id}", () => Warehouse(null, origin.Id)));
                }
                var laid = eggs.Where(e => e.Parent == member.Id).ToArray();
                body.Children.Add(PixelUi.Button($"查看产蛋记录（{laid.Length}/5）", () => Warehouse(member.Id)));
                foreach (var child in laid.Where(e => e.Stage == HatchStage.COMPLETED && e.Offspring is not null))
                {
                    long childId = child.Offspring!.Value;
                    body.Children.Add(PixelUi.Button($"查看后代 {store.FindGoose(childId)?.Name}", () => Family(childId)));
                }
            }
            list.SelectionChanged += (_, _) => Detail();
            Detail();
        }
        ShowPage("family", PixelUi.Window("鹅家族", scroll));
    }

    private void OpenSettings()
    {
        var panel = PixelUi.Page("设置", out var scroll);
        var window = PixelUi.Window("设置", scroll, 565, 685);
        void Add(string label, UIElement control)
        {
            panel.Children.Add(PixelUi.Text(label));
            panel.Children.Add(control);
        }
        var name = PixelUi.Field(resident.Name);
        Add("鹅的名字", name);
        var scale = Number("鹅的大小（物理像素）", options.Size, 50, 300);
        var fps = PixelUi.Pick(["30 FPS", "60 FPS"], options.Fps == 60 ? 1 : 0);
        Add("帧率", fps);
        var energy = PixelUi.Pick(["安静", "正常", "混乱"], options.Energy);
        Add("行为强度", energy);
        var volume = Number("音量", options.Volume, 0, 100);
        var quiet = PixelUi.Check("夜间静音", options.QuietEnabled);
        panel.Children.Add(quiet);
        var from = PixelUi.Field(TimeLabel(options.QuietFrom));
        var to = PixelUi.Field(TimeLabel(options.QuietTo));
        Add("静音开始（HH:mm）", from);
        Add("静音结束（HH:mm）", to);
        var screens = Forms.Screen.AllScreens;
        var screen = PixelUi.Pick(screens.Select(s => s.DeviceName + (s.Primary ? " · 主显示器" : "")),
            Math.Max(0, Array.FindIndex(screens, s => s.DeviceName == WindowsDesktop.Selected(options.Monitor).DeviceName)));
        Add("活动显示器", screen);
        var message = PixelUi.Text("");
        var area = new WrapPanel();
        area.Children.Add(PixelUi.Button("清除局部范围", () =>
        {
            UpdateOptions(options with { Range = null });
            message.Text = "已恢复默认活动范围。";
        }));
        panel.Children.Add(area);
        var footprints = PixelUi.Check("显示脚印", options.Footprints);
        panel.Children.Add(footprints);
        var visits = PixelUi.Check("允许家族回访", options.Visits);
        panel.Children.Add(visits);
        var chance = Number("每日回访概率（%）", options.VisitChance, 1, 30);
        var duration = Number("回访时长（秒）", options.VisitSeconds, 10, 120);
        var skin = PixelUi.Check(diamondAvailable ? "使用钻石鹅窝" : "钻石鹅窝 · 放生钻石鹅后解锁", options.DiamondNest && diamondAvailable);
        skin.IsEnabled = diamondAvailable;
        var sparkle = PixelUi.Check("钻石鹅窝闪光", options.Sparkles);
        panel.Children.Add(skin);
        panel.Children.Add(sparkle);
        var memos = Enumerable.Range(0, 3).Select(i => PixelUi.Field(options.Memos.ElementAtOrDefault(i) ?? "")).ToArray();
        panel.Children.Add(PixelUi.Text("每日备忘录（凌晨清空，每条最多 80 字）"));
        foreach (var memo in memos)
        {
            memo.MaxLength = 80;
            panel.Children.Add(memo);
        }
        area.Children.Add(PixelUi.Button("重设局部范围", () => { if (Save()) SelectRange(); }));
        var buttons = new WrapPanel();
        buttons.Children.Add(PixelUi.Button("鹅蛋仓库", () => Warehouse()));
        buttons.Children.Add(PixelUi.Button("鹅家族", () => Family()));
        buttons.Children.Add(PixelUi.Button("存档维护", OpenBackups));
        panel.Children.Add(buttons);
        panel.Children.Add(PixelUi.Button("保存设置", () => Save()));
        panel.Children.Add(message);

        Slider Number(string label, int current, int min, int max)
        {
            var slider = new Slider { Minimum = min, Maximum = max, Value = current, TickFrequency = 1,
                IsSnapToTickEnabled = true, Width = 260, HorizontalAlignment = HorizontalAlignment.Left };
            var heading = PixelUi.Text($"{label}  {current}");
            slider.ValueChanged += (_, _) => heading.Text = $"{label}  {(int)slider.Value}";
            panel.Children.Add(heading);
            panel.Children.Add(slider);
            return slider;
        }

        bool Save()
        {
            try
            {
                string validName = Production.Name(name.Text);
                if (!ParseTime(from.Text, out int start) || !ParseTime(to.Text, out int end))
                    throw new ArgumentException("请输入 00:00–23:59 的时间。");
                string monitor = screens[screen.SelectedIndex].DeviceName;
                var updated = options with
                {
                    Size = (int)scale.Value, Fps = fps.SelectedIndex == 1 ? 60 : 30, Energy = energy.SelectedIndex,
                    Volume = (int)volume.Value, QuietEnabled = quiet.IsChecked == true, QuietFrom = start, QuietTo = end,
                    Monitor = monitor, Range = options.Monitor == monitor || (options.Monitor.Length == 0 && screens[screen.SelectedIndex].Primary) ? options.Range : null,
                    Visits = visits.IsChecked == true, VisitChance = (int)chance.Value, VisitSeconds = (int)duration.Value,
                    DiamondNest = skin.IsChecked == true && diamondAvailable, Sparkles = sparkle.IsChecked == true,
                    Footprints = footprints.IsChecked == true, MemoDay = store.LocalDate,
                    Memos = memos.Select(m => m.Text.Trim()).Where(text => text.Length > 0).ToArray()
                };
                store.Rename(validName);
                UpdateOptions(updated);
                SyncState();
                if (!options.Visits)
                    FinishVisit();
                nextVisitPlan = 0;
                message.Text = "设置已保存。";
                return true;
            }
            catch (ArgumentException e)
            {
                message.Text = e.Message;
                return false;
            }
        }
        ShowPage("settings", window);
    }

    private static string TimeLabel(int minutes) => new TimeOnly(minutes / 60, minutes % 60).ToString("HH:mm", CultureInfo.InvariantCulture);
    private static bool ParseTime(string text, out int minutes)
    {
        bool ok = TimeOnly.TryParseExact(text, "HH:mm", CultureInfo.InvariantCulture, DateTimeStyles.None, out var time);
        minutes = time.Hour * 60 + time.Minute;
        return ok;
    }

    private void OpenBackups()
    {
        var panel = PixelUi.Page("存档维护", out var scroll);
        var window = PixelUi.Window("存档维护", scroll, 535, 390);
        panel.Children.Add(PixelUi.Text(Program.SaveDirectory));
        var files = store.Backups().ToArray();
        var list = PixelUi.Pick(files.Select(f => System.IO.Path.GetFileName(f)[..15]), files.Length > 0 ? 0 : -1);
        panel.Children.Add(list);
        var status = PixelUi.Text(string.IsNullOrEmpty(backupError) ? "自动保留最近七份校验通过的备份。" : backupError);
        panel.Children.Add(status);
        panel.Children.Add(PixelUi.Button("立即备份", () => { FlushInput(); TryBackup(); OpenBackups(); }));
        var restore = PixelUi.Button("恢复所选备份", () =>
        {
            if (list.SelectedIndex < 0)
                return;
            if (MessageBox.Show(window, "恢复后将读取备份中的家族与进度。当前存档会先另存一份。", "恢复备份",
                MessageBoxButton.YesNo, MessageBoxImage.Warning) != MessageBoxResult.Yes)
                return;
            try
            {
                FlushInput();
                store.Restore(files[list.SelectedIndex]);
                CloseDecision();
                FinishVisit();
                scheduled = null;
                queuedEggs = 0;
                options = store.LoadSettings();
                SyncState();
                if (egg?.Stage == HatchStage.RELEASE)
                    PrepareRelease();
                ConfigureArea(true);
                diamondAvailable = store.DiamondUnlocked;
                foreach (var page in pages.Values.ToArray())
                    page.Close();
                nextSystem = 0;
            }
            catch (Exception error) when (error is InvalidOperationException or System.IO.IOException or UnauthorizedAccessException)
            {
                status.Text = error.Message;
            }
        });
        restore.IsEnabled = files.Length > 0;
        panel.Children.Add(restore);
        ShowPage("backups", window);
    }

    private void SelectRange()
    {
        var screen = WindowsDesktop.Selected(options.Monitor);
        var work = screen.WorkingArea;
        var full = screen.Bounds;
        var canvas = new Canvas { Background = new SolidColorBrush(Color.FromArgb(170, 23, 29, 43)) };
        var selection = new Rectangle { Stroke = PixelUi.Accent, StrokeThickness = 3, Fill = new SolidColorBrush(Color.FromArgb(75, 255, 204, 102)) };
        canvas.Children.Add(selection);
        var hint = new TextBlock { Text = "拖出活动范围（至少 50 × 50 像素）　Esc 关闭", FontSize = 21,
            Foreground = PixelUi.White, Margin = new Thickness(20) };
        canvas.Children.Add(hint);
        var window = new Window { Title = "Desktop Goose · 活动范围", AllowDrop = false, Content = canvas,
            AllowsTransparency = true, Background = Brushes.Transparent, WindowStyle = WindowStyle.None,
            ResizeMode = ResizeMode.NoResize, ShowInTaskbar = false, Topmost = true, Width = 400, Height = 300 };
        var helper = new WindowInteropHelper(window);
        nint handle = helper.EnsureHandle();
        var rect = new Rect(work.X, work.Y, work.Width, work.Height);
        WindowsDesktop.Place(handle, rect);
        Point? origin = null;
        window.KeyDown += (_, e) => { if (e.Key == Key.Escape) window.Close(); };
        canvas.MouseLeftButtonDown += (_, _) =>
        {
            origin = WindowsDesktop.Cursor;
            canvas.CaptureMouse();
        };
        canvas.MouseMove += (_, _) =>
        {
            if (origin is not Point a)
                return;
            Point b = WindowsDesktop.Cursor;
            Point first = canvas.PointFromScreen(new Point(Math.Min(a.X, b.X), Math.Min(a.Y, b.Y)));
            Point last = canvas.PointFromScreen(new Point(Math.Max(a.X, b.X), Math.Max(a.Y, b.Y)));
            Canvas.SetLeft(selection, first.X);
            Canvas.SetTop(selection, first.Y);
            selection.Width = last.X - first.X;
            selection.Height = last.Y - first.Y;
        };
        canvas.MouseLeftButtonUp += (_, _) =>
        {
            if (origin is not Point a)
                return;
            origin = null;
            canvas.ReleaseMouseCapture();
            var picked = new Rect(a, WindowsDesktop.Cursor);
            picked.Intersect(rect);
            if (picked.IsEmpty || picked.Width < 50 || picked.Height < 50)
            {
                hint.Text = "请拖出至少 50 × 50 像素的范围。";
                return;
            }
            var range = new RangeBox((picked.X - full.X) / full.Width, (picked.Y - full.Y) / full.Height,
                picked.Width / full.Width, picked.Height / full.Height);
            UpdateOptions(options with { Monitor = screen.DeviceName, Range = range });
            window.Close();
        };
        ShowPage("range", window);
        WindowsDesktop.Place(handle, rect);
    }
}
