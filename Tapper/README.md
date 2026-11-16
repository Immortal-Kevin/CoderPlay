# Tapper

简洁的 Windows Python 鼠标连点器 / A simple Windows mouse auto clicker.

## 运行 / Run

安装带 Tkinter 的 Python 3.10 或更新版本（python.org 官方 Windows 安装包自带），双击 `启动Tapper.vbs`（全程不显示命令行窗口）或 `Tapper.pyw`。原 `run.bat` 也会转为无控制台运行并关闭自身窗口。也可运行：

```powershell
pythonw Tapper.pyw
```

不需要 pip 安装依赖。运行平台：Windows 10 / 11。

## 使用 / Usage

- 窗口最小 640 × 640，可调整大小、最大化；F11 全屏，Esc 退出全屏。
- 点击右上角 `中文 / EN` 切换语言。
- 输入间隔并选择 `ms`（毫秒）、`s`（秒）、`min`（分钟）。范围为 10 ms 至 120 s，即最高每秒 100 次、最低每两分钟一次。
- 选择左键、右键或中键。点击始终跟随当前鼠标位置。
- 点击“按下后3秒开始”，界面显示 3 秒倒计时。倒计时内可再次点击按钮取消。
- 倒计时和连点期间，按键盘任意键即可全局停止，包括软件不在前台时；鼠标按键不算键盘按键。F6/F8 不再用于启动。
- 第一次点击在 3 秒倒计时结束时发出，此后按设定间隔重复。请在倒计时期间将鼠标移到目标区域；停止后可修改参数。
- 关闭窗口会停止工作线程。任意键停止通过 Windows 键盘状态轮询（约 10 毫秒一次）及窗口按键事件实现。

The UI supports Chinese and English. Set the interval (10 ms–120 s), choose a mouse button, then click “Start after 3 seconds”. Move to your target during the countdown. Press any keyboard key to stop or cancel, even when another window has focus. Clicks follow the cursor. F11 toggles fullscreen; Esc exits fullscreen.

实际频率受 Windows 调度和目标程序影响，100 次/秒是目标频率而非实时保证。普通权限程序可能无法向管理员权限窗口发送输入；失败时会停止并显示提示。

## 验证 / Verification

```powershell
python -m unittest discover -s tests -v
```

## 许可 / License

项目原创代码按 Apache License 2.0 发布，见 LICENSE。允许商业使用和闭源衍生产品；分发时须遵守该许可证，保留适用的版权、许可及归属声明，并标明对原文件的修改。本项目不依赖 GPL/LGPL 鼠标控制库。

Python 和 Tcl/Tk 自身采用各自许可证。若将解释器打包分发，需同时保留其适用许可证；Apache 2.0 不替代这些许可证。

## BongoCat 兼容模式（2026-11-03）

默认勾选 BongoCat 模式：鼠标按住 150 ms，并至少释放 150 ms。有效间隔为输入间隔与 300 ms 中较大者（最高约 3.33 次/秒），界面频率显示此有效值。取消勾选后恢复原来的瞬时 SendInput 点击和最高 100 次/秒目标频率；高速模式不保证被 BongoCat 轮询计数。

原有三秒倒计时、任意键全局停止、语言、鼠标按钮和启动入口保留。鼠标释放放在 finally 中，停止最多等待当前一次 150 ms 按住结束。源码恢复副本：../Diagnostics/tapper.py.before。
