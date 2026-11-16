@echo off
where pythonw.exe >nul 2>&1
if not errorlevel 1 (
    start "" pythonw.exe "%~dp0name_changer.pyw"
    exit /b
)
where pyw.exe >nul 2>&1
if not errorlevel 1 (
    start "" pyw.exe -3 "%~dp0name_changer.pyw"
    exit /b
)
echo Python 3 with Tkinter is required.
pause
