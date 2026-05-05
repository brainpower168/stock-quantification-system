@echo off
echo ========================================
echo 初中数学知识图谱可视化系统
echo ========================================
echo.
echo 正在启动本地服务器...
echo 请在浏览器中打开: http://localhost:8080
echo.
echo 按 Ctrl+C 停止服务器
echo ========================================
cd /d "%~dp0visualizer"
python -m http.server 8080
