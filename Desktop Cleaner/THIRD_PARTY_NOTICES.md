# 第三方依赖和许可证

| 组件 | Windows x64 自包含发布 | 许可及声明 |
| --- | --- | --- |
| Microsoft .NET 8 Runtime 和 apphost | 8.0.33，来自 Microsoft.NETCore.App.Runtime.win-x64 和 Microsoft.NETCore.App.Host.win-x64 | 两个包的 [MIT 许可证](licenses/dotnet-apphost-MIT.txt) 和 [第三方声明](licenses/dotnet-apphost-THIRD-PARTY-NOTICES.txt) 内容一致，归档各附一份 |
| Microsoft .NET Desktop Runtime 和 WPF | 8.0.33，来自 Microsoft.WindowsDesktop.App.Runtime.win-x64 | [运行时包的 MIT 许可证](licenses/dotnet-windowsdesktop-MIT.txt)，[WPF 8.0.33 第三方声明](licenses/wpf-THIRD-PARTY-NOTICES.txt)（[上游原文](https://github.com/dotnet/wpf/blob/v8.0.33/THIRD-PARTY-NOTICES.TXT)） |
| Windows Shell、User32、DWM、MSAA、Shcore、Kernel32 | Windows 提供的 COM 和 Win32 API | 适用用户的 Windows 许可条款。系统 DLL 由系统提供 |

App、Recovery 和 Tests 的 `dotnet list package --include-transitive` 未列出应用或测试 NuGet 包。检查了已发布的运行时版本、对应许可证和声明，未发现 GPL 或 AGPL 依赖。项目源代码的 Apache-2.0 许可独立于这些组件。
