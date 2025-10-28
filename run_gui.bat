@echo off
echo ========================================
echo VSE Screenshot GUI Launcher
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found, please install Python 3.10+
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [INFO] Python is installed
echo.

REM Check if dependencies are installed
echo [INFO] Checking dependencies...
python -c "import customtkinter" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [WARN] Missing dependencies detected, installing...
    echo.
    call install_dependencies.bat
    if %ERRORLEVEL% NEQ 0 (
        echo.
        echo [ERROR] Installation failed, please run manually: pip install -r requirements.txt
        pause
        exit /b 1
    )
    echo.
    echo [OK] Dependencies installed
    echo.
)

echo [INFO] Starting application...
echo.

python vse_screenshot_gui.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Failed to start!
    echo.
    echo Possible reasons:
    echo 1. Python version too low (need 3.10+)
    echo 2. Missing dependencies
    echo 3. VapourSynth not installed
    echo.
    echo Please try:
    echo 1. Run install_dependencies.bat to install dependencies
    echo 2. Check Python version: python --version
    echo 3. Check error messages above
    echo.
    pause
)

