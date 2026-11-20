import csv
from dataclasses import asdict
import json
import math
from pathlib import Path
from core.signals import MAX_SAMPLES

MAX_BYTES = 8 * 1024 * 1024


def import_csv(path):
    path = Path(path)
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("CSV 超过8 MiB限制")
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        # Export metadata comments are deliberately ignored for round-trip reads.
        lines = [line for line in stream if not line.lstrip().startswith("#")]
    if not lines or not any(line.strip() for line in lines):
        raise ValueError("CSV 为空")
    sample = "".join(lines[:10])
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    rows = csv.reader(lines, dialect)
    first = next(rows)
    def numeric(row):
        try:
            return len(row) >= 2 and all(math.isfinite(float(v)) for v in row[:2])
        except ValueError:
            return False
    if numeric(first):
        ti, xi = 0, 1
        from itertools import chain
        rows = chain([first], rows)
    else:
        names = [v.strip().lower().replace(" ", "") for v in first]
        def find(aliases):
            found = [i for i, v in enumerate(names) if v in aliases]
            if len(found) != 1:
                raise ValueError("无法唯一识别时间/幅值列；使用 time_s,amplitude 或 时间,幅值")
            return found[0]
        ti = find({"time", "time_s", "time(s)", "t", "时间", "时间(s)"})
        xi = find({"amplitude", "amplitude(au)", "amplitude(a.u.)", "value", "signal", "幅值", "幅值(a.u.)"})
    times, signal = [], []
    for row in rows:
        if not row or not any(v.strip() for v in row):
            continue
        try:
            t, x = float(row[ti]), float(row[xi])
        except (ValueError, IndexError):
            raise ValueError(f"CSV 第{len(times) + 2}行缺少有效数字") from None
        if not math.isfinite(t) or not math.isfinite(x):
            raise ValueError("CSV 含 NaN / Inf")
        times.append(t)
        signal.append(x)
        if len(times) > MAX_SAMPLES:
            raise ValueError(f"CSV 超过{MAX_SAMPLES}点")
    if len(times) < 32:
        raise ValueError("CSV 至少需要32个样本")
    dt = (times[-1] - times[0]) / (len(times) - 1)
    if dt <= 0 or any(abs((b - a) - dt) > max(1e-10, dt * 0.001)
                      for a, b in zip(times, times[1:])):
        raise ValueError("时间必须递增且等间隔（允许0.1%误差），请先重采样")
    return times, signal, 1 / dt


def export_csv(path, result, kind="raw"):
    columns = {
        "raw": ("time_s,amplitude", result.time, result.raw),
        "fft": ("frequency_hz,amplitude", result.frequency, result.amplitude),
        "envelope": ("frequency_hz,envelope_amplitude", result.frequency, result.envelope_amplitude),
    }
    header, xs, ys = columns[kind]
    # Exclusive creation protects input data and previous exports.
    with Path(path).open("x", encoding="utf-8-sig", newline="") as stream:
        stream.write("# FFT Playground 1.0; " + json.dumps({
            "parameters": asdict(result.parameters), "source": result.source,
            "n": len(result.raw), "df_hz": result.df, "kind": kind,
            "bandpass": "circular FFT cosine-edge 10%", "units": "a.u."
        }, ensure_ascii=False) + "\n")
        stream.write(header + "\n")
        writer = csv.writer(stream)
        writer.writerows(zip(xs, ys))
