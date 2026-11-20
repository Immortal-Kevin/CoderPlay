from pathlib import Path
import subprocess
import sys


def test_real_gui_offline_without_site_packages_exits(tmp_path):
    root = Path(__file__).resolve().parents[1]
    script = root / "tools/gui_smoke.py"
    target = tmp_path / "offline.png"
    # -S removes all third-party site packages; network calls are forbidden.
    code = "\n".join([
        "import socket, runpy, sys",
        "def forbidden(*args, **kwargs): raise AssertionError('network attempted')",
        "socket.socket = forbidden",
        "socket.create_connection = forbidden",
        f"sys.argv = [{str(script)!r}, {str(target)!r}]",
        f"runpy.run_path({str(script)!r}, run_name='__main__')",
    ])
    completed = subprocess.run([sys.executable, "-S", "-c", code], cwd=root,
                               capture_output=True, text=True, timeout=20)
    assert completed.returncode == 0, completed.stderr
    assert "WM_DELETE_WINDOW callback" in completed.stdout
    assert target.is_file()


def test_close_during_calculation_exits(tmp_path):
    root = Path(__file__).resolve().parents[1]
    code = "\n".join([
        "import tkinter as tk",
        "from ui.main_window import MainWindow",
        "root=tk.Tk(); ui=MainWindow(root)",
        "ui.vars['duration'].set(str(32767/4096))",
        "root.after(0,ui.update)",
        "root.after(30,ui.close)",
        "root.mainloop()",
        "assert ui.closed",
        "print('closed during worker computation')",
    ])
    completed = subprocess.run([sys.executable, "-S", "-c", code], cwd=root,
                               capture_output=True, text=True, timeout=10)
    assert completed.returncode == 0, completed.stderr
    assert "closed during worker computation" in completed.stdout
