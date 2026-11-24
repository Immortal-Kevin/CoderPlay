using System.IO;
using System.Security.Principal;
using System.Windows;

namespace DesktopGoose.App;

internal static class Program
{
    public static string SaveDirectory => Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "CoderPlay", "DesktopGoose");

    [STAThread]
    public static void Main()
    {
        string identity = WindowsIdentity.GetCurrent().User!.Value;
        using var mutex = new Mutex(true, @"Global\CoderPlay.DesktopGoose." + identity, out bool first);
        if (!first)
        {
            MessageBox.Show("桌面捣蛋鹅已运行。请使用任务栏通知区域中的鹅头像。", "Desktop Goose");
            return;
        }

        var app = new Application { ShutdownMode = ShutdownMode.OnExplicitShutdown };
        Game? game = null;
        void ShowError(Exception error)
        {
            try
            {
                Directory.CreateDirectory(SaveDirectory);
                File.AppendAllText(Path.Combine(SaveDirectory, "errors.log"),
                    $"{DateTimeOffset.Now:O} {error.GetType().Name}: {error.Message}{Environment.NewLine}");
            }
            catch (IOException) { }
            catch (UnauthorizedAccessException) { }
            MessageBox.Show(error.Message, "Desktop Goose", MessageBoxButton.OK, MessageBoxImage.Error);
        }

        app.DispatcherUnhandledException += (_, e) =>
        {
            e.Handled = true;
            try { game?.Dispose(); }
            finally { ShowError(e.Exception); app.Shutdown(1); }
        };
        try
        {
            game = new Game(Path.Combine(SaveDirectory, "goose.sqlite"));
            if (game.Start())
                app.Run();
        }
        catch (Exception e)
        {
            ShowError(e);
        }
        finally
        {
            game?.Dispose();
        }
    }
}
