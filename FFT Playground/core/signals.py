"""Original deterministic mathematical models; no diagnostic database."""
from dataclasses import dataclass
import cmath
import math
import random

MAX_SAMPLES = 32768


@dataclass(frozen=True)
class Parameters:
    fs: float = 4096
    duration: float = 2
    rpm: float = 1800
    window: str = "Hann"
    fmax: float = 500
    band_low: float = 600
    band_high: float = 1600
    remove_dc: bool = True
    sine_frequency: float = 50
    sine_amplitude: float = 0
    phase: float = 0
    harmonics: str = "1:1,2:0.08,3:0.03"
    impact_frequency: float = 12
    impact_amplitude: float = 0
    decay: float = 180
    resonance: float = 1000
    noise: float = 0.025
    seed: int = 42
    carrier: float = 1000
    modulation: float = 15
    depth: float = 0.6
    am_amplitude: float = 0

    @property
    def n(self):
        return round(self.fs * self.duration)

    def harmonic_terms(self):
        if not self.harmonics.strip():
            return []
        try:
            pairs = [tuple(map(float, item.strip().split(":")))
                     for item in self.harmonics.split(",")]
            if len(pairs) > 32 or any(len(p) != 2 for p in pairs):
                raise ValueError
            if any(not all(math.isfinite(v) for v in p) or p[0] <= 0
                   or p[1] < 0 for p in pairs):
                raise ValueError
            return pairs
        except (ValueError, TypeError):
            raise ValueError("谐波格式为 倍频:幅值，例如 1:1,2:0.3,3:0.1（最多32项）") from None

    def validate(self):
        for key, value in vars(self).items():
            if isinstance(value, (float, int)) and not math.isfinite(value):
                raise ValueError(f"{key} 必须为有限数值")
        if self.fs <= 0 or self.duration <= 0 or not 32 <= self.n <= MAX_SAMPLES:
            raise ValueError(f"Fs、T 必须大于0，样本数 round(Fs×T) 必须在 32–{MAX_SAMPLES}")
        if self.rpm <= 0 or not 0 < self.fmax <= self.fs / 2:
            raise ValueError("RPM 必须大于0；显示上限必须在 (0, Fs/2]")
        if not 0 < self.band_low < self.band_high < self.fs / 2:
            raise ValueError("包络频带必须满足 0 < 下限 < 上限 < Nyquist (Fs/2)")
        if self.window not in ("Hann", "Rectangular"):
            raise ValueError("仅支持 Hann / Rectangular")
        if any(v < 0 for v in (self.sine_amplitude, self.impact_amplitude,
                              self.am_amplitude, self.noise)):
            raise ValueError("信号幅值及噪声强度不得为负")
        if not isinstance(self.seed, int):
            raise ValueError("随机种子必须为整数")
        if self.decay <= 0 or not 0 <= self.depth <= 1:
            raise ValueError("冲击衰减必须大于0；调制深度必须在 [0,1]")
        frequencies = [m * self.rpm / 60 for m, a in self.harmonic_terms() if a]
        if self.sine_amplitude:
            frequencies.append(self.sine_frequency)
        if self.impact_amplitude:
            frequencies.extend((self.impact_frequency, self.resonance))
        if self.am_amplitude:
            if not 0 < self.modulation < self.carrier:
                raise ValueError("调制频率必须在 (0, 载波频率)")
            frequencies.extend((self.carrier - self.modulation,
                                self.carrier + self.modulation))
        if any(not 0 < f < self.fs / 2 for f in frequencies):
            raise ValueError("启用信号的所有频率（含倍频及边带）必须小于 Nyquist 并大于0")
        return self


def generate(p: Parameters):
    p.validate()
    times = [i / p.fs for i in range(p.n)]
    x = [0.0] * p.n
    terms = [(m * p.rpm / 60, a, 0) for m, a in p.harmonic_terms()]
    terms.append((p.sine_frequency, p.sine_amplitude, math.radians(p.phase)))
    for f, a, phase in terms:
        if a:
            for i, t in enumerate(times):
                x[i] += a * math.sin(2 * math.pi * f * t + phase)
    if p.am_amplitude:
        for i, t in enumerate(times):
            x[i] += p.am_amplitude * (1 + p.depth * math.cos(2 * math.pi * p.modulation * t)) * math.sin(2 * math.pi * p.carrier * t)
    if p.impact_amplitude:
        # Continuous-time impacts sampled at Fs; include ring-down from every impact.
        pole = complex(-p.decay, 2 * math.pi * p.resonance)
        step = complex(math.cos(2 * math.pi * p.resonance / p.fs),
                       math.sin(2 * math.pi * p.resonance / p.fs)) * math.exp(-p.decay / p.fs)
        ring = 0j
        event = 0
        for i, t in enumerate(times):
            ring *= step
            while event / p.impact_frequency <= t + 1e-12:
                delay = t - event / p.impact_frequency
                ring += p.impact_amplitude * cmath.exp(pole * delay)
                event += 1
            x[i] += ring.imag
    if p.noise:
        rng = random.Random(p.seed)
        for i in range(p.n):
            x[i] += rng.gauss(0, p.noise)
    return times, x
