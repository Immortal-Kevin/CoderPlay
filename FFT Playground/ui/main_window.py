from dataclasses import fields, replace
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from core.signals import Parameters
from core.spectrum import analyze, peaks
from core.presets import PRESETS, preset
from io_utils.csv_handler import import_csv, export_csv
from io_utils.png_export import export_canvases
from .plots import Plot, BG, FG, BLUE
from .i18n import LocalizedVar, translate


class MainWindow:
    def __init__(self, root):
        self.root = root
        self.language = "zh"
        root.title("FFT Playground · 振动信号与频谱实验室 v1.0")
        # Tk fonts use DPI-scaled points; geometry and Canvas coordinates use pixels.
        # Both must use the same scale (not only SetProcessDpiAwareness).
        self.scale = max(1.0, root.winfo_fpixels("1i") / 96)
        px = lambda value: round(value * self.scale)
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        root.geometry(f"{min(px(1320), sw-px(28))}x{min(px(680), sh-px(90))}")
        root.minsize(min(px(1050), sw-px(28)), min(px(650), sh-px(90)))
        root.configure(bg=BG)
        self.result = None
        self.imported = None
        self.busy = False
        self.closed = False
        self.playing = False
        self.offset = 0
        self.mailbox = queue.Queue()
        self.status = LocalizedVar(root, lambda: self.language, "就绪 · 完全离线 · 教学模拟，频谱特征不构成确定诊断")
        self.info = tk.StringVar(value="")
        self.source = LocalizedVar(root, lambda: self.language, "数据源：数学模型")
        self.vars = {f.name: (tk.BooleanVar(value=getattr(Parameters(), f.name)) if f.name == "remove_dc"
                             else tk.StringVar(value=str(getattr(Parameters(), f.name)))) for f in fields(Parameters)}
        self.style()
        self.build()
        self._text_bindings = []
        def collect(widget):
            if "text" in widget.keys() and widget.cget("text"):
                self._text_bindings.append((widget, widget.cget("text")))
            for child in widget.winfo_children():
                collect(child)
        collect(root)
        self._tab_texts = [self.notebook.tab(tab, "text") for tab in self.notebook.tabs()]
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.after(50, self.poll)
        root.after(100, self.update)

    def style(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure(".", background=BG, foreground=FG, font=("Microsoft YaHei UI", 9))
        s.configure("TFrame", background=BG)
        s.configure("TLabel", background=BG, foreground=FG)
        s.configure("TButton", background=BLUE, foreground="white", borderwidth=0, padding=(8, 5))
        s.map("TButton", background=[("active", "#3289ff"), ("disabled", "#314154")])
        s.configure("TEntry", fieldbackground="#1d2937", foreground=FG, insertcolor=FG, padding=3)
        s.configure("TCombobox", fieldbackground="#1d2937", background="#26374a", foreground=FG, arrowcolor=FG)
        s.map("TCombobox", fieldbackground=[("readonly", "#1d2937")], foreground=[("readonly", FG)])
        s.configure("TNotebook", background=BG, borderwidth=0)
        s.configure("TNotebook.Tab", background="#243245", padding=(10, 5))
        s.map("TNotebook.Tab", background=[("selected", BLUE)])
        s.configure("TCheckbutton", background=BG, foreground=FG)

    def build(self):
        head = ttk.Frame(self.root, padding=(14, 8))
        head.pack(fill="x")
        ttk.Label(head, text="FFT PLAYGROUND", font=("Segoe UI", 17, "bold"), foreground="#63bcff").pack(side="left")
        ttk.Label(head, text="  振动信号与频谱实验室   /   v1.0", font=("Microsoft YaHei UI", 10)).pack(side="left")
        self.language_choice = tk.StringVar(value="中文")
        self.language_switch = ttk.Combobox(head, textvariable=self.language_choice,
                                          values=["中文", "English"], width=10, state="readonly")
        self.language_switch.pack(side="right", padx=(8, 0))
        self.language_switch.bind("<<ComboboxSelected>>", self.change_language)
        ttk.Label(head, text="OFFLINE · CPU", foreground="#70debd").pack(side="right")
        body = ttk.Frame(self.root, padding=(10, 0))
        body.pack(fill="both", expand=True)
        left = ttk.Frame(body, width=round(332 * self.scale))
        left.pack(side="left", fill="y", padx=(0, 12))
        left.pack_propagate(False)
        ttk.Label(left, text="教学场景预设").pack(anchor="w", pady=(0, 4))
        self.preset_name = tk.StringVar(value="正常运行")
        choose = ttk.Combobox(left, textvariable=self.preset_name, values=list(PRESETS), state="readonly")
        self.preset_selector = choose
        choose.pack(fill="x")
        choose.bind("<<ComboboxSelected>>", self.load_preset)
        ttk.Label(left, textvariable=self.source, foreground="#70debd").pack(anchor="w", pady=5)
        notebook = ttk.Notebook(left)
        self.notebook = notebook
        notebook.pack(fill="both", expand=True)
        basic, signal, envelope = (ttk.Frame(notebook, padding=8) for _ in range(3))
        notebook.add(basic, text="采样 / 分析")
        notebook.add(signal, text="信号叠加")
        notebook.add(envelope, text="Envelope")
        def entry(parent, row, name, label):
            ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=4)
            e = ttk.Entry(parent, textvariable=self.vars[name], width=17)
            e.grid(row=row, column=1, sticky="ew", padx=(6, 0), pady=3)
            parent.columnconfigure(1, weight=1)
        for i, (key, label) in enumerate([
                ("fs", "采样率 Fs (Hz)"), ("duration", "时长 T (s)"),
                ("rpm", "转速 RPM"), ("fmax", "频谱上限 (Hz)")]):
            entry(basic, i, key, label)
        ttk.Label(basic, text="FFT 窗函数").grid(row=4, column=0, sticky="w", pady=6)
        ttk.Combobox(basic, textvariable=self.vars["window"], values=["Hann", "Rectangular"], width=15, state="readonly").grid(row=4, column=1, sticky="ew", padx=(6, 0))
        for i, (key, label) in enumerate([("noise", "背景底噪 σ (a.u.)"), ("seed", "随机种子（整数）")], 5):
            entry(basic, i, key, label)
        ttk.Label(basic, text="N = round(Fs × T)，上限 32768 点\nΔf = Fs/N，观测时长为 N/Fs\n\n各图独立：滚轮缩放、拖动平移\n鼠标读取最近采样点；双击重置\n\n播放：循环浏览当前记录的时间窗口\n频谱始终对应完整记录；默认静态\n导入数据后，更新仅重新分析该记录",
                  wraplength=round(295*self.scale), foreground="#a6b7cc").grid(row=7, column=0, columnspan=2, sticky="w", pady=10)
        for i, (key, label) in enumerate([
            ("sine_frequency", "正弦频率 (Hz)"), ("sine_amplitude", "正弦幅值"), ("phase", "正弦相位 (°)"),
            ("harmonics", "倍频:幅值, …"), ("impact_frequency", "周期冲击频率 (Hz)"),
            ("impact_amplitude", "冲击幅值"), ("decay", "冲击衰减 (1/s)"), ("resonance", "共振频率 (Hz)"),
            ("carrier", "调幅载波 (Hz)"), ("modulation", "调制频率 (Hz)"),
            ("depth", "调制深度 [0,1]"), ("am_amplitude", "调幅信号幅值")]):
            entry(signal, i, key, label)
        ttk.Label(signal, text="幅值为0表示关闭；谐波留空表示关闭\n倍频相对 RPM/60；例如 1:1,2:0.3\n正弦、谐波、冲击、噪声、AM 可叠加", wraplength=round(295*self.scale), foreground="#a6b7cc").grid(row=12, column=0, columnspan=2, sticky="w", pady=6)
        entry(envelope, 0, "band_low", "带通下限 (Hz)")
        entry(envelope, 1, "band_high", "带通上限 (Hz)")
        ttk.Checkbutton(envelope, text="包络 FFT 前去除 DC", variable=self.vars["remove_dc"]).grid(row=2, column=0, columnspan=2, sticky="w", pady=7)
        ttk.Label(envelope, text="信号 → 带通 → Hilbert 解析信号\n→ 模值包络 → 可选去 DC → FFT\n\n带通采用频域滤波，带内两端各10%\n余弦过渡，中央80%增益为1。\n边界按周期延拓，记录边缘可能振铃。\n\n包络峰值用于观察重复冲击/调制。\n只有载波位于带通内，包络才有意义。\n\n预设仅为原创数学教学模拟。\n1×、2×、谐波及边带并不唯一对应\n某种故障，不能代替实测诊断。", wraplength=round(295*self.scale), foreground="#a6b7cc").grid(row=3, column=0, columnspan=2, sticky="w", pady=8)
        buttons = ttk.Frame(left)
        buttons.pack(fill="x", pady=(7, 0))
        self.update_button = ttk.Button(buttons, text="生成 / 更新", command=self.update)
        self.update_button.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(buttons, text="恢复默认", command=self.defaults).pack(side="left")
        buttons2 = ttk.Frame(left)
        buttons2.pack(fill="x", pady=5)
        for text, callback in [("开始", self.start), ("暂停", self.pause), ("停止", self.stop), ("说明", self.help)]:
            ttk.Button(buttons2, text=text, command=callback).pack(side="left", fill="x", expand=True, padx=2)
        charts = ttk.Frame(body)
        charts.pack(side="left", fill="both", expand=True)
        ttk.Label(charts, textvariable=self.info, foreground="#a6b7cc").pack(anchor="w", pady=(0, 5))
        self.plots = [Plot(charts, "① 时域波形", "Time (s)", self.status),
                      Plot(charts, "② FFT 幅值频谱", "Frequency (Hz)", self.status, "#65aaff"),
                      Plot(charts, "③ Envelope 包络频谱", "Frequency (Hz)", self.status, "#b793ff")]
        for plot in self.plots:
            plot.pack(fill="both", expand=True, pady=(0, 3))
        footer = ttk.Frame(self.root, padding=(10, 6))
        footer.pack(fill="x")
        for text, callback in [("CSV 导入", self.load_csv), ("导出原始 CSV", lambda: self.save_csv("raw")),
                               ("导出 FFT", lambda: self.save_csv("fft")), ("导出 Envelope", lambda: self.save_csv("envelope")),
                               ("导出 PNG", self.save_png), ("重置视图", self.reset_views), ("峰值检测", self.detect)]:
            ttk.Button(footer, text=text, command=callback).pack(side="left", padx=(0, 5))
        ttk.Label(self.root, textvariable=self.status, padding=(12, 4), anchor="w", foreground="#a6b7cc").pack(fill="x")

    def tr(self, text):
        return translate(text, self.language)

    def error(self, title, text, **kwargs):
        messagebox.showerror(self.tr(title), self.tr(text), parent=self.root)

    def info_dialog(self, title, text, **kwargs):
        messagebox.showinfo(self.tr(title), self.tr(text), parent=self.root)

    def preset_key(self, value):
        return next((key for key in PRESETS if value in (key, translate(key, "en"))), value)

    def change_language(self, _event=None):
        key = self.preset_key(self.preset_name.get())
        self.language = "en" if self.language_choice.get() == "English" else "zh"
        self.root.title(self.tr("FFT Playground · 振动信号与频谱实验室 v1.0"))
        for widget, source in self._text_bindings:
            widget.configure(text=self.tr(source))
        for tab, source in zip(self.notebook.tabs(), self._tab_texts):
            self.notebook.tab(tab, text=self.tr(source))
        self.preset_selector.configure(values=[self.tr(key) for key in PRESETS])
        self.preset_name.set(self.tr(key))
        self.source.refresh()
        self.status.refresh()
        for plot in self.plots:
            plot.language = self.language
            plot.draw()

    def read_parameters(self):
        values = {}
        for f in fields(Parameters):
            value = self.vars[f.name].get()
            if f.name in ("harmonics", "window", "remove_dc"):
                values[f.name] = value
            elif f.name == "seed":
                values[f.name] = int(value)
            else:
                values[f.name] = float(value)
        return Parameters(**values).validate()

    def fill(self, p):
        for key, value in vars(p).items():
            self.vars[key].set(value)

    def load_preset(self, _event=None):
        if self.busy:
            self.status.set("计算中，请稍后再次选择预设")
            return
        self.imported = None
        self.source.set("数据源：数学模型")
        self.fill(preset(self.preset_key(self.preset_name.get())))
        self.update()

    def defaults(self):
        if self.busy: return
        self.preset_name.set(self.tr("正常运行"))
        self.load_preset()

    def run_job(self, function):
        if self.busy:
            return
        self.pause()
        self.busy = True
        self.update_button.configure(state="disabled")
        self.status.set("计算 / 读取中…（可继续操作窗口）")
        def worker():
            try:
                self.mailbox.put((True, function()))
            except Exception as exc:
                self.mailbox.put((False, str(exc)))
        threading.Thread(target=worker, daemon=True, name="fft-worker").start()

    def update(self):
        if self.busy: return
        try:
            p = self.read_parameters()
            if self.imported:
                t, x, fs = self.imported
                if abs(p.fs - fs) > fs * 1e-9 or p.n != len(x):
                    raise ValueError("导入记录的 Fs/T 不可改写；选择预设可返回信号生成")
            data = self.imported[:2] if self.imported else None
            self.run_job(lambda: analyze(p, data))
        except (ValueError, OverflowError) as exc:
            self.error("参数错误", str(exc), parent=self.root)

    def poll(self):
        if self.closed: return
        try:
            ok, payload = self.mailbox.get_nowait()
        except queue.Empty:
            pass
        else:
            self.busy = False
            self.update_button.configure(state="normal")
            if ok:
                if isinstance(payload, tuple):
                    self.result, self.imported = payload
                    self.fill(self.result.parameters)
                    self.source.set("数据源：导入 CSV（原始记录只读）")
                else:
                    self.result = payload
                self.render()
                self.status.set("已更新 · 教学模拟，频谱特征不构成确定诊断；导出使用最后成功计算的参数")
            else:
                self.error("处理失败", payload, parent=self.root)
                self.status.set("处理失败；保留上一次有效结果")
        self.root.after(50, self.poll)

    def render(self):
        a, p = self.result, self.result.parameters
        self.info.set(f"N = {len(a.raw)}   |   Fs = {p.fs:g} Hz   |   Δf = {a.df:.6g} Hz   |   {p.rpm:g} RPM   |   {p.window}   |   {len(a.raw)/p.fs:g} s")
        self.plots[0].set_data(a.time, a.raw, a.time[-1], p.rpm)
        self.plots[1].set_data(a.frequency, a.amplitude, p.fmax, p.rpm, True)
        self.plots[2].set_data(a.frequency, a.envelope_amplitude, p.fmax, p.rpm, True)

    def reset_views(self):
        self.pause()
        for plot in self.plots: plot.reset()

    def detect(self):
        if not self.result: return
        lines = []
        for label, amplitudes in [("FFT", self.result.amplitude), ("Envelope", self.result.envelope_amplitude)]:
            view = self.plots[1 if label == "FFT" else 2].view
            ids = peaks(self.result.frequency, amplitudes, maximum=view[1], minimum=max(0, view[0]))
            lines.append(label + self.tr("（当前频率视图；DC不计）："))
            for i in ids:
                f = self.result.frequency[i]
                lines.append(f"  {f:.6g} Hz   {amplitudes[i]:.6g} a.u.   {f/(self.result.parameters.rpm/60):.3f}×")
        self.info_dialog("峰值检测 · 频率分辨率受 Δf 限制", "\n".join(lines), parent=self.root)

    def start(self):
        if self.playing or not self.result or self.busy: return
        self.playing = True
        self.tick()

    def tick(self):
        if not self.playing or self.closed: return
        a = self.result
        span = (a.time[-1] - a.time[0]) * 0.2
        self.offset = (self.offset + span * 0.08) % max(span, a.time[-1] - a.time[0] - span)
        v = self.plots[0].default_view
        self.plots[0].view = (a.time[0] + self.offset, a.time[0] + self.offset + span, v[2], v[3])
        self.plots[0].draw()
        self.status.set("播放：循环浏览当前时域记录；FFT / Envelope 对应完整记录")
        self.animation_id = self.root.after(120, self.tick)

    def pause(self):
        self.playing = False
        if hasattr(self, "animation_id"):
            self.root.after_cancel(self.animation_id)
            del self.animation_id

    def stop(self):
        self.pause()
        self.offset = 0
        self.plots[0].reset()

    def load_csv(self):
        if self.busy: return
        path = filedialog.askopenfilename(title=self.tr("CSV 导入"), filetypes=[("CSV", "*.csv"), ("All files", "*.*")], parent=self.root)
        if not path: return
        try:
            base = self.read_parameters()
        except ValueError:
            base = Parameters()
        def job():
            t, x, fs = import_csv(path)
            p = replace(base, fs=fs, duration=len(x)/fs, fmax=min(base.fmax, fs/2),
                        band_low=fs*0.15, band_high=fs*0.4, harmonics="", sine_amplitude=0,
                        impact_amplitude=0, am_amplitude=0)
            return analyze(p, (t, x)), (t, x, fs)
        self.run_job(job)

    def save_path(self, extension, title):
        return filedialog.asksaveasfilename(defaultextension=extension, title=self.tr(title + "（请使用新文件名，保护已有数据）"),
                                          filetypes=[(extension.upper()[1:], "*" + extension)], parent=self.root)

    def save_csv(self, kind):
        if not self.result: return
        path = self.save_path(".csv", "导出 " + kind)
        if path:
            try:
                export_csv(path, self.result, kind)
                self.status.set("CSV 已导出（包含最后成功分析的参数），原记录未改写")
            except (OSError, ValueError) as exc:
                self.error("导出失败", str(exc), parent=self.root)

    def save_png(self):
        if not self.result: return
        self.pause()
        path = self.save_path(".png", "导出当前图表视图")
        if path:
            try:
                export_canvases(path, self.plots)
                self.status.set("PNG 已导出（当前三幅图表视图）")
            except (OSError, ValueError) as exc:
                self.error("导出失败", str(exc), parent=self.root)

    def help(self):
        self.info_dialog("参数与原理", "RPM/60 为转频；倍频是该频率的倍数。\n"
            "FFT 单边幅值除以窗权重之和；内部频点×2，DC及偶数N的Nyquist不×2。\n"
            "Hann 为周期窗。Δf=Fs/N，并非峰值插值估计。\n"
            "背景底噪采用高斯白噪声，σ为标准差（a.u.）；0关闭，数值越大噪声越强。\n"
            "固定种子便于比较不同底噪强度。真实监测噪声可能有色、非平稳，并非都符合此模型。相位单位为度。\n"
            "周期冲击是等间隔激励的指数衰减正弦叠加；衰减越大，振铃越短。\n"
            "AM=(1+d cos(2πfm t))A sin(2πfc t)，边带为fc±fm。\n"
            "包络为带通后Hilbert解析信号的模，峰值不是故障确诊。\n"
            "CSV要求等间隔时间（秒），幅值为a.u.；不自动插值或改写原文件。\n"
            "算法上限32768点；计算在线程中进行；无联网、账户或遥测。", parent=self.root)

    def close(self):
        self.closed = True
        self.pause()
        self.root.destroy()
