using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Interop;
using System.Windows.Threading;
using DesktopGoose.Core;
using Forms = System.Windows.Forms;

namespace DesktopGoose.App;

internal sealed partial class Game : IDisposable
{
    private readonly GameStore store;
    private readonly IClock clock = new GameClock();
    private readonly IRandomSource random = new GameRandom();
    private readonly Stopwatch uptime = Stopwatch.StartNew();
    private readonly DispatcherTimer timer;
    private readonly SpriteWindow goose = new("Desktop Goose · 鹅");
    private readonly SpriteWindow nest = new("Desktop Goose · 鹅窝");
    private readonly SpriteWindow guest = new("Desktop Goose · 访客", true);
    private readonly SpriteWindow shell = new("Desktop Goose · 破壳", true);
    private readonly Honks audio = new();
    private readonly List<(SpriteWindow Window, Point At, double Born, bool Left)> tracks = [];
    private readonly List<(Window Window, double Expires)> notes = [];
    private readonly Dictionary<string, Window> pages = [];
    private IInputCounter? input;
    private Forms.NotifyIcon? tray;
    private System.Drawing.Icon? icon;
    private Forms.ContextMenuStrip? trayMenu;
    private Settings options;
    private Goose resident = null!;
    private Egg? egg;
    private bool disposed, started, visual, desktop, holding, lifted, closingDecision, inputLimited;
    private Point position, heading = new(1, 0), dragOffset, down, nearAt, nestPreview;
    private Rect bounds, display;
    private SpriteWindow? captured;
    private Pose action = Pose.Walk;
    private bool left, returning, visitHint;
    private int queuedEggs, operations;
    private double Now => uptime.Elapsed.TotalSeconds;
    private double lastTick, nextSystem, nextAction, actionUntil, nextTrack, nextNote, downAt,
        nearSince = -1, avoidUntil, lastClick = -100, hoveredUntil, crackStart = -1, releaseStart = -1,
        nextVisitPlan, guestStart;
    private Visit? scheduled, currentVisit;
    private Goose? visitor, leaving, staying;
    private Window? decision;
    private int size => Math.Max(1, Math.Min(options.Size, (int)Math.Min(bounds.Width, bounds.Height)));
    private DateTime LocalNow => TimeZoneInfo.ConvertTime(clock.Now, clock.Zone).DateTime;
    private static readonly string[] Jokes = [
        "这段代码能跑。先别告诉它。", "提交说明：修正了一只鹅。",
        "缓存失效、命名，以及鹅为什么站在这里。", "我找到了边界条件。它在屏幕右边。",
        "今天的站会改成走路。嘎。", "我的单元测试只有一个断言：嘎。"
    ];

    public Game(string path)
    {
        store = new GameStore(path, clock, random);
        options = store.LoadSettings();
        timer = new DispatcherTimer(DispatcherPriority.Background);
        timer.Tick += (_, _) => Tick();
        ConfigurePointer(goose);
        ConfigurePointer(nest);
    }

    public bool Start()
    {
        if (store.Resident is not Goose found)
        {
            var panel = PixelUi.Page("给你的鹅取名字", out var scroll);
            panel.Children.Add(PixelUi.Image(PixelArt.Goose(new(Rarity.Common, 0, -1, 0), Pose.Stand, 0, false), 92));
            var name = PixelUi.Field();
            var message = PixelUi.Text("");
            panel.Children.Add(name);
            panel.Children.Add(message);
            var window = PixelUi.Window("给你的鹅取名字", scroll, 410, 340);
            var accept = PixelUi.Button("带鹅回家", () =>
            {
                try { store.Initialize(name.Text); window.DialogResult = true; }
                catch (ArgumentException error) { message.Text = error.Message; }
            });
            accept.IsDefault = true;
            panel.Children.Add(accept);
            window.Loaded += (_, _) => name.Focus();
            if (window.ShowDialog() != true)
                return false;
            found = store.Resident!;
        }

        resident = found;
        store.Recover();
        queuedEggs = store.SettleProduction();
        egg = store.ActiveEgg;
        try
        {
            input = new RawInput();
            input.Operation += RecordOperation;
            input.MousePressed += NearbyClick;
        }
        catch (System.ComponentModel.Win32Exception) { inputLimited = true; }
        tray = new Forms.NotifyIcon { Visible = true };
        tray.DoubleClick += (_, _) => UpdateOptions(options with { Hidden = !options.Hidden });
        SyncState();
        ConfigureArea(true);
        position = Clamp(new Point(bounds.Right - size - 18, bounds.Bottom - size - 18));
        nextAction = Now + RandomActionDelay();
        nextNote = Now + RandomNoteDelay();
        if (egg?.Stage == HatchStage.RELEASE)
            PrepareRelease();
        TryBackup();
        started = true;
        SetTimer(30);
        timer.Start();
        Tick();
        return true;
    }

    private void SetTimer(int fps)
    {
        var interval = TimeSpan.FromSeconds(1d / fps);
        if (timer.Interval != interval)
            timer.Interval = interval;
    }

    private void Tick()
    {
        double t = Now;
        double delta = Math.Clamp(t - lastTick, 0, .12);
        lastTick = t;
        if (t >= nextSystem)
        {
            nextSystem = t + 1;
            SystemTick(t);
        }
        if (egg?.Stage is HatchStage.CHOOSE or HatchStage.NAME_NEW)
            ShowDecision();
        if (!visual)
        {
            SetTimer(8);
            return;
        }

        SetTimer(options.Paused || action is Pose.Sleep or Pose.Rest or Pose.Sit
            ? egg?.Stage is HatchStage.RELEASE or HatchStage.CRACKING || lifted || visitor is not null ? options.Fps : 12
            : options.Fps);
        if (holding && !WindowsDesktop.LeftDown)
            CompletePointer();
        TrackDrag(t);
        DrawNest(t);
        if (egg?.Stage == HatchStage.CRACKING)
        {
            DrawCrack(t);
            return;
        }
        if (egg?.Stage == HatchStage.RELEASE)
        {
            DrawRelease(t);
            return;
        }

        AdvanceGoose(t, delta);
        DrawGoose(t);
        DrawVisit(t, delta);
        DrawTracks(t);
        DrawNotes(t);
    }

    private void SystemTick(double t)
    {
        var previous = visual;
        var prevDesktop = desktop;
        var foreground = WindowsDesktop.Foreground();
        desktop = foreground.Desktop;
        visual = !options.Hidden && !foreground.Fullscreen && !WindowsDesktop.PresentationFullscreen();
        ConfigureArea(false);
        if (previous && !visual)
        {
            if (captured is not null)
                EndDrag();
            if (egg?.Stage == HatchStage.RELEASE)
                releaseStart = -1;
            if (egg?.Stage == HatchStage.CRACKING)
                crackStart = t;
            HideSprites();
        }
        if (!previous && visual)
        {
            avoidUntil = t + .3;
            if (egg?.Stage == HatchStage.CRACKING)
                crackStart = t;
        }
        if (!visual && prevDesktop != desktop)
            nearSince = -1;

        queuedEggs += store.SettleProduction();
        FlushInput();
        string day = store.LocalDate;
        if (options.MemoDay != day && options.Memos.Length > 0)
            UpdateOptions(options with { MemoDay = day, Memos = [] });
        if (t >= nextVisitPlan)
        {
            nextVisitPlan = t + 12;
            scheduled = store.PlanVisit(options);
            string localDay = store.LocalDate;
            if (backupDay != localDay)
                TryBackup();
        }
        if (visitor is not null && t - guestStart >= options.VisitSeconds)
            FinishVisit();
        if (visual && scheduled is Visit visit && visit.Due <= clock.Now.ToUnixTimeSeconds() &&
            currentVisit is null && egg?.Stage is not (HatchStage.CRACKING or HatchStage.CHOOSE or HatchStage.NAME_NEW or HatchStage.RELEASE) &&
            !holding && store.BeginVisit(visit))
        {
            currentVisit = visit;
            visitor = store.FindGoose(visit.Guest);
            guestStart = t;
            visitRelationship = Relationship(visit.Guest);
            visitorPosition = new Point(bounds.Left, bounds.Bottom - size);
            visitHint = false;
            scheduled = null;
        }
    }

    private void ConfigureArea(bool force)
    {
        var screen = WindowsDesktop.Selected(options.Monitor);
        var work = screen.WorkingArea;
        var full = screen.Bounds;
        display = new Rect(full.X, full.Y, full.Width, full.Height);
        var area = new Rect(work.X, work.Y, work.Width, work.Height);
        Rect desired = area;
        if (options.Range is RangeBox box)
        {
            desired = new Rect(display.X + box.X * display.Width, display.Y + box.Y * display.Height,
                box.Width * display.Width, box.Height * display.Height);
            desired.Intersect(area);
            if (desired.IsEmpty || desired.Width < 50 || desired.Height < 50)
                desired = area;
        }
        else if (!desktop && egg is null)
        {
            double w = Math.Min(area.Width, Math.Max(options.Size + 12, area.Width * .28));
            double h = Math.Min(area.Height, Math.Max(options.Size + 12, area.Height * .26));
            desired = new Rect(area.Right - w, area.Bottom - h, w, h);
        }
        if (force || desired != bounds)
        {
            bounds = desired;
            position = Clamp(position);
        }
    }

    private Rect At(Point p) => new(p.X, p.Y, size, size);
    private Point Clamp(Point p) => new(Math.Clamp(p.X, bounds.Left, Math.Max(bounds.Left, bounds.Right - size)),
        Math.Clamp(p.Y, bounds.Top, Math.Max(bounds.Top, bounds.Bottom - size)));
    private Point NestPoint => Clamp(new Point(display.X + egg!.NestX * display.Width, display.Y + egg.NestY * display.Height));
    private Point Relative(Point p) => new((p.X - display.X) / display.Width, (p.Y - display.Y) / display.Height);
    private int RandomActionDelay() => 30 + random.Next(61);
    private int RandomNoteDelay() => 300 + random.Next(601);

    private void RecordOperation()
    {
        if (egg?.Stage == HatchStage.INCUBATING)
            operations = Math.Min(Production.HatchTarget - egg.Progress, operations + 1);
        if (egg is not null && operations > 0 && egg.Progress + operations >= Production.HatchTarget)
            goose.Dispatcher.BeginInvoke(FlushInput);
    }

    private void FlushInput()
    {
        if (operations == 0 || egg is null)
            return;
        store.Count(egg.Id, operations);
        operations = 0;
        var updated = store.ActiveEgg;
        if (updated?.Stage != egg.Stage)
            SyncState();
        else
            egg = updated;
    }

    private void SyncState()
    {
        var old = resident;
        var oldStage = egg?.Stage;
        resident = store.Resident!;
        egg = store.ActiveEgg;
        if (input is not null)
        {
            try { input.CountsKeyboard = egg?.Stage == HatchStage.INCUBATING; }
            catch (System.ComponentModel.Win32Exception) { inputLimited = true; }
        }
        if (oldStage != egg?.Stage || old?.Id != resident.Id || trayMenu is null)
            SetTrayIcon();
    }

    private void NearbyClick(Point p)
    {
        if (!visual || options.Paused || holding || PriorityHatch || goose.Distance(p) > 80)
            return;
        double t = Now;
        if (goose.Distance(p) == 0)
            return; // A body click is resolved on mouse-up after the hold decision.
        ReactClick(t, p);
    }

    private void ReactClick(double t, Point p)
    {
        Play(t - lastClick < .55 ? Honk.Startled : Honk.Normal);
        if (t - lastClick < .55)
            Flee(p, Pose.Run, 2.4);
        else
            Flee(p, Pose.Startle, .45);
        lastClick = t;
    }

    private bool PriorityHatch => egg?.Stage is HatchStage.INCUBATING or HatchStage.READY or
        HatchStage.CRACKING or HatchStage.CHOOSE or HatchStage.NAME_NEW or HatchStage.RELEASE;
    private bool Sitting => egg?.Stage is HatchStage.INCUBATING or HatchStage.READY;

    private void Flee(Point p, Pose pose, double duration)
    {
        var away = (position + new Vector(size / 2d, size / 2d)) - p;
        if (away.Length < 1)
            away = new Vector(position.X < bounds.Left + bounds.Width / 2 ? 1 : -1, 0);
        away.Normalize();
        heading = new Point(away.X, away.Y);
        avoidUntil = Now + .85;
        SetAction(pose, duration);
    }

    private void SetAction(Pose value, double seconds)
    {
        action = value;
        actionUntil = Now + seconds;
    }

    private void AdvanceGoose(double t, double delta)
    {
        if (holding)
            return;
        if (egg?.Stage is HatchStage.CHOOSE or HatchStage.NAME_NEW)
        {
            action = Pose.Sit;
            return;
        }
        if (action == Pose.Dizzy && t < actionUntil)
            return;
        if (Sitting)
        {
            var target = NestPoint + new Vector(0, -size * .08);
            target = Clamp(target);
            if (returning || (target - position).Length > 2)
            {
                returning = GoToward(target, Math.Max(180, size * 2.4), delta);
                action = returning ? Pose.Run : Pose.Sit;
            }
            else
                action = Pose.Sit;
            return;
        }
        if (options.Paused)
            return;

        if (queuedEggs > 0 && t >= actionUntil)
        {
            queuedEggs--;
            SetAction(Pose.Lay, 1.2);
            Play(Honk.Lay);
        }
        if (t >= actionUntil)
        {
            uint idle = WindowsDesktop.IdleMilliseconds();
            if (idle >= 120000)
                action = Pose.Sleep;
            else if (idle >= 30000)
                action = Pose.Rest;
            else if (action != Pose.Walk)
                action = Pose.Walk;

            if (t >= nextAction && action == Pose.Walk)
                RandomAction(t);
        }

        if (t >= avoidUntil && action is Pose.Walk or Pose.Observe or Pose.Stand)
        {
            Point pointer = WindowsDesktop.Cursor;
            double distance = goose.Distance(pointer);
            if (distance is > 0 and <= 50)
            {
                Flee(pointer, Pose.Startle, .48);
                nearSince = -1;
            }
            else if (distance is > 50 and <= 100)
            {
                if (nearSince < 0 || (pointer - nearAt).Length > 8)
                {
                    nearSince = t;
                    nearAt = pointer;
                }
                if (t - nearSince >= 2 && t >= hoveredUntil)
                {
                    SetAction(Pose.Observe, 1.3);
                    hoveredUntil = t + 4;
                }
                else if (t - nearSince < 2)
                    action = Pose.Stand;
            }
            else
                nearSince = -1;
        }

        if (action is not (Pose.Walk or Pose.Run or Pose.Startle or Pose.Slide or Pose.Backwards))
            return;
        double pace = action switch
        {
            Pose.Run => size * 2.5, Pose.Startle => size * 3.0, Pose.Slide => size * 1.3,
            Pose.Backwards => size * .55, _ => size * (.44 + .15 * Math.Sin(t * .87))
        };
        var projected = position + new Vector(heading.X, heading.Y) * (pace * delta);
        var legal = Clamp(projected);
        if ((projected - legal).Length > .1)
        {
            if (action is Pose.Walk or Pose.Run && random.Next(8) == 0)
                SetAction(Pose.Dizzy, 2);
            else if (action == Pose.Walk)
                SetAction(Pose.Turn, .22);
            heading = new Point(projected.X == legal.X ? heading.X : -heading.X,
                projected.Y == legal.Y ? heading.Y : -heading.Y);
        }
        left = action == Pose.Backwards ? heading.X > 0 : heading.X < 0;
        position = legal;
    }

    private bool GoToward(Point target, double speed, double delta)
    {
        Vector line = target - position;
        if (line.Length <= Math.Max(1, speed * delta))
        {
            position = target;
            return false;
        }
        left = line.X < 0;
        line.Normalize();
        position = Clamp(position + line * (speed * delta));
        return true;
    }

    private void RandomAction(double t)
    {
        nextAction = t + RandomActionDelay();
        store.UnlockAbility(resident.Id);
        var abilities = store.Abilities(resident.Id);
        if (abilities.Count > 0 && random.Next(4) == 0)
        {
            var pose = (Pose)((int)Pose.Spin + (int)abilities[random.Next(abilities.Count)]);
            SetAction(pose, pose == Pose.Slide ? 1.4 : 2);
            return;
        }
        if (random.Next(3) > options.Energy)
            return;
        Pose bias = resident.Temperament switch
        {
            Temperament.Lazy => Pose.Rest, Temperament.Shy => Pose.Observe,
            Temperament.Lively => Pose.Dance, _ => Pose.Run
        };
        Pose[] choices = [Pose.Fall, Pose.Sneeze, Pose.Dance, Pose.Run, Pose.Stand, bias, bias];
        var next = choices[random.Next(choices.Length)];
        if (next == Pose.Run)
            Play(Honk.Normal);
        SetAction(next, next == Pose.Rest ? 5 : 1.3);
    }

    private void DrawGoose(double t)
    {
        var pose = lifted ? Pose.Drag : action;
        double rate = pose is Pose.Sleep or Pose.Rest ? 3 : pose is Pose.Run or Pose.Drag ? 16 : 10;
        int frame = (int)(t * rate) % 8;
        goose.Display(PixelArt.Goose(resident.Look, pose, frame, left), At(position));
    }

    private void DrawNest(double t)
    {
        if (egg is null)
        {
            nest.Hide();
            return;
        }
        bool diamond = options.DiamondNest && diamondAvailable;
        int glow = diamond && options.Sparkles ? 1 + (int)(t * 5) % 6 : 0;
        var at = captured == nest && lifted ? nestPreview : NestPoint;
        nest.Display(PixelArt.Nest(diamond, true, egg.Stage == HatchStage.READY, glow,
            egg.Kind == EggKind.Diamond), At(at));
    }

    private void ConfigurePointer(SpriteWindow window)
    {
        window.PreviewMouseLeftButtonDown += (_, e) =>
        {
            if (!visual || egg?.Stage is HatchStage.CRACKING or HatchStage.CHOOSE or HatchStage.NAME_NEW or HatchStage.RELEASE)
                return;
            captured = window;
            down = WindowsDesktop.Cursor;
            downAt = Now;
            dragOffset = new Point(down.X - window.Pixels.X, down.Y - window.Pixels.Y);
            holding = true;
            lifted = false;
            e.Handled = true;
        };
        window.PreviewMouseLeftButtonUp += (_, e) =>
        {
            if (captured != window)
                return;
            CompletePointer();
            e.Handled = true;
        };
        window.PreviewMouseRightButtonUp += (_, e) =>
        {
            var menu = new ContextMenu { PlacementTarget = window };
            foreach (var (label, action) in MenuActions())
            {
                var item = new MenuItem { Header = label };
                item.Click += (_, _) => action();
                menu.Items.Add(item);
            }
            menu.IsOpen = true;
            e.Handled = true;
        };
    }

    private void CompletePointer()
    {
        var window = captured;
        bool wasLifted = lifted;
        EndDrag();
        if (wasLifted || window is null || (WindowsDesktop.Cursor - down).Length > 12)
            return;
        if (window == nest && egg?.Stage == HatchStage.READY)
        {
            var p = WindowsDesktop.Cursor;
            var r = nest.Pixels;
            double x = (p.X - r.X) * 64 / r.Width;
            double y = (p.Y - r.Y) * 64 / r.Height;
            if (Math.Pow((x - 39) / 8, 2) + Math.Pow((y - 35) / 11, 2) <= 1)
                Crack();
        }
        else if (window == nest && egg?.Stage == HatchStage.PAUSED)
            ResumeHatch();
        else if (window == goose && !options.Paused && !PriorityHatch)
            ReactClick(Now, down);
    }

    private void TrackDrag(double t)
    {
        if (captured is null || !holding || t - downAt < .35)
            return;
        if (!lifted && captured == goose)
            Play(Honk.Protest);
        lifted = true;
        Point pointer = WindowsDesktop.Cursor;
        Point target = Clamp(new Point(pointer.X - dragOffset.X, pointer.Y - dragOffset.Y));
        if (captured == goose)
            position = target;
        else
            nestPreview = target;
    }

    private void EndDrag()
    {
        var target = captured;
        captured = null;
        holding = false;
        if (!lifted)
            return;
        lifted = false;
        if (target == nest && egg is not null)
        {
            Point p = Relative(nestPreview);
            store.MoveNest(egg.Id, p.X, p.Y);
            egg = store.ActiveEgg;
        }
        else
            SetAction(Pose.Dizzy, 2);
        returning = Sitting;
    }

    private void Play(Honk sound)
    {
        try { audio.Play(sound, options, LocalNow); }
        catch (InvalidOperationException) { } // Machines with no playback device can still run the pet.
    }

    private string backupDay = "";
    private bool diamondAvailable;
    private void TryBackup()
    {
        diamondAvailable = store.DiamondUnlocked;
        backupDay = store.LocalDate;
        try { store.Backup(); }
        catch (Exception e) when (e is System.IO.IOException or UnauthorizedAccessException or InvalidOperationException)
        {
            backupError = e.Message;
            return;
        }
        backupError = "";
    }

    private string backupError = "";

    private void UpdateOptions(Settings next)
    {
        store.SaveSettings(next);
        options = next;
        ConfigureArea(true);
        nextSystem = 0;
    }

    private void SetTrayIcon()
    {
        if (tray is null)
            return;
        var current = new System.Drawing.Bitmap(32, 32);
        var pixels = new byte[64 * 64 * 4];
        PixelArt.Goose(resident.Look, Pose.Stand, 0, false).Bitmap.CopyPixels(pixels, 256, 0);
        for (int y = 0; y < 32; y++)
            for (int x = 0; x < 32; x++)
            {
                int i = y * 512 + x * 8;
                if (egg?.Stage == HatchStage.READY && x >= 24 && y <= 7)
                    current.SetPixel(x, y, System.Drawing.Color.FromArgb(255, 253, 194, 65));
                else
                    current.SetPixel(x, y, System.Drawing.Color.FromArgb(pixels[i + 3], pixels[i + 2], pixels[i + 1], pixels[i]));
            }
        nint handle = current.GetHicon();
        var next = (System.Drawing.Icon)System.Drawing.Icon.FromHandle(handle).Clone();
        DestroyIcon(handle);
        current.Dispose();
        tray.Icon = next;
        tray.Text = egg?.Stage == HatchStage.READY ? "Desktop Goose · 鹅蛋可以破壳" : "Desktop Goose";
        icon?.Dispose();
        icon = next;

        var menu = new Forms.ContextMenuStrip();
        menu.Opening += (_, _) =>
        {
            while (menu.Items.Count > 0)
            {
                var oldItem = menu.Items[0];
                menu.Items.RemoveAt(0);
                oldItem.Dispose();
            }
            foreach (var (label, execute) in MenuActions())
                menu.Items.Add(label, null, (_, _) => execute());
        };
        if (trayMenu is null)
        {
            trayMenu = menu;
            tray.ContextMenuStrip = menu;
        }
        else
            menu.Dispose();
    }

    private IEnumerable<(string, Action)> MenuActions()
    {
        yield return ("鹅蛋仓库", () => Warehouse());
        yield return ("鹅家族", () => Family());
        yield return ("开始 / 继续孵化", ResumeHatch);
        yield return ("暂停孵化", PauseHatch);
        yield return ("重设活动范围", SelectRange);
        yield return (options.Paused ? "继续鹅的活动" : "暂停鹅的活动", () => UpdateOptions(options with { Paused = !options.Paused }));
        yield return ("设置", OpenSettings);
        yield return (options.Hidden ? "显示鹅" : "隐藏鹅", () => UpdateOptions(options with { Hidden = !options.Hidden }));
        yield return ("退出", Exit);
    }

    private void Exit()
    {
        Dispose();
        Application.Current.Shutdown();
    }

    private void HideSprites()
    {
        goose.Hide(); nest.Hide(); guest.Hide(); shell.Hide();
        foreach (var item in tracks) item.Window.Hide();
        foreach (var item in notes) item.Window.Hide();
    }

    public void Dispose()
    {
        if (disposed)
            return;
        disposed = true;
        timer.Stop();
        closingDecision = true;
        try
        {
            FlushInput();
            if (started)
                store.SettleProduction();
        }
        finally
        {
            try { input?.Dispose(); }
            finally
            {
                tray?.Dispose();
                trayMenu?.Dispose();
                icon?.Dispose();
                audio.Dispose();
                goose.Close(); nest.Close(); guest.Close(); shell.Close();
                foreach (var item in tracks) item.Window.Close();
                foreach (var item in notes) item.Window.Close();
                foreach (var page in pages.Values.ToArray()) page.Close();
                decision?.Close();
                store.Dispose();
            }
        }
    }

    [DllImport("user32.dll")] private static extern bool DestroyIcon(nint icon);
}
