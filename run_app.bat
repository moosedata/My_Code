@echo off

REM 抖音风格视频App启动脚本

REM 设置UTF-8编码
chcp 65001 > nul

REM 检查Python是否安装
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到Python。请先安装Python 3.6或更高版本。
    pause
    exit /b 1
)

REM 检查依赖是否安装
pip show PyQt5 > nul 2>&1
if %errorlevel% neq 0 (
    echo 正在安装依赖包...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo 错误: 依赖包安装失败。
        pause
        exit /b 1
    )
)

REM 启动应用
python main.py

REM 如果应用意外退出，显示错误信息
if %errorlevel% neq 0 (
    echo 应用程序意外退出，错误代码: %errorlevel%
    pause
    exit /b %errorlevel%
)

REM 正常退出
pause