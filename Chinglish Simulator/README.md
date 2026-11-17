# Chinglish Simulator

Windows 11 桌面翻译工具。把中文里的语气、关系与表达习惯一起翻成易懂的 Chinglish。界面为原生窗口，模型可以运行在本机，也可以使用远程 API。

## 启动

1. 双击 `dist/Chinglish Simulator/Chinglish Simulator.exe`。这是免安装的 Windows x64 程序，移动时保留同目录的运行库和数据文件。也可以装有 Tkinter 的 Python 3.11+ 双击 `start.cmd` 或运行 `python desktop.py`。
2. 在 **API 设置**填写 OpenAI 兼容 Base URL 和 Model ID，保存后测试连接。使用 Ollama 时先启动本地服务，地址填写 `http://127.0.0.1:11434/v1`，模型名填本机已安装的模型，通常无需 Key。远程 API 使用 HTTPS。
3. 仅在模型支持时填写 Temperature。不确定就留空。模型未设置或请求失败时，窗口会给出错误信息。
4. 输入文本，调整 **Chinglish Intensity**（0–100，默认 60），然后点 **Translate** 或 **Regenerate**。滑动只更新百分比与标签。可随时点「保存偏好」，翻译或关闭窗口时也会保存。

在 Windows 构建 EXE 时，运行 `python -m pip install -r requirements-build.txt`，然后运行 `build.cmd`。产物生成在 `dist/`，由 Git 忽略。EXE 的可写数据目录为 `%LOCALAPPDATA%/Chinglish Simulator/data`，从源码启动时使用项目的 `data/`。如果以前运行过源码，可以在程序关闭时把已有的 `config.json`、`preferences.json`、`user_examples.json` 等个人数据复制到 EXE 的数据目录。密钥仍从 Windows 凭据管理器按 API 地址读取。

## 强度与语义约束

`app.py` 的 `style_parameters()` 用 `base + scale * (intensity / 100) ** exponent` 计算中文语序、文化词保留、梗密度和情绪表达四个值。`data/intensity.json` 提供默认曲线。要自定义，可将该文件复制到可写数据目录并命名为 `intensity.override.json`，再编辑各条曲线的三个数值。界面标签只描述区间，模型收到实际整数和四个连续值。

粗口的 0–3 级独立控制，级别 0 优先使用非粗俗替代词。模型根据关系、语境和原文决定是否保留梗与夸张；风格参数不对应词数比例。模型对提示词的响应存在波动，相邻强度可以生成相同文本。译文完成后由同一模型作结构化语义审核，必要时重试一次。一次翻译最多发出四次模型请求，远程服务可能逐次收费。

## 本地文件和隐私

- `data/chinglish_rules.json` 是项目规则库，只给模型作参考，匹配规则不会直接生成译文。
- API Key 按 Base URL 写入 Windows 凭据管理器。也可设置 PowerShell 环境变量，见 `.env.example`；应用不会读取 .env 文件。
- 偏好、反馈计数及配置存于本机 JSON。历史默认关闭，开启后最多保留 50 条；关闭历史后仍可点击「清空记录」删除旧数据。
- 自己修订的译文可保存到 `data/user_examples.json`。示例可导入、导出、编辑和删除；匹配时只取参数一致且文本相似的少数条目。只有在设置中开启明确授权，才会随请求发送这些示例。更换 API 地址会自动关闭此选项。
- 远程翻译会向所配服务发送原文、上下文和待审译文。默认日志只记录处理事件和错误，不保存正文或凭据。不要提交 `data` 中的个人文件。

## 测试和评测

- `python -m unittest discover -s tests -v` 使用临时目录和本地模拟 API。90 组请求来自 15 条输入 × 6 个强度点（0、20、40、60、80、100），检查四个公式、提示词参数传递、独立粗口设置和错误处理。
- `python -m tests.desktop_smoke` 在 Windows 创建真实 Tk 窗口，验证 101 个整数位置、滑动无模型请求、翻译与重新生成使用当时强度，以及重启后偏好恢复。
- `python -m tests.evaluate_intensity --send --case-count 15 --repeats 3` 对所配置的真实模型进行重复采样。保持同一模型与 Temperature，逐行输出 JSON，关闭历史和个人示例。全量每轮 90 组，此命令执行三轮，远程服务可能收费。可先把 `--case-count` 设为 1。
- 人工复核时按输入对照六个强度下的多次结果，观察中文语序、文化词、合语境的梗和原有情绪是否呈整体上升趋势。逐条检查事实、关系、反讽、粗口级别和可读性。模型自审不等同于人工验收。32 条通用语义用例仍保存在 `tests/cases.json`。

## 许可和依赖

项目代码采用 [Apache-2.0](LICENSE)。运行使用 Python 标准库及 Tkinter（Python 采用 PSF 许可，Tcl/Tk 采用 BSD 风格许可）和 Windows 系统 API。Windows EXE 使用单独的构建依赖 cx_Freeze 和 freeze-core（PSF 许可）。可选 Ollama、模型及 API 服务分别适用其许可证或服务条款。
