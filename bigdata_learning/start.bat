@echo off
chcp 65001 >nul
title 大数据学习闯关平台
cd /d "%~dp0"

set PY=python
python --version >nul 2>nul
if %errorlevel% neq 0 (
    set PY=py -3
    py -3 --version >nul 2>nul
    if %errorlevel% neq 0 (
        echo [错误] 未检测到 Python。
        echo 请先到 https://www.python.org/downloads/ 安装 Python 3.8 或更高版本，
        echo 安装时勾选 "Add Python to PATH"，然后重新双击本文件。
        pause
        exit /b 1
    )
)

echo.
echo  正在启动 大数据学习闯关平台 ...
echo  浏览器将自动打开 http://127.0.0.1:8321
echo  关闭本窗口即退出程序。
echo.
%PY% app.py
pause
