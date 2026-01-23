#!/bin/bash

# 快速安装和启动脚本 (Linux/macOS)

set -e

clear

echo ""
echo "====================================================================="
echo "  Spec Locator Service - Quick Setup for Linux/macOS"
echo "====================================================================="
echo ""

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python3 not found. Please install Python 3.8+"
    exit 1
fi

echo "[1/3] Checking Python..."
python3 --version
echo ""

# 检查是否已有虚拟环境
if [ -d "venv" ]; then
    echo "[2/3] Virtual environment already exists"
else
    echo "[2/3] Creating virtual environment..."
    
    # 检查 uv
    if command -v uv &> /dev/null; then
        echo "Installing with uv (faster)..."
        uv sync --dev
    else
        echo "Installing with pip..."
        python3 -m venv venv
        source venv/bin/activate
        python -m pip install -e ".[dev]"
    fi
    
    if [ $? -ne 0 ]; then
        echo "Error: Installation failed"
        exit 1
    fi
    echo "Done!"
    echo ""
fi

echo "[3/3] Starting service..."
echo ""

# 激活虚拟环境
source venv/bin/activate

echo "====================================================================="
echo "  Service starting on http://localhost:8000"
echo "====================================================================="
echo ""
echo "Press Ctrl+C to stop the service"
echo ""

python main.py
