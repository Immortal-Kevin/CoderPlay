"""Teaching examples, never deterministic diagnostic conclusions."""
from dataclasses import replace
from .signals import Parameters

PRESETS = {
    "正常运行": dict(),
    "转子不平衡（1×主导）": dict(harmonics="1:1.5,2:0.04,3:0.02"),
    "不对中（2×成分）": dict(harmonics="1:0.5,2:1.2,3:0.15"),
    "机械松动（多次谐波）": dict(harmonics="1:1,2:0.7,3:0.5,4:0.3,5:0.2,6:0.15"),
    "轴承周期冲击": dict(harmonics="1:0.15", impact_amplitude=3, noise=0.02),
    "调幅与频谱边带": dict(harmonics="", am_amplitude=1, noise=0, fmax=1200),
}


def preset(name):
    return replace(Parameters(), **PRESETS[name])
