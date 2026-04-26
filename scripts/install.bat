@echo off
REM 安装量化系统依赖
REM 使用方法：双击运行此文件，或从命令行执行

cd /d "%~dp0.."

echo ========================================
echo   炒股大师量化系统 安装程序
echo ========================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python 3.7+
    pause
    exit /b 1
)

echo [1/3] 安装核心依赖...
pip install requests pydantic

echo [2/3] 安装API服务依赖...
pip install fastapi uvicorn

echo [3/3] 以可编辑模式安装本包...
pip install -e .

echo.
echo ========================================
echo   安装完成！
echo ========================================
echo.
echo 快速开始：
echo   1. 查看API文档：python -m uvicorn api.quant_api:app --reload
echo   2. 运行测试：pytest tests/ -v
echo   3. 使用示例：python -c "from quant_system import DailyPicker; print(DailyPicker())"
echo.
pause