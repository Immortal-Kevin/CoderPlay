FFT Playground 1.0.2 — Windows x64 portable edition

New preset: 正常运行（有底噪）. Adjust 背景底噪 σ in 采样 / 分析,
then click 生成 / 更新. Default sigma is 0.15 a.u.; zero disables it.

1. Extract the entire ZIP to a normal writable folder.
2. Double-click FFT Playground.exe. No Python installation or Internet required.
3. Keep the runtime, application and licenses folders beside the EXE.
   The EXE alone is a launcher and must not be separated from these files.

Windows 10/11 x64 with the OS .NET Framework 4.x runtime is required.
No installer, administrator rights, paid license or pip installation is needed.
The application is unsigned; publisher code signing has not been purchased.

On failure, keep the displayed error and these local logs:
%LOCALAPPDATA%\FFT Playground\logs\application.log
The bundled command-line diagnostic can also be run from PowerShell:
.\runtime\python.exe .\application\startup_check.py

Application source/launcher: Apache-2.0 (LICENSE and NOTICE).
Bundled CPython/Tcl/Tk/libffi/LibTomMath/zlib have their own retained notices.
See PORTABLE_LICENSES.md and licenses/CPython-Windows-3.14.7.txt.
Microsoft runtime code is for Windows only; preserve its notices and restrictions
when redistributing. These conditions apply only to Microsoft's code and do not
replace Apache-2.0 for the original application.
