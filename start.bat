@echo off
title 3D-Print CostCulator
echo.
echo ===============================================
echo    3D-Print CostCulator is starting...
echo ===============================================
echo.
cd src
py main.py
if %ERRORLEVEL% neq 0 (
    echo.
    echo ERROR: The application could not be started!
    echo.
    echo Possible causes:
    echo - Python is not installed or not in PATH
    echo - Dependencies are not installed
    echo.
    echo Suggested solutions:
    echo 1. Install Python from https://python.org
    echo 2. Install dependencies: py -m pip install -r requirements.txt
    echo.
    pause
)