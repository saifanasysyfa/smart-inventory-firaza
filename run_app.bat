@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creating Python virtual environment...
    py -m venv .venv
    if errorlevel 1 (
        echo Failed to create virtual environment. Check that Python is installed.
        pause
        exit /b 1
    )
)

call ".venv\Scripts\activate.bat"

REM Install dependencies only when core packages are missing.
python -c "import streamlit, pandas, sklearn, fastapi, google.genai, dotenv" >nul 2>&1
if errorlevel 1 (
    echo Installing project dependencies. This is normally needed only once...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Dependency installation failed. Check your internet connection and disk space.
        pause
        exit /b 1
    )
)

python -m streamlit run app.py
pause
