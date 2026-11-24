# 第三方组件与素材

| 组件 | 版本／来源 | 许可与分发 |
|---|---|---|
| .NET Runtime x64 | 10.0.14；[dotnet/runtime](https://github.com/dotnet/runtime/tree/v10.0.14) 与官方运行时包 | MIT。构建脚本从实际选用的包复制许可证与第三方声明。 |
| WPF / Windows Forms x64 | 10.0.14；[dotnet/wpf](https://github.com/dotnet/wpf/tree/v10.0.14)、[dotnet/winforms](https://github.com/dotnet/winforms/tree/v10.0.14) 与官方桌面运行时包 | MIT。构建脚本从实际选用的包复制许可证。 |
| Windows SQLite、Win32、DWM、系统字体 | Windows 11 系统组件，随系统版本更新；[Windows 文档](https://learn.microsoft.com/windows/win32/) | 由 Windows 提供，发布包不从系统目录再分发这些文件。 |
| Windows Installer / MakeCab | Windows 11 内置打包工具 | 打包时使用系统组件。MSI 通过目标机器的 Windows Installer 执行。 |
| 像素绘制和鹅叫 | 本项目的 PixelArt.cs 和 Honks.cs | 本项目原创，Apache-2.0。 |

运行库的具体版本以成品内的 `licenses/runtime-versions.txt` 为准。未引入外部 NuGet 应用依赖、下载安装器 SDK 或外部图片、音效及字体文件。
