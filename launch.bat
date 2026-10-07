@echo off
setlocal enabledelayedexpansion
title Indoor Positioning -- Project 1 Research Operations Launcher

echo ======================================================================
echo  Indoor Positioning -- Project 1 Research Operations Launcher
echo ======================================================================
echo.

cd /d "%~dp0"

REM ---------------------------------------------------------------------
REM 1. Detect Best Python Environment
REM ---------------------------------------------------------------------
set "PY_EXE="
if exist "ble-indoor-positioning\.venv\Scripts\python.exe" (
    set "PY_EXE=ble-indoor-positioning\.venv\Scripts\python.exe"
    echo [LAUNCHER] Using project virtual environment: !PY_EXE!
) else if exist ".venv\Scripts\python.exe" (
    set "PY_EXE=.venv\Scripts\python.exe"
    echo [LAUNCHER] Using workspace virtual environment: !PY_EXE!
) else if exist "C:\Espressif\tools\python\python.exe" (
    set "PY_EXE=C:\Espressif\tools\python\python.exe"
    echo [LAUNCHER] Using Espressif tools Python: !PY_EXE!
) else if exist "C:\Espressif\python_env\idf6.1_py3.11_env\Scripts\python.exe" (
    set "PY_EXE=C:\Espressif\python_env\idf6.1_py3.11_env\Scripts\python.exe"
    echo [LAUNCHER] Using IDF Python environment: !PY_EXE!
) else (
    set "PY_EXE=python"
    echo [LAUNCHER] Using system Python: !PY_EXE!
)

REM ---------------------------------------------------------------------
REM 2. Pre-Flight Health Checks: Free Ports (8000, 5005)
REM ---------------------------------------------------------------------
echo [PRE-FLIGHT] Verifying and freeing service ports (8000, 5005)...
"!PY_EXE!" -c "import sys; from pathlib import Path; sys.path.insert(0, str(Path('ble-indoor-positioning').resolve())); from core.config import free_port; free_port(8000); free_port(5005)" 2>nul

REM ---------------------------------------------------------------------
REM 3. Pipeline Dispatcher
REM ---------------------------------------------------------------------
set "TARGET_CMD=%1"

if /i "%TARGET_CMD%"=="help" goto do_help
if /i "%TARGET_CMD%"=="--help" goto do_help
if /i "%TARGET_CMD%"=="-h" goto do_help

if /i "%TARGET_CMD%"=="setup" goto do_setup
if /i "%TARGET_CMD%"=="--setup" goto do_setup
if /i "%TARGET_CMD%"=="flasher" goto do_setup
if /i "%TARGET_CMD%"=="provision" goto do_setup

if /i "%TARGET_CMD%"=="collector" goto do_collector
if /i "%TARGET_CMD%"=="--collector" goto do_collector
if /i "%TARGET_CMD%"=="controller" goto do_collector

if /i "%TARGET_CMD%"=="admin" goto do_admin
if /i "%TARGET_CMD%"=="--admin" goto do_admin
if /i "%TARGET_CMD%"=="telemetry" goto do_admin

if /i "%TARGET_CMD%"=="trainer" goto do_trainer
if /i "%TARGET_CMD%"=="--trainer" goto do_trainer
if /i "%TARGET_CMD%"=="train" goto do_trainer

if /i "%TARGET_CMD%"=="benchmark" goto do_benchmark
if /i "%TARGET_CMD%"=="--benchmark" goto do_benchmark
if /i "%TARGET_CMD%"=="tournament" goto do_benchmark

if /i "%TARGET_CMD%"=="test" goto do_test
if /i "%TARGET_CMD%"=="--test" goto do_test
if /i "%TARGET_CMD%"=="tests" goto do_test

if /i "%TARGET_CMD%"=="headless" goto do_headless
if /i "%TARGET_CMD%"=="--headless" goto do_headless

REM ---------------------------------------------------------------------
REM Default Route: Interactive Operations Console
REM ---------------------------------------------------------------------
echo [LAUNCHER] Starting Operations Console...
"!PY_EXE!" control.py %*
goto handle_exit

:do_setup
echo [PIPELINE] Launching ESP32 Wireless Provisioner and Flasher GUI...
"!PY_EXE!" setup.py
goto handle_exit

:do_collector
echo [PIPELINE] Launching Experiment Controller and Data Collector GUI...
"!PY_EXE!" controller.py
goto handle_exit

:do_admin
echo [PIPELINE] Launching System Administrator and Telemetry GUI...
"!PY_EXE!" admin_gui.py
goto handle_exit

:do_trainer
echo [PIPELINE] Launching AI Model Studio and Trainer GUI...
"!PY_EXE!" trainer_gui.py
goto handle_exit

:do_benchmark
echo [PIPELINE] Launching Model Tournament Benchmark and Performance Studio...
"!PY_EXE!" benchmark_gui.py
goto handle_exit

:do_test
echo [PIPELINE] Running automated test suite with retry recovery...
"!PY_EXE!" control.py --test
goto handle_exit

:do_headless
echo [PIPELINE] Launching headless backend API with watchdog...
shift
"!PY_EXE!" control.py --headless %*
goto handle_exit

:do_help
echo.
echo ======================================================================
echo  Indoor Positioning Pipeline Commands
echo ======================================================================
echo   launch.bat                    Launch interactive Operations Console
echo   launch.bat setup              Launch ESP32 Wireless Provisioner and Flasher GUI
echo   launch.bat collector          Launch Experiment Controller and Collector GUI
echo   launch.bat admin              Launch System Administrator and Telemetry GUI
echo   launch.bat trainer            Launch AI Model Studio and Trainer GUI
echo   launch.bat benchmark          Launch Model Tournament Benchmark & Studio
echo   launch.bat test               Run automated test suite with retries
echo   launch.bat headless           Run backend API in headless CLI mode
echo   launch.bat help               Display this help guide
echo ======================================================================
echo.
exit /b 0


REM ---------------------------------------------------------------------
REM 4. Robust Exit & Retry Handling
REM ---------------------------------------------------------------------
:handle_exit
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ======================================================================
    echo [ERROR] Pipeline step exited with error code %ERRORLEVEL%.
    echo ======================================================================
    echo Options:
    echo   [1] Press any key to close this terminal.
    echo   [2] Re-run the launcher to retry: launch.bat
    echo.
    pause
)
