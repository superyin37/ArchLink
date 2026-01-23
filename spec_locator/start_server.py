# 规范定位识别系统 - 启动脚本
# 使用方法：python start_server.py

import os
import sys
import subprocess
import webbrowser
from pathlib import Path

def main():
    print("=" * 50)
    print("  规范定位识别系统 - 服务器启动")
    print("=" * 50)
    print()

    # 获取项目根目录
    project_root = Path(__file__).parent
    os.chdir(project_root)

    # 检查虚拟环境
    venv_python = project_root / ".venv" / "Scripts" / "python.exe"
    if not venv_python.exists():
        print("❌ 错误: 虚拟环境不存在")
        print("请先运行 setup.bat 安装依赖")
        input("按回车键退出...")
        sys.exit(1)

    print("[1/3] 检查环境...")
    
    # 安装包（可编辑模式）
    print("[2/3] 安装包（可编辑模式）...")
    try:
        subprocess.run(
            [str(venv_python), "-m", "pip", "install", "-e", "."],
            check=False,
            capture_output=True,
            timeout=30
        )
    except Exception as e:
        print(f"⚠️  警告: 包安装失败 ({e})，继续尝试启动...")

    # 启动服务器
    print("[3/3] 启动 API 服务器...")
    print()
    print("=" * 50)
    print("  服务地址: http://127.0.0.1:8001")
    print("  API文档: http://127.0.0.1:8001/docs")
    print("  演示页面: api/demo.html")
    print("=" * 50)
    print()
    print("提示: 按 Ctrl+C 停止服务")
    print()

    # 打开演示页面
    demo_html = project_root / "api" / "demo.html"
    if demo_html.exists():
        print("🌐 正在打开演示页面...")
        webbrowser.open(str(demo_html))

    # 启动 uvicorn
    try:
        subprocess.run(
            [
                str(venv_python), "-m", "uvicorn",
                "spec_locator.api.server:app",
                "--host", "0.0.0.0",
                "--port", "8001",
                "--reload"
            ],
            cwd=str(project_root)
        )
    except KeyboardInterrupt:
        print("\n\n✅ 服务器已停止")
    except Exception as e:
        print(f"\n\n❌ 错误: {e}")
        input("按回车键退出...")
        sys.exit(1)

if __name__ == "__main__":
    main()
