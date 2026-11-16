"""Photo decoding and Intel-only tiled super-resolution."""

from pathlib import Path
from time import monotonic
from io import BytesIO

import numpy as np
import openvino as ov
from openvino import opset11 as ops
from PIL import Image, ImageCms, ImageOps
from pillow_heif import register_heif_opener
import rawpy

register_heif_opener()

RAW = {".cr2", ".cr3", ".nef", ".nrw", ".arw", ".sr2", ".dng",
       ".raf", ".rw2", ".orf", ".pef", ".srw"}
MODEL = Path(__file__).parent / "models" / "realesr-general-wdn-x4v3.xml"
MAX_PIXELS = 48_000_000
MAX_BATCH_SOURCE_PIXELS = 96_000_000
HEIGHT, WIDTH, HALO = 256, 256, 44
STEP_X, STEP_Y = WIDTH - 2 * HALO, HEIGHT - 2 * HALO


def check_size(width, height, limit=MAX_PIXELS):
    if min(width, height) < 1 or width * height > limit:
        raise ValueError(f"图像需至少为 1 × 1，且不能超过 {limit // 10_000} 万像素。")


def read_photo(path, limit=MAX_PIXELS):
    extension = Path(path).suffix.lower()
    if extension in RAW:
        try:
            with rawpy.imread(str(path)) as raw:
                check_size(raw.sizes.width, raw.sizes.height, limit)
                image = Image.fromarray(raw.postprocess(use_camera_wb=True))
        except rawpy.LibRawError as error:
            raise ValueError(f"无法解码 RAW 照片：{error}") from error
        check_size(*image.size, limit)
        return image, extension[1:].upper() + " · RAW"

    with Image.open(path) as source:
        check_size(*source.size, limit)
        image = ImageOps.exif_transpose(source)
        alpha = image.convert("RGBA").getchannel("A") if (
            "A" in image.getbands() or "transparency" in image.info
        ) else None
        profile = image.info.get("icc_profile")
        if profile:
            try:
                color = image if image.mode in ("RGB", "L", "CMYK", "LAB") else image.convert("RGB")
                image = ImageCms.profileToProfile(
                    color, BytesIO(profile), ImageCms.createProfile("sRGB"), outputMode="RGB"
                )
            except (ValueError, OSError, ImageCms.PyCMSError):
                image = image.convert("RGB")
        else:
            image = image.convert("RGB")
        if alpha is not None:
            image.putalpha(alpha)
        return image, source.format


def available_devices(core):
    devices = {}
    for device in core.available_devices:
        if device.split(".")[0] not in ("GPU", "NPU"):
            continue
        try:
            name = core.get_property(device, "FULL_DEVICE_NAME")
            if "intel" not in name.lower():
                continue
            if device.startswith("GPU"):
                kind = core.get_property(device, "DEVICE_TYPE")
                if str(kind).split(".")[-1].upper() != "INTEGRATED":
                    continue
            devices[device] = name
        except RuntimeError:
            continue
    return devices


def output_size(size, scale):
    return tuple(max(1, round(dimension * scale)) for dimension in size)


def resize(node, height, width, mode):
    return ops.interpolate(
        node, np.array([height, width], np.int64), mode, "sizes",
        coordinate_transformation_mode="half_pixel", axes=np.array([2, 3], np.int64)
    )


def processing_graph(core, scale, sharpen, detail):
    model = core.read_model(MODEL)
    photo = model.get_parameters()[0]
    reconstructed = model.output(0).get_node().input_value(0)
    out_w, out_h = output_size((WIDTH, HEIGHT), scale)
    baseline = photo if scale == 1 else resize(photo, out_h, out_w, "cubic")
    # Area-pool before reducing the model's 4× output to small output sizes.
    if scale <= 2:
        factor = 4 if scale <= 1 else 2
        reconstructed = ops.avg_pool(reconstructed, [factor, factor], [0, 0], [0, 0],
                                     [factor, factor], True)
    model_image = reconstructed if scale in (1, 2) else resize(
        reconstructed, out_h, out_w, "linear"
    )
    luma_weights = np.array([0.2126, 0.7152, 0.0722], np.float32).reshape(1, 3, 1, 1)

    def luma(rgb):
        return ops.reduce_sum(ops.multiply(rgb, luma_weights), np.array([1], np.int64), True)

    def high_pass(signal, radius):
        width = 2 * radius + 1
        low = ops.avg_pool(signal, [1, 1], [radius, radius], [radius, radius],
                           [width, width], True)
        return ops.subtract(signal, low)

    # Apply only a luminance delta so the original skin color and shading stay stable.
    original_luma = luma(baseline)
    delta = ops.subtract(luma(model_image), original_luma)
    recovered = ops.clamp(high_pass(delta, 2), -0.05, 0.05)
    microcontrast = ops.add(high_pass(original_luma, 1),
                            ops.multiply(high_pass(original_luma, 3), np.float32(0.5)))
    boost = ops.clamp(ops.multiply(microcontrast, np.float32(sharpen * 2.0)), -0.075, 0.075)
    enhanced = ops.add(baseline, ops.add(ops.multiply(recovered, np.float32(detail)), boost))
    result = ops.clamp(enhanced, 0.0, 1.0)
    alpha = ops.parameter([1, 1, HEIGHT, WIDTH], np.float16, name="alpha")
    return ov.Model([result, resize(alpha, out_h, out_w, "linear")],
                    [photo, alpha], "AIsharpner")


def compile_optimizer(core, device, scale, sharpen, detail):
    if device not in available_devices(core):
        raise ValueError("所选 Intel 核显或 NPU 当前不可用。")
    graph = processing_graph(core, scale, sharpen, detail)
    compiled = core.compile_model(graph, device)
    execution = compiled.get_property("EXECUTION_DEVICES")
    if isinstance(execution, str):
        execution = [execution]
    allowed = {device}
    if "." not in device:
        allowed.add(f"{device}.0")
    if not execution or any(target not in allowed for target in execution):
        raise RuntimeError(f"推理设备校验失败：{execution}")
    return compiled


def optimize(core, image, device, scale, sharpen, detail, report):
    check_size(*output_size(image.size, scale))
    report(0, None, "正在为设备编译模型")
    compiled = compile_optimizer(core, device, scale, sharpen, detail)
    return optimize_image(compiled, image, scale, report)


def optimize_image(compiled, image, scale, report):
    width, height = image.size
    out_size = output_size(image.size, scale)
    check_size(*out_size)
    request = compiled.create_infer_request()
    result = Image.new(image.mode, out_size)
    columns = (width + STEP_X - 1) // STEP_X
    rows = (height + STEP_Y - 1) // STEP_Y
    total = columns * rows
    offset = round(HALO * scale)
    started = monotonic()
    for index in range(total):
        x, y = (index % columns) * STEP_X, (index // columns) * STEP_Y
        left, top = max(0, x - HALO), max(0, y - HALO)
        right, bottom = min(width, x - HALO + WIDTH), min(height, y - HALO + HEIGHT)
        tile = np.asarray(image.crop((left, top, right, bottom)))
        pad_x, pad_y = left - x + HALO, top - y + HALO
        tile = np.pad(tile, ((pad_y, HEIGHT - tile.shape[0] - pad_y),
                            (pad_x, WIDTH - tile.shape[1] - pad_x), (0, 0)), mode="edge")
        rgb = np.ascontiguousarray(tile[:, :, :3].transpose(2, 0, 1)[None], dtype=np.float32)
        alpha = tile[:, :, 3] if image.mode == "RGBA" else np.full((HEIGHT, WIDTH), 255, np.uint8)
        outputs = request.infer([
            rgb / np.float32(255),
            np.ascontiguousarray(alpha[None, None], dtype=np.float16),
        ])
        rgb = np.rint(outputs[0][0].transpose(1, 2, 0) * 255).clip(0, 255).astype(np.uint8)
        if image.mode == "RGBA":
            mask = np.rint(outputs[1][0, 0]).clip(0, 255).astype(np.uint8)
            rgb = np.dstack((rgb, mask))
        target_x, target_y = round(x * scale), round(y * scale)
        tile_w = min(round(STEP_X * scale), out_size[0] - target_x)
        tile_h = min(round(STEP_Y * scale), out_size[1] - target_y)
        if tile_w > 0 and tile_h > 0:
            pixels = rgb[offset:offset + tile_h, offset:offset + tile_w]
            result.paste(Image.fromarray(pixels), (target_x, target_y))
        done = index + 1
        report(done / total, (monotonic() - started) * (total - done) / done,
               f"分块推理 · {done} / {total}" if done < total else "优化完成")
    return result
