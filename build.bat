@echo off
title 3D-Print CostCulator
echo.
echo ===============================================
echo    3D Print CostCulator.exe is being built...
echo ===============================================
echo.
py build.py
if %ERRORLEVEL% neq 0 (
    echo.
    echo ERROR: The application could not be built!
    echo.
    echo.
    pause
)
echo.
echo =========================================================================
echo    Done! 3D-Print-Cost-Culator.exe is located in the "release" folder.
echo =========================================================================
echo.
pause