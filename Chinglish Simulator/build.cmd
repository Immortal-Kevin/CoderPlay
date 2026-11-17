@echo off
cd /d "%~dp0"
python freeze.py build_exe --build-exe "dist\Chinglish Simulator"
exit /b %errorlevel%
