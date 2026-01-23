@echo off
chcp 65001 >nul
echo ====================================
echo  规范定位识别系统 - 演示启动脚本
echo ====================================
echo.

echo [1/3] 激活虚拟环境...
call .venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo 错误: 虚拟环境激活失败
    echo 请先运行 setup.bat 安装依赖
    pause
    exit /b 1
)

echo [2/3] 设置环境变量...
set PYTHONPATH=%CD%;%PYTHONPATH%
REM 可选：设置数据目录（默认使用 .env 文件或 ../output_pages）
REM set SPEC_DATA_DIR=D:\projects\liuzong\output_pages

echo 服务地址: http://127.0.0.1:8002
echo API文档: http://127.0.0.1:8002/docs
echo 演示页面: api/demo.html
echo.
echo 提示: 如果端口 8002 被占用，可以手动修改 start_demo.bat 中的端口号
echo.

start "" "api\demo.html"

echo 运行中... (Ctrl+C 停止服务)
echo.
uvicorn spec_locator.api.server:app --host 0.0.0.0 --port 8002 --reload

pause
