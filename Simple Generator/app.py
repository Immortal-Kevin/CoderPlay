import io
import logging
from logging.handlers import RotatingFileHandler
import os
import secrets
import threading
import webbrowser
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_file, session

from engine import ROOT, SIZES, STYLES, generate, translate

app = Flask(__name__, static_folder=None)
app.secret_key = secrets.token_bytes(32)
app.config.update(MAX_CONTENT_LENGTH=32_768, SESSION_COOKIE_SAMESITE="Strict")
log = logging.getLogger("simple_generator.generation")
log.setLevel(logging.INFO)
log.propagate = False
log_dir = ROOT / "logs"
log_dir.mkdir(exist_ok=True)
for handler in (logging.StreamHandler(), RotatingFileHandler(
        log_dir / "generation_debug.log", maxBytes=4_000_000, backupCount=2, encoding="utf-8")):
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(handler)
lock = threading.Lock()
images = {}
state = {"busy": False, "progress": 0, "message": "等待生成"}
last = None
folder = ROOT / "outputs"


@app.before_request
def local_only():
    if request.host != "127.0.0.1:8765":
        abort(403)
    if request.method == "POST" and request.headers.get("Origin") != request.host_url.rstrip("/"):
        abort(403)
    if request.path.startswith("/api/") and request.path != "/api/age" and not session.get("adult"):
        abort(401)


@app.get("/")
def home():
    return send_file(ROOT / "index.html")


@app.post("/api/age")
def age():
    year = (request.get_json() or {}).get("year")
    if type(year) is not int or not 1900 <= year <= 2100:
        return jsonify(error="请输入有效的四位出生年份"), 400
    if year >= 2005:
        threading.Timer(0.8, os._exit, args=(0,)).start()
        return jsonify(allowed=False)
    session["adult"] = True
    return jsonify(allowed=True)


def work(settings):
    def progress(value, message):
        with lock:
            state.update(progress=min(99, int(value * 100)), message=message)

    def publish(image):
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        with lock:
            images[secrets.token_hex(8)] = buffer.getvalue()

    try:
        log.info("stage=job_start prompt=%r translation=%r effective_prompt=%r negative=%r batch_size=%d rounds=%d",
                 settings.get("original_positive", settings["positive"]),
                 settings.get("translated_positive"), settings["positive"], settings["negative"],
                 settings["count"], settings["rounds"])
        failed = generate(settings, progress, publish)
        total = settings["count"] * settings["rounds"]
        if failed == total:
            message = f"生成失败 · {failed}/{total} 张失败，详情见日志"
        elif failed:
            message = f"批次结束 · 成功 {total - failed}/{total}，失败 {failed} 张"
        else:
            message = "生成完成"
        with lock:
            state.update(progress=100, message=message)
    except Exception as exc:
        log.exception("模型加载或生成失败")
        with lock:
            state.update(message=f"生成失败 · {exc}")
    finally:
        with lock:
            state["busy"] = False


@app.post("/api/generate")
def start():
    global last
    body = request.get_json()
    log.info("stage=generation_request")
    with lock:
        if state["busy"]:
            return jsonify(error="正在生成"), 409
        if body.get("again"):
            if last is None:
                return jsonify(error="请先提交一次生成"), 400
            settings = last
        else:
            try:
                settings = {key: body[key] for key in ("positive", "negative", "style", "size",
                            "freedom", "detail", "color", "rounds", "count")}
                if not isinstance(settings["size"], list) or tuple(settings["size"]) not in SIZES:
                    raise ValueError
                if settings["style"] not in STYLES:
                    raise ValueError
                for key in ("positive", "negative"):
                    if not isinstance(settings[key], str) or len(settings[key]) > 2000:
                        raise ValueError
                if not settings["positive"].strip():
                    raise ValueError
                for key, high in (("freedom", 10), ("detail", 10), ("color", 10),
                                  ("rounds", 10), ("count", 5)):
                    if type(settings[key]) is not int or not 1 <= settings[key] <= high:
                        raise ValueError
            except (KeyError, ValueError, TypeError):
                return jsonify(error="请检查提示词及生成参数"), 400
            for key in ("original_positive", "translated_positive"):
                value = body.get(key)
                if isinstance(value, str) and len(value) <= 2000:
                    settings[key] = value
            last = settings
        images.clear()
        state.update(busy=True, progress=0, message="正在加载本地模型")
        threading.Thread(target=work, args=(settings,), daemon=True).start()
    return jsonify(ok=True)


@app.get("/api/status")
def status():
    with lock:
        return jsonify(**state, images=list(images), folder=str(folder))


@app.get("/api/image/<key>")
def preview(key):
    with lock:
        data = images.get(key)
    if data is None:
        abort(404)
    return send_file(io.BytesIO(data), mimetype="image/png")


@app.post("/api/image/<key>/<action>")
def image_action(key, action):
    global folder
    with lock:
        data = images.get(key)
        if data is None:
            abort(404)
        if action == "delete":
            del images[key]
            return jsonify(ok=True)
        if action != "save":
            abort(404)
    try:
        target = Path(request.get_json()["folder"]).expanduser()
        if not target.is_absolute():
            raise ValueError("请输入绝对路径")
        target.mkdir(parents=True, exist_ok=True)
        path = target / f"simple-{key}.png"
        log.info("stage=save_output image=%s", key)
        path.write_bytes(data)
        with lock:
            folder = target
        return jsonify(path=str(path))
    except (OSError, KeyError, ValueError, TypeError) as exc:
        return jsonify(error=f"保存失败 · {exc}"), 400


@app.post("/api/folder")
def choose_folder():
    global folder
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        try:
            root.withdraw()
            root.attributes("-topmost", True)
            selected = filedialog.askdirectory(parent=root, initialdir=str(folder if folder.exists() else ROOT))
        finally:
            root.destroy()
        if selected:
            with lock:
                folder = Path(selected)
        return jsonify(folder=str(folder))
    except Exception as exc:
        return jsonify(error=f"无法打开目录选择器 · {exc}"), 400


@app.post("/api/translate")
def translation():
    body = request.get_json()
    try:
        values = [body[key] for key in ("positive", "negative")]
        if any(not isinstance(value, str) or len(value) > 2000 for value in values):
            raise ValueError("提示词过长")
        with translation_lock:
            positive, negative = translate(values)
        log.info("stage=translation prompt=%r translated_prompt=%r negative=%r translated_negative=%r",
                 values[0], positive, values[1], negative)
        return jsonify(positive=positive, negative=negative)
    except Exception as exc:
        return jsonify(error=f"翻译失败 · {exc}"), 400


translation_lock = threading.Lock()

if __name__ == "__main__":
    threading.Timer(1, webbrowser.open, args=("http://127.0.0.1:8765/",)).start()
    app.run(host="127.0.0.1", port=8765)
