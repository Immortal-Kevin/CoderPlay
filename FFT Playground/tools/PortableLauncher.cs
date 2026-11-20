// Copyright 2026 FFT Playground contributors. Apache-2.0.
using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

internal static class PortableLauncher {
    [STAThread]
    private static int Main() {
        try {
            string home = AppDomain.CurrentDomain.BaseDirectory;
            string python = Path.Combine(home, "runtime", "python.exe");
            string app = Path.Combine(home, "application", "app.py");
            if (!File.Exists(python) || !File.Exists(app))
                throw new FileNotFoundException("Please extract the entire ZIP. Keep runtime and application beside FFT Playground.exe.");
            var start = new ProcessStartInfo(python, "-B -E -s \"" + app + "\"");
            start.UseShellExecute = false;
            start.CreateNoWindow = true;
            start.WorkingDirectory = home;
            foreach (string key in new [] {"PYTHONHOME", "PYTHONPATH", "TCL_LIBRARY", "TK_LIBRARY"})
                start.EnvironmentVariables.Remove(key);
            using (var child = Process.Start(start)) {
                child.WaitForExit();
                if (child.ExitCode != 0)
                    throw new Exception("GUI exit code " + child.ExitCode + ". Logs: %LOCALAPPDATA%\\FFT Playground\\logs\\application.log");
            }
            return 0;
        } catch (Exception error) {
            MessageBox.Show(error.Message, "FFT Playground could not start", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }
}
