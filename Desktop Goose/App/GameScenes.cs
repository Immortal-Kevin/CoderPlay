using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using DesktopGoose.Core;

namespace DesktopGoose.App;

internal sealed partial class Game
{
    private Point visitorPosition;
    private enum Kinship { Parent, Ancestor, Other }
    private Kinship visitRelationship;

    private void ResumeHatch()
    {
        FlushInput();
        if (egg?.Stage == HatchStage.PAUSED)
        {
            store.Resume(egg.Id);
            returning = true;
            SyncState();
        }
        else if (egg is null)
            Warehouse();
        else if (egg.Stage is HatchStage.CHOOSE or HatchStage.NAME_NEW)
            ShowDecision();
        else
            Warehouse();
    }

    private void PauseHatch()
    {
        FlushInput();
        if (egg?.Stage != HatchStage.INCUBATING)
            return;
        store.Pause(egg.Id);
        returning = false;
        SyncState();
    }

    private void StartHatch(long id)
    {
        var start = Relative(position);
        if (!store.Start(id, start.X, start.Y))
            return;
        SyncState();
        TryBackup();
    }

    private void Crack()
    {
        if (egg?.Stage != HatchStage.READY || !visual)
            return;
        if (store.Crack(egg.Id) is null)
            return;
        FinishVisit();
        crackStart = Now;
        SyncState();
        TryBackup();
    }

    private Goose? revealed;
    private void DrawCrack(double t)
    {
        revealed ??= store.FindGoose(egg!.Offspring!.Value)!;
        double elapsed = t - crackStart;
        var at = NestPoint;
        int frame = Math.Clamp((int)(elapsed * 4), 0, 7);
        goose.Display(PixelArt.Goose(resident.Look, Pose.Observe, frame, left), At(position));
        shell.Display(PixelArt.Cracking(egg!.Kind == EggKind.Diamond, frame), At(at));
        if (elapsed > 1.0)
        {
            guest.Opacity = Math.Min(1, (elapsed - 1) / .9);
            var head = Clamp(at + new Vector(size * .45, -size * .65));
            guest.Display(PixelArt.Goose(revealed.Look, Pose.Startle, frame, true), At(head));
        }
        if (elapsed < 2.4)
            return;
        guest.Opacity = 1;
        guest.Hide();
        shell.Hide();
        revealed = null;
        store.FinishCrack(egg.Id);
        SyncState();
    }

    private void ShowDecision()
    {
        if (decision is not null || egg is null)
            return;
        long id = egg.Id;
        var choice = store.Choice(id);
        var chick = store.FindGoose(choice.Offspring)!;
        bool choose = egg.Stage == HatchStage.CHOOSE;
        string caption = choose ? "留下哪只鹅？" : "给新鹅取名字";
        var panel = PixelUi.Page(caption, out var scroll);
        var window = PixelUi.Window(caption, scroll, 520, choose ? 430 : 470);
        decision = window;
        window.Closing += (_, e) => e.Cancel = !closingDecision && !disposed;
        window.Closed += (_, _) => decision = null;
        if (choose)
        {
            panel.Children.Add(PixelUi.Text("另一只鹅会正式放生，之后仍可能回访。两只鹅都会留下家族档案。"));
            var cards = new WrapPanel();
            cards.Children.Add(ChoiceCard(resident, resident.Name, () => PickResident(id, resident.Id)));
            cards.Children.Add(ChoiceCard(chick, "新鹅", () => PickResident(id, chick.Id)));
            panel.Children.Add(cards);
        }
        else
        {
            panel.Children.Add(PixelUi.Image(PixelArt.Goose(chick.Look, Pose.Stand, 0, false), 88));
            var name = PixelUi.Field();
            var error = PixelUi.Text("");
            panel.Children.Add(name);
            var choices = store.Abilities(egg.Parent);
            var inheritance = PixelUi.Pick(choices.Select(PixelUi.AbilityName), -1);
            if (choices.Count > 0)
            {
                panel.Children.Add(PixelUi.Text("从亲代继承一项特殊动作"));
                panel.Children.Add(inheritance);
            }
            var confirm = PixelUi.Button("确认并告别", () =>
            {
                try
                {
                    Ability? selected = inheritance.SelectedIndex >= 0 ? choices[inheritance.SelectedIndex] : null;
                    store.NameChild(id, name.Text, selected);
                    CloseDecision();
                    SyncState();
                    PrepareRelease();
                }
                catch (ArgumentException ex) { error.Text = ex.Message; }
            });
            confirm.IsDefault = true;
            panel.Children.Add(confirm);
            panel.Children.Add(error);
            window.Loaded += (_, _) => name.Focus();
        }
        panel.Children.Add(PixelUi.Button("退出游戏并保存", Exit));
        window.Show();
        window.Activate();
    }

    private StackPanel ChoiceCard(Goose candidate, string label, Action choose)
    {
        var panel = new StackPanel { Width = 190, Margin = new Thickness(0, 6, 8, 6) };
        panel.Children.Add(PixelUi.Image(PixelArt.Goose(candidate.Look, Pose.Stand, 0, false), 108));
        panel.Children.Add(PixelUi.Text($"{label} · {PixelUi.RarityName(candidate.Look.Rarity)}\n{PixelUi.ColorName(candidate.Look)}"));
        panel.Children.Add(PixelUi.Button($"留下{label}", choose));
        return panel;
    }

    private void PickResident(long id, long chosen)
    {
        store.Choose(id, chosen);
        CloseDecision();
        SyncState();
        ShowDecision();
    }

    private void CloseDecision()
    {
        closingDecision = true;
        decision?.Close();
        closingDecision = false;
    }

    private void PrepareRelease()
    {
        var choice = store.Choice(egg!.Id);
        var newGoose = store.FindGoose(choice.Offspring)!;
        bool keepOld = choice.Keep == resident.Id;
        leaving = keepOld ? newGoose : resident;
        staying = keepOld ? resident : newGoose;
        releaseStart = -1;
        FinishVisit();
    }

    private void DrawRelease(double t)
    {
        if (releaseStart < 0)
        {
            releaseStart = t;
            Play(Honk.Normal);
        }
        double elapsed = t - releaseStart;
        double progress = Math.Clamp((elapsed - .65) / 4.4, 0, 1);
        int step = (int)(t * 15) % 8;
        double x = display.Left + (display.Width + size) * progress;
        double y = Math.Clamp(position.Y, display.Top, display.Bottom - size);
        goose.Display(PixelArt.Goose(staying!.Look, Pose.Observe, step, false), At(position));
        guest.Display(PixelArt.Goose(leaving!.Look, elapsed < .65 ? Pose.Turn : Pose.Bye, step, elapsed < .32),
            new Rect(x, y, size, size));
        if (progress < 1)
            return;
        store.Release(egg!.Id);
        releaseStart = -1;
        leaving = staying = null;
        guest.Hide();
        SyncState();
        TryBackup();
        nextVisitPlan = 0;
    }

    private void DrawVisit(double t, double delta)
    {
        if (visitor is null)
            return;
        var target = Clamp(position + new Vector(position.X > bounds.Left + size ? -size * .7 : size * .7, 0));
        Vector direction = target - visitorPosition;
        double distance = direction.Length;
        double elapsed = t - guestStart;
        if (elapsed >= options.VisitSeconds - 2)
        {
            target = new Point(bounds.Left - size, visitorPosition.Y);
            direction = target - visitorPosition;
            distance = direction.Length;
        }
        if (distance > 2)
            visitorPosition += direction * (Math.Min(distance, delta * size * 1.5) / distance);
        Pose pose = distance > 7 ? Pose.Walk : Sitting ? Pose.Observe : visitRelationship switch
        {
            Kinship.Parent => Pose.Turn,
            Kinship.Ancestor => Pose.Observe,
            _ => Pose.Dance
        };
        if (egg?.Stage == HatchStage.READY && distance < size && !visitHint)
        {
            visitHint = true;
            Play(Honk.Normal);
            ShowNote("！", 4);
        }
        guest.Display(PixelArt.Goose(visitor.Look, pose, (int)(t * 10) % 8, direction.X < 0), At(visitorPosition));
    }

    private Kinship Relationship(long guestId)
    {
        var parents = store.Eggs().Where(e => e.Offspring.HasValue)
            .ToDictionary(e => e.Offspring!.Value, e => e.Parent);
        if (!parents.TryGetValue(resident.Id, out long parent))
            return Kinship.Other;
        if (parent == guestId)
            return Kinship.Parent;
        while (parents.TryGetValue(parent, out parent))
            if (parent == guestId)
                return Kinship.Ancestor;
        return Kinship.Other;
    }

    private void FinishVisit()
    {
        if (currentVisit is Visit visit)
            store.FinishVisit(visit);
        currentVisit = null;
        visitor = null;
        guest.Hide();
    }

    private void DrawTracks(double t)
    {
        if (options.Footprints && !options.Paused && !holding &&
            action is Pose.Walk or Pose.Run && t >= nextTrack)
        {
            nextTrack = t + .56;
            SpriteWindow window;
            if (tracks.Count == 5)
            {
                window = tracks[0].Window;
                tracks.RemoveAt(0);
            }
            else
                window = new SpriteWindow("Desktop Goose · 足迹", true);
            tracks.Add((window, position + new Vector(size * .42, size * .78), t, left));
        }
        for (int i = tracks.Count - 1; i >= 0; i--)
        {
            var track = tracks[i];
            double age = t - track.Born;
            if (age >= 2.8 || !options.Footprints)
            {
                track.Window.Close();
                tracks.RemoveAt(i);
            }
            else
            {
                int side = Math.Max(11, size / 7);
                track.Window.Display(PixelArt.Footprint(track.Left, Math.Min(6, (int)(age / .4))),
                    new Rect(track.At.X, track.At.Y, side, side));
            }
        }
    }

    private void DrawNotes(double t)
    {
        for (int i = notes.Count - 1; i >= 0; i--)
        {
            var (window, expires) = notes[i];
            if (t < expires)
                continue;
            window.Close();
            notes.RemoveAt(i);
        }
        if (t < nextNote || holding || PriorityHatch)
            return;
        nextNote = t + RandomNoteDelay();
        var pool = Jokes.Concat(options.Memos).ToArray();
        ShowNote(pool[random.Next(pool.Length)], 15);
    }

    private void ShowNote(string text, int seconds)
    {
        if (!visual || notes.Count >= 3)
            return;
        var content = new Border { BorderBrush = PixelUi.Ink, Background = PixelUi.Accent,
            BorderThickness = new Thickness(3), Padding = new Thickness(8, 3, 8, 3), Child = PixelUi.Text(text) };
        var window = new Window { Content = content, ShowActivated = false, ShowInTaskbar = false,
            WindowStyle = WindowStyle.None, ResizeMode = ResizeMode.NoResize, AllowsTransparency = true,
            Background = Brushes.Transparent, Width = 220, Height = 65, Topmost = true, Focusable = false };
        var helper = new System.Windows.Interop.WindowInteropHelper(window);
        nint hwnd = helper.EnsureHandle();
        WindowsDesktop.NonActivating(hwnd, true);
        var area = WindowsDesktop.Selected(options.Monitor).WorkingArea;
        var rect = new Rect(Math.Clamp(position.X, area.Left, Math.Max(area.Left, area.Right - 220)),
            Math.Clamp(position.Y - 70 - notes.Count * 65, area.Top, Math.Max(area.Top, area.Bottom - 65)), 220, 65);
        WindowsDesktop.Place(hwnd, rect);
        window.Show();
        WindowsDesktop.Place(hwnd, rect);
        notes.Add((window, Now + seconds));
    }
}
