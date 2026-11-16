"""Windows desktop UI for AIsharpner."""

from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from math import prod
from pathlib import Path
from queue import Empty, SimpleQueue
import re
from tempfile import NamedTemporaryFile
from time import monotonic
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import openvino as ov
from PIL import Image, ImageTk

from engine import (MAX_BATCH_SOURCE_PIXELS, MAX_PIXELS, RAW, available_devices,
                    compile_optimizer, optimize_image, output_size, read_photo)

BG, PANEL, INK, MUTED, ACCENT = "#10131b", "#181d29", "#eff3fb", "#aab6ca", "#7de6d2"
DRAFT_DIR = Path(__file__).resolve().parent / "output draft"
DRAFT_NAME = re.compile(r"AIDR-IMG-(\d+)- S\d+P\d+F\d+\.[^.]+", re.IGNORECASE)
SCALE_STEP = 25


def save_draft(image, sharpness, scale, detail):
    DRAFT_DIR.mkdir(exist_ok=True)
    numbers = (DRAFT_NAME.fullmatch(path.name) for path in DRAFT_DIR.iterdir())
    number = max((int(match[1]) for match in numbers if match), default=-1) + 1
    with NamedTemporaryFile(dir=DRAFT_DIR, suffix=".png", delete=False) as file:
        temporary = Path(file.name)
    try:
        image.save(temporary, format="PNG")
        while True:
            target = DRAFT_DIR / f"AIDR-IMG-{number}- S{sharpness:02d}P{scale:02d}F{detail:02d}.png"
            try:
                # On Windows rename fails when the destination already exists.
                return temporary.rename(target)
            except FileExistsError:
                number += 1
    finally:
        temporary.unlink(missing_ok=True)


class App:
    def __init__(self, root):
        self.root = root
        self.core = ov.Core()
        self.worker = ThreadPoolExecutor(max_workers=1)
        self.events = SimpleQueue()
        self.original = self.result = self.path = None
        self.paths = ()
        self.drafts = {}
        self.show_result = True
        self.busy = False
        self.zoom = 1.0
        self.pan = (0, 0)
        self.anchor = None
        self.preview_key = None
        self.photo = None
        root.title("AIsharpner · AI 锐化")
        root.geometry("1280x790")
        root.minsize(1000, 700)
        root.configure(bg=BG)
        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure(".", font=("Microsoft YaHei UI", 10), background=PANEL, foreground=INK)
        style.configure("TButton", padding=(10, 8), background="#283246", bordercolor="#344258")
        style.map("TButton", background=[("active", "#364761")], foreground=[("disabled", "#8792a6")])
        style.configure("Accent.TButton", background=ACCENT, foreground=BG, padding=12)
        style.map("Accent.TButton", background=[("disabled", "#364655"), ("active", "#a2f4e4")])
        style.configure("TCombobox", fieldbackground="#283246", arrowcolor=INK)
        style.map("TCombobox", fieldbackground=[("readonly", "#283246")],
                  foreground=[("readonly", INK)])
        style.configure("Horizontal.TScale", troughcolor="#303a4d", background=ACCENT)
        style.configure("Horizontal.TProgressbar", troughcolor="#303a4d", background=ACCENT,
                        bordercolor=PANEL, lightcolor=ACCENT, darkcolor=ACCENT)

        header = tk.Frame(root, bg=BG)
        header.pack(fill="x", padx=24, pady=(16, 12))
        self.label(header, "AIsharpner", size=25, bold=True, bg=BG).pack(side="left")
        self.label(header, "AI 锐化   /   本地照片工作台", color=MUTED, bg=BG).pack(side="left", padx=18)
        self.label(header, "●  INTEL 设备推理", color=ACCENT, bg=BG).pack(side="right")
        body = tk.Frame(root, bg=BG)
        body.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        body.rowconfigure(0, weight=1)
        for column, weight in enumerate((1, 1, 2)):
            body.columnconfigure(column, weight=weight, uniform="columns")
        left, middle, right = [self.panel(body, column, title) for column, title in enumerate(
            ("01  导入照片", "02  AI 优化设置", "03  预览与导出")
        )]

        self.import_button = ttk.Button(left, text="＋  导入照片（可多选）…", command=self.import_photo)
        self.import_button.pack(fill="x", pady=(0, 12))
        self.label(left, "JPEG · PNG · TIFF · WebP · BMP\nHEIC · HEIF · AVIF · 相机 RAW",
                   color=MUTED, wrap=220).pack(anchor="w")
        self.queue_note = self.label(left, "尚未导入照片", color=MUTED)
        self.queue_note.pack(anchor="w", pady=(14, 4))
        self.selection = ttk.Combobox(left, state="disabled", width=18)
        self.selection.pack(fill="x")
        self.selection.bind("<<ComboboxSelected>>", self.preview_selected)
        self.label(left, "图片基本信息", size=13, bold=True).pack(anchor="w", pady=(20, 12))
        self.metadata = {}
        for title in ("文件名", "文件格式", "文件尺寸", "文件大小"):
            self.label(left, title, color=MUTED).pack(anchor="w", pady=(8, 0))
            self.metadata[title] = self.label(left, "—", wrap=220)
            self.metadata[title].pack(anchor="w", fill="x")

        self.label(middle, "AI 模型", color=MUTED).pack(anchor="w")
        self.label(middle, "Real-ESRGAN · 肌肤纹理", bold=True, wrap=190).pack(anchor="w", pady=(4, 14))
        self.label(middle, "AI 推理设备", color=MUTED).pack(anchor="w")
        self.device = ttk.Combobox(middle, state="readonly", width=16)
        self.device.pack(fill="x", pady=5)
        self.device.bind("<<ComboboxSelected>>", self.update_controls)
        self.refresh_button = ttk.Button(middle, text="重新检测设备", command=self.detect)
        self.refresh_button.pack(anchor="w", pady=(0, 6))
        self.device_note = self.label(middle, "", color=MUTED, wrap=215)
        self.device_note.pack(anchor="w")
        self.sharpness = self.slider(middle, "AI 锐化率", 0, 100, 55, 1, "%")
        self.detail = self.slider(middle, "AI 细节补全自由度", 0, 100, 45, 1, "%")
        self.scale = self.slider(middle, "分辨率缩放", SCALE_STEP, 300, 100, SCALE_STEP, "%")
        self.size_note = self.label(middle, "输出尺寸  —", color=MUTED, wrap=215)
        self.size_note.pack(anchor="w", pady=8)
        self.run_button = ttk.Button(middle, text="✦  AI 优化", style="Accent.TButton",
                                     command=self.run, state="disabled")
        self.run_button.pack(fill="x", pady=(10, 0))

        self.progress = ttk.Progressbar(right, maximum=100)
        self.progress.pack(fill="x")
        self.status = self.label(right, "等待导入照片", color=MUTED, wrap=420)
        self.status.pack(anchor="w", pady=(6, 10))
        toolbar = tk.Frame(right, bg=PANEL)
        toolbar.pack(fill="x", pady=(0, 8))
        self.compare = ttk.Button(toolbar, text="切换原图 / 优化图", command=self.toggle)
        self.compare.pack(side="left")
        self.compare.configure(state="disabled")
        ttk.Button(toolbar, text="−", width=2, command=lambda: self.zoom_by(1 / 1.2)).pack(side="right")
        ttk.Button(toolbar, text="＋", width=2, command=lambda: self.zoom_by(1.2)).pack(side="right")
        ttk.Button(toolbar, text="适应", width=4, command=self.reset_view).pack(side="right")
        ttk.Button(toolbar, text="1:1", width=3, command=self.actual_pixels).pack(side="right")
        self.canvas = tk.Canvas(right, bg="#0b0e15", highlightthickness=0, width=1, height=1)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _: self.draw())
        self.canvas.bind("<MouseWheel>", self.wheel)
        self.canvas.bind("<ButtonPress-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.drag)
        footer = tk.Frame(right, bg=PANEL)
        footer.pack(fill="x", pady=(10, 0))
        self.view_note = self.label(footer, "滚轮缩放 · 按住拖动", color=MUTED)
        self.view_note.pack(side="left")
        self.save_button = ttk.Button(footer, text="另存为…", command=self.save, state="disabled")
        self.save_button.pack(side="right")
        self.detect()
        root.after(50, self.poll)

    def label(self, parent, text, size=10, bold=False, color=INK, bg=PANEL, wrap=0):
        return tk.Label(parent, text=text, font=("Microsoft YaHei UI", size, "bold" if bold else "normal"),
                        bg=bg, fg=color, justify="left", anchor="w", wraplength=wrap)

    def panel(self, parent, column, title):
        panel = tk.Frame(parent, bg=PANEL, padx=16, pady=16)
        panel.grid(row=0, column=column, sticky="nsew", padx=6)
        self.label(panel, title, size=15, bold=True).pack(anchor="w", pady=(0, 16))
        return panel

    def slider(self, parent, title, low, high, initial, step, suffix):
        line = tk.Frame(parent, bg=PANEL)
        line.pack(fill="x", pady=(18, 2))
        self.label(line, title).pack(side="left")
        value = self.label(line, f"{initial}{suffix}", color=ACCENT)
        value.pack(side="right")
        scale = ttk.Scale(parent, from_=low, to=high)
        scale.set(initial)

        def change(raw):
            snapped = round(float(raw) / step) * step
            if scale.get() != snapped:
                scale.set(snapped)
            value.configure(text=f"{snapped}{suffix}")
            self.update_controls()

        scale.configure(command=change)
        scale.pack(fill="x")
        return scale

    def detect(self):
        try:
            self.devices = available_devices(self.core)
            choices = [f"{key} · {'Intel NPU' if key.startswith('NPU') else 'Intel 核显'}"
                       for key in self.devices]
            self.device.configure(values=choices)
            self.device.set(choices[0] if choices else "")
            self.device_note.configure(text="选择要运行模型的设备" if choices else
                                       "未检测到可用的 Intel 核显或 NPU，请检查驱动。")
        except RuntimeError as error:
            self.devices = {}
            self.device.configure(values=())
            self.device.set("")
            self.device_note.configure(text=str(error))
        self.update_controls()

    def update_controls(self, _event=None):
        valid = False
        if self.original is not None:
            width, height = output_size(self.original.size, self.scale.get() / 100)
            valid = width * height <= MAX_PIXELS
            self.size_note.configure(text=f"输出尺寸  {width} × {height}" +
                                     ("" if valid else "\n超过 4800 万像素上限"))
        batch = len(self.paths) > 1
        self.run_button.configure(text=f"✦  批量 AI 优化（{len(self.paths)} 张）" if batch else "✦  AI 优化",
                                  state="normal" if (batch or valid) and self.device.get()
                                  and not self.busy else "disabled")

    def import_photo(self):
        patterns = " ".join(["*.jpg", "*.jpeg", "*.png", "*.tif", "*.tiff", "*.webp", "*.bmp",
                             "*.heic", "*.heif", "*.avif", *["*" + ext for ext in sorted(RAW)]])
        paths = filedialog.askopenfilenames(filetypes=[("照片", patterns), ("所有文件", "*.*")])
        if not paths:
            return
        self.paths = tuple(dict.fromkeys(Path(path) for path in paths))
        self.drafts = {}
        self.queue_note.configure(text=f"已导入 {len(self.paths)} 张 · 选择预览")
        self.selection.configure(values=[f"{i}. {path.name}" for i, path in enumerate(self.paths, 1)],
                                 state="readonly")
        self.selection.current(0)
        self.progress["value"] = 0
        self.preview_selected()

    @staticmethod
    def photo_data(path, limit=MAX_PIXELS):
        return (*read_photo(path, limit), path, path.stat().st_size)

    def preview_selected(self, _event=None):
        index = self.selection.current()
        if self.busy or index < 0:
            return
        path = self.paths[index]
        draft = self.drafts.get(path)
        limit = MAX_BATCH_SOURCE_PIXELS if len(self.paths) > 1 else MAX_PIXELS
        self.original = self.result = self.path = None
        for label in self.metadata.values():
            label.configure(text="—")
        self.size_note.configure(text="输出尺寸  —")
        self.reset_view()
        self.set_busy(True)
        self.status.configure(text="正在读取照片")

        def load():
            return self.photo_data(path, limit), read_photo(draft)[0] if draft else None

        def show(data):
            photo, self.result = data
            self.show_result = True
            self.loaded(photo)
            self.status.configure(text=f"已自动保存 · {draft.name}" if draft else "照片已导入")

        self.submit(load, show)

    def loaded(self, data):
        self.original, kind, self.path, size = data
        width, height = self.original.size
        for label, value in zip(self.metadata.values(), (self.path.name, kind,
                                  f"{width} × {height} px", f"{size:,} B · {size / 1048576:.2f} MiB")):
            label.configure(text=value)
        self.reset_view()

    def set_busy(self, busy):
        self.busy = busy
        for control in (self.import_button, self.refresh_button, self.sharpness, self.detail, self.scale):
            control.configure(state="disabled" if busy else "normal")
        self.device.configure(state="disabled" if busy else "readonly")
        self.selection.configure(state="disabled" if busy or not self.paths else "readonly")
        self.save_button.configure(state="normal" if self.result is not None and not busy else "disabled")
        self.compare.configure(state="normal" if self.result is not None else "disabled")
        self.update_controls()

    def submit(self, work, callback):
        future = self.worker.submit(work)
        future.add_done_callback(lambda completed: self.events.put(("done", completed, callback)))

    def run(self):
        paths = self.paths
        device = self.device.get().split()[0]
        scale, sharpness, detail = (round(control.get()) for control in (self.scale, self.sharpness, self.detail))
        self.set_busy(True)
        self.progress["value"] = 0
        self.status.configure(text="正在准备模型 · 预计剩余时间计算中")

        def work():
            drafts = {}
            preview = None
            batch = len(paths) > 1
            limit = MAX_BATCH_SOURCE_PIXELS if batch else MAX_PIXELS

            @lru_cache(maxsize=2)
            def compiled_model(percent):
                return compile_optimizer(self.core, device, percent / 100, sharpness / 100, detail / 100)

            pending = {path: scale for path in paths}
            for attempt in range(1, 3 if batch else 2):
                if not pending:
                    break
                total = len(pending)
                started = monotonic()
                failures = {}
                compile_errors = {}
                for index, (path, ceiling) in enumerate(pending.items()):
                    def report(fraction, eta, stage):
                        completed = index + fraction
                        remaining = ((monotonic() - started) * (total - completed) / completed
                                     if completed else eta)
                        prefix = f"第 {attempt} 遍 · " if batch else ""
                        self.events.put(("progress", completed / total, remaining,
                                         f"{prefix}{index + 1}/{total} · {path.name} · {stage}"))

                    report(0, None, "正在读取")
                    try:
                        photo = self.photo_data(path, limit)
                        choices = (scale,) if attempt == 1 else range(ceiling, 0, -SCALE_STEP)
                        compiled = None
                        compile_error = None
                        for percent in choices:
                            if prod(output_size(photo[0].size, percent / 100)) > MAX_PIXELS:
                                continue
                            if percent not in compile_errors:
                                report(0, None, f"正在准备模型 · 缩放 {percent}%")
                                try:
                                    compiled = compiled_model(percent)
                                except (RuntimeError, ValueError) as error:
                                    compile_errors[percent] = str(error)
                            if compiled is not None:
                                break
                            compile_error = compile_errors[percent]
                        if compiled is None:
                            if compile_error:
                                raise RuntimeError(compile_error)
                            raise ValueError("目标尺寸超过 4800 万像素上限。")
                        try:
                            result = optimize_image(compiled, photo[0], percent / 100,
                                                    lambda fraction, eta, stage: report(
                                                        0.99 * fraction, eta, f"缩放 {percent}% · {stage}"))
                        except RuntimeError:
                            ceiling = max(SCALE_STEP, percent - SCALE_STEP)
                            raise
                        preview = photo, result
                        report(0.99, None, "正在自动保存")
                        drafts[path] = save_draft(result, sharpness, percent, detail)
                    except (OSError, RuntimeError, ValueError, Image.DecompressionBombError) as error:
                        failures[path] = (ceiling, str(error))
                    report(1, 0, "已保存" if path in drafts else "待重试" if batch and attempt == 1 else "失败")
                pending = {path: ceiling for path, (ceiling, _) in failures.items()}
            errors = [(path.name, error) for path, (_, error) in failures.items()]
            return drafts, errors, preview

        self.submit(work, self.optimized)

    def optimized(self, data):
        drafts, errors, preview = data
        self.drafts.update(drafts)
        if preview:
            photo, self.result = preview
            self.selection.current(self.paths.index(photo[2]))
            self.show_result = True
            self.loaded(photo)
        if len(self.paths) == 1 and drafts:
            self.status.configure(text=f"已自动保存 · {next(iter(drafts.values())).name}")
        else:
            self.status.configure(text=f"处理完成 · 已保存 {len(drafts)} 张 · 失败 {len(errors)} 张")
        if errors:
            details = "\n\n".join(f"{name}\n{error[:400]}" for name, error in errors[:5])
            if len(errors) > 5:
                details += f"\n\n另有 {len(errors) - 5} 张失败。"
            messagebox.showwarning("照片处理失败", details, parent=self.root)

    def poll(self):
        try:
            while True:
                kind, *data = self.events.get_nowait()
                if kind == "progress":
                    fraction, eta, stage = data
                    self.progress["value"] = 100 * fraction
                    estimate = "计算中" if eta is None else f"{int(eta + 0.5)} 秒"
                    self.status.configure(text=f"{stage} · {fraction:.0%} · 预计剩余 {estimate}")
                else:
                    future, callback = data
                    try:
                        callback(future.result())
                    except Exception as error:
                        self.status.configure(text="操作失败")
                        messagebox.showerror("AIsharpner", str(error), parent=self.root)
                    finally:
                        self.set_busy(False)
        except Empty:
            pass
        self.root.after(50, self.poll)

    def toggle(self):
        self.show_result = not self.show_result
        self.draw()

    def reset_view(self):
        self.zoom, self.pan = 1.0, (0, 0)
        self.draw()

    def actual_pixels(self):
        image = self.result if self.show_result and self.result is not None else self.original
        if image is None:
            return
        fit = min(self.canvas.winfo_width() / image.width,
                  self.canvas.winfo_height() / image.height)
        self.zoom = 1 / fit
        self.draw()

    def zoom_by(self, factor, x=None, y=None):
        if self.original is None:
            return
        old_zoom = self.zoom
        self.zoom = min(max(16.0, old_zoom), max(0.25, self.zoom * factor))
        if x is not None:
            center_x, center_y = self.canvas.winfo_width() / 2, self.canvas.winfo_height() / 2
            factor = self.zoom / old_zoom
            dx, dy = self.pan
            self.pan = (x - center_x - (x - center_x - dx) * factor,
                        y - center_y - (y - center_y - dy) * factor)
        self.draw()

    def wheel(self, event):
        self.zoom_by(1.2 ** (event.delta / 120), event.x, event.y)

    def start_drag(self, event):
        self.anchor = (event.x, event.y)

    def drag(self, event):
        if self.original is not None and self.anchor is not None:
            self.pan = (self.pan[0] + event.x - self.anchor[0], self.pan[1] + event.y - self.anchor[1])
            self.anchor = (event.x, event.y)
            self.draw()

    def draw(self):
        canvas = self.canvas
        width, height = canvas.winfo_width(), canvas.winfo_height()
        canvas.delete("all")
        image = self.result if self.show_result and self.result is not None else self.original
        if image is None:
            canvas.create_text(width / 2, height / 2, text="导入照片后在这里预览", fill=MUTED,
                               font=("Microsoft YaHei UI", 13))
            return
        ratio = min(width / image.width, height / image.height) * self.zoom
        left = round((width - image.width * ratio) / 2 + self.pan[0])
        top = round((height - image.height * ratio) / 2 + self.pan[1])
        x0, y0 = max(0, round(left)), max(0, round(top))
        x1, y1 = min(width, round(left + image.width * ratio)), min(height, round(top + image.height * ratio))
        if x1 > x0 and y1 > y0:
            box = (max(0, (x0 - left) / ratio), max(0, (y0 - top) / ratio),
                   min(image.width, (x1 - left) / ratio), min(image.height, (y1 - top) / ratio))
            key = (id(image), x1 - x0, y1 - y0, box)
            if key != self.preview_key:
                visible = image.resize((x1 - x0, y1 - y0), Image.Resampling.BILINEAR, box=box)
                self.photo = ImageTk.PhotoImage(visible)
                self.preview_key = key
            canvas.create_image(x0, y0, anchor="nw", image=self.photo)
        label = "优化图" if image is self.result else "原图"
        self.view_note.configure(text=f"{label} · {ratio:.0%} · 滚轮缩放")

    def save(self):
        path = filedialog.asksaveasfilename(
            initialfile=self.path.stem + "_AI", defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("WebP", "*.webp"), ("TIFF", "*.tif")]
        )
        if not path:
            return
        target = Path(path)
        if target.resolve() in {path.resolve() for path in self.paths}:
            messagebox.showerror("AIsharpner", "请选择与原照片不同的保存路径。", parent=self.root)
            return
        image = self.result
        self.set_busy(True)
        self.status.configure(text="正在导出")

        def export():
            encoded = image
            if target.suffix.lower() in (".jpeg", ".jpg") and image.mode == "RGBA":
                encoded = Image.new("RGB", image.size, "white")
                encoded.paste(image, mask=image.getchannel("A"))
            with NamedTemporaryFile(dir=target.parent, suffix=target.suffix, delete=False) as file:
                temporary = Path(file.name)
            try:
                encoded.save(temporary, quality=95)
                temporary.replace(target)
            finally:
                temporary.unlink(missing_ok=True)
            return target

        self.submit(export, lambda saved: self.status.configure(text=f"已保存 · {saved.name}"))


if __name__ == "__main__":
    window = tk.Tk()
    App(window)
    window.mainloop()
