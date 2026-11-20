import json
import os
from pathlib import Path
import subprocess
import sys
import pytest
import app
import startup_check

ROOT = Path(__file__).resolve().parents[1]


def test_probe_rejects_old_python(monkeypatch):
    monkeypatch.setattr(startup_check.sys, "version_info", (3, 10))
    result, status = startup_check.check()
    assert status == 1 and result["status"] == "FAIL"
    assert "3.11" in result["error"]


def test_entry_logs_real_startup_exception(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    def fail(): raise RuntimeError("test startup failure evidence")
    monkeypatch.setattr(app, "main", fail)
    messages = []
    monkeypatch.setattr(app, "show_failure", messages.append)
    assert app.entry() == 1
    assert sys.executable in messages[0]
    assert "test startup failure evidence" in messages[0]
    assert "test startup failure evidence" in (app.log_directory()/"application.log").read_text(encoding="utf-8")
    import logging
    logging.shutdown()


@pytest.mark.skipif(os.name != "nt", reason="Windows launcher")
def test_launcher_diagnostic_and_missing_python(tmp_path):
    env = dict(os.environ, LOCALAPPDATA=str(tmp_path))
    command = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT/"launch.ps1"), "-Diagnostic", "-PythonPath"]
    ok = subprocess.run(command+[sys.executable], input="\n", capture_output=True, text=True, env=env, timeout=25)
    assert ok.returncode == 0, ok.stdout+ok.stderr
    assert "Selected interpreter:" in ok.stdout and '"status": "PASS"' in ok.stdout
    missing = subprocess.run(command+[str(tmp_path/"missing-python.exe")], capture_output=True, text=True, env=env, timeout=25)
    assert missing.returncode != 0
    assert "No compatible Python" in missing.stdout
    assert "missing-python.exe" in (tmp_path/"FFT Playground/logs/launcher.log").read_text(encoding="utf-8-sig")


@pytest.mark.skipif(os.name != "nt", reason="Windows DPI-aware process")
def test_actual_250_percent_dpi_layout_in_separate_process():
    code = '''
import ctypes, tkinter as tk
ctypes.windll.shcore.SetProcessDpiAwareness(1)
from ui.main_window import MainWindow
r=tk.Tk()
r.tk.call('tk','scaling',240/72)
u=MainWindow(r)
r.update()
assert u.scale>2.4
assert r.winfo_width()>2500
def descendants(w):
    for c in w.winfo_children():
        yield c
        yield from descendants(c)
notebook=next(w for w in descendants(r) if w.winfo_class()=='TNotebook')
for tab in notebook.tabs():
    notebook.select(tab);r.update()
    for w in descendants(r.nametowidget(tab)):
        if w.winfo_class()=='TEntry':
            assert w.winfo_rootx()+w.winfo_width()<=notebook.winfo_rootx()+notebook.winfo_width()
            assert w.winfo_rooty()+w.winfo_height()<=notebook.winfo_rooty()+notebook.winfo_height()
for p in u.plots:
    assert p.bounds()[0]>170
u.close()
print('DPI PASS')
'''
    result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=20)
    assert result.returncode==0, result.stderr
    assert "DPI PASS" in result.stdout


@pytest.mark.skipif(os.name != "nt", reason="actual Windows batch failure path")
def test_bat_failure_retains_diagnostics_from_unicode_path(tmp_path):
    import shutil
    project = tmp_path / "项目 空格"
    project.mkdir()
    for name in ("run.bat", "launch.ps1"):
        shutil.copy2(ROOT/name, project/name)
    (project/"startup_check.py").write_text("import sys;print('Tk unavailable: injected probe failure');sys.exit(1)\n", encoding="utf-8")
    env = dict(os.environ, LOCALAPPDATA=str(tmp_path/"logs"))
    result = subprocess.run([os.environ["COMSPEC"], "/d", "/c", str(project/"run.bat")],
                            cwd=tmp_path, env=env, input="\n", capture_output=True, text=True, timeout=40)
    assert result.returncode == 1
    assert "Tk unavailable: injected probe failure" in result.stdout
    assert "Please keep this window" in result.stdout
    assert "No compatible Python" in result.stdout
    assert "python.exe" in result.stdout
