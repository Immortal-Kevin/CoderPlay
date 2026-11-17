# Simple Generator

Windows 本地图片生成器。启动后在浏览器打开本机页面，输入出生年份。2005 年及以后出生会停止本地服务，浏览器可能保留提示页。

## 首次联网安装

在项目目录打开 PowerShell。使用 64 位 Python 3.14 和本机的 Intel Arc B390 时，先安装 XPU 版 PyTorch，再安装应用依赖。

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/xpu
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe download_models.py
```

在 [Civitai](https://civitai.com/search/models?query=Chilloutmix) 登录并开启 Adult 内容显示。搜索 Chilloutmix，下载 SD 1.5 的 SafeTensor checkpoint，放到 `models/Chilloutmix.safetensors`。

双击 `Start.cmd` 启动。模型装齐后，生成和中译英均可离线使用。程序通过 PyTorch 自动选择 CUDA、Intel XPU 或 CPU，可用以下命令检查 Intel GPU 是否就绪。

```powershell
.\.venv\Scripts\python.exe -c "import torch; print(torch.__version__, torch.xpu.is_available())"
```

## 使用

- 正向提示词和负向提示词可同时中译英。生成前可继续编辑翻译结果。
- 写实模式使用 Chilloutmix。漫画和油画模式先生成写实底图，再用底图的 Canny 边缘作为 ControlNet 条件进行图生图，风格由提示词引导。
- 自由度映射到提示词引导强度，细节补全度映射到去噪步数，颜色丰富度映射到色彩提示词。每批逐张生成，图片完成后即可预览。
- 1920×1080 等大尺寸采用最高约 768 像素长边的推理图，再缩放到目标输出尺寸。
- 保存会在所选目录写入 PNG。删除只移除当前预览。重新生成沿用上一次提交的参数，使用新随机种子。每轮新任务会清空上一任务的预览。

本地 Diffusers Safety Checker 使用可选组件参数禁用。双击 Start.cmd 即可使用此配置。批次内单张运行失败会写入 logs/generation_debug.log，其余图片继续生成。
