"""FFT Playground v1.0 — offline Windows entry point, Apache-2.0."""
import sys
import logging
from pathlib import Path
import os
import traceback


def log_directory():
    base = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "FFT Playground" / "logs"
    base.mkdir(parents=True, exist_ok=True)
    return base


def configure_logging():
    from logging.handlers import RotatingFileHandler
    path = log_directory() / "application.log"
    handler = RotatingFileHandler(path, maxBytes=1_000_000, backupCount=2, encoding="utf-8")
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
    logging.info("Start executable=%s version=%s cwd=%s frozen=%s", sys.executable,
                 sys.version, Path.cwd(), getattr(sys, "frozen", False))
    return path


def show_failure(text):
    if sys.stderr is not None:
        print(text, file=sys.stderr)
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, text, "FFT Playground 启动/运行失败", 0x10)


def main():
    if sys.platform == "win32":
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (OSError, AttributeError):
            pass
    import tkinter as tk
    from ui.main_window import MainWindow
    root = tk.Tk()
    logging.info("Tcl=%s Tk=%s DPI=%s", root.tk.call("info", "patchlevel"),
                 root.tk.call("package", "require", "Tk"), root.winfo_fpixels("1i"))
    def callback_error(kind, value, tb):
        logging.error("Tk callback failed", exc_info=(kind, value, tb))
        from tkinter import messagebox
        messagebox.showerror("运行错误", f"{kind.__name__}: {value}\n\n完整日志：{log_directory() / 'application.log'}", parent=root)
    root.report_callback_exception = callback_error
    window = MainWindow(root)
    root.application = window
    root.mainloop()
    logging.info("Normal GUI shutdown")


def entry():
    path = None
    try:
        path = configure_logging()
        if sys.version_info < (3, 11):
            raise RuntimeError("需要 Python 3.11 或更高版本")
        main()
        return 0
    except Exception:
        detail = traceback.format_exc()
        logging.error("Startup failed\n%s", detail)
        show_failure(f"解释器：{sys.executable}\n\n{detail}\n日志：{path or '无法创建日志文件'}")
        return 1


if __name__ == "__main__":
    raise SystemExit(entry())
