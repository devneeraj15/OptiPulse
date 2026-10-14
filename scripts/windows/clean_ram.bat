@echo off
title OptiPulse Instant RAM Cleaner
cd /d "%~dp0..\.."

python -m optipulse --clean-ram
timeout /t 3 >nul
exit
