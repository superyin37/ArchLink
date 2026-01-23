@echo off
REM 快速安装和启动脚本 (Windows)

setlocal enabledelayexpand

title Spec Locator Service Setup

echo.
echo =====================================================================
echo   Spec Locator Service - Windows Quick Setup
echo =====================================================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found. Please install Python 3.8+
    pause
    exit /b 1
)

echo [1/3] Checking Python...
python --version
echo.

REM 检查是否已有虚拟环境
if exist "venv\" (
    echo [2/3] Virtual environment already exists
    goto :activate
) else (
    echo [2/3] Creating virtual environment...
    
    REM 检查 uv
    where uv >nul 2>&1
    if errorlevel 1 (
        echo Installing with pip...
        python -m venv venv
        call venv\Scripts\activate.bat
        python -m pip install -e ".[dev]"
    ) else (
        echo Installing with uv (faster)...
        uv sync --dev
    )
    
    if errorlevel 1 (
        echo Error: Installation failed
        pause
        exit /b 1
    )
    echo Done!
    echo.
)

:activate
echo [3/3] Starting service...
echo.
echo Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo =====================================================================
echo   Service starting on http://localhost:8000
echo =====================================================================
echo.
echo Press Ctrl+C to stop the service
echo.

python main.py

pause
exit /b 0
