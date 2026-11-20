from dataclasses import replace
import struct
import zlib
import pytest
from core.signals import Parameters
from core.spectrum import analyze
from io_utils.csv_handler import import_csv, export_csv
from io_utils.png_export import write_png


@pytest.fixture
def result():
    return analyze(replace(Parameters(), duration=.25))


def test_csv_roundtrip_and_no_overwrite(tmp_path, result):
    path = tmp_path / "raw.csv"
    export_csv(path, result)
    before = path.read_bytes()
    t, x, fs = import_csv(path)
    assert t == result.time
    assert x == result.raw
    assert fs == pytest.approx(result.parameters.fs)
    for kind in ("fft", "envelope"):
        target = tmp_path / (kind + ".csv")
        export_csv(target, result, kind)
        assert f'"kind": "{kind}"' in target.read_text(encoding="utf-8-sig")
        assert len(target.read_text(encoding="utf-8-sig").splitlines()) == len(result.frequency)+2
    with pytest.raises(FileExistsError):
        export_csv(path, result)
    assert path.read_bytes() == before


@pytest.mark.parametrize("header", ["幅值;时间", "amplitude;time_s"])
def test_autodetect_swapped_columns(tmp_path, header):
    path = tmp_path / "input.csv"
    path.write_text(header + "\n" + "\n".join(f"{i*2};{i*.001}" for i in range(40)), encoding="utf-8")
    t, x, fs = import_csv(path)
    assert x[10] == 20
    assert fs == pytest.approx(1000)


@pytest.mark.parametrize("content", ["", "time_s,amplitude\n0,1", "time_s,amplitude\n0,nan",
    "unknown,amplitude\n0,1", "time_s,amplitude\n"+"\n".join(f"{i*i},1" for i in range(40)),
    "time_s,amplitude\n"+"\n".join(f"{-i},1" for i in range(40)),
    "time_s,amplitude\n"+"\n".join("0,1" for _ in range(40))])
def test_invalid_csv(tmp_path, content):
    path = tmp_path / "bad.csv"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError):
        import_csv(path)


def test_large_csv(tmp_path):
    path = tmp_path / "large.csv"
    with path.open("wb") as f:
        f.truncate(8*1024*1024+1)
    with pytest.raises(ValueError): import_csv(path)


def test_png_encoder(tmp_path):
    path = tmp_path / "plot.png"
    write_png(path, 2, 1, bytes([255, 0, 0, 0, 255, 0]))
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", data[16:24]) == (2, 1)
    assert zlib.decompress(data[41:-16]) == b"\0\xff\0\0\0\xff\0"
