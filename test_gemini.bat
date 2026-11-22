@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Run run_app.bat once first so dependencies are installed.
    pause
    exit /b 1
)
call ".venv\Scripts\activate.bat"
python check_gemini.py
pause
