@echo off
cd /d "%~dp0"
setlocal
if errorlevel 1 goto failed
if /i "%~1"=="--diagnose" (
    "%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch.ps1" -Diagnostic
) else (
    "%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch.ps1"
)
if errorlevel 1 goto failed
exit /b 0
:failed
echo.
echo FFT Playground could not start. Details are printed above.
echo Logs: %%LOCALAPPDATA%%\FFT Playground\logs
echo Run run.bat --diagnose to check every Python installation.
echo Please keep this window and the log when reporting the error.
pause
exit /b 1
