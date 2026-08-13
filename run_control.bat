@echo off
setlocal enabledelayedexpansion
title Hospital Asset Locator - Control Panel Launcher

echo ======================================================================
echo  ⚡ Hospital Asset Locator — Easy Control Panel Launcher
echo ======================================================================
echo.

cd /d "%~dp0"

if exist "ble-indoor-positioning\.venv\Scripts\python.exe" (
    echo [LAUNCHER] Using project virtual environment Python...
    "ble-indoor-positioning\.venv\Scripts\python.exe" control.py
) else (
    echo [LAUNCHER] Using system Python...
    python control.py
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Control Panel closed with an error code %ERRORLEVEL%.
    pause
)
