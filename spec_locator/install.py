#!/usr/bin/env python3
"""
快速安装脚本 - 使用 uv 或 pip 安装环境

用法：
    python install.py          # 自动选择 uv 或 pip
    python install.py --uv     # 强制使用 uv
    python install.py --pip    # 强制使用 pip
"""

import sys
import subprocess
import os
import shutil
from pathlib import Path

def print_header(text):
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}\n")

def print_success(text):
    print(f"✅ {text}")

def print_warning(text):
    print(f"⚠️  {text}")

def print_info(text):
    print(f"ℹ️  {text}")

def check_python():
    """检查 Python 版本"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ Python 版本过低: {version.major}.{version.minor}")
        print("   需要 Python 3.8+")
        sys.exit(1)
    print_success(f"Python 版本: {version.major}.{version.minor}.{version.micro}")

def has_uv():
    """检查是否安装了 uv"""
    return shutil.which("uv") is not None

def install_uv():
    """安装 uv"""
    print_info("正在安装 uv...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "uv"],
            check=True,
            capture_output=True
        )
        print_success("uv 安装成功")
        return True
    except subprocess.CalledProcessError as e:
        print_warning(f"uv 安装失败: {e}")
        return False

def setup_with_uv():
    """使用 uv 安装"""
    print_header("使用 uv 安装环境")
    
    # 检查 uv
    if not has_uv():
        print_info("未检测到 uv，正在安装...")
        if not install_uv():
            return False
    
    # 清除已存在的虚拟环境（避免冲突）
    venv_path = Path("venv")
    if venv_path.exists():
        print_warning("虚拟环境已存在，正在清理...")
        try:
            shutil.rmtree(venv_path)
            print_success("已清理旧的虚拟环境")
        except Exception as e:
            print_warning(f"无法完全清理虚拟环境: {e}")
    
    print_info("正在创建虚拟环境并安装依赖...")
    try:
        # 使用 uv sync 一次性搞定（推荐方式）
        subprocess.run(["uv", "sync", "--dev"], check=True)
        print_success("虚拟环境和依赖安装成功")
    except subprocess.CalledProcessError as e:
        print(f"❌ 安装失败: {e}")
        print_info("尝试使用 pip 方式...")
        return setup_with_pip()
    
    return True

def setup_with_pip():
    """使用 pip 安装"""
    print_header("使用 pip 安装环境")
    
    print_info("正在创建虚拟环境...")
    try:
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
        print_success("虚拟环境创建成功")
    except subprocess.CalledProcessError as e:
        print(f"❌ 虚拟环境创建失败: {e}")
        return False
    
    print_info("正在安装依赖...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", ".[dev]"],
            check=True
        )
        print_success("依赖安装成功")
    except subprocess.CalledProcessError as e:
        print(f"❌ 依赖安装失败: {e}")
        return False
    
    return True

def print_next_steps():
    """打印后续步骤"""
    print_header("✨ 安装完成！后续步骤")
    
    if sys.platform == "win32":
        activate_cmd = ".\\venv\\Scripts\\Activate.ps1"
    else:
        activate_cmd = "source venv/bin/activate"
    
    print(f"1️⃣  激活虚拟环境")
    print(f"    {activate_cmd}\n")
    
    print(f"2️⃣  启动服务")
    print(f"    python main.py\n")
    
    print(f"3️⃣  测试 API")
    print(f"    curl http://localhost:8000/health\n")
    
    print(f"📚 更多信息，查看：")
    print(f"    • UV_GUIDE.md - uv 详细使用指南")
    print(f"    • DEVELOPMENT.md - 开发指南")
    print(f"    • README_DEV.md - 完整文档\n")

def main():
    """主程序"""
    print_header("Spec Locator Service - 环境安装器")
    
    # 检查 Python
    check_python()
    
    # 解析命令行参数
    use_uv = "--uv" in sys.argv
    use_pip = "--pip" in sys.argv
    
    if use_uv and use_pip:
        print("❌ 不能同时指定 --uv 和 --pip")
        sys.exit(1)
    
    # 自动选择
    if not use_uv and not use_pip:
        print_info("自动选择安装工具...")
        if has_uv():
            print_success("检测到 uv，使用 uv 安装")
            use_uv = True
        else:
            print_info("未检测到 uv，使用 pip 安装")
            use_pip = True
    
    # 执行安装
    success = False
    if use_uv:
        success = setup_with_uv()
    else:
        success = setup_with_pip()
    
    if success:
        print_next_steps()
        print("🎉 环境安装成功！\n")
    else:
        print("\n❌ 安装过程中出现错误，请检查上面的错误信息\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
