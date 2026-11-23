# Desktop Cleaner v1.0 · 桌面整理大师

Windows 11 x64 桌面工具。点击「一键整理」后，工具通过 Windows Shell COM 把真实的桌面图标排进窗口后面的网格。拖动原生标题栏时图标留在原位置，移出遮挡范围的图标会露出来。松开鼠标或结束键盘移动后，工具按新窗口位置重新排列图标。工具只修改 Shell 视图中的图标坐标，本地运行，无需管理员权限。

[下载 Windows x64 便携 ZIP](https://github.com/Immortal-Kevin/CoderPlay/releases/tag/desktop-cleaner-v1.0.0)。完整解压后双击 `DesktopCleaner.exe`，应急入口为 `Recovery` 子目录中的 `DesktopCleaner.Recovery.exe`。便携版自带 .NET 8 Runtime。用户实测主屏的整理和拖动通过，副屏未通过。 [测试摘要](TEST_REPORT.md)

## 使用

- 启动 `DesktopCleaner.exe`。确认 Windows 已开启「显示桌面图标」，关闭「自动排列图标」。
- 点击「一键整理」。窗口可能根据网格容量自动放大。空间不足、Explorer 调整了目标坐标，或图标及标签露出窗口时，应用会报告失败。已开始的整理会尝试恢复原布局。
- 拖动标题栏，或使用系统菜单的「移动」。最小化时图标可见，窗口还原后重新核对遮挡范围。
- 点击「恢复桌面」或关闭窗口。恢复会逐项回读坐标并报告恢复、失败和缺失数量。若失败，可在关闭提示中重试，或保留快照并退出。

## 布局恢复

首次移动前，工具将校验过的快照原子提交到 `%LOCALAPPDATA%\DesktopCleaner\original-layout.json`。拖动不会覆盖该快照。快照包含坐标、Shell 标识、显示器分辨率、工作区、DPI、图标间距和 SHA-256 校验值。文件项按 Shell 生成的路径、卷和文件标识匹配，同名的替换文件会被视为新项目。改名或删除的项目可能计为缺失。新增图标保持原位，若占用恢复目标坐标，需要先手动移开该新增图标。

主窗口无法运行时，在原 Windows 账户的交互式桌面上启动 `DesktopCleaner.Recovery.exe`，或在终端执行 `DesktopCleaner.Recovery.exe --restore`。工具会在完成回读验证后清除待恢复快照。若显示器、缩放、工作区或网格变化，恢复前需还原快照对应的配置。恢复工具与主程序使用同一恢复目录，一次只能有一个进程执行操作。Explorer 无响应、断电或快照损坏可能需要人工处理。

`DesktopCleaner.Recovery.exe --probe` 只读检查 Shell 坐标、可见边界和网格容量，可在当前桌面运行。

## 编译和验证

使用 .NET 8 SDK 或支持 `net8.0-windows` 的较新 SDK。框架依赖的 Release 构建在 Windows 11 x64 上需要 .NET 8 Desktop Runtime。

```powershell
dotnet build .\App\App.csproj -c Release
dotnet build .\Recovery\Recovery.csproj -c Release
dotnet build .\Tests\Tests.csproj -c Release
& .\Tests\bin\Release\net8.0-windows\Tests.exe
& .\Recovery\bin\Release\net8.0-windows\DesktopCleaner.Recovery.exe --probe
```

主窗口和紧急恢复程序分别在各自项目的 `bin\Release\net8.0-windows` 目录。便携发布使用 `dotnet publish -c Release -r win-x64 --self-contained true` 分别发布两项程序。恢复程序及其运行时放入 `Recovery` 子目录，随 ZIP 附上源代码许可证、第三方清单、实际运行时包的许可证和随包声明，以及测试结果。

## 实现与许可证

Shell 发现通过 `IShellWindows`、`IShellBrowser` 和 `IShellView` 完成。定位由 `IFolderView::SelectAndPositionItems` 执行，位置通过 `GetItemPosition` 验证。MSAA 读取图标与标签实际边界，用于核对 DWM 窗口遮挡范围。Shell 操作在 STA 工作线程执行，WPF 通过原生窗口消息识别拖动及调整大小。 [Microsoft Shell 实现参考](https://devblogs.microsoft.com/oldnewthing/20211122-00/?p=105948) · [原生移动及调整大小消息](https://learn.microsoft.com/en-us/windows/win32/winmsg/wm-exitsizemove)

项目源代码按 [Apache License 2.0](LICENSE) 许可，框架及系统组件的条款见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
