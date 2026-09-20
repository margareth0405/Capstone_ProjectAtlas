@echo off
setlocal
cd /d "%~dp0"
title ATLAS e-Library

echo Starting ATLAS in quick-start mode...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_atlas.ps1" -UseSQLite -OpenBrowser

if errorlevel 1 (
  echo.
  echo ATLAS could not start. Review the error shown above.
  pause
)
