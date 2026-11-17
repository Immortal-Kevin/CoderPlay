"""Offline inference through a pinned llama.cpp Vulkan executable."""
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

INSTALL_ROOT = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'Chinglish Simulator'
INFERENCE = INSTALL_ROOT / 'inference'
ENGINE = INFERENCE / 'llama-b12466' / 'llama-completion.exe'
MODEL = INFERENCE / 'qwen2.5-1.5b-instruct-q5_k_m.gguf'
MODEL_SIZE = 1285494304
MODEL_NAME = 'Qwen2.5-1.5B-Instruct Q5_K_M'
TEMPERATURE = 0.3
OFFLOADED = re.compile(r'offloaded (\d+)/(\d+) layers to GPU')
TRANSLATION_SCHEMA = {
    'type': 'object',
    'properties': {'translation': {'type': 'string'}, 'analysis': {'type': 'string'}},
    'required': ['translation', 'analysis'], 'additionalProperties': False,
}
def installed():
    return ENGINE.is_file() and MODEL.is_file() and MODEL.stat().st_size == MODEL_SIZE


def environment():
    return {key: value for key, value in os.environ.items()
            if not key.upper().startswith(('LLAMA_', 'GGML_', 'HF_', 'VULKAN_', 'VK_'))}


def generate(system, payload, schema):
    if not installed():
        raise ValueError('本地模型或 Vulkan 推理组件缺失，请运行 setup-local.cmd。')
    data = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
    # Keep special ChatML delimiters inside the JSON data from becoming control tokens.
    data = data.replace('<', r'\u003c').replace('>', r'\u003e')
    prompt = f'<|im_start|>system\n{system}<|im_end|>\n<|im_start|>user\n{data}<|im_end|>\n<|im_start|>assistant\n'
    if len(prompt.encode('utf-8')) > 24000:
        raise ValueError('原文、上下文和示例合计过长，请缩短输入。')
    try:
        with tempfile.TemporaryDirectory(prefix='chinglish-') as scratch:
            path = Path(scratch) / 'prompt.txt'
            path.write_text(prompt, encoding='utf-8')
            args = [str(ENGINE), '--model', str(MODEL), '--file', str(path),
                    '--device', 'Vulkan0', '--gpu-layers', 'all', '--fit', 'off',
                    '--ctx-size', '8192', '--predict', '640', '--temp', str(TEMPERATURE),
                    '--no-conversation', '--no-display-prompt', '--no-escape',
                    '--no-warmup', '--simple-io', '--no-context-shift',
                    '--log-verbosity', '4',
                    '--json-schema', json.dumps(schema)]
            result = subprocess.run(args, cwd=ENGINE.parent, env=environment(), stdin=subprocess.DEVNULL,
                                    capture_output=True, timeout=120, creationflags=subprocess.CREATE_NO_WINDOW,
                                    encoding='utf-8', errors='replace')
    except subprocess.TimeoutExpired:
        raise ValueError('本地推理超时，请缩短输入后重试。') from None
    except OSError:
        raise ValueError('无法启动本地 Vulkan 引擎，请检查核显驱动和本地组件。') from None

    offload = OFFLOADED.search(result.stderr)
    if not offload or offload[1] == '0' or offload[1] != offload[2]:
        raise ValueError('模型未完全加载到 Vulkan 核显，请检查核显驱动和可用显存。')
    if result.returncode:
        raise ValueError('本地推理失败，请缩短文本或检查本地模型文件。')
    try:
        raw = result.stdout.strip()
        output, trailing = json.JSONDecoder().raw_decode(raw)
        if isinstance(output, dict) and raw[trailing:].strip() in ('', '[end of text]'):
            return output
    except ValueError:
        pass
    raise ValueError('本地模型未生成完整结果，请缩短原文或重新生成。')
