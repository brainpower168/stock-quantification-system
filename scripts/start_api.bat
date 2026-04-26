@echo off
REM 启动量化系统API服务
REM 使用方法：双击运行此文件，或从命令行执行

cd /d "%~dp0.."

echo ========================================
echo   炒股大师量化系统 API 服务启动
echo ========================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python 3.7+
    pause
    exit /b 1
)

REM 安装依赖（如果需要）
echo [1/3] 检查依赖...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo        安装依赖包...
    pip install -r requirements.txt
)

echo [2/3] 启动API服务...
echo        访问 http://localhost:8000/docs 查看API文档
echo.

REM 启动服务
python -m uvicorn api.quant_api:app --host 0.0.0.0 --port 8000 --reload

pause