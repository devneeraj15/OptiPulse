@echo off
title OptiPulse | Hardware Telemetry & RAM Optimizer
cd /d "%~dp0..\.."

echo ================================================================
echo      OPTIPULSE - HARDWARE TELEMETRY & OPTIMIZATION CENTER
echo ================================================================
echo [*] Checking Python environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [-] Python was not found in PATH! Please install Python 3.8+.
    pause
    exit /b 1
)

echo [*] Starting OptiPulse Dashboard Server...
python -m optipulse
pause
