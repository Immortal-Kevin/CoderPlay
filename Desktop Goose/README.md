# Desktop Goose · 桌面捣蛋鹅

Windows 11 x64 的本地桌面宠物。首次运行给鹅取名。鹅会在选定屏幕活动，从系统托盘或右键点鹅可进入仓库、家族、设置及退出。初版的实现与实测记录见 [验收追踪](TEST_REPORT.md)。

## 运行

- 便携版：完整解压 ZIP，运行 `DesktopGoose.exe`。
- 安装版：运行 MSI，然后从开始菜单打开 **CoderPlay Desktop Goose → Desktop Goose**。按当前 Windows 用户安装。
- 两种版本都自带 .NET Desktop Runtime，共用 `%LOCALAPPDATA%\CoderPlay\DesktopGoose\goose.sqlite`。升级或卸载保留该目录。软件首次启动后才创建游戏存档。
- 右键鹅头像使用「退出」。双击托盘鹅头像可隐藏或显示它。

## 养鹅

- 普通窗口前台时，鹅默认在右下角活动。可切换目标屏幕或重画活动范围。按住鹅本体约 350 ms 后可移动它。
- 鹅每个有效秒以 1/86400 的概率尝试产蛋。产蛋日从本地 04:00 开始，全家族一天最多一颗，每只鹅一生最多五颗。离线时间也按相同规则结算。
- 有蛋后在仓库选「开始孵化」。有效物理键鼠操作计入正在孵化的蛋，满 5000 次后点击桌面鹅蛋。用户暂停孵化时停止计数。输入只在内存中过滤按住产生的重复，存档仅保存计数。
- 新鹅破壳后先选择留下哪只，再给新鹅命名。放生档案可在家族中查看，之后有机会回访。
- 存档维护可查看、创建和恢复自动备份。恢复前先备份当前存档。

## 构建

使用 Windows 11 x64、PowerShell 7 和 [.NET 10 SDK](https://dotnet.microsoft.com/download/dotnet/10.0)。在本项目目录运行：

```powershell
dotnet build ./App/App.csproj -c Release
dotnet run --project ./Tests/Tests.csproj -c Release
dotnet run --project ./Tests.Desktop/Tests.Desktop.csproj -c Release
pwsh -File ./Build/Publish.ps1
```

可用 `-Dotnet` 指定现有 SDK 的 `dotnet.exe`。发布脚本把自包含便携 ZIP、每用户 MSI 和 SHA-256 清单写入新的 `artifacts/build-*` 子目录。打包使用 Windows 自带的 Windows Installer 与 MakeCab。包当前未做代码签名。

初版省略了叼文件。Windows 的文件时间和“最近使用”列表不能单独证明至少七天内没有使用，程序跳过无法可靠判定的文件。其余已知限制见 [验收追踪](TEST_REPORT.md)。

源代码、程序化绘制的像素角色和合成音效采用 [Apache-2.0](LICENSE)。系统及运行库清单见 [第三方许可](THIRD_PARTY_NOTICES.md)。
