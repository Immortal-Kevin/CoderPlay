"""Original radix-2/Bluestein FFT, coherent-gain amplitude, analytic envelope.

No numerical library is required. FFT conventions match rfft/rfftfreq:
forward unnormalized; inverse divided by N. Arbitrary record lengths are exact,
not silently zero-padded. The envelope bandpass is a circular frequency-domain
filter with cosine transitions inside the requested band (10% each edge).
"""
from dataclasses import dataclass
import cmath
import math
from .signals import Parameters, MAX_SAMPLES, generate


def _radix2(values, inverse=False):
    a = list(map(complex, values))
    n = len(a)
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j ^= bit
        if i < j:
            a[i], a[j] = a[j], a[i]
    size = 2
    while size <= n:
        root = cmath.exp((2j if inverse else -2j) * math.pi / size)
        for start in range(0, n, size):
            w = 1 + 0j
            for k in range(start, start + size // 2):
                u, v = a[k], w * a[k + size // 2]
                a[k], a[k + size // 2] = u + v, u - v
                w *= root
        size *= 2
    return [v / n for v in a] if inverse else a


def fft(values):
    n = len(values)
    if not n:
        raise ValueError("FFT 输入不能为空")
    if n & (n - 1) == 0:
        return _radix2(values)
    # Bluestein chirp convolution; internal padding never changes the DFT grid.
    m = 1 << (2 * n - 1).bit_length()
    chirp = [cmath.exp(-1j * math.pi * ((k * k) % (2 * n)) / n) for k in range(n)]
    a, b = [0j] * m, [0j] * m
    for k in range(n):
        a[k] = values[k] * chirp[k]
        b[k] = chirp[k].conjugate()
        if k:
            b[m - k] = b[k]
    fa, fb = _radix2(a), _radix2(b)
    conv = _radix2([u * v for u, v in zip(fa, fb)], inverse=True)
    return [conv[k] * chirp[k] for k in range(n)]


def ifft(values):
    n = len(values)
    return [v.conjugate() / n for v in fft([complex(v).conjugate() for v in values])]


def rfft(values):
    return fft(values)[:len(values) // 2 + 1]


def rfftfreq(n, fs):
    return [k * fs / n for k in range(n // 2 + 1)]


def amplitude_spectrum(x, fs, window="Hann", remove_dc=False):
    n = len(x)
    if n < 2 or n > MAX_SAMPLES or not math.isfinite(fs) or fs <= 0:
        raise ValueError("FFT 样本数或采样率无效")
    if any(not math.isfinite(v) for v in x):
        raise ValueError("信号不得包含 NaN / Inf")
    if window not in ("Hann", "Rectangular"):
        raise ValueError("未知窗函数")
    mean = math.fsum(x) / n if remove_dc else 0
    # Periodic Hann gives exact coherent gain 0.5 and bin-centred amplitudes.
    w = [0.5 - 0.5 * math.cos(2 * math.pi * i / n) for i in range(n)] if window == "Hann" else [1.0] * n
    gain = math.fsum(w)
    transformed = rfft([(v - mean) * wi for v, wi in zip(x, w)])
    a = [abs(v) / gain for v in transformed]
    for k in range(1, len(a)):
        if not (n % 2 == 0 and k == n // 2):
            a[k] *= 2
    return rfftfreq(n, fs), a


def analytic_envelope(x, fs, low, high):
    if not 0 < low < high < fs / 2:
        raise ValueError("包络滤波频带无效")
    n = len(x)
    coefficients = fft(x)
    analytic = [0j] * n
    transition = (high - low) * 0.1
    for k in range(1, (n + 1) // 2):
        f = k * fs / n
        if low < f < high:
            edge = min(f - low, high - f)
            weight = 0.5 - 0.5 * math.cos(math.pi * edge / transition) if edge < transition else 1
            # Positive frequencies doubled; negatives suppressed: Hilbert analytic signal.
            analytic[k] = 2 * coefficients[k] * weight
    return [abs(v) for v in ifft(analytic)]


def peaks(f, a, count=5, minimum=0, maximum=float("inf")):
    candidates = [i for i in range(1, len(a) - 1)
                  if minimum <= f[i] <= maximum and a[i] > a[i - 1] and a[i] >= a[i + 1]]
    if len(a) > 1 and minimum <= f[-1] <= maximum and a[-1] > a[-2]:
        candidates.append(len(a) - 1)
    selected = []
    threshold = max(a, default=0) * 0.01
    for i in sorted(candidates, key=lambda i: a[i], reverse=True):
        if a[i] > threshold and all(abs(i - j) > 1 for j in selected):
            selected.append(i)
            if len(selected) == count:
                break
    return selected


@dataclass(frozen=True)
class Analysis:
    parameters: Parameters
    time: list
    raw: list
    frequency: list
    amplitude: list
    envelope: list
    envelope_amplitude: list
    source: str = "generated"

    @property
    def df(self):
        return self.parameters.fs / len(self.raw)


def analyze(p, imported=None):
    p.validate()
    t, raw = generate(p) if imported is None else (list(imported[0]), list(imported[1]))
    if len(t) != p.n or len(raw) != p.n:
        raise ValueError("导入记录长度与采样参数不一致")
    f, a = amplitude_spectrum(raw, p.fs, p.window)
    envelope = analytic_envelope(raw, p.fs, p.band_low, p.band_high)
    _, ea = amplitude_spectrum(envelope, p.fs, p.window, p.remove_dc)
    return Analysis(p, t, raw, f, a, envelope, ea,
                    "generated" if imported is None else "imported")
