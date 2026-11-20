"""Stdlib-only interpreter and real Tk probe, independent of GUI code."""
import json
import os
import platform
import sys
import traceback


def check():
    report = {"executable": sys.executable, "version": sys.version,
              "platform": platform.platform(), "cwd": os.getcwd()}
    try:
        if sys.version_info < (3, 11):
            raise RuntimeError("Python >=3.11 required")
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        root.update_idletasks()
        report.update(tcl=root.tk.call("info", "patchlevel"),
                      tk=root.tk.call("package", "require", "Tk"),
                      tcl_library=root.tk.call("info", "library"),
                      dpi=root.winfo_fpixels("1i"))
        root.destroy()
        report["status"] = "PASS"
        return report, 0
    except Exception:
        report.update(status="FAIL", error=traceback.format_exc())
        return report, 1


if __name__ == "__main__":
    data, code = check()
    print(json.dumps(data, ensure_ascii=True, indent=2))
    raise SystemExit(code)
