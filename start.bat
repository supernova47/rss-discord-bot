@echo off
setlocal
title FeedFlow - Ctrl+C to stop
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  where.exe py >nul 2>&1
  if not errorlevel 1 (
    py -3 -m venv .venv
  ) else (
    python -m venv .venv
  )
  if errorlevel 1 goto failed
  .venv\Scripts\python.exe -m pip install --upgrade pip
  if errorlevel 1 goto failed
  .venv\Scripts\python.exe -m pip install -e .
  if errorlevel 1 goto failed
)
echo FeedFlow is running in this window. Press Ctrl+C or close the window to stop it.
.venv\Scripts\python.exe main.py
if errorlevel 1 goto failed
goto done
:failed
echo.
echo Launch failed. Follow the setup steps in README.md.
pause
:done
endlocal

