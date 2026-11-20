"""Launch real GUI, export original charts, close normally; no automation helper."""
import json
from pathlib import Path
import sys
import time
import tkinter as tk
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ui.main_window import MainWindow
from io_utils.png_export import export_canvases


def main():
    root = tk.Tk()
    ui = MainWindow(root)
    root.geometry("1366x768+0+0")
    deadline = time.monotonic()+15
    output = Path(sys.argv[1]) if len(sys.argv)>1 else Path("test_output/gui.png")
    output.parent.mkdir(parents=True, exist_ok=True)
    success = []
    def finish():
        if not ui.result:
            if time.monotonic()>deadline:
                ui.close()
                raise RuntimeError("GUI initial calculation timed out")
            root.after(50, finish)
            return
        export_canvases(output, ui.plots)
        print(json.dumps({"size":[root.winfo_width(),root.winfo_height()],
                          "n":len(ui.result.raw),"df":ui.result.df,
                          "png":str(output),"close":"WM_DELETE_WINDOW callback"}))
        success.append(True)
        ui.close()
    root.after(500, finish)
    root.mainloop()
    assert ui.closed and success, "GUI smoke test did not finish successfully"


if __name__=="__main__":
    main()
