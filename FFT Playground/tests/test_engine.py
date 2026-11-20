from dataclasses import replace
import cmath
import math
import random
import pytest
from core.signals import Parameters, generate
from core.spectrum import fft, ifft, amplitude_spectrum, analyze, peaks, analytic_envelope
from core.presets import PRESETS, preset


def sine(f, n=4096, fs=4096, a=1):
    return [a * math.sin(2 * math.pi * f * i / fs) for i in range(n)]


@pytest.mark.parametrize("n", [7, 31, 32, 63, 101, 128])
def test_fft_against_independent_dft(n):
    rng = random.Random(7)
    x = [rng.uniform(-1, 1) for _ in range(n)]
    expected = [sum(v * cmath.exp(-2j * math.pi * k * j / n) for j, v in enumerate(x)) for k in range(n)]
    actual = fft(x)
    assert max(abs(a - b) for a, b in zip(actual, expected)) < 1e-10
    assert max(abs(a - b) for a, b in zip(ifft(actual), x)) < 1e-10


@pytest.mark.parametrize("window", ["Hann", "Rectangular"])
def test_50hz_unit_amplitude(window):
    f, a = amplitude_spectrum(sine(50), 4096, window)
    peak = max(range(len(a)), key=a.__getitem__)
    assert f[peak] == 50
    assert abs(a[peak] - 1) <= 0.02


def test_two_tones():
    x = [a + b for a, b in zip(sine(50), sine(100, a=0.7))]
    f, a = amplitude_spectrum(x, 4096)
    ids = peaks(f, a, count=2)
    assert {f[i] for i in ids} == {50, 100}
    assert a[50] == pytest.approx(1, abs=1e-10)
    assert a[100] == pytest.approx(0.7, abs=1e-10)


def test_leakage_and_hann_far_sidelobes():
    _, rect = amplitude_spectrum(sine(50.5), 4096, "Rectangular")
    _, hann = amplitude_spectrum(sine(50.5), 4096, "Hann")
    assert sum(v*v for v in hann[60:200]) < sum(v*v for v in rect[60:200]) * 0.01
    # A non-bin-centred tone has scalloping: do not claim exact peak recovery.
    assert max(hann) < 1


@pytest.mark.parametrize("window", ["Hann", "Rectangular"])
def test_dc_nyquist_and_odd_last_bin(window):
    _, a = amplitude_spectrum([2.0]*128, 128, window)
    assert a[0] == pytest.approx(2)
    _, a = amplitude_spectrum([3*(-1)**i for i in range(128)], 128, window)
    assert a[-1] == pytest.approx(3)
    n = 127
    _, a = amplitude_spectrum([math.cos(2*math.pi*63*i/n) for i in range(n)], 127, "Rectangular")
    assert a[-1] == pytest.approx(1)


def test_impact_envelope_matches_period():
    p = replace(preset("轴承周期冲击"), harmonics="", noise=0)
    a = analyze(p)
    ids = peaks(a.frequency, a.envelope_amplitude, count=3, maximum=100)
    assert a.frequency[ids[0]] == p.impact_frequency
    # Locate maxima within the first half-cycle of ringing following successive events.
    local = []
    for event in range(1, 12):
        start = round(event*p.fs/p.impact_frequency)
        stop = start + round(p.fs/(2*p.resonance)) + 2
        local.append(max(range(start, stop), key=lambda i: abs(a.raw[i])))
    assert all(abs((b-a)/p.fs - 1/p.impact_frequency) < 2/p.fs for a,b in zip(local, local[1:]))
    # Raw FFT and envelope FFT must be different transforms.
    assert a.amplitude != a.envelope_amplitude


def test_am_carrier_sidebands_and_envelope_calibration():
    p = preset("调幅与频谱边带")
    a = analyze(p)
    for frequency, expected in [(1000, 1), (985, 0.3), (1015, 0.3)]:
        i = round(frequency / a.df)
        assert a.amplitude[i] == pytest.approx(expected, abs=1e-9)
    assert a.envelope_amplitude[round(15/a.df)] == pytest.approx(0.6, abs=1e-9)
    assert a.envelope_amplitude[0] < 1e-10
    b = analyze(replace(p, remove_dc=False))
    assert b.envelope_amplitude[0] == pytest.approx(1, abs=1e-9)


def test_bandpass_rejects_out_of_band():
    envelope = analytic_envelope(sine(50), 4096, 600, 1600)
    assert max(envelope) < 1e-10


@pytest.mark.parametrize("fs,duration,rpm", [(4096, 1, 1200), (2048, 2, 2400), (3000, 1.1, 1800)])
def test_sampling_duration_speed(fs, duration, rpm):
    p = replace(Parameters(), fs=fs, duration=duration, rpm=rpm, band_low=fs*.15,
                band_high=fs*.4, harmonics="1:1", noise=0)
    a = analyze(p)
    assert len(a.raw) == round(fs*duration)
    assert a.df == fs / round(fs*duration)
    i = max(range(len(a.amplitude)), key=a.amplitude.__getitem__)
    assert abs(a.frequency[i] - rpm/60) <= a.df


@pytest.mark.parametrize("kwargs", [dict(fs=0), dict(duration=0), dict(duration=1000),
    dict(fs=float("nan")), dict(band_low=0), dict(band_high=2048), dict(band_low=1700),
    dict(sine_amplitude=1, sine_frequency=2048), dict(harmonics="100:1"),
    dict(am_amplitude=1, carrier=2040), dict(depth=2), dict(decay=-1),
    dict(noise=-1), dict(harmonics="1:2:3"), dict(harmonics="nan:1"), dict(rpm=0)])
def test_invalid_parameters(kwargs):
    with pytest.raises(ValueError):
        replace(Parameters(), **kwargs).validate()


def test_noise_seed_and_no_mutation():
    p = Parameters()
    t, x = generate(p)
    assert generate(p) == (t, x)
    original = x.copy()
    analyze(p, (t, x))
    assert x == original
    assert generate(replace(p, seed=43))[1] != x


@pytest.mark.parametrize("name", PRESETS)
def test_presets_valid(name):
    preset(name).validate()
