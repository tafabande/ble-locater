@echo off
setlocal enabledelayedexpansion
title Indoor Positioning - Control Panel Launcher

echo ======================================================================
echo  ⚡ Indoor Positioning — Easy Control Panel Launcher
echo ======================================================================
echo.

cd /d "%~dp0"

if exist "ble-indoor-positioning\.venv\Scripts\python.exe" (
    echo [LAUNCHER] Using project virtual environment Python...
    "ble-indoor-positioning\.venv\Scripts\python.exe" control.py
) else if exist ".venv\Scripts\python.exe" (
    echo [LAUNCHER] Using app-local virtual environment Python...
    ".venv\Scripts\python.exe" control.py
) else if exist "C:\Espressif\tools\python\python.exe" (
    echo [LAUNCHER] Using Espressif tools Python...
    "C:\Espressif\tools\python\python.exe" control.py
) else if exist "C:\Espressif\python_env\idf6.1_py3.11_env\Scripts\python.exe" (
    echo [LAUNCHER] Using IDF Python environment...
    "C:\Espressif\python_env\idf6.1_py3.11_env\Scripts\python.exe" control.py
) else (
    echo [LAUNCHER] Using system Python...
    python control.py
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Control Panel closed with an error code %ERRORLEVEL%.
    pause
)
