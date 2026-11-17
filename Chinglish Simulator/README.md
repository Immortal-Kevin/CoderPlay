# Chinglish Simulator

Windows 11 x64 桌面翻译工具。它用本机的 Qwen2.5-1.5B-Instruct Q5_K_M 模型生成并审核译文，通过 llama.cpp Vulkan 后端将模型层加载到核显。无需 API 设置、账号或密钥。原文、上下文、译文和个人示例均在本机处理。

## 启动

1. 在首次安装模型时双击 `setup-local.cmd`。脚本从官方发布地址下载约 1.2 GiB 的模型与 Vulkan 运行库，校验 SHA-256，并列出 Vulkan 设备。安装文件放在 `%LOCALAPPDATA%/Chinglish Simulator/inference`。已经安装成功可直接跳到下一步。
2. 双击 `dist/Chinglish Simulator/Chinglish Simulator.exe`。移动时保留整个便携目录。源码模式可用装有 Tkinter 的 Python 3.11+ 执行 `start.cmd`。
3. 输入中文，选择交流对象、情绪、粗口级别等选项，再点 Translate 或 Regenerate。滑动强度不会触发推理。程序直接启动本地子进程，模型安装完后可以断网使用。

需要 Windows x64 和可用的 Vulkan 图形驱动。程序要求 Vulkan 设备加载全部模型层；驱动不可用或显存不足时会报错。这版实现使用核显路径。通过 Vulkan 加载模型层时，CPU 仍负责分词及部分运行时工作。

在 Windows 构建 EXE 时，运行 `python -m pip install -r requirements-build.txt`，然后运行 `build.cmd`。产物在 `dist/`，由 Git 忽略。

## 连续强度

强度为 0–100 的整数，默认 60。`app.py` 的 `style_parameters()` 使用 `base + scale * (intensity / 100) ** exponent` 计算中文语序、文化词保留、梗密度和情绪表达四个值。默认曲线见 `data/intensity.json`。要自定义，可把该文件复制到可写数据目录，命名为 `intensity.override.json`，编辑后重新翻译。

粗口级别独立控制，级别 0 使用非粗俗表达。连续数值用于提示词，相邻强度可能产生相同文本。1.5B 模型对隐晦反讽、复杂上下文和严格风格要求仍可能判断错误。程序对生成结果执行本地语义复核，并按需要重试一次。

## 本地数据

- 便携版数据位于 `%LOCALAPPDATA%/Chinglish Simulator/data`；源码模式使用项目的 `data/`。
- 历史默认关闭，可在「历史」窗口开启或清空。本地示例可导入、导出、编辑和删除。翻译只引用有限的相似示例。
- 程序把提示词放在本机临时目录供推理子进程读取，推理完成后立即删除。日志只记录操作失败类型。应用不把翻译内容发送到网络。

## 测试

- `python -m unittest discover -s tests -v` 跑基础检查和 90 组强度配置。覆盖四个连续参数、独立粗口级别、模型文件缺失、GPU 卸载验证、临时提示词清理和错误处理。
- `python -m tests.desktop_smoke` 验证 101 个滑块位置、翻译与重新生成的参数，以及重启后的偏好。
- `python -m tests.evaluate_intensity --run --case-count 15 --repeats 3` 使用已安装模型重复采样并输出 JSON。逐条复核事实、关系、反讽、粗口级别与可读性，并比较同一输入下的强度趋势。可先将 `--case-count` 设为 1。

## 许可和依赖

项目代码采用 [Apache-2.0](LICENSE)。Python 使用 PSF 许可，Tcl/Tk 使用 BSD 风格许可，cx_Freeze 和 freeze-core 使用 PSF 许可。外部运行库使用 [llama.cpp 的 MIT 许可](https://github.com/ggml-org/llama.cpp/blob/b12466/LICENSE)；其二进制发布包提供 LLVM OpenMP 的许可文件。[Qwen2.5-1.5B-Instruct-GGUF 模型](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF)采用 Apache-2.0。
