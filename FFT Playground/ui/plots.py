import bisect
import math
import tkinter as tk
from core.spectrum import peaks
from .i18n import translate

BG, GRID, FG, BLUE, CYAN = "#121820", "#293645", "#edf3fc", "#1677FF", "#42d5dc"


class Plot(tk.Canvas):
    def __init__(self, parent, title, xlabel, status, color=CYAN):
        super().__init__(parent, background=BG, highlightthickness=0, height=185)
        self.scale = max(1.0, self.winfo_fpixels("1i") / 96)
        self.configure(height=round(185 * self.scale))
        self.title, self.xlabel, self.status, self.color = title, xlabel, status, color
        self.language = "zh"
        self.x, self.y, self.marks = [], [], []
        self.view = None
        self.drag_origin = None
        self.rpm = 1800
        self.bind("<Configure>", lambda e: self.draw())
        self.bind("<MouseWheel>", self.zoom)
        self.bind("<ButtonPress-1>", self.press)
        self.bind("<B1-Motion>", self.pan)
        self.bind("<Motion>", self.motion)
        self.bind("<Double-Button-1>", lambda e: self.reset())

    def set_data(self, x, y, xmax, rpm, annotate=False):
        self.x, self.y, self.xmax, self.rpm = x, y, xmax, rpm
        self.marks = peaks(x, y, count=3, maximum=xmax) if annotate else []
        self.reset()

    def reset(self):
        if not self.x:
            return
        right = min(self.xmax, self.x[-1])
        start = self.x[0]
        end = max(start + 1e-9, right)
        ys = self.y[:max(1, bisect.bisect_right(self.x, end))]
        low, high = min(ys), max(ys)
        margin = max((high - low) * 0.16, abs(high) * 0.05, 1e-8)
        self.default_view = (start, end, low - margin, high + margin)
        self.view = self.default_view
        self.draw()

    def bounds(self):
        s = self.scale
        return 72*s, 33*s, max(130*s, self.winfo_width() - 20*s), max(80*s, self.winfo_height() - 37*s)

    def draw(self):
        self.delete("all")
        s = self.scale
        self.create_text(12*s, 12*s, text=translate(self.title, self.language) + "  ·  Amplitude (a.u.)", fill=FG, anchor="w", font=("Microsoft YaHei UI", 10, "bold"))
        if not self.view:
            return
        left, top, right, bottom = self.bounds()
        xmin, xmax, ymin, ymax = self.view
        def sx(x): return left + (x - xmin) / (xmax - xmin) * (right - left)
        def sy(y): return bottom - (y - ymin) / (ymax - ymin) * (bottom - top)
        for k in range(6):
            x = left + k * (right - left) / 5
            self.create_line(x, top, x, bottom, fill=GRID, width=s)
            self.create_text(x, bottom + 11*s, text=f"{xmin + k * (xmax - xmin) / 5:.4g}", fill="#9cacbf", font=("Segoe UI", 8))
        for k in range(4):
            y = top + k * (bottom - top) / 3
            self.create_line(left, y, right, y, fill=GRID, width=s)
            self.create_text(left - 7*s, y, text=f"{ymax - k * (ymax - ymin) / 3:.3g}", fill="#9cacbf", anchor="e", font=("Segoe UI", 8))
        self.create_text((left + right) / 2, bottom + 28*s, text=self.xlabel, fill=FG, font=("Segoe UI", 8))
        # Per-pixel min/max buckets retain narrow impulses without huge canvas paths.
        first = max(0, bisect.bisect_left(self.x, xmin) - 1)
        last = min(len(self.x), bisect.bisect_right(self.x, xmax) + 1)
        buckets = {}
        for i in range(first, last):
            px = min(right, max(left, round(sx(self.x[i]))))
            buckets.setdefault(px, []).append((i, self.y[i]))
        coords = []
        for px, items in buckets.items():
            extrema = sorted({min(items, key=lambda v: v[1]), max(items, key=lambda v: v[1])})
            for _, y in extrema:
                coords.extend((px, min(bottom, max(top, sy(y)))))
        if len(coords) >= 4:
            self.create_line(*coords, fill=self.color, width=1.2*s)
        for index, i in enumerate(self.marks):
            if xmin <= self.x[i] <= xmax and ymin <= self.y[i] <= ymax:
                px, py = sx(self.x[i]), sy(self.y[i])
                self.create_line(px, max(top, py - 5*s), px, min(bottom, py + 5*s), fill="#ffcd6a", width=2*s)
                label = f"{self.x[i]:.3g} Hz | {self.y[i]:.3g} | {self.x[i] / (self.rpm / 60):.2f}×"
                # Stagger fixed-width peak callouts to avoid tall labels hiding the trace.
                tx = min(right - 3, max(left + 3, px))
                anchor = "e" if tx > (left + right) / 2 else "w"
                self.create_text(tx, top + (6 + index * 15)*s, text=label, anchor=anchor, fill="#ffcd6a", font=("Segoe UI", 8))

    def zoom(self, event):
        if not self.view:
            return
        l, t, r, b = self.bounds()
        fx, fy = min(1, max(0, (event.x - l) / (r - l))), min(1, max(0, (b - event.y) / (b - t)))
        xmin, xmax, ymin, ymax = self.view
        factor = 0.8 if event.delta > 0 else 1.25
        cx, cy = xmin + fx * (xmax - xmin), ymin + fy * (ymax - ymin)
        self.view = (cx + (xmin - cx) * factor, cx + (xmax - cx) * factor,
                     cy + (ymin - cy) * factor, cy + (ymax - cy) * factor)
        self.draw()

    def press(self, event):
        self.drag_origin = (event.x, event.y, self.view)

    def pan(self, event):
        if not self.drag_origin or not self.view:
            return
        ox, oy, view = self.drag_origin
        l, t, r, b = self.bounds()
        dx = (event.x - ox) / (r - l) * (view[1] - view[0])
        dy = (event.y - oy) / (b - t) * (view[3] - view[2])
        self.view = (view[0] - dx, view[1] - dx, view[2] + dy, view[3] + dy)
        self.draw()

    def motion(self, event):
        if not self.view:
            return
        l, t, r, b = self.bounds()
        if l <= event.x <= r and t <= event.y <= b:
            x = self.view[0] + (event.x - l) / (r - l) * (self.view[1] - self.view[0])
            i = min(len(self.x) - 1, max(0, bisect.bisect_left(self.x, x)))
            if i and abs(self.x[i - 1] - x) < abs(self.x[i] - x): i -= 1
            self.status.set(f"{self.xlabel}: {self.x[i]:.7g}   Amplitude: {self.y[i]:.7g} a.u.   | 滚轮缩放 · 拖动平移 · 双击重置")
