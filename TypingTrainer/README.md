# Typing Trainer 1.0

Windows 11 x64 原生离线打字训练器，C# / .NET 10 / WPF。无账号、联网调用、遥测、全局键盘监听或 AI。原有 Typper/Tapper 保持独立。

## 运行与安装

便携版：解压整个 ZIP，运行 `TypingTrainer.exe`，不需要管理员权限或预装 .NET。
安装版：运行 `TypingTrainer-Setup.exe`，安装到 `%LOCALAPPDATA%\Programs\TypingTrainer`，从开始菜单启动；Windows「已安装的应用」可卸载。安装目录非空时拒绝覆盖，请先卸载旧版。
卸载保留用户数据和被用户修改过的安装文件。卸载器从系统临时目录运行辅助进程，以便删除原安装目录；临时辅助文件可随系统临时文件清理。
构建未签名，Windows SmartScreen 可能提示。未做跨电脑实机验证。

## 训练

12 篇原创中英文、数字、标点和混合文本。首次正式输入开始计时；Esc 暂停/继续，Ctrl+Enter 提前结算，Ctrl+R 确认后重新开始。Ctrl+S 未绑定。支持回退、选择、插入和换行。目标位置着色提示错误与当前进度；下方原生 TextBox 保留 IME 输入体验。
达到目标文章 Unicode 字符数即完整结束，包括仍有错字的情况；提前结束另记状态。零提交训练不进入历史。暂停时间不计入时长。
粘贴、拖放、撤销/重做及 UI Automation Value.SetValue 被禁用。系统级伪造键盘输入无法仅凭本应用可靠鉴别，未使用全局 hook 或反作弊驱动。

## 统计定义

字符按 Unicode scalar（Rune）计数，CRLF/CR 统一为 LF，大小写、空格、制表符与标点均区分。
首次正确率 = 正式提交事件中相同目标位置正确字符数 / 全部正式提交字符数。回退不会抹除先前事件；相同字符重新替换也计为新提交。IME 临时组合字符不进入统计，最终提交后处理。实际 Windows 拼音 IME 候选/取消/暂停交互仍需人工验收。
最终正确率 = `max(0, 1 - Levenshtein(targetSegment, input) / max(length(targetSegment), length(input))) * 100`。空输入为 0。完整训练使用全文；提前结束使用目标中与当前输入长度相同的前缀，未输入后缀不算错误。插入/删除造成的歧义采用该明确的前缀规则。
有效匹配字符数 = `max(0, length(targetSegment) - editDistance)`，CPM = 有效匹配字符数 × 60 / 实际秒数，WPM = CPM / 5。零秒返回 0，不通过错误输入增加速度。完成率 = 当前文本 Unicode 字符数 / 全文字符数，上限 100%。
历史默认仅完整成绩；取消勾选可查看提前结束记录。图表默认当前文章，左轴 CPM（除以 5 为 WPM）、右轴最终准确率；悬停数据点显示详情。删除文章后历史仍以文章 ID 和标题快照保存，全部文章视图可查看这些记录。

## 文本与数据

TXT 自动识别 UTF-8、UTF-8 BOM、UTF-16 BOM 和常见无 BOM UTF-16LE；可手动选 UTF-16LE/BE、GB18030。DOCX 通过 ZIP/XML 提取正文、段落、tab 与换行，不执行宏、脚本、外部链接或 XML 外部实体。
**旧版二进制 DOC 暂不支持**，导入时说明原因；请先另存为 DOCX/TXT。不依赖 Office/COM 或云端转换。
上限 4 MB 文件、4000 Unicode 字符（保证精确编辑距离性能）；空白、损坏、非法控制字符和相同正文重复导入会被拒绝，原文件不修改。
默认数据目录 `%LOCALAPPDATA%\TypingTrainer`：`articles/`（预留）、`database/trainer.db`（文章元数据及正文、成绩）、`config/settings.json`、`backups/`。SQLite 通过 Windows 11 自带 winsqlite3.dll 使用，不分发系统 DLL。
数据库事务写入、版本 1 初始化、拒绝较新版本降级、单实例互斥。每日首次运行或保存时备份，清空成绩前额外备份，最多保留 7 份。
目录迁移要求独立空目录，复制后 SHA-256 校验与 SQLite integrity_check，通过后原子更新默认目录下 location.json；失败回滚，原目录保留。迁移拒绝符号链接目录。请仅选择本地磁盘路径。

## 构建与测试

开发需要 .NET 10 SDK；运行不需要。PowerShell 中设置 `DOTNET_CLI_TELEMETRY_OPTOUT=1` 后运行：

```powershell
./build.ps1 -DotNet dotnet
```

`tests/` 是无外部测试框架依赖的自动化断言测试程序，失败返回非零退出码；`ui-tests/` 是隔离临时数据库的 WPF 集成测试，包含程序化组件测试和离屏渲染，不代表物理屏幕或真实 IME 实测。
详见 TEST_REPORT.md 与 DISTRIBUTION_CHECK.md。依赖清单和 SHA-256 文件来源见 SBOM.json。未添加第三方图表库、图片、图标或字体文件。

## 许可证

本项目原创源代码及练习文章：Apache-2.0；第三方组件保留各自许可证。用户私人数据不因此开源。
This product includes software developed by the University of California, Berkeley and its contributors.

