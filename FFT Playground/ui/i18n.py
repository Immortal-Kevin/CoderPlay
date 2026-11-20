"""Offline UI translations. Engine identifiers, data and units remain unchanged."""
import re
import tkinter as tk

EN = {
    "FFT Playground · 振动信号与频谱实验室 v1.0": "FFT Playground · Vibration & Spectrum Lab v1.0",
    "  振动信号与频谱实验室   /   v1.0": "  Vibration & Spectrum Lab   /   v1.0",
    "教学场景预设": "Teaching preset",
    "正常运行": "Normal operation",
    "正常运行（有底噪）": "Normal operation (background noise)",
    "转子不平衡（1×主导）": "Rotor imbalance (1x dominant)",
    "不对中（2×成分）": "Misalignment (2x component)",
    "机械松动（多次谐波）": "Mechanical looseness (harmonics)",
    "轴承周期冲击": "Bearing periodic impacts",
    "调幅与频谱边带": "AM and spectral sidebands",
    "数据源：数学模型": "Source: mathematical model",
    "数据源：导入 CSV（原始记录只读）": "Source: imported CSV (read-only record)",
    "采样 / 分析": "Sampling / Analysis", "信号叠加": "Signal mix",
    "采样率 Fs (Hz)": "Sample rate Fs (Hz)", "时长 T (s)": "Duration T (s)",
    "转速 RPM": "Speed RPM", "频谱上限 (Hz)": "Max frequency (Hz)",
    "FFT 窗函数": "FFT window", "背景底噪 σ (a.u.)": "Background σ (a.u.)",
    "随机种子（整数）": "Seed (integer)",
    "正弦频率 (Hz)": "Sine frequency (Hz)", "正弦幅值": "Sine amplitude",
    "正弦相位 (°)": "Sine phase (deg)", "倍频:幅值, …": "Order:amplitude, ...",
    "周期冲击频率 (Hz)": "Impact rate (Hz)", "冲击幅值": "Impact amplitude",
    "冲击衰减 (1/s)": "Decay (1/s)", "共振频率 (Hz)": "Resonance (Hz)",
    "调幅载波 (Hz)": "Carrier (Hz)", "调制频率 (Hz)": "Modulation (Hz)",
    "调制深度 [0,1]": "AM depth [0,1]", "调幅信号幅值": "AM amplitude",
    "带通下限 (Hz)": "Band low (Hz)", "带通上限 (Hz)": "Band high (Hz)",
    "包络 FFT 前去除 DC": "Remove DC before envelope FFT",
    "生成 / 更新": "Generate / Update", "恢复默认": "Defaults",
    "开始": "Start", "暂停": "Pause", "停止": "Stop", "说明": "Help",
    "CSV 导入": "Import CSV", "导出原始 CSV": "Export raw CSV",
    "导出 FFT": "Export FFT", "导出 Envelope": "Export Envelope", "导出 PNG": "Export PNG",
    "重置视图": "Reset views", "峰值检测": "Detect peaks",
    "① 时域波形": "1. Time waveform", "② FFT 幅值频谱": "2. FFT amplitude spectrum",
    "③ Envelope 包络频谱": "3. Envelope spectrum",
    "N = round(Fs × T)，上限 32768 点\nΔf = Fs/N，观测时长为 N/Fs\n\n各图独立：滚轮缩放、拖动平移\n鼠标读取最近采样点；双击重置\n\n播放：循环浏览当前记录的时间窗口\n频谱始终对应完整记录；默认静态\n导入数据后，更新仅重新分析该记录":
        "N = round(Fs × T), max 32768 samples\nΔf = Fs/N; record duration = N/Fs\n\nWheel: zoom; drag: pan (per plot)\nHover: nearest sample; double-click: reset\n\nPlayback scrolls through this record.\nSpectra use the full record; static by default.\nImported records are reanalyzed on Update.",
    "幅值为0表示关闭；谐波留空表示关闭\n倍频相对 RPM/60；例如 1:1,2:0.3\n正弦、谐波、冲击、噪声、AM 可叠加":
        "Amplitude 0 disables a component.\nBlank harmonics disables the orders.\nOrders use RPM/60; e.g. 1:1,2:0.3\nSine, harmonics, impacts, noise and AM mix.",
    "信号 → 带通 → Hilbert 解析信号\n→ 模值包络 → 可选去 DC → FFT\n\n带通采用频域滤波，带内两端各10%\n余弦过渡，中央80%增益为1。\n边界按周期延拓，记录边缘可能振铃。\n\n包络峰值用于观察重复冲击/调制。\n只有载波位于带通内，包络才有意义。\n\n预设仅为原创数学教学模拟。\n1×、2×、谐波及边带并不唯一对应\n某种故障，不能代替实测诊断。":
        "Signal → bandpass → Hilbert analytic signal\n→ magnitude envelope → optional DC removal\n→ FFT\n\nFFT bandpass: 10% cosine edge transitions;\ncentral 80% has unity gain. Circular edges\nmay ring. Keep the carrier within the band.\n\nEnvelope peaks show repetition/modulation.\nTeaching models only: orders, harmonics\nand sidebands are not unique fault evidence.\nThey cannot replace field diagnosis.",
    "就绪 · 完全离线 · 教学模拟，频谱特征不构成确定诊断": "Ready · Offline · Teaching simulation; spectral features are not a confirmed diagnosis",
    "计算中，请稍后再次选择预设": "Computing; select the preset again when finished",
    "计算 / 读取中…（可继续操作窗口）": "Computing / reading... (window remains responsive)",
    "已更新 · 教学模拟，频谱特征不构成确定诊断；导出使用最后成功计算的参数": "Updated · Teaching simulation, not a confirmed diagnosis; exports use the last successful analysis",
    "处理失败；保留上一次有效结果": "Processing failed; previous valid result retained",
    "播放：循环浏览当前时域记录；FFT / Envelope 对应完整记录": "Playing: scroll through the time record; FFT / Envelope use the full record",
    " a.u.   | 滚轮缩放 · 拖动平移 · 双击重置": " a.u.   | Wheel: zoom · Drag: pan · Double-click: reset",
    "参数错误": "Invalid parameters", "处理失败": "Processing failed", "导出失败": "Export failed",
    "参数与原理": "Parameters and principles", "运行错误": "Runtime error", "完整日志：": "Full log: ",
    "峰值检测 · 频率分辨率受 Δf 限制": "Peak detection · Frequency resolution is limited by Δf",
    "（当前频率视图；DC不计）：": " (current frequency view; DC excluded):",
    "（请使用新文件名，保护已有数据）": " (use a new filename to protect existing data)",
    "导出当前图表视图": "Export current chart views", "导出 ": "Export ",
    "CSV 已导出（包含最后成功分析的参数），原记录未改写": "CSV exported with last successful analysis parameters; original record unchanged",
    "PNG 已导出（当前三幅图表视图）": "PNG exported (current three chart views)",
    "导入记录的 Fs/T 不可改写；选择预设可返回信号生成": "Cannot change Fs/sample count of an imported record; select a preset to generate signals",
    "RPM/60 为转频；倍频是该频率的倍数。": "RPM/60 is shaft frequency; orders are multiples of it.",
    "FFT 单边幅值除以窗权重之和；内部频点×2，DC及偶数N的Nyquist不×2。": "Single-sided FFT divides by the window sum; interior bins ×2, DC/even-N Nyquist unchanged.",
    "Hann 为周期窗。Δf=Fs/N，并非峰值插值估计。": "Hann is periodic. Δf=Fs/N; peaks are not interpolated.",
    "背景底噪采用高斯白噪声，σ为标准差（a.u.）；0关闭，数值越大噪声越强。": "Background noise is Gaussian white noise; σ is its standard deviation (a.u.). Zero disables it.",
    "固定种子便于比较不同底噪强度。真实监测噪声可能有色、非平稳，并非都符合此模型。相位单位为度。": "Use a fixed seed to compare noise levels. Real noise may be colored/nonstationary. Phase is in degrees.",
    "周期冲击是等间隔激励的指数衰减正弦叠加；衰减越大，振铃越短。": "Periodic impacts sum equally spaced decaying sinusoids; higher decay shortens ringing.",
    "AM=(1+d cos(2πfm t))A sin(2πfc t)，边带为fc±fm。": "AM=(1+d cos(2πfm t))A sin(2πfc t); sidebands are at fc±fm.",
    "包络为带通后Hilbert解析信号的模，峰值不是故障确诊。": "Envelope is the magnitude of the bandpassed Hilbert analytic signal; peaks do not confirm faults.",
    "CSV要求等间隔时间（秒），幅值为a.u.；不自动插值或改写原文件。": "CSV needs uniform time steps (seconds), amplitudes in a.u.; no automatic resampling or source rewriting.",
    "算法上限32768点；计算在线程中进行；无联网、账户或遥测。": "Maximum 32768 samples; background computation; no networking, accounts or telemetry.",
    "谐波格式为 倍频:幅值，例如 1:1,2:0.3,3:0.1（最多32项）": "Use order:amplitude, e.g. 1:1,2:0.3,3:0.1 (max 32 terms)",
    " 必须为有限数值": " must be finite",
    "Fs、T 必须大于0，样本数 round(Fs×T) 必须在 32–": "Fs and T must be positive; round(Fs×T) must be within 32–",
    "RPM 必须大于0；显示上限必须在 (0, Fs/2]": "RPM must be positive; display maximum must be within (0, Fs/2]",
    "包络频带必须满足 0 < 下限 < 上限 < Nyquist (Fs/2)": "Envelope band must satisfy 0 < low < high < Nyquist (Fs/2)",
    "仅支持 Hann / Rectangular": "Only Hann / Rectangular windows are supported",
    "信号幅值及噪声强度不得为负": "Signal amplitudes and noise strength must not be negative",
    "随机种子必须为整数": "Random seed must be an integer",
    "冲击衰减必须大于0；调制深度必须在 [0,1]": "Impact decay must be positive; AM depth must be within [0,1]",
    "调制频率必须在 (0, 载波频率)": "Modulation frequency must be within (0, carrier frequency)",
    "启用信号的所有频率（含倍频及边带）必须小于 Nyquist 并大于0": "All active frequencies, including orders and sidebands, must be positive and below Nyquist",
    "FFT 输入不能为空": "FFT input must not be empty", "FFT 样本数或采样率无效": "Invalid FFT sample count or sample rate",
    "信号不得包含 NaN / Inf": "Signal must not contain NaN / Inf", "未知窗函数": "Unknown window",
    "包络滤波频带无效": "Invalid envelope filter band", "导入记录长度与采样参数不一致": "Imported length does not match sampling parameters",
    "CSV 超过8 MiB限制": "CSV exceeds the 8 MiB limit", "CSV 为空": "CSV is empty",
    "CSV 含 NaN / Inf": "CSV contains NaN / Inf", "CSV 至少需要32个样本": "CSV needs at least 32 samples",
    "无法唯一识别时间/幅值列；使用 time_s,amplitude 或 时间,幅值": "Cannot uniquely identify time/amplitude columns; use time_s,amplitude",
    "时间必须递增且等间隔（允许0.1%误差），请先重采样": "Time must increase with uniform steps (0.1% tolerance); resample first",
    "PNG 图表导出需要 Windows GDI": "PNG chart export requires Windows GDI",
    "无法创建 PNG 渲染缓冲区": "Cannot create PNG rendering buffer",
}


def translate(text, language="zh"):
    text = str(text)
    if language != "en":
        return text
    if text in EN:
        return EN[text]
    match = re.fullmatch(r"CSV 第(\d+)行缺少有效数字", text)
    if match:
        return f"CSV line {match[1]} has missing or invalid numbers"
    match = re.fullmatch(r"CSV 超过(\d+)点", text)
    if match:
        return f"CSV exceeds {match[1]} samples"
    for source in sorted(EN, key=len, reverse=True):
        text = text.replace(source, EN[source])
    return text


class LocalizedVar(tk.StringVar):
    """Keep the source message so switching back never reverse-translates text."""
    def __init__(self, master, language, value):
        self.language = language
        self.original = value
        super().__init__(master)
        self.refresh()

    def set(self, value):
        self.original = value
        self.refresh()

    def refresh(self):
        super().set(translate(self.original, self.language()))
