@echo off
setlocal enabledelayedexpansion
title Indoor Positioning — Auto-Host Launch Console

echo ======================================================================
echo  ⚡ Indoor Positioning — Starting Backend Engine ^& Web Dashboard
echo ======================================================================
echo.

cd /d "%~dp0"

if exist "ble-indoor-positioning\.venv\Scripts\python.exe" (
    echo [LAUNCHER] Auto-hosting using virtual environment Python...
    "ble-indoor-positioning\.venv\Scripts\python.exe" control.py --autostart %*
) else if exist ".venv\Scripts\python.exe" (
    echo [LAUNCHER] Auto-hosting using app-local virtual environment Python...
    ".venv\Scripts\python.exe" control.py --autostart %*
) else if exist "C:\Espressif\tools\python\python.exe" (
    echo [LAUNCHER] Auto-hosting using Espressif tools Python...
    "C:\Espressif\tools\python\python.exe" control.py --autostart %*
) else if exist "C:\Espressif\python_env\idf6.1_py3.11_env\Scripts\python.exe" (
    echo [LAUNCHER] Auto-hosting using IDF Python environment...
    "C:\Espressif\python_env\idf6.1_py3.11_env\Scripts\python.exe" control.py --autostart %*
) else (
    echo [LAUNCHER] Auto-hosting using system Python...
    python control.py --autostart %*
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Control room closed with error code %ERRORLEVEL%.
    pause
)
