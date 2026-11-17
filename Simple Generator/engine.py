import logging
import os
import secrets
from pathlib import Path

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
ROOT = Path(__file__).resolve().parent
MODELS = ROOT / "models"
SIZES = {(640, 640), (768, 768), (1024, 1024), (1080, 1080),
         (640, 360), (960, 540), (1280, 720), (1600, 900), (1920, 1080)}
STYLES = {"photo": "", "comic": "manga illustration, ink outlines, cel shading",
          "oil": "oil painting, expressive brushwork, textured canvas"}
base = styled = translator = None
log = logging.getLogger("simple_generator.generation")


def require(name):
    path = MODELS / name
    if not path.exists():
        raise RuntimeError(f"缺少本地模型 models/{name}，请参照 README 安装。")
    return str(path)


def translate(values):
    global translator
    if not any(values):
        return values
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    if translator is None:
        path = require("translate")
        translator = (AutoTokenizer.from_pretrained(path, local_files_only=True),
                      AutoModelForSeq2SeqLM.from_pretrained(path, local_files_only=True).eval())
    tokenizer, model = translator
    output = []
    for value in values:
        if not any("\u3400" <= c <= "\u9fff" for c in value):
            output.append(value)
            continue
        inputs = tokenizer(value, return_tensors="pt", truncation=True, max_length=512)
        tokens = model.generate(**inputs, max_new_tokens=256)
        output.append(tokenizer.decode(tokens[0], skip_special_tokens=True))
    return output


def generate(settings, progress, publish):
    global base, styled
    log.info("stage=model_load style=%s", settings["style"])
    checkpoint = require("Chilloutmix.safetensors")
    config = require("sd15")
    style = settings["style"]
    control_path = require("controlnet-canny") if style != "photo" else None
    import torch
    from PIL import Image
    from diffusers import (ControlNetModel, StableDiffusionControlNetImg2ImgPipeline,
                           StableDiffusionPipeline)

    device = "cpu"
    if torch.cuda.is_available():
        device = "cuda"
    elif torch.xpu.is_available():
        device = "xpu"
    dtype = torch.float32 if device == "cpu" else torch.float16
    if base is None:
        pipeline = StableDiffusionPipeline.from_single_file(
            checkpoint, config=config, local_files_only=True, torch_dtype=dtype,
            safety_checker=None, feature_extractor=None, requires_safety_checker=False)
        pipeline.enable_attention_slicing()
        pipeline.vae.enable_tiling()
        base = pipeline.to(device)
    if control_path and styled is None:
        control = ControlNetModel.from_pretrained(control_path, local_files_only=True, torch_dtype=dtype)
        pipeline = StableDiffusionControlNetImg2ImgPipeline(
            **base.components, controlnet=control,
            requires_safety_checker=False)
        pipeline.enable_attention_slicing()
        styled = pipeline.to(device)

    width, height = settings["size"]
    # Render at a moderate SD 1.5 resolution, then scale to the chosen output size.
    ratio = min(1, 768 / max(width, height))
    render_width = round(width * ratio / 8) * 8
    render_height = round(height * ratio / 8) * 8
    steps = 16 + 3 * settings["detail"]
    guidance = 10 - settings["freedom"] * 0.55
    colors = ("muted palette" if settings["color"] <= 3 else
              "rich vibrant colors" if settings["color"] >= 7 else "")
    prompt = ", ".join(filter(None, [settings["positive"], colors]))
    total = settings["rounds"] * settings["count"]
    stages = 2 if control_path else 1

    def callback(index, stage, length, label):
        def update(pipe, step, timestep, values):
            progress((index + (stage + min(1, (step + 1) / length)) / stages) / total,
                     f"第 {index + 1}/{total} 张 · {label} · {values['latents'].device}")
            return values
        return update

    log.info("stage=pipeline_ready device=%s", device)
    failed = 0
    for index in range(total):
        try:
            log.info("stage=text_to_image image=%d/%d", index + 1, total)
            args = dict(negative_prompt=settings["negative"], width=render_width,
                        height=render_height, num_inference_steps=steps,
                        guidance_scale=guidance,
                        generator=torch.Generator(device="cpu").manual_seed(secrets.randbits(32)))
            result = base(prompt=prompt, **args,
                          callback_on_step_end=callback(index, 0, steps, "写实底图"))
            image = result.images[0]
            if control_path:
                log.info("stage=controlnet_preprocess image=%d/%d", index + 1, total)
                import cv2
                import numpy as np
                edge = cv2.Canny(cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2GRAY), 90, 180)
                strength = 0.67
                log.info("stage=controlnet_img2img image=%d/%d", index + 1, total)
                result = styled(prompt=f"{STYLES[style]}, {prompt}", image=image,
                                control_image=Image.fromarray(edge).convert("RGB"),
                                strength=strength, controlnet_conditioning_scale=0.7, **args,
                                callback_on_step_end=callback(index, 1, int(steps * strength), "风格转换"))
                image = result.images[0]
            log.info("stage=preview_output image=%d/%d", index + 1, total)
            publish(image.resize((width, height), Image.Resampling.LANCZOS))
        except (RuntimeError, ValueError, OSError):
            failed += 1
            log.exception("单张生成失败 image=%d/%d", index + 1, total)
            progress((index + 1) / total, f"第 {index + 1}/{total} 张生成失败")
    return failed
