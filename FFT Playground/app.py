"""FFT Playground v1.0 — offline Windows entry point, Apache-2.0."""
import sys


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
    MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
