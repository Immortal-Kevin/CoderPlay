using System.Windows;

namespace DesktopCleaner;

public partial class App : Application
{
    private IDisposable? session;

    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);
        try
        {
            var store = SnapshotStore.ForCurrentUser();
            session = store.Acquire();
            MainWindow = new MainWindow(new DesktopIconManager(store, () => new ShellDesktopView()));
            MainWindow.Show();
        }
        catch (Exception error)
        {
            MessageBox.Show(error.Message, "Desktop Cleaner", MessageBoxButton.OK, MessageBoxImage.Error);
            Shutdown(1);
        }
    }

    protected override void OnExit(ExitEventArgs e)
    {
        session?.Dispose();
        base.OnExit(e);
    }
}

