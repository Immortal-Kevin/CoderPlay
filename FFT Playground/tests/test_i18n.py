"""Pure translation checks; numerical engine remains GUI-independent."""
import ast
from pathlib import Path
import re
import pytest
from core.presets import PRESETS
from core.signals import Parameters
from dataclasses import replace
from ui.i18n import translate


def han(text):
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def test_ui_static_translation_coverage():
    root = Path(__file__).resolve().parents[1]
    for filename in ("ui/main_window.py", "ui/plots.py"):
        for node in ast.walk(ast.parse((root/filename).read_text(encoding="utf-8"))):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and han(node.value):
                if node.value == "中文":  # Intentional native-language selector label.
                    continue
                assert not han(translate(node.value, "en")), (filename, node.value)
                assert translate(node.value, "zh") == node.value
    assert len({translate(key, "en") for key in PRESETS}) == len(PRESETS)


@pytest.mark.parametrize("changes", [dict(band_high=2048), dict(harmonics="bad"), dict(noise=-1),
    dict(fs=0), dict(seed=.5), dict(am_amplitude=1, carrier=2040), dict(depth=2), dict(fs=float("nan"))])
def test_validation_errors_translated_at_ui_boundary(changes):
    with pytest.raises(ValueError) as caught:
        replace(Parameters(), **changes).validate()
    assert not han(translate(str(caught.value), "en"))


@pytest.mark.parametrize("source,expected", [
    ("CSV 第17行缺少有效数字", "CSV line 17 has missing or invalid numbers"),
    ("CSV 超过32768点", "CSV exceeds 32768 samples"),
    ("导出 raw（请使用新文件名，保护已有数据）", "Export raw (use a new filename to protect existing data)"),
])
def test_dynamic_messages(source, expected):
    assert translate(source, "en") == expected
